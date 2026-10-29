"""L02-07l: authorization/SoD and operational monitoring without PostgreSQL."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from pyaccountingkit.company_configuration.application.iam_ack_recovery import (
    IamAckRecoveryService,
    RedriveRequest,
    VerifiedRedriveApproval,
)
from pyaccountingkit.company_configuration.application.privileged_operations import (
    PrivilegedAccessDenied,
    VerifiedOperator,
)
from pyaccountingkit.company_configuration.infrastructure.iam.ack_delivery import (
    AckDeliveryBatch,
)
from pyaccountingkit.company_configuration.infrastructure.iam.ack_operations import (
    IamAckOperationsRunner,
)

NOW = datetime(2026, 10, 29, 18, 0, tzinfo=UTC)


class Identity:
    def verify(self, ctx):
        if ctx != "verified":
            raise PrivilegedAccessDenied("Identity unavailable")
        return VerifiedOperator("investigator", "tenant-a")


class Policy:
    def __init__(self):
        self.calls = 0
        self.fail_after = None

    def require(self, *, actor, tenant_id, action):
        self.calls += 1
        if tenant_id != "tenant-a" or action not in (
            "inspect_iam_ack_dead", "redrive_iam_ack_dead"
        ) or (self.fail_after is not None and self.calls >= self.fail_after):
            raise PrivilegedAccessDenied("No recovery permission")


class Approvals:
    def __init__(self, record):
        self.record = record
        self.change_after = None
        self.calls = 0

    def resolve(self, *, reference):
        self.calls += 1
        if self.change_after is not None and self.calls >= self.change_after:
            return replace(self.record, evidence_reference="different-evidence")
        return self.record


class Repo:
    def __init__(self):
        self.calls = []

    def list_dead(self, tenant_id, limit):
        self.calls.append(("inspect", tenant_id, limit))
        return ()

    def redrive(self, request, *, actor_id, approver_id):
        self.calls.append(("redrive", request, actor_id, approver_id))
        return 1


class Clock:
    def now(self):
        return NOW


@pytest.fixture
def recovery():
    req = RedriveRequest(
        uuid4(), uuid4(), "tenant-a", "approval-r1",
        "incident-123", "PROVIDER_RECOVERED",
    )
    approval = VerifiedRedriveApproval(
        req.approval_reference, "checker-b", req.event_id, req.request_id,
        req.tenant_id, req.evidence_reference, req.reason_code,
        NOW - timedelta(minutes=1), NOW + timedelta(minutes=2),
    )
    policy = Policy()
    approvals = Approvals(approval)
    repo = Repo()
    svc = IamAckRecoveryService(
        identity=Identity(), policy=policy, approvals=approvals,
        repository=repo, clock=Clock(),
    )
    return req, approval, svc, policy, approvals, repo


def test_redrive_requires_two_distinct_verified_actors(recovery):
    req, _, svc, policy, _, repo = recovery
    assert svc.redrive(req, auth_context="verified") == 1
    assert policy.calls == 2
    assert repo.calls[0][2:] == ("investigator", "checker-b")


@pytest.mark.parametrize("field,value", [
    ("approver_id", "investigator"),
    ("event_id", uuid4()),
    ("request_id", uuid4()),
    ("tenant_id", "tenant-b"),
    ("reason_code", "INCIDENT_REVIEWED"),
    ("evidence_reference", "other"),
    ("approval_reference", "other"),
    ("expires_at", NOW),
    ("issued_at", NOW + timedelta(minutes=1)),
])
def test_scope_sod_or_expiry_denied_before_sql(recovery, field, value):
    req, approval, _, policy, approvals, repo = recovery
    approvals.record = replace(approval, **{field: value})
    svc = IamAckRecoveryService(
        identity=Identity(), policy=policy, approvals=approvals,
        repository=repo, clock=Clock(),
    )
    with pytest.raises(PrivilegedAccessDenied):
        svc.redrive(req, auth_context="verified")
    assert repo.calls == []


def test_unverified_or_foreign_tenant_cannot_inspect(recovery):
    _, _, svc, _, _, repo = recovery
    with pytest.raises(PrivilegedAccessDenied):
        svc.list_dead(tenant_id="tenant-a", auth_context="forged")
    with pytest.raises(PrivilegedAccessDenied):
        svc.list_dead(tenant_id="tenant-b", auth_context="verified")
    assert repo.calls == []


def test_inspection_bounded(recovery):
    _, _, svc, _, _, repo = recovery
    with pytest.raises(ValueError):
        svc.list_dead(tenant_id="tenant-a", auth_context="verified", limit=100)
    assert svc.list_dead(tenant_id="tenant-a", auth_context="verified") == ()
    assert repo.calls == [("inspect", "tenant-a", 10)]


def test_current_grant_revocation_blocks_before_sql(recovery):
    req, _, svc, policy, _, repo = recovery
    policy.fail_after = 2
    with pytest.raises(PrivilegedAccessDenied):
        svc.redrive(req, auth_context="verified")
    assert repo.calls == []


def test_changed_approval_blocks_before_sql(recovery):
    req, _, svc, _, approvals, repo = recovery
    approvals.change_after = 2
    with pytest.raises(PrivilegedAccessDenied):
        svc.redrive(req, auth_context="verified")
    assert repo.calls == []


class Worker:
    def run_once(self, *, limit):
        return AckDeliveryBatch(2, 1, 1, 0)


class Metrics:
    def __init__(self, dead=0, oldest=0):
        self.dead = dead
        self.oldest = oldest

    def snapshot(self):
        return SimpleNamespace(
            pending=1, in_flight=0, retry=1, delivered=3, dead=self.dead,
            stale_leases=0, due_count=2, oldest_open_seconds=self.oldest,
        )


class Sink:
    def __init__(self):
        self.samples = []
        self.offline = False

    def report(self, sample):
        if self.offline:
            raise OSError("Monitor unavailable")
        self.samples.append(sample)


def test_operational_metrics_raise_dead_and_backlog_flags():
    sink = Sink()
    runner = IamAckOperationsRunner(
        worker=Worker(), metrics=Metrics(dead=3, oldest=700), telemetry=sink,
    )
    sample = runner.tick(limit=2)
    assert sample.alert_dead and sample.alert_backlog
    assert sample.dead == 3 and sample.batch.delivered == 1
    assert sink.samples == [sample]


def test_monitoring_failure_is_not_reported_healthy():
    sink = Sink()
    sink.offline = True
    runner = IamAckOperationsRunner(
        worker=Worker(), metrics=Metrics(), telemetry=sink,
    )
    with pytest.raises(OSError):
        runner.tick(limit=1)


def test_runner_rejects_unbounded_alert_threshold():
    with pytest.raises(ValueError):
        IamAckOperationsRunner(
            worker=Worker(), metrics=Metrics(), telemetry=Sink(),
            backlog_threshold_seconds=0,
        )
