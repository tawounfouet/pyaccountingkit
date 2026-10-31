"""L06-04 unapproved publication/audit/Outbox proposal contracts and NO-GO."""

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, date, datetime, timedelta, timezone

import pytest

from pyaccountingkit.company_configuration.application.fiscal_publication_contracts import (
    CalendarPublicationContractPreviewService,
    PreviewCalendarPublicationContract,
)
from pyaccountingkit.company_configuration.application.ports import TrustedPrincipal
from pyaccountingkit.company_configuration.domain.fiscal_calendar import (
    AccountingPeriodDraft,
    CalendarCode,
    CalendarCoveragePolicy,
    CalendarPublicationIntentConflict,
    CalendarPublicationIntentTampered,
    CalendarPublicationRequestCandidate,
    CalendarVersionCandidate,
    DeclaredRoleCandidate,
    FiscalCalendarDraft,
    FiscalYearCode,
    FiscalYearDraft,
    InvalidCalendarPublicationIntent,
    PeriodCode,
    PeriodKind,
    PublicationRoleClaimCandidate,
    UnverifiedPublicationGate,
    preview_calendar_publication_contract,
)
from pyaccountingkit.company_configuration.domain.shared.accounting_scope import (
    ConfigurationScope,
)
from pyaccountingkit.company_configuration.domain.shared.effective_interval import (
    EffectiveInterval,
    KnowledgeInterval,
)
from pyaccountingkit.company_configuration.domain.shared.identifiers import (
    AccountingPeriodId,
    CalendarCandidateVersionId,
    CalendarPublicationIntentId,
    CompanyId,
    FiscalCalendarId,
    FiscalYearId,
    LegalEntityId,
)
from pyaccountingkit.company_configuration.infrastructure.fiscal_publication_memory import (
    MemoryCalendarPublicationIntents,
)

JAN = datetime(2027, 1, 1, tzinfo=UTC)
FEB = datetime(2027, 2, 1, tzinfo=UTC)
MAR = datetime(2027, 3, 1, tzinfo=UTC)
END = date(2028, 1, 1)
VALID = EffectiveInterval(date(2027, 1, 1), END)


def fixture():
    scope = ConfigurationScope(
        "tenant-a", CompanyId.new(), LegalEntityId.new(),
    )
    calendar = FiscalCalendarDraft(
        FiscalCalendarId.new(), scope, CalendarCode("RND_FISCAL"),
        "R&D calendar", VALID, "rnd:jurisdiction", "rnd:calendar",
    )
    year = FiscalYearDraft(
        FiscalYearId.new(), calendar.id, scope, FiscalYearCode("FY2027"),
        VALID, "rnd:year",
    )
    first = AccountingPeriodDraft(
        AccountingPeriodId.new(), year.id, calendar.id, scope,
        PeriodCode("P01"), PeriodKind.ORDINARY,
        EffectiveInterval(date(2027, 1, 1), date(2027, 2, 1)),
        "rnd:period-a", 1,
    )
    second = AccountingPeriodDraft(
        AccountingPeriodId.new(), year.id, calendar.id, scope,
        PeriodCode("P02"), PeriodKind.ORDINARY,
        EffectiveInterval(date(2027, 2, 1), END), "rnd:period-b", 2,
    )
    return CalendarVersionCandidate(
        CalendarCandidateVersionId.new(), calendar, (year,), (first, second),
        CalendarCoveragePolicy.REQUIRE_CONTIGUOUS, VALID, KnowledgeInterval(JAN),
        "rnd:version",
    )


def claim(role, actor=None, *, start=JAN, end=MAR):
    return PublicationRoleClaimCandidate(
        role, actor or role.value.lower() + ":unverified",
        start, end, "rnd:unverified-role-claim",
    )


def request(version, *, identity=None, roles=(), effective=VALID,
            at=FEB, key="request-2027-001", correlation="corr-2027-001"):
    return CalendarPublicationRequestCandidate(
        identity or CalendarPublicationIntentId.new(),
        version, version.calendar.scope, effective,
        at, version.content_digest, key, correlation,
        "Proposed calendar publication review", "rnd:publication-intent",
        tuple(roles),
    )


def preview(value, competing=()):
    return preview_calendar_publication_contract(
        request=value, competing_intents=tuple(competing),
    )


