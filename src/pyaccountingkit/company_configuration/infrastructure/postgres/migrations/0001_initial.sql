-- L02-02 candidate schema, NOT approved for a production deployment.
-- Run as a schema owner; use a separate non-BYPASSRLS application role.
CREATE TABLE company_configuration.legal_entities (
    tenant_id text NOT NULL CHECK (length(trim(tenant_id)) > 0),
    company_id uuid NOT NULL,
    entity_id uuid NOT NULL,
    legal_name text NOT NULL CHECK (length(trim(legal_name)) > 0),
    jurisdiction char(2) NOT NULL CHECK (jurisdiction ~ '^[A-Z]{2}$'),
    functional_currency char(3) NOT NULL CHECK (functional_currency ~ '^[A-Z]{3}$'),
    revision integer NOT NULL CHECK (revision > 0),
    PRIMARY KEY (tenant_id, entity_id)
);
CREATE TABLE company_configuration.idempotency_requests (
    tenant_id text NOT NULL,
    actor_id text NOT NULL,
    company_id uuid NOT NULL,
    entity_id uuid NOT NULL,
    action text NOT NULL,
    request_key text NOT NULL,
    request_digest text NOT NULL CHECK (request_digest ~ '^[0-9a-f]{64}$'),
    receipt_revision integer NOT NULL CHECK (receipt_revision > 0),
    receipt_correlation_id text NOT NULL,
    receipt_audit_id uuid NOT NULL,
    receipt_event_id uuid NOT NULL,
    PRIMARY KEY (tenant_id, actor_id, company_id, entity_id, action, request_key)
);
CREATE TABLE company_configuration.audit_records (
    record_id uuid PRIMARY KEY,
    tenant_id text NOT NULL,
    company_id uuid NOT NULL,
    entity_id uuid NOT NULL,
    actor_id text NOT NULL,
    action text NOT NULL,
    before_revision integer NOT NULL,
    after_revision integer NOT NULL,
    reason text NOT NULL,
    correlation_id text NOT NULL,
    recorded_at timestamptz NOT NULL
);
CREATE TABLE company_configuration.outbox_events (
    event_id uuid PRIMARY KEY,
    tenant_id text NOT NULL,
    company_id uuid NOT NULL,
    entity_id uuid NOT NULL,
    event_type text NOT NULL,
    schema_version integer NOT NULL CHECK (schema_version > 0),
    revision integer NOT NULL CHECK (revision > 0),
    correlation_id text NOT NULL,
    recorded_at timestamptz NOT NULL
);
CREATE INDEX audit_tenant_entity_idx
    ON company_configuration.audit_records (tenant_id, entity_id, recorded_at);
CREATE INDEX outbox_tenant_entity_idx
    ON company_configuration.outbox_events (tenant_id, entity_id, recorded_at);

-- RLS is defense in depth; the application must still authorize each action.
-- Missing/empty tenant context returns no rows and rejects inserts.
DO $$
DECLARE tab text;
BEGIN
    FOREACH tab IN ARRAY ARRAY[
        'legal_entities', 'idempotency_requests', 'audit_records', 'outbox_events'
    ] LOOP
        EXECUTE format('ALTER TABLE company_configuration.%I ENABLE ROW LEVEL SECURITY', tab);
        EXECUTE format('ALTER TABLE company_configuration.%I FORCE ROW LEVEL SECURITY', tab);
        EXECUTE format(
            'CREATE POLICY isolate_tenant ON company_configuration.%I '
            || 'USING (tenant_id = nullif(current_setting(''app.tenant_id'', true), '''')) '
            || 'WITH CHECK (tenant_id = nullif(current_setting(''app.tenant_id'', true), ''''))',
            tab
        );
    END LOOP;
END $$;

-- Append-only evidence. This does not claim certified WORM or regulatory retention.
CREATE FUNCTION company_configuration.forbid_evidence_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'Evidence records are append-only' USING ERRCODE = '23514';
END;
$$;
CREATE TRIGGER no_audit_update_delete
    BEFORE UPDATE OR DELETE ON company_configuration.audit_records
    FOR EACH ROW EXECUTE FUNCTION company_configuration.forbid_evidence_mutation();
CREATE TRIGGER no_outbox_update_delete
    BEFORE UPDATE OR DELETE ON company_configuration.outbox_events
    FOR EACH ROW EXECUTE FUNCTION company_configuration.forbid_evidence_mutation();
