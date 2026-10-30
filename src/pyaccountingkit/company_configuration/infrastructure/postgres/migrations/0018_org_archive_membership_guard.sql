-- L03 ORG-5a R&D: Company archival cannot orphan active/future affiliations.
-- Additive; do not modify immutable migrations 0001..0017. ARCHIVED is
-- recorded-time state, so the cutoff here is the recorded UTC calendar date.
-- The same per-(tenant,company) transaction advisory lock serializes archival
-- with ANY membership insertion (new membership or correction). Both direct
-- SQL and application paths are subject to these triggers.
CREATE FUNCTION company_configuration.guard_org_company_archive()
RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $$
BEGIN
    IF NEW.status <> 'ARCHIVED' THEN
        RETURN NEW;
    END IF;
    PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(
        'cc:org:affiliation:'||NEW.tenant_id||':'||NEW.company_id::text, 0
    ));
    IF EXISTS (
        SELECT 1 FROM (
            SELECT DISTINCT ON (m.membership_id)
                m.membership_id,m.valid_to
            FROM company_configuration.organizational_membership_revisions m
            WHERE m.tenant_id=NEW.tenant_id AND m.company_id=NEW.company_id
            ORDER BY m.membership_id,m.revision DESC
        ) latest
        WHERE latest.valid_to IS NULL
           OR latest.valid_to > (NEW.recorded_at AT TIME ZONE 'UTC')::date
    ) THEN
        RAISE EXCEPTION 'Cannot archive company with current or future affiliations'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER org_company_archive_membership_guard
BEFORE INSERT ON company_configuration.organizational_company_revisions
FOR EACH ROW EXECUTE FUNCTION company_configuration.guard_org_company_archive();

CREATE FUNCTION company_configuration.guard_org_membership_company()
RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $$
DECLARE latest_status text;
BEGIN
    PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(
        'cc:org:affiliation:'||NEW.tenant_id||':'||NEW.company_id::text, 0
    ));
    SELECT COALESCE(r.status,c.status) INTO latest_status
    FROM company_configuration.organizational_companies c
    LEFT JOIN LATERAL (
        SELECT revision,status
        FROM company_configuration.organizational_company_revisions
        WHERE tenant_id=c.tenant_id AND company_id=c.company_id
        ORDER BY revision DESC LIMIT 1
    ) r ON true
    WHERE c.tenant_id=NEW.tenant_id AND c.company_id=NEW.company_id;
    IF latest_status IS NULL THEN
        RAISE EXCEPTION 'Missing same-tenant organization company parent'
            USING ERRCODE='23503';
    END IF;
    IF latest_status='ARCHIVED' THEN
        RAISE EXCEPTION 'Cannot attach or revise membership under archived company'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER org_membership_archived_company_guard
BEFORE INSERT ON company_configuration.organizational_membership_revisions
FOR EACH ROW EXECUTE FUNCTION company_configuration.guard_org_membership_company();
REVOKE ALL ON FUNCTION company_configuration.guard_org_company_archive() FROM PUBLIC;
REVOKE ALL ON FUNCTION company_configuration.guard_org_membership_company() FROM PUBLIC;
