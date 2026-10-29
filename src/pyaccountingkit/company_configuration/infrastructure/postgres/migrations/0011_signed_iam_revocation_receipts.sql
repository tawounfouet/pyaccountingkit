-- L02-07j: database acknowledgement of signed, externally sourced IAM revocations.
-- The signed evidence is verified in Python BEFORE invoking this capability.
-- SQL role alone is not cryptographically authenticated and must remain isolated.

CREATE TABLE company_configuration.privileged_iam_revocation_receipts (
    request_id uuid PRIMARY KEY,
    event_id uuid NOT NULL UNIQUE,
    tenant_id text NOT NULL CHECK (tenant_id <> '' AND btrim(tenant_id) = tenant_id),
    login_role name NOT NULL,
    operation text NOT NULL CHECK (operation IN ('rotate', 'revoke')),
    issuer text NOT NULL CHECK (issuer <> ''),
    signer_kid text NOT NULL CHECK (signer_kid <> ''),
    revoker_id text NOT NULL CHECK (revoker_id <> ''),
    signed_digest text NOT NULL CHECK (signed_digest ~ '^[0-9a-f]{64}$'),
    disposition text NOT NULL CHECK (
        disposition IN ('TOMBSTONED','REVOKED','ALREADY_REVOKED','ALREADY_CONSUMED')
    ),
    acknowledged_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TRIGGER no_privileged_iam_receipt_change
    BEFORE UPDATE OR DELETE ON company_configuration.privileged_iam_revocation_receipts
    FOR EACH ROW EXECUTE FUNCTION company_configuration.forbid_evidence_mutation();
REVOKE ALL ON company_configuration.privileged_iam_revocation_receipts FROM PUBLIC;

-- Important: a revoke delivered BEFORE the fence is issued must also win.
-- Both the INSERT trigger and acknowledgement function take the same
-- transaction-level advisory lock on the request UUID. Hash collisions can
-- cause extra serialization but cannot bypass the tombstone check.
CREATE FUNCTION company_configuration.deny_revoked_fence_issuance()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, pg_temp AS $$
BEGIN
    PERFORM pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtextextended(NEW.request_id::text, 77011)
    );
    IF EXISTS (
        SELECT 1 FROM company_configuration.privileged_iam_revocation_receipts
        WHERE request_id = NEW.request_id
    ) THEN
        RAISE EXCEPTION 'Request was revoked by IAM before fence issuance'
            USING ERRCODE = '42501';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER deny_fence_after_iam_revocation
    BEFORE INSERT ON company_configuration.privileged_authorization_fences
    FOR EACH ROW EXECUTE FUNCTION company_configuration.deny_revoked_fence_issuance();
REVOKE ALL ON FUNCTION company_configuration.deny_revoked_fence_issuance() FROM PUBLIC;

-- Acknowledgement is one atomic PostgreSQL transaction with a fence update.
-- No schema-owner credentials should be available to the IAM receiver.
CREATE FUNCTION company_configuration.cp_ack_iam_revocation(
    p_event uuid, p_request uuid, p_tenant text, p_login text,
    p_operation text, p_issuer text, p_kid text, p_revoker text, p_digest text
) RETURNS text LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, pg_temp AS $$
DECLARE
    prior record;
    current_fence record;
    status text;
BEGIN
    IF p_event IS NULL OR p_request IS NULL OR p_tenant IS NULL
       OR p_tenant = '' OR btrim(p_tenant) <> p_tenant
       OR p_login IS NULL OR p_login !~ '^cc_(runtime|dispatcher|inbox)_[a-z][a-z0-9_]*$'
       OR p_operation IS NULL OR p_operation NOT IN ('rotate','revoke')
       OR p_issuer IS NULL OR p_issuer = '' OR p_kid IS NULL OR p_kid = ''
       OR p_revoker IS NULL OR p_revoker = ''
       OR p_digest IS NULL OR p_digest !~ '^[0-9a-f]{64}$'
    THEN
        RAISE EXCEPTION 'Invalid signed IAM revocation scope'
            USING ERRCODE = '42501';
    END IF;
    PERFORM pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtextextended(p_request::text, 77011)
    );
    SELECT * INTO prior FROM company_configuration.privileged_iam_revocation_receipts
    WHERE request_id = p_request FOR UPDATE;
    IF FOUND THEN
        IF (prior.event_id, prior.tenant_id, prior.login_role::text,
            prior.operation, prior.issuer, prior.signer_kid, prior.revoker_id,
            prior.signed_digest) IS DISTINCT FROM
           (p_event, p_tenant, p_login, p_operation, p_issuer, p_kid,
            p_revoker, p_digest)
        THEN
            RAISE EXCEPTION 'Conflicting IAM revocation receipt'
                USING ERRCODE = '42501';
        END IF;
        RETURN prior.disposition;
    END IF;
    SELECT * INTO current_fence
    FROM company_configuration.privileged_authorization_fences
    WHERE request_id = p_request FOR UPDATE;
    IF NOT FOUND THEN
        status := 'TOMBSTONED';
    ELSIF (current_fence.tenant_id, current_fence.login_role::text,
           current_fence.operation) IS DISTINCT FROM (p_tenant,p_login,p_operation)
    THEN
        RAISE EXCEPTION 'IAM revocation target mismatch'
            USING ERRCODE = '42501';
    ELSIF current_fence.state = 'ACTIVE' THEN
        UPDATE company_configuration.privileged_authorization_fences
        SET state = 'REVOKED', revoked_at = clock_timestamp()
        WHERE request_id = p_request;
        INSERT INTO company_configuration.privileged_fence_events (
            event_id, request_id, tenant_id, actor_id, action
        ) VALUES (
            pg_catalog.gen_random_uuid(),p_request,p_tenant,p_revoker,'REVOKED'
        );
        status := 'REVOKED';
    ELSIF current_fence.state = 'REVOKED' THEN
        status := 'ALREADY_REVOKED';
    ELSE
        status := 'ALREADY_CONSUMED';
    END IF;
    INSERT INTO company_configuration.privileged_iam_revocation_receipts (
        request_id,event_id,tenant_id,login_role,operation,issuer,
        signer_kid,revoker_id,signed_digest,disposition
    ) VALUES (
        p_request,p_event,p_tenant,p_login,p_operation,p_issuer,
        p_kid,p_revoker,p_digest,status
    );
    RETURN status;
END $$;
REVOKE ALL ON FUNCTION company_configuration.cp_ack_iam_revocation(
    uuid,uuid,text,text,text,text,text,text,text
) FROM PUBLIC;
