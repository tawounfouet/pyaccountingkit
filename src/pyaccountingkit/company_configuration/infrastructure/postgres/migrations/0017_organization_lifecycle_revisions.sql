-- ORG-4c / L03 R&D. Original 0001..0016 bytes are immutable.
-- Baseline Company/Establishment rows hold revision=1; append-only lifecycle
-- revisions form the authoritative current status for revision >= 2.
-- This is recorded-time state history, NOT retroactive effective-time lifecycle.
CREATE TABLE company_configuration.organizational_company_revisions (
    tenant_id text NOT NULL,
    company_id uuid NOT NULL,
    revision integer NOT NULL CHECK (revision >= 2),
    status text NOT NULL CHECK (status IN ('DRAFT','ACTIVE','INACTIVE','ARCHIVED')),
    recorded_at timestamptz NOT NULL,
    source_ref text NOT NULL CHECK (btrim(source_ref) <> ''),
    PRIMARY KEY (tenant_id,company_id,revision),
    FOREIGN KEY (tenant_id,company_id) REFERENCES
        company_configuration.organizational_companies(tenant_id,company_id)
);
CREATE TABLE company_configuration.organizational_establishment_revisions (
    tenant_id text NOT NULL,
    establishment_id uuid NOT NULL,
    revision integer NOT NULL CHECK (revision >= 2),
    status text NOT NULL CHECK (status IN ('PLANNED','ACTIVE','INACTIVE','CLOSED')),
    recorded_at timestamptz NOT NULL,
    source_ref text NOT NULL CHECK (btrim(source_ref) <> ''),
    PRIMARY KEY (tenant_id,establishment_id,revision),
    FOREIGN KEY (tenant_id,establishment_id) REFERENCES
        company_configuration.organizational_establishments(tenant_id,establishment_id)
);
CREATE FUNCTION company_configuration.validate_organization_lifecycle()
RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $$
DECLARE previous_status text;
DECLARE previous_revision integer;
DECLARE previous_recorded_at timestamptz;
BEGIN
    IF TG_TABLE_NAME='organizational_company_revisions' THEN
        PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(
            'cc:org:company:lifecycle:'||NEW.tenant_id||':'||NEW.company_id::text,0
        ));
        SELECT r.status,r.revision,r.recorded_at INTO
            previous_status,previous_revision,previous_recorded_at
        FROM company_configuration.organizational_company_revisions r
        WHERE r.tenant_id=NEW.tenant_id AND r.company_id=NEW.company_id
        ORDER BY r.revision DESC LIMIT 1;
        IF previous_revision IS NULL THEN
            SELECT c.status,c.revision INTO previous_status,previous_revision
            FROM company_configuration.organizational_companies c
            WHERE c.tenant_id=NEW.tenant_id AND c.company_id=NEW.company_id;
        END IF;
        IF NOT (
            (previous_status='DRAFT' AND NEW.status='ACTIVE')
            OR (previous_status='ACTIVE' AND NEW.status='INACTIVE')
            OR (previous_status='INACTIVE' AND NEW.status IN ('ACTIVE','ARCHIVED'))
        ) THEN
            RAISE EXCEPTION 'Illegal company lifecycle transition'
                USING ERRCODE='23514';
        END IF;
    ELSIF TG_TABLE_NAME='organizational_establishment_revisions' THEN
        PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(
            'cc:org:site:lifecycle:'||NEW.tenant_id||':'||NEW.establishment_id::text,0
        ));
        SELECT r.status,r.revision,r.recorded_at INTO
            previous_status,previous_revision,previous_recorded_at
        FROM company_configuration.organizational_establishment_revisions r
        WHERE r.tenant_id=NEW.tenant_id
          AND r.establishment_id=NEW.establishment_id
        ORDER BY r.revision DESC LIMIT 1;
        IF previous_revision IS NULL THEN
            SELECT e.status,e.revision INTO previous_status,previous_revision
            FROM company_configuration.organizational_establishments e
            WHERE e.tenant_id=NEW.tenant_id
              AND e.establishment_id=NEW.establishment_id;
        END IF;
        IF NOT (
            (previous_status='PLANNED' AND NEW.status IN ('ACTIVE','CLOSED'))
            OR (previous_status='ACTIVE' AND NEW.status IN ('INACTIVE','CLOSED'))
            OR (previous_status='INACTIVE' AND NEW.status IN ('ACTIVE','CLOSED'))
        ) THEN
            RAISE EXCEPTION 'Illegal establishment lifecycle transition'
                USING ERRCODE='23514';
        END IF;
    ELSE
        RAISE EXCEPTION 'Lifecycle trigger attached to unexpected table';
    END IF;
    IF previous_revision IS NULL OR NEW.revision<>previous_revision+1
       OR (previous_recorded_at IS NOT NULL AND
           NEW.recorded_at<=previous_recorded_at) THEN
        RAISE EXCEPTION 'Lifecycle revision/knowledge sequence conflict'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER company_lifecycle_insert_guard
