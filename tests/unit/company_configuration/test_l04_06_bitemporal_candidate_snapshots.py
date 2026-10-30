"""L04-06 adversarial tests: bitemporal candidate versions and SHA-256 receipts.

Neither signatures nor durable publishing/IAM/SQL posting are implemented.
"""

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, date, datetime, timedelta, timezone

import pytest

from pyaccountingkit.company_configuration.application.accounting_book_candidate_snapshots import (
    BookCandidateSnapshotPreviewService,
    PreviewBookConfigurationSnapshot,
)
from pyaccountingkit.company_configuration.application.accounting_books import (
    BookDraftPermissionDenied,
)
from pyaccountingkit.company_configuration.application.ports import TrustedPrincipal
from pyaccountingkit.company_configuration.domain.accounting_books import (
    AccountingBookDraft,
    BookAssignmentCandidate,
    BookAssignmentPurpose,
    BookCandidateVersionAmbiguous,
    BookCandidateVersionMissing,
    BookCode,
    BookConfigurationCandidateSnapshot,
    BookConfigurationCandidateVersion,
    CandidateSnapshotDigestMismatch,
    InvalidBookCandidateVersion,
    InvalidNormativeStatement,
    NormativeDeclaration,
    NormativeReferenceStatement,
    NormativeSourceCode,
    NormativeStatementMissing,
    NormativeStatementUnavailable,
    ReferenceFrameworkBindingCandidate,
    select_book_candidate_version,
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
    accounting_book_normative_history_memory,
)
from pyaccountingkit.company_configuration.infrastructure.accounting_books_memory import (
    MemoryBookAuthorization,
    MemoryCompanyEntityMembership,
)

VersionFixture = accounting_book_candidate_snapshots_memory.MemoryBookCandidateVersions
ClaimsFixture = accounting_book_normative_history_memory.MemoryNormativeReferenceClaims

SOURCE = NormativeSourceCode("TEST_REGISTRY")
DAY = date(2026, 2, 15)
JAN = datetime(2026, 1, 1, tzinfo=UTC)
FEB = datetime(2026, 2, 1, tzinfo=UTC)
MAR = datetime(2026, 3, 1, tzinfo=UTC)


def book(
    *, book_id=None, company=None, entity=None, tenant="tenant-a",
    framework="FR-PCG", edition="2026", name="Original"
):
    identity = book_id or AccountingBookId.new()
    return AccountingBookDraft(
        id=identity,
        scope=ConfigurationScope(
            tenant_id=tenant,
            company_id=company or CompanyId.new(),
            legal_entity_id=entity or LegalEntityId.new(),
            book_id=identity,
        ),
        code=BookCode("MAIN"),
        label=name,
        currency=CurrencyCode("EUR"),
        framework=ReferenceFrameworkRef(framework, edition),
        effective=EffectiveInterval(date(2026, 1, 1)),
        source_ref="l04:book-intent",
    )


def assignment(b, *, purpose=None, scope=None):
    return BookAssignmentCandidate(
        id=BookAssignmentId.new(),
        scope=scope or b.scope,
        purpose=purpose or BookAssignmentPurpose("STATUTORY"),
        effective=b.effective,
        source_ref="l04:assignment-intent",
    )


def binding(b, *, purpose=None, framework=None):
    return ReferenceFrameworkBindingCandidate(
        id=FrameworkBindingId.new(),
        scope=b.scope,
        purpose=purpose or BookAssignmentPurpose("STATUTORY"),
        framework=framework or b.framework,
        effective=b.effective,
        source_ref="l04:framework-intent",
    )


def version(
    b, *, revision_id=None, knowledge=None, effective=None,
    link=None, ref_binding=None, purpose=None, source_ref="l04:version-intent"
):
    return BookConfigurationCandidateVersion(
        id=revision_id or BookCandidateVersionId.new(),
        book=b,
        assignment=link or assignment(b),
        binding=ref_binding or binding(b),
        purpose=purpose or BookAssignmentPurpose("STATUTORY"),
        effective=effective or b.effective,
        knowledge=knowledge or KnowledgeInterval(JAN),
        source_ref=source_ref,
    )


def statement(
    b, *, knowledge=None, declaration=NormativeDeclaration.DECLARED_AVAILABLE,
    source=SOURCE
):
    return NormativeReferenceStatement(
        id=NormativeStatementId.new(),
        source=source,
        framework=b.framework,
        effective=b.effective,
        knowledge=knowledge or KnowledgeInterval(JAN),
        declaration=declaration,
        source_ref="unverified:test-declaration",
    )


