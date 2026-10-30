-- L03 ORG-5b1 R&D: fail-closed lifecycle evidence at transaction COMMIT.
-- Migration is additive: 0001..0018 remain byte-for-byte unchanged.
--
-- The app/runtime login has direct INSERT rights today. A row-level trigger
-- from 0017 validates allowed state transitions, but did not ensure that
-- request + audit + outbox were committed with the new lifecycle revision.
-- A deferred CONSTRAINT trigger rejects a bare lifecycle INSERT at COMMIT.
-- This is an integrity guarantee, NOT SQL principal/actor authentication.
CREATE FUNCTION company_configuration.require_org_lifecycle_evidence()
RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $$
DECLARE
    expected_action text;
    expected_kind text;
    v_target_uuid uuid;
    previous_status text;
BEGIN
    IF TG_TABLE_NAME = 'organizational_company_revisions' THEN
        expected_action := 'organization.company.transition';
        expected_kind := 'COMPANY';
        v_target_uuid := NEW.company_id;
        IF NEW.revision = 2 THEN
            SELECT c.status INTO previous_status
            FROM company_configuration.organizational_companies c
            WHERE c.tenant_id=NEW.tenant_id AND c.company_id=NEW.company_id;
        ELSE
            SELECT r.status INTO previous_status
            FROM company_configuration.organizational_company_revisions r
            WHERE r.tenant_id=NEW.tenant_id
              AND r.company_id=NEW.company_id AND r.revision=NEW.revision-1;
        END IF;
    ELSIF TG_TABLE_NAME = 'organizational_establishment_revisions' THEN
        expected_action := 'organization.establishment.transition';
        expected_kind := 'ESTABLISHMENT';
        v_target_uuid := NEW.establishment_id;
        IF NEW.revision = 2 THEN
            SELECT e.status INTO previous_status
            FROM company_configuration.organizational_establishments e
            WHERE e.tenant_id=NEW.tenant_id
              AND e.establishment_id=NEW.establishment_id;
        ELSE
            SELECT r.status INTO previous_status
            FROM company_configuration.organizational_establishment_revisions r
            WHERE r.tenant_id=NEW.tenant_id
              AND r.establishment_id=NEW.establishment_id
              AND r.revision=NEW.revision-1;
        END IF;
    ELSE
        RAISE EXCEPTION 'Unexpected organization lifecycle table'
            USING ERRCODE='23514';
    END IF;

    IF previous_status IS NULL OR NOT EXISTS (
        SELECT 1
        FROM company_configuration.organization_lifecycle_requests request
        JOIN company_configuration.organization_lifecycle_audit audit
          ON audit.record_id=request.audit_id
        JOIN company_configuration.organization_lifecycle_outbox event
          ON event.event_id=request.event_id
        WHERE request.tenant_id=NEW.tenant_id
          AND request.action=expected_action
          AND request.target_kind=expected_kind
          AND request.target_id=v_target_uuid
          AND request.revision=NEW.revision
          AND audit.tenant_id=request.tenant_id
          AND audit.actor_id=request.actor_id
          AND audit.action=request.action
          AND audit.target_kind=request.target_kind
          AND audit.target_id=request.target_id
          AND audit.before_revision=NEW.revision-1
          AND audit.after_revision=NEW.revision
          AND audit.from_status=previous_status
          AND audit.to_status=NEW.status
          AND audit.correlation_id=request.correlation_id
          AND audit.recorded_at=NEW.recorded_at
          AND event.tenant_id=request.tenant_id
          AND event.event_type=request.action
          AND event.target_kind=request.target_kind
          AND event.target_id=request.target_id
          AND event.revision=NEW.revision
          AND event.from_status=previous_status
          AND event.to_status=NEW.status
          AND event.correlation_id=request.correlation_id
          AND event.recorded_at=NEW.recorded_at
    ) THEN
        RAISE EXCEPTION
            'Lifecycle revision requires matching request, audit and outbox in one transaction'
            USING ERRCODE='23514';
    END IF;
    RETURN NULL;
END $$;

CREATE CONSTRAINT TRIGGER organization_company_commit_evidence
AFTER INSERT ON company_configuration.organizational_company_revisions
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION company_configuration.require_org_lifecycle_evidence();

CREATE CONSTRAINT TRIGGER organization_establishment_commit_evidence
AFTER INSERT ON company_configuration.organizational_establishment_revisions
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION company_configuration.require_org_lifecycle_evidence();

REVOKE ALL ON FUNCTION company_configuration.require_org_lifecycle_evidence()
    FROM PUBLIC;