def test_publication_preview_creates_only_deterministic_unsigned_local_intents():
    version = fixture()
    req = request(version)
    report = preview(req)
    report.verify_integrity()
    assert report.disposition == "EXTERNAL_GOVERNANCE_AND_COMMIT_GATES_UNVERIFIED"
    assert report.canonical_manifest()["committed"] is False
    assert report.canonical_manifest()["event_emitted"] is False
    assert report.canonical_manifest()["signed"] is False
    assert report.audit_intent.intent_action == "CALENDAR_PUBLICATION_REQUESTED"
    assert report.outbox_intent.event_type == "CALENDAR_VERSION_PUBLICATION_PROPOSED"
    assert report.audit_intent.publication_intent_id == req.id
    assert report.outbox_intent.publication_intent_id == req.id
    assert report.audit_intent.version_digest == version.content_digest
    assert report.outbox_intent.version_digest == version.content_digest
    assert report.audit_intent.correlation_id == report.outbox_intent.correlation_id
    assert len(report.content_digest) == 71
    assert report.content_digest.startswith("sha256:")
    for value in (req, report, report.audit_intent, report.outbox_intent):
        for action in ("publish", "commit", "post", "execute", "emit", "save", "approve"):
            assert not hasattr(value, action)


def test_all_external_gates_remain_unverified_even_if_roles_declared():
    v = fixture()
    roles = tuple(claim(role) for role in DeclaredRoleCandidate)
    report = preview(request(v, roles=roles))
    assert report.missing_role_claims == ()
    assert report.unverified_external_gates == tuple(UnverifiedPublicationGate)
    assert len(report.unverified_external_gates) == 6
    assert "SIGNED_ACTOR_AND_ISSUER" in {
        item.value for item in report.unverified_external_gates
    }
    assert "ATOMIC_VERSION_AUDIT_OUTBOX_COMMIT" in {
        item.value for item in report.unverified_external_gates
    }
    assert report.disposition != "READY"


def test_missing_claims_are_diagnostic_not_automatically_approved():
    v = fixture()
    report = preview(request(v, roles=(claim(DeclaredRoleCandidate.PREPARER),)))
    assert report.missing_role_claims == (
        DeclaredRoleCandidate.REVIEWER,
        DeclaredRoleCandidate.APPROVER,
        DeclaredRoleCandidate.PUBLISHER,
    )
    assert all(
        x["signature_status"] == "UNVERIFIED_UNTRUSTED_CLAIM"
        for x in report.request.canonical_manifest()["unverified_role_claims"]
    )


def test_order_of_unverified_role_claims_does_not_change_digest():
    v = fixture()
    roles = tuple(claim(role) for role in DeclaredRoleCandidate)
    a = request(v, roles=roles)
    reordered = replace(a, role_claims=tuple(reversed(roles)))
    assert reordered.content_digest == a.content_digest
    assert preview(a).content_digest == preview(reordered).content_digest


def test_timezone_equivalent_instants_produce_same_request_digest():
    v = fixture()
    a = request(v, roles=(claim(DeclaredRoleCandidate.PREPARER),))
    shifted = replace(
        a, requested_at=FEB.astimezone(timezone(timedelta(hours=1))),
    )
    assert shifted.content_digest == a.content_digest


def test_repeated_preview_intents_are_deterministically_identical_not_delivered():
    req = request(fixture())
    first = preview(req)
    second = preview(req)
    assert first.audit_intent == second.audit_intent
    assert first.outbox_intent == second.outbox_intent
    assert first.content_digest == second.content_digest
    assert first.audit_intent.id != first.outbox_intent.id


def test_invalid_pinned_digest_refused_at_request_creation():
    v = fixture()
    with pytest.raises(InvalidCalendarPublicationIntent, match="digest"):
        replace(request(v), expected_content_digest="sha256:" + "0" * 64)


def test_version_content_mutation_is_detected_on_repeated_read():
    v = fixture()
    req = request(v)
    proof = preview(req)
    object.__setattr__(v.calendar, "label", "tampered")
    with pytest.raises(Exception, match="changed"):
        proof.verify_integrity()


def test_publication_request_digest_tampering_detected():
    req = request(fixture())
    proof = preview(req)
    object.__setattr__(req, "reason", "tampered")
    with pytest.raises(CalendarPublicationIntentTampered):
        proof.verify_integrity()


def test_report_checksum_and_false_audit_outbox_claim_are_refused():
    proof = preview(request(fixture()))
    object.__setattr__(proof, "content_digest", "sha256:" + "0" * 64)
    with pytest.raises(CalendarPublicationIntentTampered):
        proof.verify_integrity()
    fresh = preview(request(fixture()))
    with pytest.raises(InvalidCalendarPublicationIntent, match="Fabricated"):
        replace(fresh, outbox_intent=replace(
            fresh.outbox_intent, event_type="CalendarVersionPublished",
        ))
    with pytest.raises(InvalidCalendarPublicationIntent, match="Fabricated"):
        replace(fresh, audit_intent=replace(
            fresh.audit_intent, intent_action="AUDIT_COMMITTED",
        ))


