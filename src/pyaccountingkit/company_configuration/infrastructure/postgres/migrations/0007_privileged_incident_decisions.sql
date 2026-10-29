-- L02-07d: manual incident decision evidence does not establish a DDL outcome.
-- Owner-only privileged control plane, independent approved incident treatment.
CREATE TABLE company_configuration.privileged_incident_decisions (
    decision_id uuid PRIMARY KEY,
    review_id uuid NOT NULL UNIQUE REFERENCES company_configuration.privileged_reconciliation_reviews(review_id),
    request_id uuid NOT NULL,
    tenant_id text NOT NULL CHECK (length(btrim(tenant_id)) > 0),
    original_operator_id text NOT NULL,
    original_reviewer_id text NOT NULL,
    decision_actor_id text NOT NULL,
    checker_id text NOT NULL,
    approval_id text NOT NULL,
    evidence_reference text NOT NULL CHECK (length(btrim(evidence_reference)) BETWEEN 1 AND 240),
    justification text NOT NULL CHECK (length(btrim(justification)) BETWEEN 1 AND 240),
    disposition text NOT NULL CHECK (
        disposition IN ('ESCALATED','REMEDIATION_REQUIRED','INVESTIGATION_DOCUMENTED')
    ),
    observed_outcome text NOT NULL DEFAULT 'UNKNOWN' CHECK (observed_outcome='UNKNOWN'),
    recorded_at timestamptz NOT NULL,
    CHECK (decision_actor_id <> original_operator_id),
    CHECK (decision_actor_id <> original_reviewer_id),
    CHECK (checker_id <> decision_actor_id),
    CHECK (checker_id <> original_operator_id),
    CHECK (checker_id <> original_reviewer_id)
);
CREATE INDEX privileged_incident_decisions_tenant_time
    ON company_configuration.privileged_incident_decisions (tenant_id,recorded_at);
CREATE TRIGGER immutable_privileged_incident_decisions
    BEFORE UPDATE OR DELETE ON company_configuration.privileged_incident_decisions
    FOR EACH ROW EXECUTE FUNCTION company_configuration.forbid_evidence_mutation();
REVOKE ALL ON company_configuration.privileged_incident_decisions FROM PUBLIC;

CREATE TABLE company_configuration.privileged_incident_denials (
    denial_id uuid PRIMARY KEY,
    review_id uuid NOT NULL,
    tenant_id text NOT NULL CHECK (length(btrim(tenant_id)) > 0),
    actor_id text NOT NULL,
    reason_code text NOT NULL CHECK (
        reason_code IN ('TENANT_MISMATCH','PERMISSION_DENIED','APPROVAL_INVALID','SOD_VIOLATION')
    ),
    recorded_at timestamptz NOT NULL
);
CREATE INDEX privileged_incident_denials_tenant_time
    ON company_configuration.privileged_incident_denials (tenant_id,recorded_at);
CREATE TRIGGER immutable_privileged_incident_denials
    BEFORE UPDATE OR DELETE ON company_configuration.privileged_incident_denials
    FOR EACH ROW EXECUTE FUNCTION company_configuration.forbid_evidence_mutation();
REVOKE ALL ON company_configuration.privileged_incident_denials FROM PUBLIC;
