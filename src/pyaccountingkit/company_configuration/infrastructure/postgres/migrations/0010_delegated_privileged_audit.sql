-- L02-07h: Audit writer cannot mutate role DDL, read privileged rows or own tables.
-- This SECURITY DEFINER endpoint is owned by the trusted schema owner; an
-- independent CI-only SQL login gets EXECUTE only, never raw table access.
CREATE FUNCTION company_configuration.cp_append_privileged_audit(
    p_record uuid, p_request uuid, p_tenant text, p_login text,
    p_actor text, p_approver text, p_approval text, p_operation text,
    p_phase text, p_reason text
) RETURNS void LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, pg_temp AS $$
DECLARE
    prior record;
BEGIN
    IF p_record IS NULL OR p_request IS NULL
       OR p_tenant IS NULL OR p_tenant = '' OR btrim(p_tenant) <> p_tenant
       OR p_login IS NULL OR p_login = '' OR btrim(p_login) <> p_login
       OR p_actor IS NULL OR p_actor = '' OR btrim(p_actor) <> p_actor
       OR p_operation IS NULL OR p_operation NOT IN ('rotate','revoke')
       OR p_phase IS NULL
       OR p_phase NOT IN ('INTENT','DENIED','SUCCEEDED','FAILED','CANCELLED')
       OR p_reason IS NULL OR p_reason = ''
    THEN
        RAISE EXCEPTION 'Invalid delegated privileged audit scope'
            USING ERRCODE = '42501';
    END IF;

    IF p_phase = 'DENIED' THEN
        IF p_approver IS NOT NULL OR p_approval IS NOT NULL
           OR p_reason NOT IN (
               'TENANT_MISMATCH','CREDENTIAL_REQUIRED','UNEXPECTED_CREDENTIAL',
               'PERMISSION_DENIED','APPROVAL_INVALID','SOD_VIOLATION'
           )
        THEN
            RAISE EXCEPTION 'Invalid denial evidence' USING ERRCODE = '42501';
        END IF;
    ELSIF p_phase = 'INTENT' THEN
        IF p_approver IS NULL OR p_approver = '' OR p_approver = p_actor
           OR p_approval IS NULL OR p_approval = '' OR p_reason <> 'APPROVED'
        THEN
            RAISE EXCEPTION 'Independent approval required for intent'
                USING ERRCODE = '42501';
        END IF;
    ELSE
        IF p_approver IS NOT NULL OR p_approval IS NOT NULL
           OR p_reason <> p_phase
        THEN
            RAISE EXCEPTION 'Outcome cannot override recorded approval'
                USING ERRCODE = '42501';
        END IF;
        SELECT intent.approver_id, intent.approval_id
          INTO prior
          FROM company_configuration.privileged_operation_audit AS intent
         WHERE intent.request_id = p_request
           AND intent.tenant_id = p_tenant
           AND intent.login_role = p_login
           AND intent.actor_id = p_actor
           AND intent.operation = p_operation
           AND intent.phase = 'INTENT'
           FOR SHARE;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'Matching durable intent required'
                USING ERRCODE = '42501';
        END IF;
        p_approver := prior.approver_id;
        p_approval := prior.approval_id;
        IF p_phase = 'SUCCEEDED' AND NOT EXISTS (
            SELECT 1 FROM company_configuration.privileged_authorization_fences AS f
             WHERE f.request_id = p_request
               AND f.tenant_id = p_tenant
               AND f.login_role::text = p_login
               AND f.operation = p_operation
               AND f.actor_id = p_actor
               AND f.approval_id = p_approval
               AND f.state = 'CONSUMED'
        ) THEN
            RAISE EXCEPTION 'Consumed exact-scoped fence required for success'
                USING ERRCODE = '42501';
        END IF;
    END IF;

    INSERT INTO company_configuration.privileged_operation_audit (
        record_id, request_id, tenant_id, login_role, actor_id,
        approver_id, approval_id, operation, phase, reason_code, recorded_at
    ) VALUES (
        p_record, p_request, p_tenant, p_login, p_actor,
        p_approver, p_approval, p_operation, p_phase, p_reason,
        pg_catalog.clock_timestamp()
    );
END $$;

REVOKE ALL ON FUNCTION company_configuration.cp_append_privileged_audit(
    uuid,uuid,text,text,text,text,text,text,text,text
) FROM PUBLIC;
-- A separately secured provisioner grants EXECUTE to one audit-writer login.
