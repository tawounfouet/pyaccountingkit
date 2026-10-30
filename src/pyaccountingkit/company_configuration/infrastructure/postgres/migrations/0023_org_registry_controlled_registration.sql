-- L03 ORG-5b3c1 R&D: controlled Establishment and LegalIdentifier registrations.
-- Additive migration: 0001..0022 remain SHA256-identical. No IAM authenticity claim.
CREATE TABLE company_configuration.organization_registry_command_issuers (
    login_role text PRIMARY KEY CHECK (btrim(login_role)<>'' AND btrim(login_role)=login_role),
    tenant_id text NOT NULL CHECK (btrim(tenant_id)<>'' AND btrim(tenant_id)=tenant_id),
    enabled boolean NOT NULL DEFAULT true
);
REVOKE ALL ON company_configuration.organization_registry_command_issuers FROM PUBLIC;

-- An owner-controlled SQL login binding, NOT a caller-provided actor string,
-- is the authority boundary. Deny ordinary runtime INSERTs even where legacy
-- table permissions remain on the shared request/audit/outbox tables.
CREATE FUNCTION company_configuration.require_org_registry_issuer(p_tenant text)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,pg_temp AS $$
BEGIN
    IF p_tenant IS DISTINCT FROM company_configuration.bound_tenant()
       OR NOT EXISTS (
           SELECT 1
           FROM company_configuration.organization_registry_command_issuers a
           WHERE a.login_role=session_user AND a.tenant_id=p_tenant AND a.enabled
       ) THEN
        RAISE EXCEPTION 'Independent registry SQL command authority required'
            USING ERRCODE='42501';
    END IF;
END $$;
REVOKE ALL ON FUNCTION company_configuration.require_org_registry_issuer(text)
    FROM PUBLIC;

CREATE FUNCTION company_configuration.guard_org_registry_issuer()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,pg_temp AS $$
DECLARE v_kind text;
BEGIN
    IF TG_TABLE_NAME='organizational_establishments' THEN
        v_kind := 'ESTABLISHMENT';
    ELSIF TG_TABLE_NAME='organizational_legal_identifiers' THEN
        v_kind := 'LEGAL_IDENTIFIER';
    ELSE
        v_kind := NEW.target_kind;
    END IF;
    IF v_kind IN ('ESTABLISHMENT','LEGAL_IDENTIFIER') THEN
        PERFORM company_configuration.require_org_registry_issuer(NEW.tenant_id);
    END IF;
    RETURN NEW;
END $$;
REVOKE ALL ON FUNCTION company_configuration.guard_org_registry_issuer()
    FROM PUBLIC;

CREATE TRIGGER org_establishment_registry_issuer_guard
BEFORE INSERT ON company_configuration.organizational_establishments
FOR EACH ROW EXECUTE FUNCTION company_configuration.guard_org_registry_issuer();
CREATE TRIGGER org_identifier_registry_issuer_guard
BEFORE INSERT ON company_configuration.organizational_legal_identifiers
FOR EACH ROW EXECUTE FUNCTION company_configuration.guard_org_registry_issuer();
CREATE TRIGGER org_command_request_registry_issuer_guard
BEFORE INSERT ON company_configuration.organization_command_requests
FOR EACH ROW EXECUTE FUNCTION company_configuration.guard_org_registry_issuer();
CREATE TRIGGER org_command_audit_registry_issuer_guard
BEFORE INSERT ON company_configuration.organization_command_audit
FOR EACH ROW EXECUTE FUNCTION company_configuration.guard_org_registry_issuer();
CREATE TRIGGER org_command_outbox_registry_issuer_guard
BEFORE INSERT ON company_configuration.organization_command_outbox
FOR EACH ROW EXECUTE FUNCTION company_configuration.guard_org_registry_issuer();