BEFORE INSERT ON company_configuration.organizational_company_revisions
FOR EACH ROW EXECUTE FUNCTION company_configuration.validate_organization_lifecycle();
CREATE TRIGGER establishment_lifecycle_insert_guard
BEFORE INSERT ON company_configuration.organizational_establishment_revisions
FOR EACH ROW EXECUTE FUNCTION company_configuration.validate_organization_lifecycle();

-- Lifecycle events deliberately do not reuse the L02 legal-entity revision or
-- 0016 registration receipt (which mandates revision=1).
CREATE TABLE company_configuration.organization_lifecycle_requests (
    tenant_id text NOT NULL,
    actor_id text NOT NULL CHECK (btrim(actor_id) <> ''),
    action text NOT NULL CHECK (action IN (
        'organization.company.transition','organization.establishment.transition'
    )),
    request_key text NOT NULL CHECK (btrim(request_key) <> ''),
    request_digest char(64) NOT NULL CHECK (request_digest ~ '^[0-9a-f]{64}$'),
    target_kind text NOT NULL CHECK (target_kind IN ('COMPANY','ESTABLISHMENT')),
    target_id uuid NOT NULL,
    revision integer NOT NULL CHECK (revision>=2),
    correlation_id text NOT NULL CHECK (btrim(correlation_id) <> ''),
    audit_id uuid NOT NULL UNIQUE,
    event_id uuid NOT NULL UNIQUE,
    PRIMARY KEY (tenant_id,actor_id,action,request_key)
);
CREATE TABLE company_configuration.organization_lifecycle_audit (
    record_id uuid PRIMARY KEY,
    tenant_id text NOT NULL,
    actor_id text NOT NULL CHECK (btrim(actor_id) <> ''),
    action text NOT NULL CHECK (action IN (
        'organization.company.transition','organization.establishment.transition'
    )),
    target_kind text NOT NULL CHECK (target_kind IN ('COMPANY','ESTABLISHMENT')),
    target_id uuid NOT NULL,
    before_revision integer NOT NULL CHECK (before_revision>=1),
    after_revision integer NOT NULL CHECK (after_revision=before_revision+1),
    from_status text NOT NULL,
    to_status text NOT NULL CHECK (to_status<>from_status),
    reason text NOT NULL CHECK (btrim(reason) <> ''),
    correlation_id text NOT NULL CHECK (btrim(correlation_id) <> ''),
    recorded_at timestamptz NOT NULL
);
CREATE TABLE company_configuration.organization_lifecycle_outbox (
    event_id uuid PRIMARY KEY,
    tenant_id text NOT NULL,
    event_type text NOT NULL CHECK (event_type IN (
        'organization.company.transition','organization.establishment.transition'
    )),
    schema_version integer NOT NULL CHECK (schema_version=1),
    target_kind text NOT NULL CHECK (target_kind IN ('COMPANY','ESTABLISHMENT')),
    target_id uuid NOT NULL,
    revision integer NOT NULL CHECK (revision>=2),
    from_status text NOT NULL,
    to_status text NOT NULL CHECK (to_status<>from_status),
    correlation_id text NOT NULL CHECK (btrim(correlation_id) <> ''),
    recorded_at timestamptz NOT NULL
);
CREATE INDEX org_lifecycle_company_as_known ON
    company_configuration.organizational_company_revisions
    (tenant_id,company_id,recorded_at,revision);
CREATE INDEX org_lifecycle_site_as_known ON
    company_configuration.organizational_establishment_revisions
    (tenant_id,establishment_id,recorded_at,revision);
-- Tenant-scoped read/write, immutable revisions and evidence, deny PUBLIC.
DO $$
DECLARE tab text;
BEGIN
    FOREACH tab IN ARRAY ARRAY[
        'organizational_company_revisions',
        'organizational_establishment_revisions',
        'organization_lifecycle_requests',
        'organization_lifecycle_audit',
        'organization_lifecycle_outbox'
    ] LOOP
        EXECUTE format(
            'ALTER TABLE company_configuration.%I ENABLE ROW LEVEL SECURITY',tab
        );
        EXECUTE format(
            'ALTER TABLE company_configuration.%I FORCE ROW LEVEL SECURITY',tab
        );
        EXECUTE format(
            'CREATE POLICY isolate_tenant ON company_configuration.%I '
            || 'USING (tenant_id=company_configuration.bound_tenant()) '
            || 'WITH CHECK (tenant_id=company_configuration.bound_tenant())',tab
        );
        EXECUTE format(
            'CREATE TRIGGER org_lifecycle_immutable '
            || 'BEFORE UPDATE OR DELETE ON company_configuration.%I '
            || 'FOR EACH ROW EXECUTE FUNCTION '
            || 'company_configuration.forbid_evidence_mutation()',tab
        );
        EXECUTE format(
            'REVOKE ALL ON company_configuration.%I FROM PUBLIC',tab
        );
    END LOOP;
END $$;
REVOKE ALL ON FUNCTION company_configuration.validate_organization_lifecycle()
    FROM PUBLIC;