def scenario(versions, claims, *, grant=True, membership=True):
    assert versions
    b = versions[0].book
    auth = MemoryBookAuthorization()
    members = MemoryCompanyEntityMembership()
    actor = TrustedPrincipal("rnd-actor", b.scope.tenant_id)
    if grant:
        auth.grant(
            principal=actor, action="book.candidate_snapshot.preview", scope=b.scope
        )
    if membership:
        members.allow(b.scope)
    service = BookCandidateSnapshotPreviewService(
        VersionFixture(tuple(versions)), ClaimsFixture(tuple(claims)), auth, members
    )
    return service, actor, auth, members


def query(b, *, known_at=FEB, as_of=DAY, source=SOURCE):
    return PreviewBookConfigurationSnapshot(
        scope=b.scope, purpose=BookAssignmentPurpose("STATUTORY"),
        source=source, as_of=as_of, known_at=known_at
    )


def test_candidate_snapshot_has_typed_ids_and_deterministic_digest():
    b = book()
    v = version(b)
    norm = statement(b)
    svc, actor, _, _ = scenario((v,), (norm,))
    one = svc.preview(query(b), principal=actor)
    two = svc.preview(query(b), principal=actor)
    assert one.content_digest == two.content_digest
    assert one.content_digest.startswith("sha256:")
    assert len(one.content_digest) == len("sha256:") + 64
    assert one.version.content_digest == v.content_digest
    assert one.version.id == v.id
    assert one.version.scope == b.scope
    one.verify_integrity()
    two.verify_integrity()
    assert not hasattr(one, "publish")
    assert not hasattr(one, "post")


def test_originally_known_then_restated_selects_different_frozen_book_revision():
    before = book()
    after = before.rename("Revised", expected_revision=1, reason="Correction")
    v1 = version(before, knowledge=KnowledgeInterval(JAN, MAR))
    v2 = version(after, knowledge=KnowledgeInterval(MAR))
    old_claim = statement(before, knowledge=KnowledgeInterval(JAN, MAR))
    new_claim = statement(after, knowledge=KnowledgeInterval(MAR))
    svc, actor, _, _ = scenario((v1, v2), (old_claim, new_claim))
    original = svc.preview(query(before, known_at=FEB), principal=actor)
    restated = svc.preview(query(before, known_at=MAR), principal=actor)
    assert original.version.book.label == "Original"
    assert restated.version.book.label == "Revised"
    assert original.version.book.revision == 1
    assert restated.version.book.revision == 2
    assert original.version.id != restated.version.id
    assert original.content_digest != restated.content_digest
    original.verify_integrity()
    restated.verify_integrity()


def test_future_recorded_candidate_is_not_available_at_earlier_known_at():
    b = book()
    v = version(b, knowledge=KnowledgeInterval(MAR))
    with pytest.raises(BookCandidateVersionMissing):
        select_book_candidate_version(
            scope=b.scope, purpose=v.purpose, as_of=DAY, known_at=FEB,
            versions=(v,)
        )


def test_future_effective_candidate_does_not_rewrite_earlier_business_date():
    b = book()
    v = version(b, effective=EffectiveInterval(date(2026, 7, 1)))
    with pytest.raises(BookCandidateVersionMissing):
        select_book_candidate_version(
            scope=b.scope, purpose=v.purpose, as_of=DAY, known_at=MAR,
            versions=(v,)
        )


def test_overlapping_bitemporal_candidate_revisions_are_ambiguous():
    b = book()
    first = version(b)
    second = version(b, knowledge=KnowledgeInterval(FEB))
    with pytest.raises(BookCandidateVersionAmbiguous):
        select_book_candidate_version(
            scope=b.scope, purpose=first.purpose, as_of=DAY, known_at=MAR,
            versions=(first, second),
        )


def test_duplicate_version_id_rejected_even_in_disjoint_knowledge_windows():
    b = book()
    first = version(b, knowledge=KnowledgeInterval(JAN, MAR))
    second = version(
        b, revision_id=first.id, knowledge=KnowledgeInterval(MAR)
    )
    with pytest.raises(BookCandidateVersionAmbiguous):
        select_book_candidate_version(
            scope=b.scope, purpose=first.purpose, as_of=DAY, known_at=FEB,
            versions=(first, second),
        )


def test_multiple_versions_of_other_purpose_cannot_be_fallback():
    b = book()
    group = BookAssignmentPurpose("GROUP")
    v = version(b, purpose=group, link=assignment(b, purpose=group),
                ref_binding=binding(b, purpose=group))
    with pytest.raises(BookCandidateVersionMissing):
        select_book_candidate_version(
            scope=b.scope, purpose=BookAssignmentPurpose("STATUTORY"),
            as_of=DAY, known_at=FEB, versions=(v,),
        )


