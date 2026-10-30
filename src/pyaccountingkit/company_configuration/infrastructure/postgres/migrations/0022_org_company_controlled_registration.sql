-- L03 ORG-5b3b R&D: independent, tenant-bound SQL authority for Company registration.
-- Migrations 0001..0021 are immutable. This is a Company-only cutover:
-- establishment / legal identifier / membership / lifecycle remain on older paths.
-- SQL login authority is independently provisioned; human IAM is NOT attested here.
CREATE TABLE company_configuration.organization_company_command_issuers (
    login_role text PRIMARY KEY CHECK (btrim(login_role)<>'' AND btrim(login_role)=login_role),
    tenant_id text NOT NULL CHECK (btrim(tenant_id)<>'' AND btrim(tenant_id)=tenant_id),
    enabled boolean NOT NULL DEFAULT true
);
REVOKE ALL ON company_configuration.organization_company_command_issuers FROM PUBLIC;

-- This trigger protects Company rows and the Company subset of shared evidence
-- even if an older migration or deployment accidentally preserves INSERT grants.
-- No client-controlled GUC, caller-asserted actor or SET ROLE is trusted.
CREATE FUNCTION company_configuration.guard_company_command_issuer()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,pg_temp AS $$
DECLARE v_tenant text;
DECLARE v_kind text;
BEGIN
    IF TG_TABLE_NAME='organizational_companies' THEN
        v_kind := 'COMPANY';
    ELSE
        v_kind := NEW.target_kind;
    END IF;
    IF v_kind IS DISTINCT FROM 'COMPANY' THEN
        RETURN NEW;
    END IF;
    v_tenant := NEW.tenant_id;
    IF v_tenant IS DISTINCT FROM company_configuration.bound_tenant()
       OR NOT EXISTS (
           SELECT 1
           FROM company_configuration.organization_company_command_issuers a
           WHERE a.login_role=session_user AND a.tenant_id=v_tenant
             AND a.enabled
       ) THEN
        RAISE EXCEPTION 'Independent Company command SQL authority required'
            USING ERRCODE='42501';
    END IF;
    RETURN NEW;
END $$;
REVOKE ALL ON FUNCTION company_configuration.guard_company_command_issuer() FROM PUBLIC;

CREATE TRIGGER org_company_issuer_guard
BEFORE INSERT ON company_configuration.organizational_companies
FOR EACH ROW EXECUTE FUNCTION company_configuration.guard_company_command_issuer();

CREATE TRIGGER org_company_request_issuer_guard
BEFORE INSERT ON company_configuration.organization_command_requests
FOR EACH ROW EXECUTE FUNCTION company_configuration.guard_company_command_issuer();
CREATE TRIGGER org_company_audit_issuer_guard
BEFORE INSERT ON company_configuration.organization_command_audit
FOR EACH ROW EXECUTE FUNCTION company_configuration.guard_company_command_issuer();
CREATE TRIGGER org_company_outbox_issuer_guard
BEFORE INSERT ON company_configuration.organization_command_outbox
FOR EACH ROW EXECUTE FUNCTION company_configuration.guard_company_command_issuer();

-- The independent issuer login has EXECUTE (not direct INSERT) on this atomic
-- function. Its credentials must NOT live alongside an ordinary runtime DSN.
-- A compromised issuer remains privileged; credential issuance and human
-- attestation are distinct production IAM controls, deliberately not claimed.
CREATE FUNCTION company_configuration.register_company_controlled(
    p_tenant text,
    p_company_id uuid,
    p_name text,
    p_kind text,
    p_home_country text,
    p_base_currency text,
    p_status text,
    p_revision integer,
    p_actor text,
    p_request_key text,
    p_request_digest text,
    p_correlation text,
    p_audit uuid,
    p_event uuid,
    p_reason text,
    p_recorded_at timestamptz
) RETURNS void LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,pg_temp AS $$
BEGIN
    IF p_tenant IS DISTINCT FROM company_configuration.bound_tenant()
       OR NOT EXISTS (
           SELECT 1 FROM company_configuration.organization_company_command_issuers a
           WHERE a.login_role=session_user AND a.tenant_id=p_tenant AND a.enabled
       ) THEN
        RAISE EXCEPTION 'Independent Company command SQL authority required'
            USING ERRCODE='42501';
    END IF;
    IF p_revision IS DISTINCT FROM 1 OR p_actor IS NULL OR btrim(p_actor)=''
       OR p_request_key IS NULL OR btrim(p_request_key)=''
       OR p_reason IS NULL OR btrim(p_reason)='' THEN
        RAISE EXCEPTION 'Invalid controlled Company registration command'
            USING ERRCODE='23514';
    END IF;
    PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(
        'cc:tenant:'||p_tenant,0
    ));

    INSERT INTO company_configuration.organizational_companies
        (tenant_id,company_id,name,kind,home_country,base_currency,status,revision)
    VALUES (p_tenant,p_company_id,p_name,p_kind,p_home_country,p_base_currency,
            p_status,p_revision);

    INSERT INTO company_configuration.organization_command_audit
        (record_id,tenant_id,actor_id,action,target_kind,target_id,
         company_id,legal_entity_id,before_revision,after_revision,reason,
         correlation_id,recorded_at)
    VALUES (p_audit,p_tenant,p_actor,'organization.company.register',
            'COMPANY',p_company_id,p_company_id,NULL,0,1,p_reason,
            p_correlation,p_recorded_at);

    INSERT INTO company_configuration.organization_command_outbox
        (event_id,tenant_id,event_type,schema_version,target_kind,target_id,
         company_id,legal_entity_id,revision,correlation_id,recorded_at)
    VALUES (p_event,p_tenant,'organization.company.register',1,'COMPANY',
            p_company_id,p_company_id,NULL,1,p_correlation,p_recorded_at);

    INSERT INTO company_configuration.organization_command_requests
        (tenant_id,actor_id,action,request_key,request_digest,target_kind,
         target_id,revision,correlation_id,audit_id,event_id)
    VALUES (p_tenant,p_actor,'organization.company.register',p_request_key,
            p_request_digest,'COMPANY',p_company_id,1,p_correlation,p_audit,p_event);
END $$;

REVOKE ALL ON FUNCTION company_configuration.register_company_controlled(
    text,uuid,text,text,text,text,text,integer,text,text,text,text,
    uuid,uuid,text,timestamptz
) FROM PUBLIC;
