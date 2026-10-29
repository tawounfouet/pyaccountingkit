-- L02-03 candidate. The source outbox remains append-only; delivery progress is separate.
-- This is not an independently verified tenant boundary when a DB client controls app.tenant_id.
ALTER TABLE company_configuration.outbox_events
    ADD CONSTRAINT outbox_tenant_event_unique UNIQUE (tenant_id, event_id);

CREATE TABLE company_configuration.outbox_delivery (
    tenant_id text NOT NULL,
    event_id uuid NOT NULL,
    attempts integer NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    available_at timestamptz NOT NULL DEFAULT now(),
    lease_owner text,
    lease_token uuid,
    lease_until timestamptz,
    delivered_at timestamptz,
    dead_letter_at timestamptz,
    last_error text,
    PRIMARY KEY (tenant_id, event_id),
    FOREIGN KEY (tenant_id, event_id)
        REFERENCES company_configuration.outbox_events (tenant_id, event_id),
    CHECK ((lease_owner IS NULL AND lease_token IS NULL AND lease_until IS NULL)
       OR (lease_owner IS NOT NULL AND lease_token IS NOT NULL AND lease_until IS NOT NULL)),
    CHECK (delivered_at IS NULL OR dead_letter_at IS NULL)
);
CREATE INDEX outbox_delivery_due_idx
    ON company_configuration.outbox_delivery (tenant_id, available_at, lease_until)
    WHERE delivered_at IS NULL AND dead_letter_at IS NULL;

CREATE TABLE company_configuration.authorization_denials (
    record_id uuid NOT NULL PRIMARY KEY,
    tenant_id text NOT NULL CHECK (length(trim(tenant_id)) > 0),
    actor_id text NOT NULL CHECK (length(trim(actor_id)) > 0),
    action text NOT NULL,
    reason_code text NOT NULL,
    correlation_id text,
    recorded_at timestamptz NOT NULL
);
CREATE INDEX authorization_denials_tenant_time_idx
    ON company_configuration.authorization_denials (tenant_id, recorded_at);

DO $$
DECLARE tab text;
BEGIN
    FOREACH tab IN ARRAY ARRAY['outbox_delivery', 'authorization_denials'] LOOP
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
CREATE TRIGGER no_denial_update_delete
    BEFORE UPDATE OR DELETE ON company_configuration.authorization_denials
    FOR EACH ROW EXECUTE FUNCTION company_configuration.forbid_evidence_mutation();
