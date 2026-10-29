-- L02-07g: narrow owner-controlled privileged role operations.
-- Functions are installed by the schema owner; only CI/provisioner GRANTs
-- EXECUTE to a dedicated non-superuser control-plane login. Never to PUBLIC.

CREATE FUNCTION company_configuration.cp_issue_fence(
    p_request uuid, p_tenant text, p_login text, p_operation text,
    p_actor text, p_checker text, p_approval text, p_expires timestamptz
) RETURNS void LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, pg_temp AS $$
DECLARE
    role_record record;
BEGIN
    IF p_request IS NULL OR p_tenant IS NULL OR btrim(p_tenant) <> p_tenant
       OR p_tenant = '' OR p_actor IS NULL OR p_actor = ''
       OR p_checker IS NULL OR p_checker = '' OR p_checker = p_actor
       OR p_approval IS NULL OR p_approval = ''
       OR p_operation NOT IN ('rotate', 'revoke') OR p_operation IS NULL
       OR p_expires IS NULL OR p_expires <= clock_timestamp()
       OR p_login IS NULL
       OR p_login !~ '^cc_(runtime|dispatcher|inbox)_[a-z][a-z0-9_]*$'
    THEN
        RAISE EXCEPTION 'Invalid privileged fence scope' USING ERRCODE = '42501';
    END IF;
    SELECT rolcanlogin, rolsuper, rolcreaterole, rolcreatedb,
           rolreplication, rolbypassrls
    INTO role_record FROM pg_catalog.pg_roles WHERE rolname = p_login;
    IF NOT FOUND OR NOT role_record.rolcanlogin OR role_record.rolsuper
       OR role_record.rolcreaterole OR role_record.rolcreatedb
       OR role_record.rolreplication OR role_record.rolbypassrls
       OR NOT EXISTS (
           SELECT 1 FROM company_configuration.tenant_role_bindings
           WHERE login_role = p_login::name AND tenant_id = p_tenant
       )
    THEN
        RAISE EXCEPTION 'Unregistered or privileged target login' USING ERRCODE = '42501';
    END IF;
    INSERT INTO company_configuration.privileged_authorization_fences (
        request_id,tenant_id,login_role,operation,actor_id,approver_id,
        approval_id,expires_at
    ) VALUES (
        p_request,p_tenant,p_login,p_operation,p_actor,p_checker,
        p_approval,p_expires
    );
    INSERT INTO company_configuration.privileged_fence_events (
        event_id,request_id,tenant_id,actor_id,action
    ) VALUES (pg_catalog.gen_random_uuid(),p_request,p_tenant,p_actor,'ISSUED');
END $$;

CREATE FUNCTION company_configuration.cp_revoke_fence(
    p_request uuid, p_tenant text, p_revoker text
) RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, pg_temp AS $$
DECLARE
    current_state text;
BEGIN
    IF p_request IS NULL OR p_tenant IS NULL OR p_tenant = ''
       OR p_revoker IS NULL OR p_revoker = '' THEN
        RAISE EXCEPTION 'Invalid revoke scope' USING ERRCODE = '42501';
    END IF;
    SELECT state INTO current_state
    FROM company_configuration.privileged_authorization_fences
    WHERE request_id = p_request AND tenant_id = p_tenant FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Fence not found in tenant' USING ERRCODE = '42501';
    END IF;
    IF current_state <> 'ACTIVE' THEN
        RETURN false;
    END IF;
    UPDATE company_configuration.privileged_authorization_fences
    SET state = 'REVOKED', revoked_at = clock_timestamp()
    WHERE request_id = p_request;
    INSERT INTO company_configuration.privileged_fence_events (
        event_id,request_id,tenant_id,actor_id,action
    ) VALUES (pg_catalog.gen_random_uuid(),p_request,p_tenant,p_revoker,'REVOKED');
    RETURN true;
END $$;

CREATE FUNCTION company_configuration.cp_execute_fence(
    p_request uuid,p_tenant text,p_login text,p_operation text,
    p_actor text,p_approval text,p_password text DEFAULT NULL
) RETURNS integer LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, pg_temp AS $$
DECLARE
    permit record;
    target record;
    terminated integer := 0;
    result record;