def test_cross_company_entity_and_tenant_catalog_leaks_fail_closed():
    b = book()
    for altered in (
        book(company=CompanyId.new(), entity=b.scope.legal_entity_id),
        book(company=b.scope.company_id, entity=LegalEntityId.new()),
        book(tenant="tenant-b"),
    ):
        with pytest.raises(InvalidBookCandidateVersion, match="foreign scope"):
            select_book_candidate_version(
                scope=b.scope, purpose=BookAssignmentPurpose("STATUTORY"),
                as_of=DAY, known_at=FEB, versions=(version(altered),),
            )


def test_out_of_book_or_assignment_validity_cannot_be_sealed():
    b = book()
    future = EffectiveInterval(date(2025, 12, 1))
    with pytest.raises(InvalidBookCandidateVersion, match="escapes"):
        version(b, effective=future)
    short = replace(
        assignment(b), effective=EffectiveInterval(
            date(2026, 1, 1), date(2026, 4, 1)
        ),
    )
    with pytest.raises(InvalidBookCandidateVersion, match="escapes"):
        version(b, link=short, effective=EffectiveInterval(date(2026, 1, 1)))


def test_component_scope_framework_and_purpose_disagreement_is_rejected():
    b = book()
    with pytest.raises(Exception, match="Cross-entity"):
        version(b, link=assignment(
            b, scope=replace(b.scope, legal_entity_id=LegalEntityId.new())
        ))
    with pytest.raises(Exception, match="conflicts"):
        version(b, ref_binding=binding(
            b, framework=ReferenceFrameworkRef("IFRS", "2026")
        ))
    with pytest.raises(InvalidBookCandidateVersion, match="purpose"):
        version(b, purpose=BookAssignmentPurpose("MANAGEMENT"))


def test_immutable_version_does_not_depend_on_python_object_identity_hashing():
    b = book()
    fixed = BookCandidateVersionId.new()
    link = assignment(b)
    bind = binding(b)
    a = version(b, revision_id=fixed, link=link, ref_binding=bind)
    b2 = version(b, revision_id=fixed, link=link, ref_binding=bind)
    assert a.content_digest == b2.content_digest
    assert a.canonical_payload() == b2.canonical_payload()


def test_normalize_known_at_to_utc_for_reproducible_digest():
    b = book()
    ref = version(b)
    first = replace(ref, knowledge=KnowledgeInterval(JAN))
    offset = JAN.astimezone(timezone(timedelta(hours=1)))
    second = replace(ref, knowledge=KnowledgeInterval(offset))
    assert first.content_digest == second.content_digest


def test_tamper_version_book_label_is_detected_by_digest():
    b = book()
    v = version(b)
    object.__setattr__(b, "label", "Tampered")
    with pytest.raises(CandidateSnapshotDigestMismatch):
        v.verify_integrity()


def test_tamper_binding_or_source_is_detected_by_digest():
    b = book()
    v = version(b)
    object.__setattr__(v.binding, "source_ref", "tampered:binding")
    with pytest.raises(CandidateSnapshotDigestMismatch):
        v.verify_integrity()


def test_tamper_snapshot_digest_or_nested_version_is_detected():
    b = book()
    v = version(b)
    svc, actor, _, _ = scenario((v,), (statement(b),))
    snap = svc.preview(query(b), principal=actor)
    object.__setattr__(snap, "content_digest", "sha256:" + "0" * 64)
    with pytest.raises(CandidateSnapshotDigestMismatch):
        snap.verify_integrity()
    fresh = svc.preview(query(b), principal=actor)
    object.__setattr__(v, "content_digest", "sha256:" + "1" * 64)
    with pytest.raises(CandidateSnapshotDigestMismatch):
        fresh.verify_integrity()


def test_frozen_dataclasses_refuse_normal_mutation():
    b = book()
    v = version(b)
    with pytest.raises(FrozenInstanceError):
        v.source_ref = "mutated"


def test_snapshot_refuses_claim_from_wrong_framework_or_timestamp():
    b = book()
    svc, actor, _, _ = scenario((version(b),), (statement(b),))
    snap = svc.preview(query(b), principal=actor)
    with pytest.raises(InvalidBookCandidateVersion, match="do not match"):
        BookConfigurationCandidateSnapshot(
            version=snap.version, normative_claim=snap.normative_claim,
            as_of=date(2026, 3, 1), known_at=FEB,
        )


def test_missing_or_declared_unavailable_normative_claim_blocks_snapshot():
    b = book()
    v = version(b)
    svc, actor, _, _ = scenario((v,), ())
    with pytest.raises(NormativeStatementMissing):
        svc.preview(query(b), principal=actor)
    unavailable = statement(
        b, declaration=NormativeDeclaration.DECLARED_UNAVAILABLE
    )
    svc, actor, _, _ = scenario((v,), (unavailable,))
    with pytest.raises(NormativeStatementUnavailable):
        svc.preview(query(b), principal=actor)


