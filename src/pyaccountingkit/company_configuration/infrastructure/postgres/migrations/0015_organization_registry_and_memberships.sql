-- L03 ORG-2/3 R&D: additive organizational registry and bitemporal affiliation.
-- Immutable 0001..0014 remain unchanged. No backfill or FK on L02 legal_entities.company_id.
-- No book assignment, shareholder-control inference or production IAM assertions.
CREATE TABLE company_configuration.organizational_companies (
    tenant_id text NOT NULL CHECK (tenant_id <> '' AND btrim(tenant_id)=tenant_id),
    company_id uuid NOT NULL,
    name text NOT NULL CHECK (name<>'' AND btrim(name)=name),
    kind text NOT NULL CHECK (kind IN ('STANDALONE','GROUP')),
    home_country char(2) NOT NULL CHECK (home_country ~ '^[A-Z]{2}$'),
    base_currency char(3) CHECK (base_currency IS NULL OR base_currency ~ '^[A-Z]{3}$'),
    status text NOT NULL CHECK (status IN ('DRAFT','ACTIVE','INACTIVE','ARCHIVED')),
    revision integer NOT NULL CHECK (revision > 0),
    PRIMARY KEY (tenant_id, company_id)
);

CREATE TABLE company_configuration.organizational_establishments (
    tenant_id text NOT NULL CHECK (tenant_id <> '' AND btrim(tenant_id)=tenant_id),
    establishment_id uuid NOT NULL,
    legal_entity_id uuid NOT NULL,
    name text NOT NULL CHECK (name<>'' AND btrim(name)=name),
    country char(2) NOT NULL CHECK (country ~ '^[A-Z]{2}$'),
    valid_from date NOT NULL,
    valid_to date CHECK (valid_to IS NULL OR valid_to > valid_from),
    status text NOT NULL CHECK (status IN ('PLANNED','ACTIVE','INACTIVE','CLOSED')),
    revision integer NOT NULL CHECK (revision > 0),
    PRIMARY KEY (tenant_id, establishment_id),
    FOREIGN KEY (tenant_id,legal_entity_id)
        REFERENCES company_configuration.legal_entities(tenant_id,entity_id)
);

CREATE TABLE company_configuration.organizational_legal_identifiers (
    tenant_id text NOT NULL CHECK (tenant_id <> '' AND btrim(tenant_id)=tenant_id),
    identifier_id uuid NOT NULL,
    legal_entity_id uuid NOT NULL,
    scheme text NOT NULL CHECK (scheme<>'' AND btrim(scheme)=scheme),
    value text NOT NULL CHECK (value<>'' AND btrim(value)=value),
    issuer text NOT NULL CHECK (issuer<>'' AND btrim(issuer)=issuer),
    jurisdiction char(2) NOT NULL CHECK (jurisdiction ~ '^[A-Z]{2}$'),
    valid_from date NOT NULL,
    valid_to date CHECK (valid_to IS NULL OR valid_to > valid_from),
    source_ref text NOT NULL CHECK (source_ref<>'' AND btrim(source_ref)=source_ref),
    PRIMARY KEY (tenant_id, identifier_id),
    FOREIGN KEY (tenant_id,legal_entity_id)
        REFERENCES company_configuration.legal_entities(tenant_id,entity_id)
);
CREATE INDEX org_ident_lookup ON company_configuration.organizational_legal_identifiers
    (tenant_id, scheme, issuer, jurisdiction, value);

CREATE TABLE company_configuration.organizational_membership_revisions (
    tenant_id text NOT NULL CHECK (tenant_id<>'' AND btrim(tenant_id)=tenant_id),
    membership_id uuid NOT NULL,
    revision integer NOT NULL CHECK (revision > 0),
    company_id uuid NOT NULL,
    legal_entity_id uuid NOT NULL,
    kind text NOT NULL CHECK (kind IN ('ADMINISTRATIVE','OPERATIONAL')),
    exclusive boolean NOT NULL,
    valid_from date NOT NULL,
    valid_to date CHECK (valid_to IS NULL OR valid_to > valid_from),
    recorded_at timestamptz NOT NULL,
    source_ref text NOT NULL CHECK (source_ref<>'' AND btrim(source_ref)=source_ref),
    PRIMARY KEY (tenant_id,membership_id,revision),
    FOREIGN KEY (tenant_id,company_id)
        REFERENCES company_configuration.organizational_companies(tenant_id,company_id),
    FOREIGN KEY (tenant_id,legal_entity_id)
        REFERENCES company_configuration.legal_entities(tenant_id,entity_id)
);
CREATE INDEX org_memberships_as_known ON
    company_configuration.organizational_membership_revisions
    (tenant_id,legal_entity_id,kind,recorded_at,valid_from,valid_to);

