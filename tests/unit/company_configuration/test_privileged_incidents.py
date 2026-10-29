"""L02-07d two-person UNKNOWN incident disposition and audit fail-closed tests."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from pyaccountingkit.company_configuration.application.privileged_incidents import (
    IncidentDecisionReceipt,
    IncidentDecisionRequest,
    PrivilegedIncidentService,
    VerifiedIncidentApproval,
)
from pyaccountingkit.company_configuration.application.privileged_operations import (
    PrivilegedAccessDenied,
    VerifiedOperator,
)

NOW = datetime(2026, 10, 29, 15, 0, tzinfo=UTC)


class Identity:
    def __init__(self, actor=None):
        self.actor = actor or VerifiedOperator("investigator-3", "tenant-a")

    def verify(self, context):
        if context != "trusted":
            raise PrivilegedAccessDenied("Untrusted control-plane context")
        return self.actor


class Clock:
    def now(self):
        return NOW


class Policy:
    def __init__(self, allowed=True):
        self.allowed = allowed
        self.calls = 0

    def require_decision(self, **kwargs):
        self.calls += 1
        if not self.allowed:
            raise PrivilegedAccessDenied("Grant revoked")


class Approval:
    def __init__(self, value):
        self.value = value

    def resolve(self, *, reference):
        assert reference == "incident-approval-1"
        return self.value


class Repository:
    def __init__(self, fail_denial=False):
        self.denials = []
        self.decisions = []
        self.fail_denial = fail_denial

    def record_decision(self, **kwargs):
        self.decisions.append(kwargs)
        req = kwargs["request"]
        return IncidentDecisionReceipt(uuid4(), req.review_id, req.tenant_id,
                                       req.disposition, "UNKNOWN")

    def record_denial(self, **kwargs):
        if self.fail_denial:
            raise OSError("Incident denial audit unavailable")
        self.denials.append(kwargs)


@pytest.fixture
def case():
    req = IncidentDecisionRequest(
        uuid4(), "tenant-a", "REMEDIATION_REQUIRED", "case-attachment-42",
        "incident-approval-1", "Forensic review requires separate key rotation",
    )
    approval = VerifiedIncidentApproval(
        "incident-approval-1", "checker-4", req.review_id, req.tenant_id,
        req.disposition, req.evidence_reference,
        NOW - timedelta(minutes=5), NOW + timedelta(minutes=10),
    )
    return req, approval


def make_service(approval, *, actor=None, allowed=True, repo=None):
    storage = repo or Repository()
    return PrivilegedIncidentService(
        identity=Identity(actor), policy=Policy(allowed), approvals=Approval(approval),
        repository=storage, clock=Clock(),
    ), storage


def test_records_only_unknown_disposition_without_privileged_mutation(case):
    req, approval = case
    svc, store = make_service(approval)
    result = svc.decide(req, auth_context="trusted")
    assert result.observed_outcome == "UNKNOWN"
    assert result.disposition == "REMEDIATION_REQUIRED"
    assert len(store.decisions) == 1 and store.denials == []
    assert store.decisions[0]["actor"].actor_id == "investigator-3"


@pytest.mark.parametrize("field,value", [
    ("tenant_id", "tenant-b"), ("disposition", "ESCALATED"),
    ("review_id", uuid4()), ("approval_id", "unrelated"),
    ("evidence_reference", "not-the-same-evidence"),
    ("expires_at", NOW), ("issued_at", NOW + timedelta(seconds=1)),
])
def test_invalid_approval_is_durably_denied(case, field, value):
    req, approval = case
    svc, store = make_service(replace(approval, **{field: value}))
    with pytest.raises(PrivilegedAccessDenied, match="APPROVAL_INVALID"):
        svc.decide(req, auth_context="trusted")
    assert not store.decisions and store.denials[0]["code"] == "APPROVAL_INVALID"


def test_self_approval_is_rejected(case):
    req, approval = case
    svc, store = make_service(replace(approval, approver_id="investigator-3"))
    with pytest.raises(PrivilegedAccessDenied, match="SOD_VIOLATION"):
        svc.decide(req, auth_context="trusted")
    assert not store.decisions and store.denials[0]["code"] == "SOD_VIOLATION"


def test_policy_denial_prevents_write_and_audits_authenticated_tenant(case):
    req, approval = case
    svc, store = make_service(approval, allowed=False)
    with pytest.raises(PrivilegedAccessDenied, match="PERMISSION_DENIED"):
        svc.decide(req, auth_context="trusted")
    assert not store.decisions and store.denials[0]["actor"].tenant_id == "tenant-a"


def test_cross_tenant_denial_records_actual_authenticated_tenant(case):
    req, approval = case
    svc, store = make_service(approval, actor=VerifiedOperator("outside", "tenant-b"))
    with pytest.raises(PrivilegedAccessDenied, match="TENANT_MISMATCH"):
        svc.decide(req, auth_context="trusted")
    assert store.denials[0]["actor"].tenant_id == "tenant-b"
    assert not store.decisions


def test_denial_audit_failure_never_authorizes_case(case):
    req, approval = case
    store = Repository(fail_denial=True)
    svc, _ = make_service(approval, allowed=False, repo=store)
    with pytest.raises(OSError, match="denial audit unavailable"):
        svc.decide(req, auth_context="trusted")
    assert not store.decisions


def test_unverified_context_is_rejected_without_sql_write(case):
    req, approval = case
    svc, store = make_service(approval)
    with pytest.raises(PrivilegedAccessDenied, match="Untrusted"):
        svc.decide(req, auth_context="untrusted")
    assert not store.decisions


@pytest.mark.parametrize("disposition", ["SUCCEEDED", "FAILED", "CLOSED"])
def test_disposition_does_not_pretend_to_prove_ddl_outcome(case, disposition):
    req, _ = case
    with pytest.raises(ValueError, match="disposition"):
        replace(req, disposition=disposition)


def test_invalid_evidence_reference_fails_before_any_authz(case):
    req, _ = case
    with pytest.raises(ValueError, match="Canonical"):
        replace(req, evidence_reference="   ")
