"""L04-07 synthetic dependency declarations and read receipt invariants.

References are NOT resolved against real chart, calendar, policy or IAM systems.
"""

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, date, datetime

import pytest

from pyaccountingkit.company_configuration.application.accounting_book_candidate_snapshots import (
    BookCandidateSnapshotPreviewService,
    PreviewBookConfigurationSnapshot,
)
from pyaccountingkit.company_configuration.application.accounting_book_dependency_receipts import (
    BookDependencyReadReceiptService,
    PreviewBookDependencyReadReceipt,
)
from pyaccountingkit.company_configuration.application.accounting_books import (
    BookDraftPermissionDenied,
)
from pyaccountingkit.company_configuration.application.ports import TrustedPrincipal
from pyaccountingkit.company_configuration.domain.accounting_books import (
    AccountingBookDraft,
    BookAssignmentCandidate,
    BookAssignmentPurpose,
    BookCode,
    BookConfigurationCandidateVersion,
    BookDependencyAmbiguous,
    BookDependencyClaim,
    BookDependencyDeclaration,
    BookDependencyDigestMismatch,
    BookDependencyKind,
    BookDependencyMissing,
    BookDependencyRef,
    BookDependencyUnavailable,
    CandidateSnapshotDigestMismatch,
    InvalidBookDependency,
    NormativeDeclaration,
    NormativeReferenceStatement,
    NormativeSourceCode,
    ReferenceFrameworkBindingCandidate,
    preview_book_dependency_completeness,
)
from pyaccountingkit.company_configuration.domain.shared.accounting_scope import (
    ConfigurationScope,
)
from pyaccountingkit.company_configuration.domain.shared.effective_interval import (
    EffectiveInterval,
    KnowledgeInterval,
)
from pyaccountingkit.company_configuration.domain.shared.identifiers import (
    AccountingBookId,
    BookAssignmentId,
    BookCandidateVersionId,
    BookDependencyClaimId,
    CompanyId,
    FrameworkBindingId,
    LegalEntityId,
    NormativeStatementId,
)
from pyaccountingkit.company_configuration.domain.shared.references import (
    CurrencyCode,
    ReferenceFrameworkRef,
)
from pyaccountingkit.company_configuration.infrastructure import (
    accounting_book_candidate_snapshots_memory,
    accounting_book_dependency_receipts_memory,
    accounting_book_normative_history_memory,
)
from pyaccountingkit.company_configuration.infrastructure.accounting_books_memory import (
    MemoryBookAuthorization,
    MemoryCompanyEntityMembership,
)

VERSION_MEMORY = accounting_book_candidate_snapshots_memory.MemoryBookCandidateVersions
CLAIM_MEMORY = accounting_book_dependency_receipts_memory.MemoryBookDependencyClaims
NORM_MEMORY = accounting_book_normative_history_memory.MemoryNormativeReferenceClaims
SOURCE = NormativeSourceCode("TEST_REGISTRY")
START = datetime(2026, 1, 1, tzinfo=UTC)
CORRECTION = datetime(2026, 3, 1, tzinfo=UTC)
QUERY_DATE = date(2026, 2, 15)
KNOWN = datetime(2026, 2, 1, tzinfo=UTC)


def make_version(*, knowledge=None, book=None, version_id=None):
    book_id = AccountingBookId.new() if book is None else book.id
    if book is None:
        book = AccountingBookDraft(
            id=book_id,
            scope=ConfigurationScope(
                "tenant-a", CompanyId.new(), LegalEntityId.new(), book_id
            ),
            code=BookCode("MAIN"), label="Test book",
            currency=CurrencyCode("EUR"),
            framework=ReferenceFrameworkRef("FR-PCG", "2026"),
            effective=EffectiveInterval(date(2026, 1, 1)),
            source_ref="rnd:book",
        )
    purpose = BookAssignmentPurpose("STATUTORY")
    return BookConfigurationCandidateVersion(
        id=version_id or BookCandidateVersionId.new(),
        book=book,
        assignment=BookAssignmentCandidate(
            id=BookAssignmentId.new(), scope=book.scope, purpose=purpose,
            effective=book.effective, source_ref="rnd:assignment",
        ),
        binding=ReferenceFrameworkBindingCandidate(
            id=FrameworkBindingId.new(), scope=book.scope, purpose=purpose,
            framework=book.framework, effective=book.effective,
            source_ref="rnd:framework",
        ),
        purpose=purpose, effective=book.effective,
        knowledge=knowledge or KnowledgeInterval(START),
        source_ref="rnd:version",
    )


