-- L03 ORG-5b2a R&D: registration data and organization-native evidence
-- must commit together. Additive migration; 0001..0019 immutable.
--
-- Scope: organizational_companies, organizational_establishments,
-- organizational_legal_identifiers. Membership history uses an L02
-- legal-entity-centric event and needs a separate target-aware redesign.
-- This constrains presence/consistency, NOT provenance of human actors.
CREATE FUNCTION company_configuration.require_org_registration_evidence()
RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $$
DECLARE
    v_action text;
    v_kind text;
    v_target_id uuid;
    v_company_id uuid;
    v_legal_entity_id uuid;
BEGIN
    IF TG_TABLE_NAME='organizational_companies' THEN
        v_action := 'organization.company.register';
        v_kind := 'COMPANY';
        v_target_id := NEW.company_id;
        v_company_id := NEW.company_id;
        v_legal_entity_id := NULL;
    ELSIF TG_TABLE_NAME='organizational_establishments' THEN
        v_action := 'organization.establishment.register';
        v_kind := 'ESTABLISHMENT';
        v_target_id := NEW.establishment_id;
        v_company_id := NULL;
        v_legal_entity_id := NEW.legal_entity_id;
    ELSIF TG_TABLE_NAME='organizational_legal_identifiers' THEN
        v_action := 'organization.legal_identifier.register';
        v_kind := 'LEGAL_IDENTIFIER';
        v_target_id := NEW.identifier_id;
        v_company_id := NULL;
        v_legal_entity_id := NEW.legal_entity_id;
    ELSE
        RAISE EXCEPTION 'Unexpected organization registration table'
            USING ERRCODE='23514';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM company_configuration.organization_command_requests AS req
        JOIN company_configuration.organization_command_audit AS aud
          ON aud.record_id=req.audit_id
        JOIN company_configuration.organization_command_outbox AS evt
          ON evt.event_id=req.event_id
        WHERE req.tenant_id=NEW.tenant_id
          AND req.action=v_action
          AND req.target_kind=v_kind
          AND req.target_id=v_target_id
          AND req.revision=1
          AND aud.tenant_id=req.tenant_id
          AND aud.actor_id=req.actor_id
          AND aud.action=req.action
          AND aud.target_kind=req.target_kind
          AND aud.target_id=req.target_id
          AND aud.company_id IS NOT DISTINCT FROM v_company_id
          AND aud.legal_entity_id IS NOT DISTINCT FROM v_legal_entity_id
          AND aud.before_revision=0
          AND aud.after_revision=1
          AND aud.correlation_id=req.correlation_id
          AND evt.tenant_id=req.tenant_id
          AND evt.event_type=req.action
          AND evt.schema_version=1
          AND evt.target_kind=req.target_kind
          AND evt.target_id=req.target_id
          AND evt.company_id IS NOT DISTINCT FROM v_company_id
          AND evt.legal_entity_id IS NOT DISTINCT FROM v_legal_entity_id
          AND evt.revision=1
          AND evt.correlation_id=req.correlation_id
          AND evt.recorded_at=aud.recorded_at
    ) THEN
        RAISE EXCEPTION
          'Organization registration requires matching request, audit and outbox'
            USING ERRCODE='23514';
    END IF;
    RETURN NULL;
END $$;

CREATE CONSTRAINT TRIGGER org_company_registration_evidence
AFTER INSERT ON company_configuration.organizational_companies
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION company_configuration.require_org_registration_evidence();

CREATE CONSTRAINT TRIGGER org_establishment_registration_evidence
AFTER INSERT ON company_configuration.organizational_establishments
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION company_configuration.require_org_registration_evidence();

CREATE CONSTRAINT TRIGGER org_identifier_registration_evidence
AFTER INSERT ON company_configuration.organizational_legal_identifiers
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION company_configuration.require_org_registration_evidence();

REVOKE ALL ON FUNCTION company_configuration.require_org_registration_evidence()
FROM PUBLIC;