def test_forged_claim_of_external_verified_gates_is_rejected():
    proof = preview(request(fixture()))
    with pytest.raises(InvalidCalendarPublicationIntent, match="Fabricated"):
        replace(proof, unverified_external_gates=())


def test_duplicate_roles_are_refused_without_approval():
    v = fixture()
    with pytest.raises(InvalidCalendarPublicationIntent, match="Duplicate"):
        request(v, roles=(
            claim(DeclaredRoleCandidate.PREPARER, "actor-a"),
            claim(DeclaredRoleCandidate.PREPARER, "actor-b"),
        ))


def test_claimed_sod_separation_rejects_same_actor_different_roles():
    v = fixture()
    with pytest.raises(InvalidCalendarPublicationIntent, match="SoD"):
        request(v, roles=(
            claim(DeclaredRoleCandidate.PREPARER, "same-actor"),
            claim(DeclaredRoleCandidate.APPROVER, "same-actor"),
        ))


@pytest.mark.parametrize("kwargs", [
    {"at": JAN - timedelta(seconds=1)},
    {"at": datetime(2027, 2, 1)},
])
def test_out_of_knowledge_or_naive_publication_instant_rejected(kwargs):
    with pytest.raises(InvalidCalendarPublicationIntent):
        request(fixture(), **kwargs)


def test_expired_or_future_role_claim_refused():
    v = fixture()
    with pytest.raises(InvalidCalendarPublicationIntent, match="Future or expired"):
        request(v, roles=(
            claim(DeclaredRoleCandidate.PREPARER, start=MAR, end=MAR + timedelta(days=5)),
        ))
    with pytest.raises(InvalidCalendarPublicationIntent, match="Future or expired"):
        request(v, roles=(
            claim(DeclaredRoleCandidate.PREPARER, start=JAN, end=FEB),
        ))


@pytest.mark.parametrize("invalid", ["", "x", " ", "bad key", " é", "A" * 129])
def test_invalid_idempotency_and_correlation_keys_refused(invalid):
    v = fixture()
    with pytest.raises(InvalidCalendarPublicationIntent, match="idempotency"):
        request(v, key=invalid)
    with pytest.raises(InvalidCalendarPublicationIntent, match="idempotency"):
        request(v, correlation=invalid)


def test_duplicate_intent_id_detected_even_if_competing_identical():
    v = fixture()
    req = request(v)
    with pytest.raises(CalendarPublicationIntentConflict, match="Duplicate"):
        preview(req, (req,))


def test_same_idempotency_key_with_distinct_id_is_unverified_conflict():
    v = fixture()
    req = request(v)
    another = request(v)
    with pytest.raises(CalendarPublicationIntentConflict, match="Idempotency"):
        preview(req, (another,))


def test_competing_effective_versions_cannot_silently_overlap():
    v = fixture()
    req = request(v)
    other = request(v, key="request-2027-002")
    with pytest.raises(CalendarPublicationIntentConflict, match="Overlapping"):
        preview(req, (other,))


def test_adjacent_half_open_publication_intents_not_conflicting():
    v = fixture()
    earlier = request(
        v, effective=EffectiveInterval(date(2027, 1, 1), date(2027, 7, 1)),
    )
    later = request(
        v, effective=EffectiveInterval(date(2027, 7, 1), END),
        key="request-2027-002",
    )
    preview(earlier, (later,))


def test_foreign_scope_in_competing_intents_is_rejected():
    v = fixture()
    original = request(v)
    foreign = request(fixture())
    with pytest.raises(InvalidCalendarPublicationIntent, match="Foreign"):
        preview(original, (foreign,))


def test_invalid_scope_or_unbounded_effective_interval_refused():
    v = fixture()
    req = request(v)
    with pytest.raises(InvalidCalendarPublicationIntent, match="scope"):
        replace(req, scope=replace(req.scope, legal_entity_id=LegalEntityId.new()))
    with pytest.raises(InvalidCalendarPublicationIntent, match="validity"):
        replace(req, effective=EffectiveInterval(date(2026, 1, 1), END))


def test_unknown_expected_prior_version_and_same_version_refused():
    v = fixture()
    req = request(v)
    with pytest.raises(InvalidCalendarPublicationIntent, match="prior"):
        replace(req, expected_prior_version_id="latest")
    with pytest.raises(InvalidCalendarPublicationIntent, match="supersede"):
        replace(req, expected_prior_version_id=v.id)