BEGIN
    IF p_request IS NULL OR p_tenant IS NULL OR p_login IS NULL
       OR p_actor IS NULL OR p_approval IS NULL OR p_operation IS NULL
       OR p_login !~ '^cc_(runtime|dispatcher|inbox)_[a-z][a-z0-9_]*$'
       OR p_operation NOT IN ('rotate','revoke') THEN
        RAISE EXCEPTION 'Invalid privileged operation identity' USING ERRCODE = '42501';
    END IF;
    IF (p_operation = 'rotate' AND (p_password IS NULL
        OR length(p_password) < 16))
        OR (p_operation = 'revoke' AND p_password IS NOT NULL) THEN
        RAISE EXCEPTION 'Invalid credential action' USING ERRCODE = '42501';
    END IF;
    SELECT * INTO permit
    FROM company_configuration.privileged_authorization_fences
    WHERE request_id = p_request FOR UPDATE;
    IF NOT FOUND OR permit.state <> 'ACTIVE'
       OR permit.expires_at <= clock_timestamp()
       OR (permit.tenant_id,permit.login_role::text,permit.operation,
           permit.actor_id,permit.approval_id) IS DISTINCT FROM
          (p_tenant,p_login,p_operation,p_actor,p_approval)
    THEN
        RAISE EXCEPTION 'Active exact-scoped authorization fence required'
            USING ERRCODE = '42501';
    END IF;
    -- Lock the tenant binding as well as the fence before any DDL.
    PERFORM 1 FROM company_configuration.tenant_role_bindings
    WHERE login_role = p_login::name AND tenant_id = p_tenant FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Tenant role binding absent' USING ERRCODE = '42501';
    END IF;
    SELECT rolcanlogin,rolsuper,rolcreaterole,rolcreatedb,
           rolreplication,rolbypassrls INTO target
    FROM pg_catalog.pg_roles WHERE rolname = p_login;
    IF NOT FOUND OR NOT target.rolcanlogin OR target.rolsuper
       OR target.rolcreaterole OR target.rolcreatedb OR target.rolreplication
       OR target.rolbypassrls THEN
        RAISE EXCEPTION 'Cannot mutate privileged or absent login'
            USING ERRCODE = '42501';
    END IF;
    IF p_operation = 'rotate' THEN
        EXECUTE format('ALTER ROLE %I PASSWORD %L', p_login, p_password);
    ELSE
        EXECUTE format('ALTER ROLE %I NOLOGIN', p_login);
        DELETE FROM company_configuration.tenant_role_bindings
        WHERE login_role = p_login::name AND tenant_id = p_tenant;
    END IF;
    UPDATE company_configuration.privileged_authorization_fences
    SET state = 'CONSUMED', consumed_at = clock_timestamp()
    WHERE request_id = p_request;
    INSERT INTO company_configuration.privileged_fence_events (
        event_id,request_id,tenant_id,actor_id,action
    ) VALUES (pg_catalog.gen_random_uuid(),p_request,p_tenant,p_actor,'CONSUMED');
    -- Drain inside the SQL transaction to avoid a delegated role needing
    -- pg_signal_backend. A failure aborts the transaction and is NOT success.
    FOR result IN
        SELECT pg_catalog.pg_terminate_backend(pid,5000) AS ok
        FROM pg_catalog.pg_stat_activity
        WHERE usename = p_login AND pid <> pg_catalog.pg_backend_pid()
    LOOP
        IF NOT result.ok THEN
            RAISE EXCEPTION 'Backend drain incomplete' USING ERRCODE = '55000';
        END IF;
        terminated := terminated + 1;
    END LOOP;
    RETURN terminated;
END $$;

-- No inherited or PUBLIC privilege. An independent provisioner grants these
-- routines to a dedicated non-superuser identity, never to tenant roles.
REVOKE ALL ON FUNCTION company_configuration.cp_issue_fence(
    uuid,text,text,text,text,text,text,timestamptz
) FROM PUBLIC;
REVOKE ALL ON FUNCTION company_configuration.cp_revoke_fence(uuid,text,text)
    FROM PUBLIC;
REVOKE ALL ON FUNCTION company_configuration.cp_execute_fence(
    uuid,text,text,text,text,text,text
) FROM PUBLIC;
