-- L02-04 candidate, not C10 qualification or production tenant isolation.
-- Untrusted transport MUST NOT choose producer_id or tenant database credentials.
CREATE TABLE company_configuration.inbox_receipts (
    tenant_id text NOT NULL CHECK (length(trim(tenant_id)) > 0),
    consumer_id text NOT NULL CHECK (length(trim(consumer_id)) > 0),
    producer_id text NOT NULL CHECK (length(trim(producer_id)) > 0),
    event_id uuid NOT NULL,
    payload_sha256 text NOT NULL CHECK (payload_sha256 ~ '^[0-9a-f]{64}$'),
    event_type text NOT NULL,
    schema_version integer NOT NULL CHECK (schema_version > 0),
    processed_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, consumer_id, producer_id, event_id)
);
CREATE INDEX inbox_receipts_tenant_processed_idx
    ON company_configuration.inbox_receipts (tenant_id, processed_at);

-- Demo consumer read-model, separate from accounting journals and posting.
CREATE TABLE company_configuration.inbox_projection_counts (
    tenant_id text NOT NULL,
    consumer_id text NOT NULL,
    event_type text NOT NULL,
    applied_count bigint NOT NULL CHECK (applied_count > 0),
    PRIMARY KEY (tenant_id, consumer_id, event_type)
);

DO $$
DECLARE tab text;
BEGIN
    FOREACH tab IN ARRAY ARRAY['inbox_receipts', 'inbox_projection_counts'] LOOP
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
CREATE TRIGGER no_inbox_receipt_update_delete
    BEFORE UPDATE OR DELETE ON company_configuration.inbox_receipts
    FOR EACH ROW EXECUTE FUNCTION company_configuration.forbid_evidence_mutation();