def test_invalid_actor_claim_fields_are_rejected_as_non_authoritative():
    c = claim(DeclaredRoleCandidate.REVIEWER)
    with pytest.raises(InvalidCalendarPublicationIntent):
        replace(c, actor_ref=" ")
    with pytest.raises(InvalidCalendarPublicationIntent):
        replace(c, expires_at=c.claimed_at)
    with pytest.raises(InvalidCalendarPublicationIntent):
        replace(c, claimed_at=datetime(2027, 1, 1))
    with pytest.raises(InvalidCalendarPublicationIntent):
        replace(c, role="APPROVER")


def test_immutable_contract_objects_have_no_sql_or_event_dispatch():
    v = fixture()
    req = request(v)
    proof = preview(req)
    with pytest.raises(FrozenInstanceError):
        req.reason = "tampered"
    with pytest.raises(FrozenInstanceError):
        proof.outbox_intent.event_type = "published"
    with pytest.raises(FrozenInstanceError):
        proof.audit_intent.intent_action = "committed"


def test_query_service_has_distinct_fake_grant_and_scoped_read_only_port():
    v = fixture()
    req = request(v)

    class Grants:
        allowed = False

        def require(self, *, principal, action, scope):
            assert action == "calendar.publication.intent.candidate.preview"
            if not self.allowed:
                raise PermissionError("Candidate publication preview denied")

    grants = Grants()
    svc = CalendarPublicationContractPreviewService(
        reader=MemoryCalendarPublicationIntents((req,)),
        authorization=grants,
    )
    query = PreviewCalendarPublicationContract(req.scope, req.id)
    principal = TrustedPrincipal("candidate-reviewer", "tenant-a")
    with pytest.raises(PermissionError, match="denied"):
        svc.preview(query, principal=principal)
    grants.allowed = True
    assert svc.preview(query, principal=principal).audit_intent.publication_intent_id == req.id
    with pytest.raises(PermissionError, match="Cross-tenant"):
        svc.preview(query, principal=TrustedPrincipal("candidate-reviewer", "tenant-b"))
    with pytest.raises(PermissionError, match="Unverified"):
        svc.preview(query, principal="caller-supplied-principal")


def test_malicious_reader_leaking_cross_entity_intent_rejected():
    v = fixture()
    req = request(v)

    class Allow:
        def require(self, *, principal, action, scope):
            return None

    class Malicious:
        def list_for_scope(self, scope):
            return (req, request(fixture()))

    svc = CalendarPublicationContractPreviewService(
        reader=Malicious(), authorization=Allow(),
    )
    with pytest.raises(InvalidCalendarPublicationIntent, match="Foreign"):
        svc.preview(
            PreviewCalendarPublicationContract(req.scope, req.id),
            principal=TrustedPrincipal("actor-unverified", "tenant-a"),
        )


def test_exact_missing_or_duplicate_requested_intent_is_refused_by_service():
    v = fixture()
    req = request(v)

    class Allow:
        def require(self, *, principal, action, scope):
            return None

    actor = TrustedPrincipal("actor", "tenant-a")
    q = PreviewCalendarPublicationContract(req.scope, req.id)
    for values in ((), (req, req)):
        svc = CalendarPublicationContractPreviewService(
            reader=MemoryCalendarPublicationIntents(values),
            authorization=Allow(),
        )
        with pytest.raises(InvalidCalendarPublicationIntent, match="absent/ambiguous"):
            svc.preview(q, principal=actor)


def test_no_publisher_sql_outbox_writer_and_legacy_fourteen_migrations_unchanged():
    import ast
    from pathlib import Path

    from pyaccountingkit.company_configuration.application import (
        fiscal_publication_contracts,
    )
    from pyaccountingkit.company_configuration.domain.fiscal_calendar import (
        publication_intents,
    )
    from pyaccountingkit.company_configuration.infrastructure import (
        fiscal_publication_memory,
    )

    for module in (
        fiscal_publication_contracts, publication_intents, fiscal_publication_memory,
    ):
        code = Path(module.__file__).read_text(encoding="utf-8")
        tree = ast.parse(code)
        direct_imports = {
            name.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for name in node.names
        }
        assert not direct_imports & {
            "sqlalchemy", "psycopg", "django", "requests", "httpx",
        }
        for name in ("organization_issuer_gateway", "ledger.post"):
            assert name not in code.lower()
        for method in ("publish", "approve", "commit", "emit", "insert"):
            assert not hasattr(module, method)
    migrations = (
        Path(publication_intents.__file__).resolve().parents[1]
        / "infrastructure" / "postgres" / "migrations"
    )
    assert len(tuple(migrations.glob("*.sql"))) == 14
