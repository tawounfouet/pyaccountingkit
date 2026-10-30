-- G3-C02b1: durable, cross-process organization command JTI replay defense.
-- Additive migration; 0001..0025 are immutable and source-verified.
-- The table holds no signed bearer token, actor, action or credential.
CREATE TABLE company_configuration.organization_command_nonces (
    tenant_id text NOT NULL CHECK (btrim(tenant_id)<>'' AND btrim(tenant_id)=tenant_id),
    issuer text NOT NULL CHECK (btrim(issuer)<>'' AND btrim(issuer)=issuer),
    nonce uuid NOT NULL,
    expires_at timestamptz NOT NULL,
    consumed_at timestamptz NOT NULL DEFAULT pg_catalog.clock_timestamp(),
    -- Global uniqueness per independently verified issuer, including tenants.
    PRIMARY KEY (issuer,nonce)
);
CREATE INDEX org_command_nonces_retention
ON company_configuration.organization_command_nonces (expires_at);
ALTER TABLE company_configuration.organization_command_nonces ENABLE ROW LEVEL SECURITY;
ALTER TABLE company_configuration.organization_command_nonces FORCE ROW LEVEL SECURITY;
CREATE POLICY isolate_tenant ON company_configuration.organization_command_nonces
USING (tenant_id=company_configuration.bound_tenant())
WITH CHECK (tenant_id=company_configuration.bound_tenant());
REVOKE ALL ON company_configuration.organization_command_nonces FROM PUBLIC;

-- Owner-controlled mapping is distinct from domain SQL issuers, ordinary
-- runtime roles, and caller-asserted actor/tenant/GUC values.
CREATE TABLE company_configuration.organization_nonce_consumers (
    login_role text PRIMARY KEY CHECK (btrim(login_role)<>'' AND btrim(login_role)=login_role),
    tenant_id text NOT NULL CHECK (btrim(tenant_id)<>'' AND btrim(tenant_id)=tenant_id),
    enabled boolean NOT NULL DEFAULT true
);
REVOKE ALL ON company_configuration.organization_nonce_consumers FROM PUBLIC;

-- SECURITY DEFINER does not authenticate a human: only an independently
-- provisioned SQL login can consume a verified token's one-use JTI.
-- PostgreSQL's clock, not the caller's application clock, bounds expiry.
CREATE FUNCTION company_configuration.consume_organization_command_nonce(
    p_tenant text, p_issuer text, p_nonce uuid, p_expires_at timestamptz
) RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,pg_temp AS $$
DECLARE v_inserted integer;
DECLARE v_now timestamptz;
BEGIN
    IF p_tenant IS DISTINCT FROM company_configuration.bound_tenant()
       OR NOT EXISTS (
           SELECT 1 FROM company_configuration.organization_nonce_consumers a
           WHERE a.login_role=session_user AND a.tenant_id=p_tenant AND a.enabled
       ) THEN
        RAISE EXCEPTION 'Independent nonce consumer SQL authority required'
            USING ERRCODE='42501';
    END IF;

    v_now := pg_catalog.clock_timestamp();
    IF p_issuer IS NULL OR btrim(p_issuer)='' OR p_issuer<>btrim(p_issuer)
       OR p_nonce IS NULL OR p_expires_at IS NULL
       OR p_expires_at<=v_now OR p_expires_at>v_now+interval '10 minutes' THEN
        RAISE EXCEPTION 'Invalid signed command nonce/expiry'
            USING ERRCODE='23514';
    END IF;

    INSERT INTO company_configuration.organization_command_nonces
        (tenant_id,issuer,nonce,expires_at,consumed_at)
    VALUES (p_tenant,p_issuer,p_nonce,p_expires_at,v_now)
    ON CONFLICT (issuer,nonce) DO NOTHING;
    GET DIAGNOSTICS v_inserted = ROW_COUNT;
    RETURN v_inserted=1;
END $$;
REVOKE ALL ON FUNCTION company_configuration.consume_organization_command_nonce(
    text,text,uuid,timestamptz
) FROM PUBLIC;

-- Even a misconfigured direct INSERT grant cannot bypass the login authority.
CREATE FUNCTION company_configuration.guard_org_command_nonce_insert()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,pg_temp AS $$
BEGIN
    IF NEW.tenant_id IS DISTINCT FROM company_configuration.bound_tenant()
       OR NOT EXISTS (
           SELECT 1 FROM company_configuration.organization_nonce_consumers a
           WHERE a.login_role=session_user AND a.tenant_id=NEW.tenant_id AND a.enabled
       ) THEN
        RAISE EXCEPTION 'Independent nonce consumer SQL authority required'
            USING ERRCODE='42501';
    END IF;
    RETURN NEW;
END $$;
REVOKE ALL ON FUNCTION company_configuration.guard_org_command_nonce_insert()
    FROM PUBLIC;
CREATE TRIGGER org_command_nonce_insert_guard
BEFORE INSERT ON company_configuration.organization_command_nonces
FOR EACH ROW EXECUTE FUNCTION company_configuration.guard_org_command_nonce_insert();

-- Nonce audit entries are immutable even for a misconfigured app login.
CREATE TRIGGER org_command_nonce_no_mutation
BEFORE UPDATE OR DELETE ON company_configuration.organization_command_nonces
FOR EACH ROW EXECUTE FUNCTION company_configuration.forbid_evidence_mutation();
