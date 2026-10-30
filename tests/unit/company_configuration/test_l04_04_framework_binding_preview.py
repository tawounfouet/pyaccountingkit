"""L04-04 — framework binding preview negatives and explicit normative test port.

These tests cannot certify standards, legal eligibility or real IAM authority.
"""

from dataclasses import replace
from datetime import date, datetime

import pytest

from pyaccountingkit.company_configuration.application.accounting_book_frameworks import (
    BookFrameworkPreviewService,
    PreviewBookFrameworkBinding,
)
from pyaccountingkit.company_configuration.application.accounting_books import (
    BookDraftPermissionDenied,
    BookDraftService,
    ProposeBookDraft,
)
from pyaccountingkit.company_configuration.application.ports import TrustedPrincipal
from pyaccountingkit.company_configuration.domain.accounting_books import (
    AccountingBookDraft,
    BookAssignmentCandidate,
    BookAssignmentMissing,
    BookAssignmentPurpose,
    BookCode,
    FrameworkBindingAmbiguous,
    FrameworkBindingMissing,
    FrameworkUnavailable,
    InvalidFrameworkBinding,
    ReferenceFrameworkBindingCandidate,
    preview_reference_framework_binding,
)
from pyaccountingkit.company_configuration.domain.shared.accounting_scope import (
    ConfigurationScope,
)
from pyaccountingkit.company_configuration.domain.shared.effective_interval import (
    EffectiveInterval,
)
from pyaccountingkit.company_configuration.domain.shared.identifiers import (
    AccountingBookId,
    BookAssignmentId,
    CompanyId,
    FrameworkBindingId,
    LegalEntityId,
)
from pyaccountingkit.company_configuration.domain.shared.references import (
    CurrencyCode,
    ReferenceFrameworkRef,
)
from pyaccountingkit.company_configuration.infrastructure import (
    accounting_book_frameworks_memory,
)
from pyaccountingkit.company_configuration.infrastructure import (
    accounting_book_assignments_memory,
)
from pyaccountingkit.company_configuration.infrastructure.accounting_books_memory import (
    MemoryBookAuthorization,
    MemoryBookStore,
    MemoryCompanyEntityMembership,
    memory_book_uow_factory,
)

FrameworkCatalog = accounting_book_frameworks_memory.MemoryBookFrameworkCandidates
NormativeFake = accounting_book_frameworks_memory.MemoryNormativeFrameworkAvailability
MemoryBookAssignmentCandidates = (
    accounting_book_assignments_memory.MemoryBookAssignmentCandidates
)


def book(
    framework="FR-PCG", version="2026", *,
    company=None, entity=None, tenant="tenant-a",
    start=date(2026, 1, 1), end=None,
):
    book_id = AccountingBookId.new()
    return AccountingBookDraft(
        id=book_id,
        scope=ConfigurationScope(
            tenant_id=tenant,
            company_id=company or CompanyId.new(),
            legal_entity_id=entity or LegalEntityId.new(),
            book_id=book_id,
        ),
        code=BookCode("MAIN"),
        label="Demo",
        currency=CurrencyCode("EUR"),
        framework=ReferenceFrameworkRef(framework, version),
        effective=EffectiveInterval(start, end),
        source_ref="rnd:book",
    )


def assignment(b, *, purpose="STATUTORY", start=date(2026, 1, 1), end=None):
    return BookAssignmentCandidate(
        id=BookAssignmentId.new(), scope=b.scope,
        purpose=BookAssignmentPurpose(purpose),
        effective=EffectiveInterval(start, end),
        source_ref="rnd:assignment",
    )


def binding(
    b, *, purpose="STATUTORY", start=date(2026, 1, 1), end=None,
    framework=None, scope=None, binding_id=None,
):
    return ReferenceFrameworkBindingCandidate(
        id=binding_id or FrameworkBindingId.new(),
        scope=scope or b.scope,
        purpose=BookAssignmentPurpose(purpose),
        framework=framework or b.framework,
        effective=EffectiveInterval(start, end),
        source_ref="rnd:binding",
    )


def run(
    b, *, assignments=None, bindings=None, allow_action=True,
    allow_normative=True, membership=True,
):
    store = MemoryBookStore()
    access = MemoryBookAuthorization()
    relation = MemoryCompanyEntityMembership()
    principal = TrustedPrincipal("test-actor", b.scope.tenant_id)
    if membership:
        relation.allow(b.scope)
    access.grant(
        principal=principal, action="book.draft.propose", scope=b.scope
    )
    service = BookDraftService(memory_book_uow_factory(store), access, relation)
    if not membership:
        relation.allow(b.scope)
    service.propose(ProposeBookDraft(b, "R&D proposal"), principal=principal)
    if not membership:
        relation.revoke(b.scope)
    if allow_action:
        access.grant(
            principal=principal, action="book.framework.preview", scope=b.scope
        )
    norm = NormativeFake()
    if allow_normative:
        norm.allow(b.framework, effective=b.effective)
    preview = BookFrameworkPreviewService(
        memory_book_uow_factory(store),
        MemoryBookAssignmentCandidates(
            (assignment(b),) if assignments is None else assignments
        ),
        FrameworkCatalog((binding(b),) if bindings is None else bindings),
        access, relation, norm,
    )
    return preview, principal, norm, store