def norm_claim(version, *, knowledge=None):
    return NormativeReferenceStatement(
        id=NormativeStatementId.new(),
        source=SOURCE, framework=version.book.framework,
        effective=version.effective,
        knowledge=knowledge or version.knowledge,
        declaration=NormativeDeclaration.DECLARED_AVAILABLE,
        source_ref="rnd:unverified-norm",
    )


def dep(version, kind, *, knowledge=None, declaration=None, ref=None, scope=None,
        version_id=None, claim_id=None, effective=None):
    return BookDependencyClaim(
        id=claim_id or BookDependencyClaimId.new(),
        candidate_version_id=version_id or version.id,
        scope=scope or version.scope,
        kind=kind,
        reference=ref or BookDependencyRef(f"{kind.value}_V1", "1"),
        effective=effective or version.effective,
        knowledge=knowledge or version.knowledge,
        declaration=declaration or BookDependencyDeclaration.DECLARED_AVAILABLE,
        source_ref="rnd:unverified-dependency",
    )


def complete(version):
    return tuple(dep(version, kind) for kind in BookDependencyKind)


def service(versions, norms, dependencies, *, allow=True, member=True):
    base = versions[0]
    auth = MemoryBookAuthorization()
    memberships = MemoryCompanyEntityMembership()
    principal = TrustedPrincipal("rnd-reviewer", base.scope.tenant_id)
    if member:
        memberships.allow(base.scope)
    if allow:
        for action in ("book.candidate_snapshot.preview", "book.dependency_receipt.preview"):
            auth.grant(principal=principal, action=action, scope=base.scope)
    snapshots = BookCandidateSnapshotPreviewService(
        VERSION_MEMORY(tuple(versions)), NORM_MEMORY(tuple(norms)),
        auth, memberships,
    )
    receipt_service = BookDependencyReadReceiptService(
        snapshots, CLAIM_MEMORY(tuple(dependencies)), auth, memberships,
    )
    return receipt_service, principal, auth, memberships


def request(version, *, as_of=QUERY_DATE, known_at=KNOWN):
    return PreviewBookDependencyReadReceipt(
        PreviewBookConfigurationSnapshot(
            version.scope, version.purpose, SOURCE, as_of, known_at
        )
    )


def test_complete_candidate_receipt_binds_exact_version_and_norm_snapshot():
    version = make_version()
    s, principal, _, _ = service((version,), (norm_claim(version),), complete(version))
    receipt = s.preview(request(version), principal=principal)
    assert tuple(x.kind for x in receipt.selected) == tuple(BookDependencyKind)
    assert receipt.snapshot.version.id == version.id
    assert receipt.content_digest.startswith("sha256:")
    assert len(receipt.content_digest) == 71
    assert receipt.snapshot.content_digest in str(receipt.canonical_payload())
    receipt.verify_integrity()
    assert not hasattr(receipt, "publish")
    assert not hasattr(receipt, "post")


def test_receipt_deterministic_under_shuffled_source_catalog():
    version = make_version()
    claims = complete(version)
    norm = norm_claim(version)
    s, principal, _, _ = service((version,), (norm,), claims)
    a = s.preview(request(version), principal=principal)
    s, principal, _, _ = service((version,), (norm,), tuple(reversed(claims)))
    b = s.preview(request(version), principal=principal)
    assert a.content_digest == b.content_digest
    assert a.canonical_payload() == b.canonical_payload()


@pytest.mark.parametrize("missing_kind", tuple(BookDependencyKind))
def test_each_missing_required_dependency_rejects(missing_kind):
    version = make_version()
    claims = tuple(c for c in complete(version) if c.kind != missing_kind)
    s, principal, _, _ = service((version,), (norm_claim(version),), claims)
    with pytest.raises(BookDependencyMissing, match=missing_kind.value):
        s.preview(request(version), principal=principal)


def test_absent_all_claims_rejected_even_with_normative_source():
    version = make_version()
    s, principal, _, _ = service((version,), (norm_claim(version),), ())
    with pytest.raises(BookDependencyMissing):
        s.preview(request(version), principal=principal)


def test_unavailable_dependency_rejected_even_when_four_others_declared():
    version = make_version()
    claims = complete(version)
    changed = replace(
        claims[1], declaration=BookDependencyDeclaration.DECLARED_UNAVAILABLE
    )
    s, principal, _, _ = service(
        (version,), (norm_claim(version),), (claims[0], changed, *claims[2:])
    )
    with pytest.raises(BookDependencyUnavailable):
        s.preview(request(version), principal=principal)


def test_overlapping_same_slot_is_ambiguous_not_last_wins():
    version = make_version()
    claims = complete(version)
    extra = dep(version, BookDependencyKind.CHART)
    s, principal, _, _ = service(
        (version,), (norm_claim(version),), (*claims, extra)
    )
    with pytest.raises(BookDependencyAmbiguous):
        s.preview(request(version), principal=principal)


