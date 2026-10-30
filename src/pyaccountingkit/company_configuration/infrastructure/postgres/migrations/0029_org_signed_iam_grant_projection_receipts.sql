-- G3-C02b3b2b1 R&D: append-only cryptographic decision provenance metadata.
-- The independent Python owner worker verifies Ed25519 BEFORE SQL writes.
-- DB itself cannot verify IAM private-key custody or remote IdP provenance.
-- Historical migrations 0001..0028 are immutable.
CREATE TABLE company_configuration.organization_actor_grant_decision_receipts (
    authority_issuer text NOT NULL
        CHECK (btrim(authority_issuer)<>'' AND authority_issuer=btrim(authority_issuer)),
    challenge uuid NOT NULL,
    command_nonce uuid NOT NULL,
    tenant_id text NOT NULL
        CHECK (btrim(tenant_id)<>'' AND tenant_id=btrim(tenant_id)),
    grant_id uuid NOT NULL,
    grant_version bigint NOT NULL CHECK (grant_version>=1),
    actor_id text NOT NULL CHECK (btrim(actor_id)<>'' AND actor_id=btrim(actor_id)),
    action text NOT NULL CHECK (btrim(action)<>'' AND action=btrim(action)),
    target_id uuid NOT NULL,
    command_issuer text NOT NULL
        CHECK (btrim(command_issuer)<>'' AND command_issuer=btrim(command_issuer)),
    request_id text NOT NULL
        CHECK (btrim(request_id)<>'' AND request_id=btrim(request_id)),
    correlation_id text NOT NULL
        CHECK (btrim(correlation_id)<>'' AND correlation_id=btrim(correlation_id)),
    request_digest text NOT NULL CHECK (request_digest ~ '^[0-9a-f]{64}$'),
    decision_sha256 text NOT NULL CHECK (decision_sha256 ~ '^[0-9a-f]{64}$'),
    signing_key_id text NOT NULL
        CHECK (btrim(signing_key_id)<>'' AND signing_key_id=btrim(signing_key_id)),
    allowed boolean NOT NULL,
    revoked boolean NOT NULL,
    issued_at timestamptz NOT NULL,
    expires_at timestamptz NOT NULL,
    projected_at timestamptz NOT NULL DEFAULT pg_catalog.clock_timestamp(),
    PRIMARY KEY (authority_issuer,challenge),
    UNIQUE (authority_issuer,command_nonce),
    CHECK (expires_at>issued_at),
    CHECK ((allowed AND NOT revoked) OR (NOT allowed AND revoked))
);
CREATE INDEX org_actor_grant_decision_grant_idx
ON company_configuration.organization_actor_grant_decision_receipts
(grant_id,grant_version);
REVOKE ALL ON company_configuration.organization_actor_grant_decision_receipts
FROM PUBLIC;
-- Immutable audit: no SQL application or issuer identity can rewrite history,
-- even when an accidental grant is made to an application login.
CREATE TRIGGER org_actor_grant_decision_receipt_immutable
BEFORE UPDATE OR DELETE
ON company_configuration.organization_actor_grant_decision_receipts
FOR EACH ROW EXECUTE FUNCTION company_configuration.forbid_evidence_mutation();
