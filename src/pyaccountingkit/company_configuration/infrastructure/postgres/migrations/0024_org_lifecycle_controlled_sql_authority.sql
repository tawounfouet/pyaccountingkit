-- L03 ORG-5b3c2 R&D: independently authorized Company/Establishment lifecycle.
-- Additive: historical migrations 0001..0023 must remain checksum-identical.
-- The ordinary runtime principal must never forge lifecycle state + evidence.
CREATE TABLE company_configuration.organization_lifecycle_command_issuers (
    login_role text PRIMARY KEY CHECK (btrim(login_role)<>'' AND btrim(login_role)=login_role),
    tenant_id text NOT NULL CHECK (btrim(tenant_id)<>'' AND btrim(tenant_id)=tenant_id),
    enabled boolean NOT NULL DEFAULT true
);
REVOKE ALL ON company_configuration.organization_lifecycle_command_issuers FROM PUBLIC;

CREATE FUNCTION company_configuration.require_org_lifecycle_issuer(p_tenant text)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,pg_temp AS $$
BEGIN
    IF p_tenant IS DISTINCT FROM company_configuration.bound_tenant()
       OR NOT EXISTS (
           SELECT 1
           FROM company_configuration.organization_lifecycle_command_issuers a
           WHERE a.login_role=session_user AND a.tenant_id=p_tenant AND a.enabled
       ) THEN
        RAISE EXCEPTION 'Independent lifecycle SQL command authority required'
            USING ERRCODE='42501';
    END IF;
END $$;
REVOKE ALL ON FUNCTION company_configuration.require_org_lifecycle_issuer(text)
    FROM PUBLIC;

-- All lifecycle revisions and their audit/request/outbox tables are now
-- issuer-only. The triggers fail closed even if legacy INSERT were re-granted.
CREATE FUNCTION company_configuration.guard_org_lifecycle_issuer()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,pg_temp AS $$
BEGIN
    PERFORM company_configuration.require_org_lifecycle_issuer(NEW.tenant_id);
    RETURN NEW;
END $$;
REVOKE ALL ON FUNCTION company_configuration.guard_org_lifecycle_issuer()
    FROM PUBLIC;
CREATE TRIGGER company_revision_lifecycle_issuer
BEFORE INSERT ON company_configuration.organizational_company_revisions
FOR EACH ROW EXECUTE FUNCTION company_configuration.guard_org_lifecycle_issuer();
CREATE TRIGGER establishment_revision_lifecycle_issuer
BEFORE INSERT ON company_configuration.organizational_establishment_revisions
FOR EACH ROW EXECUTE FUNCTION company_configuration.guard_org_lifecycle_issuer();
CREATE TRIGGER lifecycle_request_issuer
BEFORE INSERT ON company_configuration.organization_lifecycle_requests
FOR EACH ROW EXECUTE FUNCTION company_configuration.guard_org_lifecycle_issuer();
CREATE TRIGGER lifecycle_audit_issuer
BEFORE INSERT ON company_configuration.organization_lifecycle_audit
FOR EACH ROW EXECUTE FUNCTION company_configuration.guard_org_lifecycle_issuer();
CREATE TRIGGER lifecycle_outbox_issuer
BEFORE INSERT ON company_configuration.organization_lifecycle_outbox
FOR EACH ROW EXECUTE FUNCTION company_configuration.guard_org_lifecycle_issuer();

-- SECURITY DEFINER is ONLY usable from an independently provisioned issuer
-- login. It does not authenticate the human actor; that is the issuer boundary.
-- Serializes with the 0017 per-target lock and 0018 affiliation archive lock.
-- The existing 0017/0018 row guards and 0019 deferred COMMIT guard still run.
CREATE FUNCTION company_configuration.transition_organization_controlled(
    p_tenant text, p_target_kind text, p_target_id uuid,
    p_revision integer, p_from_status text, p_to_status text,
    p_recorded_at timestamptz, p_source_ref text, p_actor text,
    p_request_key text, p_digest text, p_correlation text,
    p_audit uuid, p_event uuid, p_reason text
) RETURNS void LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,pg_temp AS $$
DECLARE
    v_status text;
    v_revision integer;
    v_action text;