def test_duplicate_claim_id_invalid_even_if_not_active_at_current_date():
    version = make_version()
    claims = complete(version)
    duplicate = dep(
        version, BookDependencyKind.CALENDAR, claim_id=claims[0].id,
        effective=EffectiveInterval(date(2026, 7, 1)),
    )
    s, principal, _, _ = service(
        (version,), (norm_claim(version),), (*claims, duplicate)
    )
    with pytest.raises(BookDependencyAmbiguous, match="claim ID"):
        s.preview(request(version), principal=principal)


def test_missing_claim_due_to_effective_date_is_not_defaulted():
    version = make_version()
    claims = complete(version)
    late = dep(
        version, BookDependencyKind.CHART,
        effective=EffectiveInterval(date(2026, 7, 1)),
    )
    changed = (late, *claims[1:])
    s, principal, _, _ = service((version,), (norm_claim(version),), changed)
    with pytest.raises(BookDependencyMissing, match="CHART"):
        s.preview(request(version), principal=principal)


def test_missing_claim_due_to_known_at_is_not_future_fallback():
    version = make_version()
    claims = complete(version)
    late = dep(
        version, BookDependencyKind.CHART,
        knowledge=KnowledgeInterval(CORRECTION),
    )
    s, principal, _, _ = service(
        (version,), (norm_claim(version),), (late, *claims[1:])
    )
    with pytest.raises(BookDependencyMissing, match="CHART"):
        s.preview(request(version), principal=principal)


def test_foreign_entity_tenant_and_candidate_version_fail_closed():
    version = make_version()
    snap_service, actor, _, _ = service(
        (version,), (norm_claim(version),), complete(version)
    )
    original = snap_service.preview(request(version), principal=actor).snapshot
    for foreign in (
        replace(
            complete(version)[0],
            scope=replace(version.scope, legal_entity_id=LegalEntityId.new()),
        ),
        replace(
            complete(version)[0],
            scope=replace(version.scope, tenant_id="tenant-b"),
        ),
        replace(
            complete(version)[0],
            candidate_version_id=BookCandidateVersionId.new(),
        ),
    ):
        with pytest.raises(InvalidBookDependency, match="Foreign"):
            preview_book_dependency_completeness(
                snapshot=original, claims=(foreign, *complete(version)[1:])
            )


def test_digest_tampering_in_selected_claim_is_detected():
    version = make_version()
    s, actor, _, _ = service((version,), (norm_claim(version),), complete(version))
    receipt = s.preview(request(version), principal=actor)
    object.__setattr__(receipt.selected[0], "source_ref", "tampered")
    with pytest.raises(BookDependencyDigestMismatch):
        receipt.verify_integrity()


def test_digest_tampering_in_snapshot_blocks_receipt_integrity():
    version = make_version()
    s, actor, _, _ = service((version,), (norm_claim(version),), complete(version))
    receipt = s.preview(request(version), principal=actor)
    object.__setattr__(receipt.snapshot, "content_digest", "sha256:" + "0" * 64)
    with pytest.raises(CandidateSnapshotDigestMismatch):
        receipt.verify_integrity()


def test_frozen_receipt_cannot_be_normally_mutated():
    version = make_version()
    s, actor, _, _ = service((version,), (norm_claim(version),), complete(version))
    receipt = s.preview(request(version), principal=actor)
    with pytest.raises(FrozenInstanceError):
        receipt.content_digest = "bad"


def test_historical_restatement_pins_distinct_dependency_receipts():
    first = make_version(knowledge=KnowledgeInterval(START, CORRECTION))
    revised_book = first.book.rename("Revised", expected_revision=1, reason="Correction")
    second = make_version(
        book=revised_book, knowledge=KnowledgeInterval(CORRECTION)
    )
    norms = (norm_claim(first), norm_claim(second))
    claims = (*complete(first), *complete(second))
    s, actor, _, _ = service((first, second), norms, claims)
    before = s.preview(request(first, known_at=KNOWN), principal=actor)
    after = s.preview(request(first, known_at=CORRECTION), principal=actor)
    assert before.snapshot.version.id == first.id
    assert after.snapshot.version.id == second.id
    assert before.content_digest != after.content_digest
    before.verify_integrity()
    after.verify_integrity()


def test_default_deny_on_missing_grants_or_revoked_membership():
    version = make_version()
    norm = norm_claim(version)
    s, actor, _, _ = service((version,), (norm,), complete(version), allow=False)
    with pytest.raises(BookDraftPermissionDenied):
        s.preview(request(version), principal=actor)
    s, actor, _, _ = service((version,), (norm,), complete(version), member=False)
    with pytest.raises(BookDraftPermissionDenied):
        s.preview(request(version), principal=actor)


