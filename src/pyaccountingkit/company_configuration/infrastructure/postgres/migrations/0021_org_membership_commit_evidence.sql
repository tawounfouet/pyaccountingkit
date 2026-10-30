-- ORG-5b2b: membership-native request/audit/outbox and COMMIT guard.
-- Additive. Migrations 0001..0020 remain byte-for-byte immutable.
-- This is consistency, not proof of the external actor's identity.
CREATE TABLE company_configuration.organization_membership_requests (
    tenant_id text NOT NULL,
    actor_id text NOT NULL CHECK (btrim(actor_id)<>''),
    action text NOT NULL CHECK (
        action IN ('organization.membership.assign','organization.membership.end')
    ),
    request_key text NOT NULL CHECK (btrim(request_key)<>''),
    request_digest char(64) NOT NULL CHECK (request_digest ~ '^[0-9a-f]{64}$'),
    membership_id uuid NOT NULL,
    company_id uuid NOT NULL,
    legal_entity_id uuid NOT NULL,
    revision integer NOT NULL CHECK (revision>0),
    correlation_id text NOT NULL CHECK (btrim(correlation_id)<>''),
    audit_id uuid NOT NULL UNIQUE,
    event_id uuid NOT NULL UNIQUE,
    PRIMARY KEY (tenant_id,actor_id,action,request_key),
    UNIQUE (tenant_id,membership_id,revision)
);
CREATE TABLE company_configuration.organization_membership_audit (
    record_id uuid PRIMARY KEY,
    tenant_id text NOT NULL,
    actor_id text NOT NULL CHECK (btrim(actor_id)<>''),
    action text NOT NULL CHECK (
        action IN ('organization.membership.assign','organization.membership.end')
    ),
    membership_id uuid NOT NULL,
    company_id uuid NOT NULL,
    legal_entity_id uuid NOT NULL,
    before_revision integer NOT NULL CHECK (before_revision>=0),
    after_revision integer NOT NULL CHECK (after_revision=before_revision+1),
    valid_from date NOT NULL,
    valid_to date CHECK (valid_to IS NULL OR valid_to>valid_from),
    source_ref text NOT NULL CHECK (btrim(source_ref)<>''),
    reason text NOT NULL CHECK (btrim(reason)<>''),
    correlation_id text NOT NULL CHECK (btrim(correlation_id)<>''),
    recorded_at timestamptz NOT NULL
);
CREATE TABLE company_configuration.organization_membership_outbox (
    event_id uuid PRIMARY KEY,
    tenant_id text NOT NULL,
    event_type text NOT NULL CHECK (
        event_type IN ('organization.membership.assign','organization.membership.end')
    ),
    schema_version integer NOT NULL CHECK (schema_version=1),
    membership_id uuid NOT NULL,
    company_id uuid NOT NULL,
    legal_entity_id uuid NOT NULL,
    revision integer NOT NULL CHECK (revision>0),
    kind text NOT NULL CHECK (kind IN ('ADMINISTRATIVE','OPERATIONAL')),
    exclusive boolean NOT NULL,
    valid_from date NOT NULL,
    valid_to date CHECK (valid_to IS NULL OR valid_to>valid_from),
    source_ref text NOT NULL CHECK (btrim(source_ref)<>''),
    correlation_id text NOT NULL CHECK (btrim(correlation_id)<>''),
    recorded_at timestamptz NOT NULL
);
CREATE INDEX org_membership_audit_target ON
    company_configuration.organization_membership_audit
    (tenant_id,membership_id,after_revision);
CREATE INDEX org_membership_outbox_target ON
    company_configuration.organization_membership_outbox
    (tenant_id,membership_id,revision);

CREATE FUNCTION company_configuration.require_org_membership_evidence()
RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $$
DECLARE
    v_action text;
BEGIN
    IF NEW.revision=1 THEN
        v_action:='organization.membership.assign';
    ELSE
        v_action:='organization.membership.end';
    END IF;
    IF NOT EXISTS (
        SELECT 1
        FROM company_configuration.organization_membership_requests req
        JOIN company_configuration.organization_membership_audit aud
          ON aud.record_id=req.audit_id
        JOIN company_configuration.organization_membership_outbox evt
          ON evt.event_id=req.event_id
        WHERE req.tenant_id=NEW.tenant_id
          AND req.action=v_action
          AND req.membership_id=NEW.membership_id
          AND req.company_id=NEW.company_id
          AND req.legal_entity_id=NEW.legal_entity_id
          AND req.revision=NEW.revision
          AND aud.tenant_id=req.tenant_id
          AND aud.actor_id=req.actor_id
          AND aud.action=req.action
          AND aud.membership_id=req.membership_id
          AND aud.company_id=req.company_id
          AND aud.legal_entity_id=req.legal_entity_id
          AND aud.before_revision=NEW.revision-1
          AND aud.after_revision=req.revision
          AND aud.valid_from=NEW.valid_from
          AND aud.valid_to IS NOT DISTINCT FROM NEW.valid_to
          AND aud.source_ref=NEW.source_ref
          AND aud.correlation_id=req.correlation_id
          AND aud.recorded_at=NEW.recorded_at
          AND evt.tenant_id=req.tenant_id
          AND evt.event_type=req.action
          AND evt.schema_version=1
          AND evt.membership_id=req.membership_id
          AND evt.company_id=req.company_id
          AND evt.legal_entity_id=req.legal_entity_id
          AND evt.revision=req.revision
          AND evt.kind=NEW.kind
          AND evt.exclusive=NEW.exclusive
          AND evt.valid_from=NEW.valid_from
          AND evt.valid_to IS NOT DISTINCT FROM NEW.valid_to
          AND evt.source_ref=NEW.source_ref
          AND evt.correlation_id=req.correlation_id
          AND evt.recorded_at=NEW.recorded_at
    ) THEN
        RAISE EXCEPTION
            'Membership revision requires matching request, audit and outbox'
            USING ERRCODE='23514';
    END IF;
    RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER org_membership_commit_evidence
AFTER INSERT ON company_configuration.organizational_membership_revisions
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION company_configuration.require_org_membership_evidence();

DO $$
DECLARE tab text;
BEGIN
    FOREACH tab IN ARRAY ARRAY[
        'organization_membership_requests',
        'organization_membership_audit',
        'organization_membership_outbox'
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
            'CREATE TRIGGER org_membership_evidence_immutable '
            || 'BEFORE UPDATE OR DELETE ON company_configuration.%I '
            || 'FOR EACH ROW EXECUTE FUNCTION '
            || 'company_configuration.forbid_evidence_mutation()',tab
        );
        EXECUTE format(
            'REVOKE ALL ON company_configuration.%I FROM PUBLIC',tab
        );
    END LOOP;
END $$;
REVOKE ALL ON FUNCTION company_configuration.require_org_membership_evidence()
FROM PUBLIC;
