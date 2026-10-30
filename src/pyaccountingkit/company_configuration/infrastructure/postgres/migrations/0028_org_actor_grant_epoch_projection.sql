-- G3-C02b3b2a R&D: owner-provisioned actor-scope grant epoch projection.
-- IMMUTABLE historical migrations 0001..0027. NOT external IAM verification.
-- Strict fail-closed SQL primitive; integration into all business UoWs is
-- future work. Owner must authenticate provider evidence *outside* PostgreSQL.
CREATE TABLE company_configuration.organization_actor_grant_epochs (
    grant_id uuid PRIMARY KEY,
    tenant_id text NOT NULL CHECK (btrim(tenant_id)<>'' AND btrim(tenant_id)=tenant_id),
    actor_id text NOT NULL CHECK (btrim(actor_id)<>'' AND btrim(actor_id)=actor_id),
    action text NOT NULL CHECK (btrim(action)<>'' AND btrim(action)=action),
    target_id uuid NOT NULL,
    authority_issuer text NOT NULL CHECK (
        btrim(authority_issuer)<>'' AND btrim(authority_issuer)=authority_issuer
    ),
    grant_version bigint NOT NULL CHECK (grant_version>=1),
    enabled boolean NOT NULL,
    valid_until timestamptz NOT NULL,
    decision_sha256 text NOT NULL CHECK (decision_sha256 ~ '^[0-9a-f]{64}$'),
    source_event_id uuid NOT NULL,
    observed_at timestamptz NOT NULL DEFAULT pg_catalog.clock_timestamp(),
    UNIQUE (tenant_id,grant_id)
);
REVOKE ALL ON company_configuration.organization_actor_grant_epochs FROM PUBLIC;
CREATE INDEX org_actor_grant_epoch_expiry
ON company_configuration.organization_actor_grant_epochs (valid_until);

-- Only owner-side externally authenticated projection/sync may mutate.
-- Identity and scope never change; every changed grant snapshot advances epoch.
CREATE FUNCTION company_configuration.guard_org_actor_epoch_revision()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,pg_temp AS $$
BEGIN
    IF ROW(
        NEW.grant_id,NEW.tenant_id,NEW.actor_id,NEW.action,
        NEW.target_id,NEW.authority_issuer
    ) IS DISTINCT FROM ROW(
        OLD.grant_id,OLD.tenant_id,OLD.actor_id,OLD.action,
        OLD.target_id,OLD.authority_issuer
    ) OR NEW.grant_version<=OLD.grant_version
       OR NEW.observed_at<OLD.observed_at
       OR NEW.source_event_id=OLD.source_event_id THEN
        RAISE EXCEPTION 'IAM actor grant epoch revision must advance with immutable scope'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END $$;
REVOKE ALL ON FUNCTION company_configuration.guard_org_actor_epoch_revision()
FROM PUBLIC;
CREATE TRIGGER org_actor_grant_epoch_monotonic
BEFORE UPDATE ON company_configuration.organization_actor_grant_epochs
FOR EACH ROW EXECUTE FUNCTION company_configuration.guard_org_actor_epoch_revision();

-- SQL issuer cannot bypass revocation epoch checks by providing a tenant GUC
-- or SET ROLE; authorization requires independent, owner-only grant projection.
-- FOR SHARE holds the specific grant row until transaction COMMIT/ROLLBACK.
-- A conflicting owner UPDATE waits until then; an earlier owner revocation or
-- version increment causes this request to fail when it acquires the lock.
CREATE FUNCTION company_configuration.require_org_actor_grant_epoch(
    p_tenant text, p_grant_id uuid, p_version bigint, p_actor_id text,
    p_action text, p_target_id uuid, p_authority_issuer text,
    p_decision_sha256 text
) RETURNS void LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,pg_temp AS $$
DECLARE
    v_now timestamptz := pg_catalog.clock_timestamp();
BEGIN
    IF p_tenant IS NULL
       OR p_tenant IS DISTINCT FROM company_configuration.bound_tenant()
       OR p_grant_id IS NULL OR p_version IS NULL OR p_version<1
       OR p_actor_id IS NULL OR p_action IS NULL OR p_target_id IS NULL
       OR p_authority_issuer IS NULL OR p_decision_sha256 IS NULL
       OR NOT (
           EXISTS(SELECT 1 FROM company_configuration.organization_company_command_issuers
                  WHERE login_role=session_user AND tenant_id=p_tenant AND enabled)
           OR EXISTS(SELECT 1 FROM company_configuration.organization_registry_command_issuers
                     WHERE login_role=session_user AND tenant_id=p_tenant AND enabled)
           OR EXISTS(SELECT 1 FROM company_configuration.organization_lifecycle_command_issuers
                     WHERE login_role=session_user AND tenant_id=p_tenant AND enabled)
           OR EXISTS(SELECT 1 FROM company_configuration.organization_membership_command_issuers
                     WHERE login_role=session_user AND tenant_id=p_tenant AND enabled)
       ) THEN
        RAISE EXCEPTION 'Independent tenant-bound SQL issuer required for actor epoch fence'
            USING ERRCODE='42501';
    END IF;

    PERFORM 1 FROM company_configuration.organization_actor_grant_epochs g
    WHERE g.tenant_id=p_tenant AND g.grant_id=p_grant_id
      AND g.grant_version=p_version AND g.actor_id=p_actor_id
      AND g.action=p_action AND g.target_id=p_target_id
      AND g.authority_issuer=p_authority_issuer
      AND g.decision_sha256=p_decision_sha256 AND g.enabled
      AND g.valid_until>v_now
      AND g.valid_until<=v_now+interval '5 minutes'
    FOR SHARE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Actor grant version/scope/decision revoked or expired'
            USING ERRCODE='42501';
    END IF;
END $$;
REVOKE ALL ON FUNCTION company_configuration.require_org_actor_grant_epoch(
    text,uuid,bigint,text,text,uuid,text,text
) FROM PUBLIC;