BEGIN
    PERFORM company_configuration.require_org_lifecycle_issuer(p_tenant);
    IF p_target_kind NOT IN ('COMPANY','ESTABLISHMENT')
       OR p_revision IS NULL OR p_revision < 2
       OR p_actor IS NULL OR btrim(p_actor)=''
       OR p_request_key IS NULL OR btrim(p_request_key)=''
       OR p_reason IS NULL OR btrim(p_reason)=''
       OR p_recorded_at IS NULL THEN
        RAISE EXCEPTION 'Invalid controlled lifecycle transition'
            USING ERRCODE='23514';
    END IF;
    PERFORM pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtextextended('cc:tenant:'||p_tenant,0)
    );
    IF p_target_kind='COMPANY' THEN
        v_action := 'organization.company.transition';
        SELECT COALESCE(rev.status,base.status),
               COALESCE(rev.revision,base.revision)
        INTO v_status,v_revision
        FROM company_configuration.organizational_companies base
        LEFT JOIN LATERAL (
            SELECT status,revision
            FROM company_configuration.organizational_company_revisions
            WHERE tenant_id=base.tenant_id AND company_id=base.company_id
            ORDER BY revision DESC LIMIT 1
        ) rev ON true
        WHERE base.tenant_id=p_tenant AND base.company_id=p_target_id;
    ELSE
        v_action := 'organization.establishment.transition';
        SELECT COALESCE(rev.status,base.status),
               COALESCE(rev.revision,base.revision)
        INTO v_status,v_revision
        FROM company_configuration.organizational_establishments base
        LEFT JOIN LATERAL (
            SELECT status,revision
            FROM company_configuration.organizational_establishment_revisions
            WHERE tenant_id=base.tenant_id
              AND establishment_id=base.establishment_id
            ORDER BY revision DESC LIMIT 1
        ) rev ON true
        WHERE base.tenant_id=p_tenant AND base.establishment_id=p_target_id;
    END IF;
    IF v_status IS DISTINCT FROM p_from_status
       OR v_revision IS DISTINCT FROM p_revision-1 THEN
        RAISE EXCEPTION 'Lifecycle optimistic revision / previous-status conflict'
            USING ERRCODE='23514';
    END IF;

    IF p_target_kind='COMPANY' THEN
        INSERT INTO company_configuration.organizational_company_revisions
            (tenant_id,company_id,revision,status,recorded_at,source_ref)
        VALUES (p_tenant,p_target_id,p_revision,p_to_status,
                p_recorded_at,p_source_ref);
    ELSE
        INSERT INTO company_configuration.organizational_establishment_revisions
            (tenant_id,establishment_id,revision,status,recorded_at,source_ref)
        VALUES (p_tenant,p_target_id,p_revision,p_to_status,
                p_recorded_at,p_source_ref);
    END IF;

    INSERT INTO company_configuration.organization_lifecycle_audit
        (record_id,tenant_id,actor_id,action,target_kind,target_id,
         before_revision,after_revision,from_status,to_status,reason,
         correlation_id,recorded_at)
    VALUES (p_audit,p_tenant,p_actor,v_action,p_target_kind,p_target_id,
            p_revision-1,p_revision,p_from_status,p_to_status,p_reason,
            p_correlation,p_recorded_at);

    INSERT INTO company_configuration.organization_lifecycle_outbox
        (event_id,tenant_id,event_type,schema_version,target_kind,target_id,
         revision,from_status,to_status,correlation_id,recorded_at)
    VALUES (p_event,p_tenant,v_action,1,p_target_kind,p_target_id,
            p_revision,p_from_status,p_to_status,p_correlation,p_recorded_at);

    INSERT INTO company_configuration.organization_lifecycle_requests
        (tenant_id,actor_id,action,request_key,request_digest,target_kind,
         target_id,revision,correlation_id,audit_id,event_id)
    VALUES (p_tenant,p_actor,v_action,p_request_key,p_digest,p_target_kind,
            p_target_id,p_revision,p_correlation,p_audit,p_event);
END $$;
REVOKE ALL ON FUNCTION company_configuration.transition_organization_controlled(
    text,text,uuid,integer,text,text,timestamptz,text,text,text,text,text,
    uuid,uuid,text
) FROM PUBLIC;