def request(b, *, purpose="STATUTORY", as_of=date(2026, 5, 1)):
    return PreviewBookFrameworkBinding(
        b.scope, BookAssignmentPurpose(purpose), as_of
    )


@pytest.mark.parametrize(
    ("framework", "version"),
    [("FR-PCG", "2026"), ("IFRS", "2026"), ("OHADA-SYSCOHADA", "AUDCIF-2017")],
)
def test_provisional_norm_pointers_can_be_previewed_without_compliance_claim(
    framework, version,
):
    b = book(framework, version)
    service, principal, _, _ = run(b)
    preview = service.preview(request(b), principal=principal)
    assert preview.book_scope == b.scope
    assert preview.framework == ReferenceFrameworkRef(framework, version)
    assert isinstance(preview.binding_id, FrameworkBindingId)
    assert preview.purpose == BookAssignmentPurpose("STATUTORY")
    assert preview.as_of == date(2026, 5, 1)
    assert not hasattr(preview, "publish")
    assert not hasattr(preview, "post")


def test_no_binding_fails_closed_even_when_draft_has_a_framework():
    b = book()
    service, principal, _, _ = run(b, bindings=())
    with pytest.raises(FrameworkBindingMissing):
        service.preview(request(b), principal=principal)


def test_no_book_assignment_blocks_framework_selection():
    b = book()
    service, principal, _, _ = run(b, assignments=())
    with pytest.raises(BookAssignmentMissing):
        service.preview(request(b), principal=principal)


def test_book_assignment_for_other_purpose_does_not_authorize_framework_preview():
    b = book()
    service, principal, _, _ = run(b, assignments=(assignment(b, purpose="GROUP"),))
    with pytest.raises(BookAssignmentMissing):
        service.preview(request(b), principal=principal)


def test_normative_registry_default_denies_even_when_binding_exists():
    b = book()
    service, principal, _, _ = run(b, allow_normative=False)
    with pytest.raises(FrameworkUnavailable):
        service.preview(request(b), principal=principal)


def test_normative_registry_does_not_fallback_to_other_version_or_expired_interval():
    b = book()
    service, principal, norm, _ = run(b, allow_normative=False)
    norm.allow(
        ReferenceFrameworkRef("FR-PCG", "2025"),
        effective=EffectiveInterval(date(2026, 1, 1)),
    )
    with pytest.raises(FrameworkUnavailable):
        service.preview(request(b), principal=principal)
    norm.allow(b.framework, effective=EffectiveInterval(
        date(2026, 1, 1), date(2026, 4, 1)
    ))
    with pytest.raises(FrameworkUnavailable):
        service.preview(request(b), principal=principal)


def test_explicit_framework_ref_must_equal_draft_ref_in_this_rnd_slice():
    b = book()
    foreign = binding(b, framework=ReferenceFrameworkRef("IFRS", "2026"))
    service, principal, _, _ = run(b, bindings=(foreign,))
    with pytest.raises(InvalidFrameworkBinding, match="conflicts with book"):
        service.preview(request(b), principal=principal)


def test_two_binding_candidates_same_purpose_and_date_are_ambiguous():
    b = book()
    service, principal, _, _ = run(
        b, bindings=(binding(b), binding(b, start=date(2026, 3, 1))),
    )
    with pytest.raises(FrameworkBindingAmbiguous):
        service.preview(request(b), principal=principal)


def test_duplicate_binding_id_is_ambiguous_even_for_nonoverlapping_periods():
    b = book()
    first = binding(b, end=date(2026, 7, 1))
    second = binding(b, binding_id=first.id, start=date(2026, 7, 1))
    with pytest.raises(FrameworkBindingAmbiguous):
        preview_reference_framework_binding(
            book=b, scope=b.scope, purpose=BookAssignmentPurpose("STATUTORY"),
            as_of=date(2026, 5, 1), bindings=(first, second),
        )


def test_half_open_adjacent_bindings_select_correct_identity():
    b = book()
    first = binding(b, end=date(2026, 7, 1))
    second = binding(b, start=date(2026, 7, 1))
    service, principal, _, _ = run(b, bindings=(first, second))
    assert service.preview(
        request(b, as_of=date(2026, 6, 30)), principal=principal
    ).binding_id == first.id
    assert service.preview(
        request(b, as_of=date(2026, 7, 1)), principal=principal
    ).binding_id == second.id


def test_other_purpose_binding_not_implicit_default():
    b = book()
    service, principal, _, _ = run(
        b, bindings=(binding(b, purpose="MANAGEMENT"),)
    )
    with pytest.raises(FrameworkBindingMissing):
        service.preview(request(b), principal=principal)