CREATE FUNCTION company_configuration.register_establishment_controlled(
    p_tenant text, p_establishment uuid, p_legal_entity uuid,
    p_name text, p_country text, p_valid_from date, p_valid_to date,
    p_status text, p_revision integer, p_actor text, p_request_key text,
    p_digest text, p_correlation text, p_audit uuid, p_event uuid,
    p_reason text, p_recorded_at timestamptz
) RETURNS void LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,pg_temp AS $$
BEGIN
    PERFORM company_configuration.require_org_registry_issuer(p_tenant);
    IF p_revision IS DISTINCT FROM 1 OR p_actor IS NULL OR btrim(p_actor)=''
       OR p_request_key IS NULL OR btrim(p_request_key)='' THEN
        RAISE EXCEPTION 'Invalid controlled Establishment registration'
            USING ERRCODE='23514';
    END IF;
    PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(
        'cc:tenant:'||p_tenant,0
    ));
    INSERT INTO company_configuration.organizational_establishments
        (tenant_id,establishment_id,legal_entity_id,name,country,
         valid_from,valid_to,status,revision)
    VALUES (p_tenant,p_establishment,p_legal_entity,p_name,p_country,
            p_valid_from,p_valid_to,p_status,p_revision);

    INSERT INTO company_configuration.organization_command_audit
        (record_id,tenant_id,actor_id,action,target_kind,target_id,
         company_id,legal_entity_id,before_revision,after_revision,reason,
         correlation_id,recorded_at)
    VALUES (p_audit,p_tenant,p_actor,'organization.establishment.register',
            'ESTABLISHMENT',p_establishment,NULL,p_legal_entity,0,1,
            p_reason,p_correlation,p_recorded_at);

    INSERT INTO company_configuration.organization_command_outbox
        (event_id,tenant_id,event_type,schema_version,target_kind,target_id,
         company_id,legal_entity_id,revision,correlation_id,recorded_at)
    VALUES (p_event,p_tenant,'organization.establishment.register',1,
            'ESTABLISHMENT',p_establishment,NULL,p_legal_entity,1,
            p_correlation,p_recorded_at);

    INSERT INTO company_configuration.organization_command_requests
        (tenant_id,actor_id,action,request_key,request_digest,target_kind,
         target_id,revision,correlation_id,audit_id,event_id)
    VALUES (p_tenant,p_actor,'organization.establishment.register',p_request_key,
            p_digest,'ESTABLISHMENT',p_establishment,1,p_correlation,p_audit,p_event);
END $$;
REVOKE ALL ON FUNCTION company_configuration.register_establishment_controlled(
    text,uuid,uuid,text,text,date,date,text,integer,text,text,text,text,
    uuid,uuid,text,timestamptz
) FROM PUBLIC;

CREATE FUNCTION company_configuration.register_legal_identifier_controlled(
    p_tenant text, p_identifier uuid, p_legal_entity uuid, p_scheme text,
    p_value text, p_issuer text, p_jurisdiction text, p_valid_from date,
    p_valid_to date, p_source_ref text, p_actor text, p_request_key text,
    p_digest text, p_correlation text, p_audit uuid, p_event uuid,
    p_reason text, p_recorded_at timestamptz
) RETURNS void LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,pg_temp AS $$
BEGIN
    PERFORM company_configuration.require_org_registry_issuer(p_tenant);
    IF p_actor IS NULL OR btrim(p_actor)=''
       OR p_request_key IS NULL OR btrim(p_request_key)='' THEN
        RAISE EXCEPTION 'Invalid controlled LegalIdentifier registration'
            USING ERRCODE='23514';
    END IF;
    PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(
        'cc:tenant:'||p_tenant,0
    ));
    INSERT INTO company_configuration.organizational_legal_identifiers
        (tenant_id,identifier_id,legal_entity_id,scheme,value,issuer,
         jurisdiction,valid_from,valid_to,source_ref)
    VALUES (p_tenant,p_identifier,p_legal_entity,p_scheme,p_value,p_issuer,
            p_jurisdiction,p_valid_from,p_valid_to,p_source_ref);

    INSERT INTO company_configuration.organization_command_audit
        (record_id,tenant_id,actor_id,action,target_kind,target_id,
         company_id,legal_entity_id,before_revision,after_revision,reason,
         correlation_id,recorded_at)
    VALUES (p_audit,p_tenant,p_actor,'organization.legal_identifier.register',
            'LEGAL_IDENTIFIER',p_identifier,NULL,p_legal_entity,0,1,
            p_reason,p_correlation,p_recorded_at);

    INSERT INTO company_configuration.organization_command_outbox
        (event_id,tenant_id,event_type,schema_version,target_kind,target_id,
         company_id,legal_entity_id,revision,correlation_id,recorded_at)
    VALUES (p_event,p_tenant,'organization.legal_identifier.register',1,
            'LEGAL_IDENTIFIER',p_identifier,NULL,p_legal_entity,1,
            p_correlation,p_recorded_at);

    INSERT INTO company_configuration.organization_command_requests
        (tenant_id,actor_id,action,request_key,request_digest,target_kind,
         target_id,revision,correlation_id,audit_id,event_id)
    VALUES (p_tenant,p_actor,'organization.legal_identifier.register',p_request_key,
            p_digest,'LEGAL_IDENTIFIER',p_identifier,1,p_correlation,p_audit,p_event);
END $$;
REVOKE ALL ON FUNCTION company_configuration.register_legal_identifier_controlled(
    text,uuid,uuid,text,text,text,text,date,date,text,text,text,text,text,
    uuid,uuid,text,timestamptz
) FROM PUBLIC;
