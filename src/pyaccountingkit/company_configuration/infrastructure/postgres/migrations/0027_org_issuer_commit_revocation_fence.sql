-- G3-C02b3b1 R&D: SQL *issuer-login* revocation at business COMMIT.
-- Owner-administered issuer bindings, not human IAM grants. 0001..0026 unchanged.
--
-- Any owner-led UPDATE(enabled=false) committed BEFORE the deferred trigger's
-- row lock is acquired makes this write fail/rollback. A write that acquires
-- the row lock first serializes ahead of the later revocation UPDATE.
-- This is local PostgreSQL ordering ONLY; external IAM revocation may not yet
-- have been propagated into the owner-managed SQL issuer binding.
CREATE FUNCTION company_configuration.require_org_issuer_commit_fence(
    p_tenant text, p_family text
) RETURNS void LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,pg_temp AS $$
BEGIN
    IF p_tenant IS NULL OR p_tenant IS DISTINCT FROM company_configuration.bound_tenant()
       OR p_family IS NULL THEN
        RAISE EXCEPTION 'SQL issuer COMMIT fence requires tenant-bound login'
            USING ERRCODE='42501';
    END IF;

    -- Explicit static table references: no caller-supplied dynamic SQL.
    -- FOR SHARE locks the issuer row through COMMIT and serializes with
    -- owner-managed enabled=false revocations (which take an UPDATE lock).
    IF p_family='company' THEN
        PERFORM 1 FROM company_configuration.organization_company_command_issuers a
        WHERE a.login_role=session_user AND a.tenant_id=p_tenant AND a.enabled
        FOR SHARE;
    ELSIF p_family='registry' THEN
        PERFORM 1 FROM company_configuration.organization_registry_command_issuers a
        WHERE a.login_role=session_user AND a.tenant_id=p_tenant AND a.enabled
        FOR SHARE;
    ELSIF p_family='lifecycle' THEN
        PERFORM 1 FROM company_configuration.organization_lifecycle_command_issuers a
        WHERE a.login_role=session_user AND a.tenant_id=p_tenant AND a.enabled
        FOR SHARE;
    ELSIF p_family='membership' THEN
        PERFORM 1 FROM company_configuration.organization_membership_command_issuers a
        WHERE a.login_role=session_user AND a.tenant_id=p_tenant AND a.enabled
        FOR SHARE;
    ELSE
        RAISE EXCEPTION 'Unknown SQL issuer COMMIT fence family'
            USING ERRCODE='42501';
    END IF;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'SQL issuer revoked before controlled command COMMIT'
            USING ERRCODE='42501';
    END IF;
END $$;
REVOKE ALL ON FUNCTION company_configuration.require_org_issuer_commit_fence(
    text,text
) FROM PUBLIC;

CREATE FUNCTION company_configuration.guard_org_issuer_commit_fence()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,pg_temp AS $$
DECLARE v_family text;
BEGIN
    IF TG_TABLE_NAME IN (
        'organization_command_requests',
        'organization_command_audit',
        'organization_command_outbox'
    ) THEN
        v_family := CASE NEW.target_kind
            WHEN 'COMPANY' THEN 'company'
            WHEN 'ESTABLISHMENT' THEN 'registry'
            WHEN 'LEGAL_IDENTIFIER' THEN 'registry'
            ELSE NULL END;
    ELSIF TG_TABLE_NAME IN (
        'organization_lifecycle_requests',
        'organization_lifecycle_audit',
        'organization_lifecycle_outbox'
    ) THEN
        v_family := 'lifecycle';
    ELSIF TG_TABLE_NAME IN (
        'organization_membership_requests',
        'organization_membership_audit',
        'organization_membership_outbox'
    ) THEN
        v_family := 'membership';
    END IF;
    -- Fail closed if an unrecognized evidence kind or trigger table appears.
    PERFORM company_configuration.require_org_issuer_commit_fence(
        NEW.tenant_id, v_family
    );
    RETURN NULL; -- AFTER ROW trigger ignores return value.
END $$;
REVOKE ALL ON FUNCTION company_configuration.guard_org_issuer_commit_fence()
    FROM PUBLIC;

-- All nine evidence surfaces, not only domain base tables, must pass the
-- commit-time issuer role guard. Existing native deferred evidence checks and
-- all pre-existing SQL issuer guards still run.
CREATE CONSTRAINT TRIGGER org_cmd_request_commit_issuer_fence
AFTER INSERT ON company_configuration.organization_command_requests
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION company_configuration.guard_org_issuer_commit_fence();

CREATE CONSTRAINT TRIGGER org_cmd_audit_commit_issuer_fence
AFTER INSERT ON company_configuration.organization_command_audit
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION company_configuration.guard_org_issuer_commit_fence();

CREATE CONSTRAINT TRIGGER org_cmd_outbox_commit_issuer_fence
AFTER INSERT ON company_configuration.organization_command_outbox
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION company_configuration.guard_org_issuer_commit_fence();

CREATE CONSTRAINT TRIGGER org_lifecycle_request_commit_issuer_fence
AFTER INSERT ON company_configuration.organization_lifecycle_requests
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION company_configuration.guard_org_issuer_commit_fence();

CREATE CONSTRAINT TRIGGER org_lifecycle_audit_commit_issuer_fence
AFTER INSERT ON company_configuration.organization_lifecycle_audit
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION company_configuration.guard_org_issuer_commit_fence();

CREATE CONSTRAINT TRIGGER org_lifecycle_outbox_commit_issuer_fence
AFTER INSERT ON company_configuration.organization_lifecycle_outbox
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION company_configuration.guard_org_issuer_commit_fence();

CREATE CONSTRAINT TRIGGER org_membership_request_commit_issuer_fence
AFTER INSERT ON company_configuration.organization_membership_requests
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION company_configuration.guard_org_issuer_commit_fence();

CREATE CONSTRAINT TRIGGER org_membership_audit_commit_issuer_fence
AFTER INSERT ON company_configuration.organization_membership_audit
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION company_configuration.guard_org_issuer_commit_fence();

CREATE CONSTRAINT TRIGGER org_membership_outbox_commit_issuer_fence
AFTER INSERT ON company_configuration.organization_membership_outbox
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION company_configuration.guard_org_issuer_commit_fence();
