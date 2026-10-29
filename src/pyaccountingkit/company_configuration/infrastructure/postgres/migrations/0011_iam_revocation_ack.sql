-- L02-07j: independent IAM revocation delivery receipt, not an external IAM lease.
-- A dedicated, non-owner cc_iam_revocation login gets EXECUTE only on the
-- narrow function. The SQL function does NOT independently verify JWS.
CREATE TABLE company_configuration.privileged_iam_revocation_receipts (
    revocation_id uuid PRIMARY KEY,
    request_id uuid NOT NULL,
    tenant_id text NOT NULL CHECK (tenant_id <> '' AND btrim(tenant_id) = tenant_id),
    login_role name NOT NULL,
    operation text NOT NULL CHECK (operation IN ('rotate', 'revoke')),
    approval_id text NOT NULL CHECK (approval_id <> ''),
    revoked_by text NOT NULL CHECK (revoked_by <> ''),
    evidence_sha256 text NOT NULL CHECK (evidence_sha256 ~ '^[0-9a-f]{64}$'),
    status text NOT NULL CHECK (status IN ('APPLIED', 'ALREADY_REVOKED', 'TOO_LATE')),
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX privileged_iam_revocations_request_idx
    ON company_configuration.privileged_iam_revocation_receipts (request_id, recorded_at);
CREATE TRIGGER forbid_privileged_iam_receipt_mutation
    BEFORE UPDATE OR DELETE ON company_configuration.privileged_iam_revocation_receipts
    FOR EACH ROW EXECUTE FUNCTION company_configuration.forbid_evidence_mutation();
REVOKE ALL ON company_configuration.privileged_iam_revocation_receipts FROM PUBLIC;

-- SERIALIZATION: cp_execute_fence() and cp_revoke_fence() already hold this
-- same fence row FOR UPDATE. Lock the fence before consulting the receipt so
-- duplicate deliveries for one request can never concurrently insert a receipt.
CREATE FUNCTION company_configuration.cp_ack_iam_revocation(
    p_revocation uuid, p_request uuid, p_tenant text, p_login text,
    p_operation text, p_approval text, p_revoker text, p_sha256 text
) RETURNS text LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, pg_temp AS $$
DECLARE
    permit record;
    old_receipt record;
    outcome text;
BEGIN
    IF p_revocation IS NULL OR p_request IS NULL OR p_tenant IS NULL
       OR p_tenant = '' OR btrim(p_tenant) <> p_tenant
       OR p_login IS NULL OR p_login = '' OR p_operation NOT IN ('rotate','revoke')
       OR p_approval IS NULL OR p_approval = ''
       OR p_revoker IS NULL OR p_revoker = '' OR btrim(p_revoker) <> p_revoker
       OR p_sha256 IS NULL OR p_sha256 !~ '^[0-9a-f]{64}$' THEN
        RAISE EXCEPTION 'Untrusted IAM revocation scope' USING ERRCODE = '42501';
    END IF;
    SELECT * INTO permit FROM company_configuration.privileged_authorization_fences
    WHERE request_id = p_request FOR UPDATE;
    IF NOT FOUND OR (permit.tenant_id, permit.login_role::text, permit.operation,
                     permit.approval_id) IS DISTINCT FROM
                    (p_tenant, p_login, p_operation, p_approval) THEN
        RAISE EXCEPTION 'Unknown or incorrect IAM revocation target'
            USING ERRCODE = '42501';
    END IF;
    SELECT * INTO old_receipt
    FROM company_configuration.privileged_iam_revocation_receipts
    WHERE revocation_id = p_revocation;
    IF FOUND THEN
        IF (old_receipt.request_id, old_receipt.tenant_id,
            old_receipt.login_role::text, old_receipt.operation,
            old_receipt.approval_id, old_receipt.revoked_by,
            old_receipt.evidence_sha256) IS DISTINCT FROM
           (p_request, p_tenant, p_login, p_operation, p_approval,
            p_revoker, p_sha256) THEN
            RAISE EXCEPTION 'IAM revocation replay conflicts with prior delivery'
                USING ERRCODE = '42501';
        END IF;
        RETURN old_receipt.status;
    END IF;
    IF permit.state = 'ACTIVE' THEN
        UPDATE company_configuration.privileged_authorization_fences
        SET state = 'REVOKED', revoked_at = clock_timestamp()
        WHERE request_id = p_request;
        INSERT INTO company_configuration.privileged_fence_events (
            event_id, request_id, tenant_id, actor_id, action
        ) VALUES (
            pg_catalog.gen_random_uuid(), p_request, p_tenant, p_revoker, 'REVOKED'
        );
        outcome := 'APPLIED';
    ELSIF permit.state = 'REVOKED' THEN
        outcome := 'ALREADY_REVOKED';
    ELSE
        -- A consumed fence may already have altered the SQL role. NEVER claim
        -- this incident was prevented by the delivered IAM revocation.
        outcome := 'TOO_LATE';
    END IF;
    INSERT INTO company_configuration.privileged_iam_revocation_receipts (
        revocation_id, request_id, tenant_id, login_role, operation,
        approval_id, revoked_by, evidence_sha256, status
    ) VALUES (
        p_revocation, p_request, p_tenant, p_login, p_operation,
        p_approval, p_revoker, p_sha256, outcome
    );
    RETURN outcome;
END $$;
REVOKE ALL ON FUNCTION company_configuration.cp_ack_iam_revocation(
    uuid,uuid,text,text,text,text,text,text
) FROM PUBLIC;
