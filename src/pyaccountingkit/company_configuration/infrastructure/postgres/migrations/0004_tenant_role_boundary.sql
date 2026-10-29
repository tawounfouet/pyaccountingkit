-- L02-05 - Candidate tenant login binding; 0001..0003 checksums stay unchanged.
-- Binding is defined by schema owner / secured deploy automation, never by the client.
-- A session_user is the authenticated original login role and is not changed by SET ROLE.
CREATE TABLE company_configuration.tenant_role_bindings (
    login_role name PRIMARY KEY,
    tenant_id text NOT NULL CHECK (length(btrim(tenant_id)) > 0)
);
REVOKE ALL ON company_configuration.tenant_role_bindings FROM PUBLIC;

-- SECURITY DEFINER is restricted to the migration/schema owner and fixes search_path.
-- Role membership and application-set GUCs do not influence this lookup.
CREATE FUNCTION company_configuration.bound_tenant()
RETURNS text
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $$
    SELECT binding.tenant_id
    FROM company_configuration.tenant_role_bindings AS binding
    WHERE binding.login_role = session_user::name
$$;
REVOKE ALL ON FUNCTION company_configuration.bound_tenant() FROM PUBLIC;

-- Fail closed for *all* current Company Configuration tables. An unknown login
-- gets NULL; SQL comparisons against NULL exclude reads and reject writes.
DO $$
DECLARE tab text;
BEGIN
    FOREACH tab IN ARRAY ARRAY[
        'legal_entities', 'idempotency_requests', 'audit_records', 'outbox_events',
        'outbox_delivery', 'authorization_denials',
        'inbox_receipts', 'inbox_projection_counts'
    ] LOOP
        EXECUTE format('DROP POLICY IF EXISTS isolate_tenant ON company_configuration.%I', tab);
        EXECUTE format(
            'CREATE POLICY isolate_tenant ON company_configuration.%I '
            || 'USING (tenant_id = company_configuration.bound_tenant()) '
            || 'WITH CHECK (tenant_id = company_configuration.bound_tenant())',
            tab
        );
        EXECUTE format('ALTER TABLE company_configuration.%I FORCE ROW LEVEL SECURITY', tab);
    END LOOP;
END $$;