def test_malicious_version_reader_leak_is_rejected():
    b = book()
    foreign = version(book(tenant="other-tenant"))
    svc, actor, access, members = scenario((version(b),), (statement(b),))

    class MaliciousVersions:
        def list_for_book(self, ignored_scope):
            return (foreign,)

    leaky = BookCandidateSnapshotPreviewService(
        MaliciousVersions(), ClaimsFixture((statement(b),)), access, members
    )
    with pytest.raises(InvalidBookCandidateVersion, match="foreign scope"):
        leaky.preview(query(b), principal=actor)


def test_malicious_claim_reader_leak_is_rejected():
    b = book()
    svc, actor, access, members = scenario((version(b),), (statement(b),))

    class MaliciousClaims:
        def list_for_reference(self, framework, source):
            return (statement(b, source=NormativeSourceCode("OTHER_SOURCE")),)

    leaky = BookCandidateSnapshotPreviewService(
        VersionFixture((version(b),)), MaliciousClaims(), access, members
    )
    with pytest.raises(InvalidNormativeStatement, match="foreign"):
        leaky.preview(query(b), principal=actor)


def test_no_action_grant_or_membership_denies_read():
    b = book()
    v = version(b)
    claim = statement(b)
    svc, actor, _, _ = scenario((v,), (claim,), grant=False)
    with pytest.raises(BookDraftPermissionDenied):
        svc.preview(query(b), principal=actor)
    svc, actor, _, _ = scenario((v,), (claim,), membership=False)
    with pytest.raises(BookDraftPermissionDenied):
        svc.preview(query(b), principal=actor)


def test_wrong_tenant_and_raw_actor_denied():
    b = book()
    svc, actor, _, _ = scenario((version(b),), (statement(b),))
    with pytest.raises(BookDraftPermissionDenied, match="Cross-tenant"):
        svc.preview(query(b), principal=TrustedPrincipal("rnd-actor", "other"))
    with pytest.raises(BookDraftPermissionDenied, match="Verified"):
        svc.preview(query(b), principal="raw:actor")


def test_revoked_action_denies_replay():
    b = book()
    svc, actor, access, _ = scenario((version(b),), (statement(b),))
    access.revoke(
        principal=actor, action="book.candidate_snapshot.preview", scope=b.scope
    )
    with pytest.raises(BookDraftPermissionDenied):
        svc.preview(query(b), principal=actor)


def test_invalid_query_scope_and_known_at_fail_closed():
    b = book()
    with pytest.raises(InvalidBookCandidateVersion):
        PreviewBookConfigurationSnapshot(
            replace(b.scope, book_id=None),
            BookAssignmentPurpose("STATUTORY"), SOURCE, DAY, FEB
        )
    with pytest.raises(InvalidBookCandidateVersion):
        query(b, known_at=datetime(2026, 2, 1))
    with pytest.raises(InvalidBookCandidateVersion):
        query(b, as_of=datetime(2026, 2, 15))
    with pytest.raises(InvalidBookCandidateVersion):
        PreviewBookConfigurationSnapshot(
            b.scope, BookAssignmentPurpose("STATUTORY"), "TEST_REGISTRY", DAY, FEB
        )


def test_version_ids_are_distinct_from_books_and_config_published_versions():
    from pyaccountingkit.company_configuration.domain.shared.identifiers import (
        ConfigurationVersionId,
    )

    v = version(book())
    assert type(v.id) is BookCandidateVersionId
    assert type(v.id) is not AccountingBookId
    assert type(v.id) is not ConfigurationVersionId


def test_snapshot_reader_is_immutable_and_has_no_writer():
    b = book()
    reader = VersionFixture((version(b),))
    assert len(reader.list_for_book(b.scope)) == 1
    assert not hasattr(reader, "save")
    assert not hasattr(reader, "publish")
    assert not hasattr(reader, "activate")
    assert not hasattr(BookCandidateSnapshotPreviewService, "post")


def test_architecture_has_no_sql_transport_or_issuer_gateway():
    import ast
    from pathlib import Path

    from pyaccountingkit.company_configuration.application import (
        accounting_book_candidate_snapshots,
    )
    from pyaccountingkit.company_configuration.infrastructure import (
        accounting_book_candidate_snapshots_memory,
    )

    for module in (
        accounting_book_candidate_snapshots,
        accounting_book_candidate_snapshots_memory,
    ):
        source = Path(module.__file__).read_text(encoding="utf-8")
        names = {
            alias.name for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.Import) for alias in node.names
        }
        assert not ({"psycopg", "sqlalchemy", "httpx", "requests"} & names)
        assert "organization_issuer_gateway" not in source
