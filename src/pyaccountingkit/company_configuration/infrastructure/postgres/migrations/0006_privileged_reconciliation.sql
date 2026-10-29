-- L02-07c: overdue INTENT is NOT evidence of successful or failed DDL.
-- CANCELLED only means an IAM/approval recheck denied execution after INTENT.
ALTER TABLE company_configuration.privileged_operation_audit
    DROP CONSTRAINT privileged_operation_audit_phase_check;
ALTER TABLE company_configuration.privileged_operation_audit
    ADD CONSTRAINT privileged_operation_audit_phase_check
    CHECK (phase IN ('INTENT', 'DENIED', 'SUCCEEDED', 'FAILED', 'CANCELLED'));
DROP INDEX company_configuration.unique_privileged_operation_outcome;
CREATE UNIQUE INDEX unique_privileged_operation_outcome
    ON company_configuration.privileged_operation_audit (request_id)
    WHERE phase IN ('SUCCEEDED', 'FAILED', 'CANCELLED');

-- An immutable request for manual review, not a terminal outcome. This journal
-- is owner-only and cannot be written from tenant runtime, dispatcher or Inbox.
CREATE TABLE company_configuration.privileged_reconciliation_reviews (
    review_id uuid PRIMARY KEY,
    request_id uuid NOT NULL UNIQUE,
    tenant_id text NOT NULL CHECK (length(btrim(tenant_id)) > 0),
    login_role text NOT NULL,
    operation text NOT NULL CHECK (operation IN ('rotate', 'revoke')),
    actor_id text NOT NULL,
    reviewer_id text NOT NULL,
    intent_recorded_at timestamptz NOT NULL,
    detected_at timestamptz NOT NULL,
    review_reason text NOT NULL CHECK (review_reason = 'OUTCOME_MISSING'),
    observed_outcome text NOT NULL CHECK (observed_outcome = 'UNKNOWN')
);
CREATE INDEX privileged_reconciliation_reviews_tenant_time
    ON company_configuration.privileged_reconciliation_reviews (tenant_id, detected_at);
CREATE TRIGGER no_privileged_review_update_delete
    BEFORE UPDATE OR DELETE ON company_configuration.privileged_reconciliation_reviews
    FOR EACH ROW EXECUTE FUNCTION company_configuration.forbid_evidence_mutation();
REVOKE ALL ON company_configuration.privileged_reconciliation_reviews FROM PUBLIC;
