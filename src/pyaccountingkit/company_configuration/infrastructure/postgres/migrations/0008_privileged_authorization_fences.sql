-- L02-07e: PostgreSQL LOCAL authorization fence (not a remote IAM lease).
-- Schema-owner-only state; no grant to runtime, dispatcher or Inbox roles.
CREATE TABLE company_configuration.privileged_authorization_fences (
    request_id uuid PRIMARY KEY,
    tenant_id text NOT NULL CHECK (tenant_id <> '' AND btrim(tenant_id) = tenant_id),
    login_role name NOT NULL,
    operation text NOT NULL CHECK (operation IN ('rotate', 'revoke')),
    actor_id text NOT NULL CHECK (actor_id <> ''),
    approver_id text NOT NULL CHECK (approver_id <> '' AND approver_id <> actor_id),
    approval_id text NOT NULL CHECK (approval_id <> ''),
    expires_at timestamptz NOT NULL,
    state text NOT NULL DEFAULT 'ACTIVE' CHECK (state IN ('ACTIVE', 'REVOKED', 'CONSUMED')),
    consumed_at timestamptz,
    revoked_at timestamptz,
    CHECK (
        (state='ACTIVE' AND consumed_at IS NULL AND revoked_at IS NULL)
        OR (state='REVOKED' AND consumed_at IS NULL AND revoked_at IS NOT NULL)
        OR (state='CONSUMED' AND consumed_at IS NOT NULL AND revoked_at IS NULL)
    )
);
CREATE UNIQUE INDEX one_active_privileged_fence_per_login
    ON company_configuration.privileged_authorization_fences (tenant_id, login_role)
    WHERE state='ACTIVE';

CREATE TABLE company_configuration.privileged_fence_events (
    event_id uuid PRIMARY KEY,
    request_id uuid NOT NULL REFERENCES company_configuration.privileged_authorization_fences,
    tenant_id text NOT NULL,
    actor_id text NOT NULL,
    action text NOT NULL CHECK (action IN ('ISSUED','REVOKED','CONSUMED')),
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE UNIQUE INDEX one_fence_event_per_transition
    ON company_configuration.privileged_fence_events (request_id, action);
CREATE TRIGGER no_privileged_fence_evidence_change
    BEFORE UPDATE OR DELETE ON company_configuration.privileged_fence_events
    FOR EACH ROW EXECUTE FUNCTION company_configuration.forbid_evidence_mutation();

CREATE FUNCTION company_configuration.validate_fence_transition()
RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $$
BEGIN
    IF (NEW.request_id,NEW.tenant_id,NEW.login_role,NEW.operation,NEW.actor_id,
        NEW.approver_id,NEW.approval_id,NEW.expires_at) IS DISTINCT FROM
       (OLD.request_id,OLD.tenant_id,OLD.login_role,OLD.operation,OLD.actor_id,
        OLD.approver_id,OLD.approval_id,OLD.expires_at) THEN
        RAISE EXCEPTION 'Privileged fence identity is immutable' USING ERRCODE='23514';
    END IF;
    IF OLD.state <> 'ACTIVE' OR NEW.state NOT IN ('REVOKED','CONSUMED') THEN
        RAISE EXCEPTION 'Privileged fence state transition denied' USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER enforce_privileged_fence_transition
    BEFORE UPDATE ON company_configuration.privileged_authorization_fences
    FOR EACH ROW EXECUTE FUNCTION company_configuration.validate_fence_transition();

REVOKE ALL ON company_configuration.privileged_authorization_fences FROM PUBLIC;
REVOKE ALL ON company_configuration.privileged_fence_events FROM PUBLIC;
REVOKE ALL ON FUNCTION company_configuration.validate_fence_transition() FROM PUBLIC;