def test_different_purposes_at_same_date_are_independent():
    b = book()
    service, principal, _, _ = run(
        b,
        assignments=(assignment(b), assignment(b, purpose="GROUP")),
        bindings=(binding(b), binding(b, purpose="GROUP")),
    )
    assert service.preview(request(b), principal=principal).purpose.value == "STATUTORY"
    assert service.preview(
        request(b, purpose="GROUP"), principal=principal
    ).purpose.value == "GROUP"


def test_missing_auth_scope_and_wrong_principal_are_denied_before_catalog_read():
    b = book()
    service, principal, _, store = run(b, allow_action=False)
    with pytest.raises(BookDraftPermissionDenied):
        service.preview(request(b), principal=principal)
    with pytest.raises(BookDraftPermissionDenied, match="Cross-tenant"):
        service.preview(
            request(b), principal=TrustedPrincipal("test-actor", "tenant-b")
        )
    with pytest.raises(BookDraftPermissionDenied, match="Verified"):
        service.preview(request(b), principal="unsafe-actor")
    assert store.snapshot() == (b,)


def test_revoked_fake_company_membership_blocks_preview():
    b = book()
    service, principal, _, _ = run(b, membership=False)
    with pytest.raises(BookDraftPermissionDenied):
        service.preview(request(b), principal=principal)


def test_orphan_binding_and_foreign_book_scope_fail_closed():
    b = book()
    foreign = binding(b, scope=replace(b.scope, company_id=CompanyId.new()))
    service, principal, _, _ = run(b, bindings=(foreign,))
    # The fixture filters foreign scopes, hence no applicable binding.
    with pytest.raises(FrameworkBindingMissing):
        service.preview(request(b), principal=principal)


def test_malicious_framework_reader_cannot_leak_foreign_scope():
    b = book()
    _, principal, _, store = run(b)
    access = MemoryBookAuthorization()
    access.grant(
        principal=principal, action="book.framework.preview", scope=b.scope
    )
    membership = MemoryCompanyEntityMembership()
    membership.allow(b.scope)

    class ForeignReader:
        def list_for_book(self, scope):
            return (binding(b, scope=replace(b.scope, tenant_id="tenant-b")),)

    malicious = BookFrameworkPreviewService(
        memory_book_uow_factory(store),
        MemoryBookAssignmentCandidates((assignment(b),)),
        ForeignReader(), access, membership, NormativeFake(),
    )
    with pytest.raises(InvalidFrameworkBinding, match="crosses"):
        malicious.preview(request(b), principal=principal)


def test_expired_or_out_of_range_binding_fails_without_silent_fallback():
    b = book(start=date(2026, 2, 1), end=date(2027, 1, 1))
    outside = binding(b, start=date(2026, 1, 1), end=date(2027, 1, 1))
    with pytest.raises(InvalidFrameworkBinding, match="beyond"):
        outside.require_draft_compatibility(b)
    unbounded = binding(b, start=date(2026, 2, 1), end=None)
    with pytest.raises(InvalidFrameworkBinding, match="beyond"):
        unbounded.require_draft_compatibility(b)


def test_invalid_identifier_scope_date_provenance_and_typed_reference():
    b = book()
    with pytest.raises(InvalidFrameworkBinding):
        ReferenceFrameworkBindingCandidate(
            id=b.id, scope=b.scope, purpose=BookAssignmentPurpose("STATUTORY"),
            framework=b.framework, effective=b.effective, source_ref="rnd:test",
        )
    with pytest.raises(InvalidFrameworkBinding):
        replace(binding(b), framework="IFRS")
    with pytest.raises(InvalidFrameworkBinding):
        replace(binding(b), source_ref=" not canonical ")
    with pytest.raises(InvalidFrameworkBinding):
        request(b, as_of=datetime(2026, 1, 1))
    with pytest.raises(InvalidFrameworkBinding):
        PreviewBookFrameworkBinding(b.scope, "STATUTORY", date(2026, 1, 1))
    with pytest.raises(InvalidFrameworkBinding):
        PreviewBookFrameworkBinding(
            replace(b.scope, book_id=None),
            BookAssignmentPurpose("STATUTORY"), date(2026, 1, 1),
        )


def test_no_database_or_live_normative_provider_is_imported():
    import ast
    from pathlib import Path

    from pyaccountingkit.company_configuration.application import (
        accounting_book_frameworks,
    )
    from pyaccountingkit.company_configuration.infrastructure import (
        accounting_book_frameworks_memory,
    )

    for module in (accounting_book_frameworks, accounting_book_frameworks_memory):
        text = Path(module.__file__).read_text(encoding="utf-8")
        imports = {
            alias.name for node in ast.walk(ast.parse(text))
            if isinstance(node, ast.Import) for alias in node.names
        }
        assert not ({"psycopg", "sqlalchemy", "requests", "httpx"} & imports)
        assert "organization_issuer_gateway" not in text
    assert not hasattr(BookFrameworkPreviewService, "activate")
    assert not hasattr(BookFrameworkPreviewService, "post")
