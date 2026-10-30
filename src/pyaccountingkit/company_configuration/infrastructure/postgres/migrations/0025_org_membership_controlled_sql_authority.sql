-- L03 ORG-5b3c3 R&D: independent membership SQL command issuer.
-- Additive: migrations 0001..0024 are byte-for-byte immutable.
-- A coherent chain of membership evidence alone must not authorize a write.
CREATE TABLE company_configuration.organization_membership_command_issuers (
    login_role text PRIMARY KEY CHECK (
        btrim(login_role)<>'' AND btrim(login_role)=login_role
    ),
    tenant_id text NOT NULL CHECK (
        btrim(tenant_id)<>'' AND btrim(tenant_id)=tenant_id
    ),
    enabled boolean NOT NULL DEFAULT true
);
REVOKE ALL ON company_configuration.organization_membership_command_issuers
    FROM PUBLIC;

CREATE FUNCTION company_configuration.require_org_membership_issuer(p_tenant text)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,pg_temp AS $$
BEGIN
    IF p_tenant IS DISTINCT FROM company_configuration.bound_tenant()
       OR NOT EXISTS (
           SELECT 1
           FROM company_configuration.organization_membership_command_issuers a
           WHERE a.login_role=session_user AND a.tenant_id=p_tenant AND a.enabled
       ) THEN
        RAISE EXCEPTION 'Independent membership SQL command authority required'
            USING ERRCODE='42501';
    END IF;
END $$;
REVOKE ALL ON FUNCTION company_configuration.require_org_membership_issuer(text)
    FROM PUBLIC;

-- Defense in depth: deny all four INSERT surfaces even if an ordinary
-- runtime role accidentally regains direct table INSERT privileges.
CREATE FUNCTION company_configuration.guard_org_membership_issuer()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,pg_temp AS $$
BEGIN
    PERFORM company_configuration.require_org_membership_issuer(NEW.tenant_id);
    RETURN NEW;
END $$;
REVOKE ALL ON FUNCTION company_configuration.guard_org_membership_issuer()
    FROM PUBLIC;
CREATE TRIGGER org_membership_revision_issuer_guard
BEFORE INSERT ON company_configuration.organizational_membership_revisions
FOR EACH ROW EXECUTE FUNCTION company_configuration.guard_org_membership_issuer();
CREATE TRIGGER org_membership_request_issuer_guard
BEFORE INSERT ON company_configuration.organization_membership_requests
FOR EACH ROW EXECUTE FUNCTION company_configuration.guard_org_membership_issuer();
CREATE TRIGGER org_membership_audit_issuer_guard
BEFORE INSERT ON company_configuration.organization_membership_audit
FOR EACH ROW EXECUTE FUNCTION company_configuration.guard_org_membership_issuer();
CREATE TRIGGER org_membership_outbox_issuer_guard
BEFORE INSERT ON company_configuration.organization_membership_outbox
FOR EACH ROW EXECUTE FUNCTION company_configuration.guard_org_membership_issuer();

-- SQL issuer session role and owner-maintained tenant binding are trusted;
-- actor_id is still caller-supplied and NOT authenticated human provenance.
-- 0015 parent, overlap, revision/temporal and 0018 archive guards, and
-- 0021 deferred membership-native COMMIT evidence check still execute.
CREATE FUNCTION company_configuration.register_membership_revision_controlled(
    p_tenant text, p_membership uuid, p_revision integer, p_company uuid,
    p_legal_entity uuid, p_kind text, p_exclusive boolean,
    p_valid_from date, p_valid_to date, p_recorded_at timestamptz,
    p_source_ref text, p_actor text, p_request_key text, p_digest text,
    p_correlation text, p_audit uuid, p_event uuid, p_reason text
) RETURNS void LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,pg_temp AS $$
DECLARE
    v_action text;
    v_previous_revision integer;
BEGIN
    PERFORM company_configuration.require_org_membership_issuer(p_tenant);
    IF p_membership IS NULL OR p_company IS NULL OR p_legal_entity IS NULL
       OR p_revision IS NULL OR p_revision < 1
       OR p_actor IS NULL OR btrim(p_actor)=''
       OR p_request_key IS NULL OR btrim(p_request_key)=''
       OR p_reason IS NULL OR btrim(p_reason)=''
       OR p_recorded_at IS NULL THEN
        RAISE EXCEPTION 'Invalid controlled membership revision'
            USING ERRCODE='23514';
    END IF;
    v_action := CASE WHEN p_revision=1 THEN 'organization.membership.assign'
                     ELSE 'organization.membership.end' END;
    -- Consistent lock order: coarse tenant lock first (idempotency), then
    -- 0018 company affiliation lock and 0015 legal_entity/kind conflict lock.
    PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(
        'cc:tenant:'||p_tenant,0
    ));
    SELECT max(revision) INTO v_previous_revision
    FROM company_configuration.organizational_membership_revisions
    WHERE tenant_id=p_tenant AND membership_id=p_membership;
    IF (v_previous_revision IS NULL AND p_revision<>1)
       OR (v_previous_revision IS NOT NULL AND
           p_revision<>v_previous_revision+1) THEN
        RAISE EXCEPTION 'Membership optimistic revision conflict'
            USING ERRCODE='23514';
    END IF;

    INSERT INTO company_configuration.organizational_membership_revisions
        (tenant_id,membership_id,revision,company_id,legal_entity_id,
         kind,exclusive,valid_from,valid_to,recorded_at,source_ref)
    VALUES (p_tenant,p_membership,p_revision,p_company,p_legal_entity,
            p_kind,p_exclusive,p_valid_from,p_valid_to,p_recorded_at,p_source_ref);

    INSERT INTO company_configuration.organization_membership_audit
        (record_id,tenant_id,actor_id,action,membership_id,company_id,
         legal_entity_id,before_revision,after_revision,valid_from,valid_to,
         source_ref,reason,correlation_id,recorded_at)
    VALUES (p_audit,p_tenant,p_actor,v_action,p_membership,p_company,
            p_legal_entity,p_revision-1,p_revision,p_valid_from,p_valid_to,
            p_source_ref,p_reason,p_correlation,p_recorded_at);

    INSERT INTO company_configuration.organization_membership_outbox
        (event_id,tenant_id,event_type,schema_version,membership_id,company_id,
         legal_entity_id,revision,kind,exclusive,valid_from,valid_to,
         source_ref,correlation_id,recorded_at)
    VALUES (p_event,p_tenant,v_action,1,p_membership,p_company,
            p_legal_entity,p_revision,p_kind,p_exclusive,p_valid_from,p_valid_to,
            p_source_ref,p_correlation,p_recorded_at);

    INSERT INTO company_configuration.organization_membership_requests
        (tenant_id,actor_id,action,request_key,request_digest,membership_id,
         company_id,legal_entity_id,revision,correlation_id,audit_id,event_id)
    VALUES (p_tenant,p_actor,v_action,p_request_key,p_digest,p_membership,
            p_company,p_legal_entity,p_revision,p_correlation,p_audit,p_event);
END $$;
REVOKE ALL ON FUNCTION company_configuration.register_membership_revision_controlled(
    text,uuid,integer,uuid,uuid,text,boolean,date,date,timestamptz,
    text,text,text,text,text,uuid,uuid,text
) FROM PUBLIC;
