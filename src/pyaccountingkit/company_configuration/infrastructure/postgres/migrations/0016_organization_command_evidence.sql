-- L03 ORG-4b R&D: organization-specific idempotency, audit, and outbox.
-- Keep original L02 evidence semantics untouched: a Company need not have a
-- LegalEntity; target_id denotes the explicitly typed organization target.
-- All three INSERTs must share the same application transaction as the target.
CREATE TABLE company_configuration.organization_command_requests (
    tenant_id text NOT NULL CHECK (tenant_id<>'' AND btrim(tenant_id)=tenant_id),
    actor_id text NOT NULL CHECK (actor_id<>'' AND btrim(actor_id)=actor_id),
    action text NOT NULL CHECK (action IN (
        'organization.company.register',
        'organization.establishment.register',
        'organization.legal_identifier.register'
    )),
    request_key text NOT NULL CHECK (request_key<>'' AND btrim(request_key)=request_key),
    request_digest char(64) NOT NULL CHECK (request_digest ~ '^[0-9a-f]{64}$'),
    target_kind text NOT NULL CHECK (
        target_kind IN ('COMPANY','ESTABLISHMENT','LEGAL_IDENTIFIER')
    ),
    target_id uuid NOT NULL,
    revision integer NOT NULL CHECK (revision=1),
    correlation_id text NOT NULL CHECK (correlation_id<>''),
    audit_id uuid NOT NULL UNIQUE,
    event_id uuid NOT NULL UNIQUE,
    PRIMARY KEY (tenant_id,actor_id,action,request_key)
);
CREATE TABLE company_configuration.organization_command_audit (
    record_id uuid PRIMARY KEY,
    tenant_id text NOT NULL CHECK (tenant_id<>'' AND btrim(tenant_id)=tenant_id),
    actor_id text NOT NULL CHECK (actor_id<>'' AND btrim(actor_id)=actor_id),
    action text NOT NULL,
    target_kind text NOT NULL CHECK (
        target_kind IN ('COMPANY','ESTABLISHMENT','LEGAL_IDENTIFIER')
    ),
    target_id uuid NOT NULL,
    company_id uuid,
    legal_entity_id uuid,
    before_revision integer NOT NULL CHECK (before_revision=0),
    after_revision integer NOT NULL CHECK (after_revision=1),
    reason text NOT NULL CHECK (reason<>'' AND btrim(reason)=reason),
    correlation_id text NOT NULL CHECK (correlation_id<>''),
    recorded_at timestamptz NOT NULL
);
CREATE TABLE company_configuration.organization_command_outbox (
    event_id uuid PRIMARY KEY,
    tenant_id text NOT NULL CHECK (tenant_id<>'' AND btrim(tenant_id)=tenant_id),
    event_type text NOT NULL,
    schema_version integer NOT NULL CHECK (schema_version=1),
    target_kind text NOT NULL CHECK (
        target_kind IN ('COMPANY','ESTABLISHMENT','LEGAL_IDENTIFIER')
    ),
    target_id uuid NOT NULL,
    company_id uuid,
    legal_entity_id uuid,
    revision integer NOT NULL CHECK (revision=1),
    correlation_id text NOT NULL CHECK (correlation_id<>''),
    recorded_at timestamptz NOT NULL
);
CREATE INDEX org_command_audit_target
    ON company_configuration.organization_command_audit
    (tenant_id,target_kind,target_id,recorded_at);
CREATE INDEX org_command_outbox_target
    ON company_configuration.organization_command_outbox
    (tenant_id,target_kind,target_id,recorded_at);
-- No UPDATE/DELETE for command evidentiary rows. RLS takes authority
-- exclusively from the PostgreSQL session_user-to-tenant binding.
DO $$
DECLARE table_name text;
BEGIN
    FOREACH table_name IN ARRAY ARRAY[
        'organization_command_requests','organization_command_audit',
        'organization_command_outbox'
    ] LOOP
        EXECUTE format(
            'CREATE TRIGGER organization_evidence_no_mutate '
            || 'BEFORE UPDATE OR DELETE ON company_configuration.%I '
            || 'FOR EACH ROW EXECUTE FUNCTION company_configuration.forbid_evidence_mutation()',
            table_name
        );
        EXECUTE format(
            'ALTER TABLE company_configuration.%I ENABLE ROW LEVEL SECURITY',
            table_name
        );
        EXECUTE format(
            'ALTER TABLE company_configuration.%I FORCE ROW LEVEL SECURITY',
            table_name
        );
        EXECUTE format(
            'CREATE POLICY isolate_tenant ON company_configuration.%I '
            || 'USING (tenant_id=company_configuration.bound_tenant()) '
            || 'WITH CHECK (tenant_id=company_configuration.bound_tenant())',
            table_name
        );
        EXECUTE format(
            'REVOKE ALL ON company_configuration.%I FROM PUBLIC',
            table_name
        );
    END LOOP;
END $$;