def test_both_distinct_read_actions_are_mandatory():
    version = make_version()
    s, actor, auth, _ = service(
        (version,), (norm_claim(version),), complete(version)
    )
    auth.revoke(
        principal=actor, action="book.candidate_snapshot.preview",
        scope=version.scope,
    )
    with pytest.raises(BookDraftPermissionDenied):
        s.preview(request(version), principal=actor)
    auth.grant(
        principal=actor, action="book.candidate_snapshot.preview",
        scope=version.scope,
    )
    auth.revoke(
        principal=actor, action="book.dependency_receipt.preview",
        scope=version.scope,
    )
    with pytest.raises(BookDraftPermissionDenied):
        s.preview(request(version), principal=actor)


def test_cross_tenant_and_raw_principals_are_rejected():
    version = make_version()
    s, _, _, _ = service(
        (version,), (norm_claim(version),), complete(version)
    )
    with pytest.raises(BookDraftPermissionDenied, match="Cross-tenant"):
        s.preview(
            request(version), principal=TrustedPrincipal("rnd-reviewer", "tenant-b")
        )
    with pytest.raises(BookDraftPermissionDenied, match="Verified"):
        s.preview(request(version), principal="raw-user")


def test_malicious_dependency_reader_cannot_leak_foreign_version():
    version = make_version()
    norm = norm_claim(version)
    s, actor, auth, memberships = service(
        (version,), (norm,), complete(version)
    )

    class MaliciousReader:
        def list_for_version(self, scope, candidate_version_id):
            return (
                dep(
                    version, BookDependencyKind.CHART,
                    version_id=BookCandidateVersionId.new(),
                ),
                *complete(version)[1:],
            )

    snapshots = BookCandidateSnapshotPreviewService(
        VERSION_MEMORY((version,)), NORM_MEMORY((norm,)), auth, memberships
    )
    malicious = BookDependencyReadReceiptService(
        snapshots, MaliciousReader(), auth, memberships
    )
    with pytest.raises(InvalidBookDependency, match="Foreign"):
        malicious.preview(request(version), principal=actor)


def test_fixture_is_read_only_not_an_authority():
    version = make_version()
    mem = CLAIM_MEMORY(complete(version))
    assert len(mem.list_for_version(version.scope, version.id)) == 5
    assert mem.list_for_version(version.scope, BookCandidateVersionId.new()) == ()
    assert not hasattr(mem, "publish")
    assert not hasattr(mem, "save")
    assert not hasattr(BookDependencyReadReceiptService, "post")


@pytest.mark.parametrize("code,edition", [("", "1"), ("lowercase", "1"), ("PCG", "")])
def test_dependency_reference_requires_explicit_canonical_code_and_version(code, edition):
    with pytest.raises(InvalidBookDependency):
        BookDependencyRef(code, edition)


def test_dependency_claims_require_typed_identity_and_declaration():
    version = make_version()
    first = complete(version)[0]
    with pytest.raises(InvalidBookDependency):
        replace(first, id=version.book.id)
    with pytest.raises(InvalidBookDependency):
        replace(first, declaration="AVAILABLE")
    with pytest.raises(InvalidBookDependency):
        replace(first, reference="CHART@1")


def test_rejected_malformed_query_and_non_tuple_claim_catalog():
    version = make_version()
    with pytest.raises(InvalidBookDependency):
        PreviewBookDependencyReadReceipt("raw-query")
    s, actor, auth, members = service(
        (version,), (norm_claim(version),), complete(version)
    )
    snapshots = BookCandidateSnapshotPreviewService(
        VERSION_MEMORY((version,)), NORM_MEMORY((norm_claim(version),)),
        auth, members,
    )
    class WrongReader:
        def list_for_version(self, scope, version_id):
            return list(complete(version))
    fail = BookDependencyReadReceiptService(snapshots, WrongReader(), auth, members)
    with pytest.raises(InvalidBookDependency, match="tuple"):
        fail.preview(request(version), principal=actor)


def test_architecture_has_no_postgres_orm_or_live_iam_gateway_dependency():
    import ast
    from pathlib import Path

    from pyaccountingkit.company_configuration.application import (
        accounting_book_dependency_receipts,
    )
    from pyaccountingkit.company_configuration.infrastructure import (
        accounting_book_dependency_receipts_memory,
    )

    for module in (accounting_book_dependency_receipts, accounting_book_dependency_receipts_memory):
        text = Path(module.__file__).read_text(encoding="utf-8")
        imports = {
            item.name for node in ast.walk(ast.parse(text))
            if isinstance(node, ast.Import) for item in node.names
        }
        assert not ({"psycopg", "sqlalchemy", "requests", "httpx"} & imports)
        assert "organization_issuer_gateway" not in text
