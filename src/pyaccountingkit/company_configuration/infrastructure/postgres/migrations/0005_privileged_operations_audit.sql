-- L02-07b candidate. Owner-only, append-only intent/decision/outcome evidence.
-- Not WORM; this is NOT a production IAM or independently approved SoD model.
CREATE TABLE company_configuration.privileged_operation_audit (
    record_id uuid NOT NULL PRIMARY KEY,
    request_id uuid NOT NULL,
    tenant_id text NOT NULL CHECK (length(btrim(tenant_id)) > 0),
    login_role text NOT NULL,
    actor_id text NOT NULL,
    approver_id text,
    approval_id text,
    operation text NOT NULL CHECK (operation IN ('rotate', 'revoke')),
    phase text NOT NULL CHECK (phase IN ('INTENT', 'DENIED', 'SUCCEEDED', 'FAILED')),
    reason_code text NOT NULL,
    recorded_at timestamptz NOT NULL
);
CREATE UNIQUE INDEX unique_privileged_operation_intent
    ON company_configuration.privileged_operation_audit (request_id)
    WHERE phase = 'INTENT';
CREATE UNIQUE INDEX unique_privileged_operation_outcome
    ON company_configuration.privileged_operation_audit (request_id)
    WHERE phase IN ('SUCCEEDED', 'FAILED');
CREATE INDEX privileged_operation_audit_tenant_time
    ON company_configuration.privileged_operation_audit (tenant_id, recorded_at);
CREATE TRIGGER no_privileged_audit_update_delete
    BEFORE UPDATE OR DELETE ON company_configuration.privileged_operation_audit
    FOR EACH ROW EXECUTE FUNCTION company_configuration.forbid_evidence_mutation();
REVOKE ALL ON company_configuration.privileged_operation_audit FROM PUBLIC;
-- Schema owner is an explicitly trusted admin; no application or tenant-role grant.