-- Valid and recorded times are explicit: same-tenant conflict locks serialize
-- concurrent direct SQL writes. No reliance on client-set GUC or RLS visibility
-- from an unrelated service: every login is bound by original session_user.
CREATE FUNCTION company_configuration.validate_organization_legal_identifier()
RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $$
BEGIN
    PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(
        'cc:org:legal:'||NEW.tenant_id||':'||NEW.scheme||':'||NEW.issuer
        ||':'||NEW.jurisdiction||':'||NEW.value, 0
    ));
    IF EXISTS (
        SELECT 1 FROM company_configuration.organizational_legal_identifiers AS i
        WHERE i.tenant_id=NEW.tenant_id
          AND i.scheme=NEW.scheme AND i.issuer=NEW.issuer
          AND i.jurisdiction=NEW.jurisdiction AND i.value=NEW.value
          AND i.legal_entity_id<>NEW.legal_entity_id
          AND daterange(i.valid_from,i.valid_to,'[)') &&
              daterange(NEW.valid_from,NEW.valid_to,'[)')
    ) THEN
        RAISE EXCEPTION 'Overlapping legal registry identifier'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER organization_identifier_insert_guard
BEFORE INSERT ON company_configuration.organizational_legal_identifiers
FOR EACH ROW EXECUTE FUNCTION company_configuration.validate_organization_legal_identifier();

CREATE FUNCTION company_configuration.validate_organization_membership()
RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $$
DECLARE previous record;
BEGIN
    PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(
        'cc:org:membership:'||NEW.tenant_id||':'||NEW.legal_entity_id::text
        ||':'||NEW.kind, 0
    ));
    SELECT m.* INTO previous
    FROM company_configuration.organizational_membership_revisions AS m
    WHERE m.tenant_id=NEW.tenant_id AND m.membership_id=NEW.membership_id
    ORDER BY m.revision DESC LIMIT 1;
    IF (NOT FOUND AND NEW.revision<>1)
       OR (FOUND AND (
           NEW.revision<>previous.revision+1
           OR NEW.recorded_at<=previous.recorded_at
           OR NEW.company_id<>previous.company_id
           OR NEW.legal_entity_id<>previous.legal_entity_id
           OR NEW.kind<>previous.kind
           OR NEW.exclusive IS DISTINCT FROM previous.exclusive
           OR NEW.valid_from<>previous.valid_from
           OR previous.valid_to IS NOT NULL AND (
               NEW.valid_to IS NULL OR NEW.valid_to>previous.valid_to
           )
       )) THEN
        RAISE EXCEPTION 'Invalid append-only membership revision'
            USING ERRCODE='23514';
    END IF;
    IF EXISTS (
        SELECT 1 FROM (
            SELECT DISTINCT ON (membership_id) *
            FROM company_configuration.organizational_membership_revisions
            WHERE tenant_id=NEW.tenant_id AND legal_entity_id=NEW.legal_entity_id
              AND kind=NEW.kind AND membership_id<>NEW.membership_id
            ORDER BY membership_id,revision DESC
        ) AS other
        WHERE (NEW.exclusive OR other.exclusive)
          AND daterange(other.valid_from,other.valid_to,'[)') &&
              daterange(NEW.valid_from,NEW.valid_to,'[)')
    ) THEN
        RAISE EXCEPTION 'Conflicting exclusive membership interval'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER organization_membership_insert_guard
BEFORE INSERT ON company_configuration.organizational_membership_revisions
FOR EACH ROW EXECUTE FUNCTION company_configuration.validate_organization_membership();

-- Updates/deletes to immutable identity and history are forbidden even to a
-- future write-enabled runtime role (schema owner has separate trusted powers).
DO $$
DECLARE tab text;
BEGIN
    FOREACH tab IN ARRAY ARRAY[
        'organizational_companies','organizational_establishments',
        'organizational_legal_identifiers','organizational_membership_revisions'
    ] LOOP
        EXECUTE format('ALTER TABLE company_configuration.%I ENABLE ROW LEVEL SECURITY',tab);
        EXECUTE format('ALTER TABLE company_configuration.%I FORCE ROW LEVEL SECURITY',tab);
        EXECUTE format('CREATE POLICY isolate_tenant ON company_configuration.%I '
            || 'USING (tenant_id=company_configuration.bound_tenant()) '
            || 'WITH CHECK (tenant_id=company_configuration.bound_tenant())',tab);
    END LOOP;
    FOREACH tab IN ARRAY ARRAY[
        'organizational_companies','organizational_establishments',
        'organizational_legal_identifiers','organizational_membership_revisions'
    ] LOOP
        EXECUTE format('CREATE TRIGGER organization_no_update_delete '
            || 'BEFORE UPDATE OR DELETE ON company_configuration.%I '
            || 'FOR EACH ROW EXECUTE FUNCTION company_configuration.forbid_evidence_mutation()',tab);
    END LOOP;
END $$;
REVOKE ALL ON company_configuration.organizational_companies FROM PUBLIC;
REVOKE ALL ON company_configuration.organizational_establishments FROM PUBLIC;
REVOKE ALL ON company_configuration.organizational_legal_identifiers FROM PUBLIC;
REVOKE ALL ON company_configuration.organizational_membership_revisions FROM PUBLIC;
REVOKE ALL ON FUNCTION company_configuration.validate_organization_legal_identifier() FROM PUBLIC;
REVOKE ALL ON FUNCTION company_configuration.validate_organization_membership() FROM PUBLIC;
