-- S1 #71: SECURITY HOLD ONLY. NOT AN AUTHORIZATION IMPLEMENTATION.
-- 0030 is an additive, intentionally fail-closed quarantine of L03 writes.
-- If a signed command is not independently paired with a signed IAM decision
-- at the PostgreSQL boundary, no actor (including an enabled SQL issuer) may
-- use any of the seven controlled organizational business operations.
-- This also guards legacy functions and direct-DML paths through the 15
-- mutable organization/evidence surfaces. 0001..0029 remain unchanged.
-- Never apply this to a production environment without an approved runbook.
-- Release only via a NEW, independently reviewed additive migration (0031+).
CREATE FUNCTION company_configuration.deny_organization_mutation_s1_hold()
RETURNS trigger LANGUAGE plpgsql
SET search_path = pg_catalog, pg_temp AS $$
BEGIN
    RAISE EXCEPTION
        'S1 HOLD_SECURITY #71: organizational mutation blocked pending signed command/IAM pairing'
        USING ERRCODE = '42501';
END $$;
REVOKE ALL ON FUNCTION
    company_configuration.deny_organization_mutation_s1_hold() FROM PUBLIC;

-- Includes all Company/Registry/Lifecycle/Membership base tables and their
-- request/audit/outbox tables, including paths from prior migrations. Every
-- rule is BEFORE ROW and fires before the old issuer-only authorizers.
-- No GUC, feature flag, application argument or SQL issuer role can unlock it.
DO $$
DECLARE v_table text;
BEGIN
    FOREACH v_table IN ARRAY ARRAY[
        'organizational_companies',
        'organizational_establishments',
        'organizational_legal_identifiers',
        'organization_command_requests',
        'organization_command_audit',
        'organization_command_outbox',
        'organizational_company_revisions',
        'organizational_establishment_revisions',
        'organization_lifecycle_requests',
        'organization_lifecycle_audit',
        'organization_lifecycle_outbox',
        'organizational_membership_revisions',
        'organization_membership_requests',
        'organization_membership_audit',
        'organization_membership_outbox'
    ] LOOP
        EXECUTE format(
            'CREATE TRIGGER a00_s1_hold_security '
            || 'BEFORE INSERT OR UPDATE OR DELETE ON company_configuration.%I '
            || 'FOR EACH ROW EXECUTE FUNCTION '
            || 'company_configuration.deny_organization_mutation_s1_hold()',
            v_table
        );
    END LOOP;
END $$;
