-- L02-07k: durable remote acknowledgement delivery after SQL revocation.
-- Enqueue in the same transaction as the append-only 0011 receipt INSERT.
CREATE TABLE company_configuration.privileged_iam_ack_outbox (
    event_id uuid PRIMARY KEY,
    request_id uuid NOT NULL UNIQUE
        REFERENCES company_configuration.privileged_iam_revocation_receipts(request_id),
    tenant_id text NOT NULL,
    disposition text NOT NULL CHECK (
        disposition IN ('TOMBSTONED','REVOKED','ALREADY_REVOKED','ALREADY_CONSUMED')
    ),
    state text NOT NULL DEFAULT 'PENDING'
        CHECK (state IN ('PENDING','IN_FLIGHT','RETRY','DELIVERED','DEAD')),
    attempts integer NOT NULL DEFAULT 0 CHECK (attempts BETWEEN 0 AND 5),
    lease_token uuid,
    lease_until timestamptz,
    next_attempt_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    error_code text,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    delivered_at timestamptz,
    CHECK ((state = 'IN_FLIGHT') = (lease_token IS NOT NULL)),
    CHECK ((state = 'IN_FLIGHT') = (lease_until IS NOT NULL)),
    CHECK ((state = 'DELIVERED') = (delivered_at IS NOT NULL))
);
REVOKE ALL ON company_configuration.privileged_iam_ack_outbox FROM PUBLIC;

CREATE FUNCTION company_configuration.enqueue_iam_ack_receipt()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, pg_temp AS $$
BEGIN
    INSERT INTO company_configuration.privileged_iam_ack_outbox (
        event_id, request_id, tenant_id, disposition
    ) VALUES (NEW.event_id, NEW.request_id, NEW.tenant_id, NEW.disposition);
    RETURN NULL;
END $$;
CREATE TRIGGER enqueue_iam_ack_after_receipt
    AFTER INSERT ON company_configuration.privileged_iam_revocation_receipts
    FOR EACH ROW EXECUTE FUNCTION company_configuration.enqueue_iam_ack_receipt();
REVOKE ALL ON FUNCTION company_configuration.enqueue_iam_ack_receipt() FROM PUBLIC;

-- Migration backfills receipts inserted by earlier L02-07j code, without a new
-- external ACK. Existing receipts are authoritative for the persisted outcome.
INSERT INTO company_configuration.privileged_iam_ack_outbox (
    event_id,request_id,tenant_id,disposition
)
SELECT event_id,request_id,tenant_id,disposition
FROM company_configuration.privileged_iam_revocation_receipts
ON CONFLICT (event_id) DO NOTHING;

CREATE FUNCTION company_configuration.cp_claim_iam_ack(p_batch integer)
RETURNS TABLE (
    event_id uuid, request_id uuid, tenant_id text, disposition text, lease_token uuid
) LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, pg_temp AS $$
BEGIN
    IF p_batch IS NULL OR p_batch < 1 OR p_batch > 20 THEN
        RAISE EXCEPTION 'Invalid IAM acknowledgement batch' USING ERRCODE='42501';
    END IF;
    -- Last attempt's expired lease must not be silently retried forever.
    UPDATE company_configuration.privileged_iam_ack_outbox AS a
    SET state='DEAD', lease_token=NULL, lease_until=NULL,
        error_code='LEASE_EXPIRED'
    WHERE a.state='IN_FLIGHT' AND a.lease_until <= clock_timestamp()
      AND a.attempts >= 5;
    RETURN QUERY
    WITH eligible AS (
        SELECT a.event_id
        FROM company_configuration.privileged_iam_ack_outbox AS a
        WHERE a.attempts < 5 AND (
            (a.state IN ('PENDING','RETRY') AND a.next_attempt_at <= clock_timestamp())
            OR (a.state='IN_FLIGHT' AND a.lease_until <= clock_timestamp())
        )
        ORDER BY a.created_at, a.event_id
        FOR UPDATE OF a SKIP LOCKED LIMIT p_batch
    )
    UPDATE company_configuration.privileged_iam_ack_outbox AS a
    SET state='IN_FLIGHT', attempts=a.attempts + 1,
        lease_token=pg_catalog.gen_random_uuid(),
        lease_until=clock_timestamp() + interval '30 seconds', error_code=NULL
    FROM eligible e WHERE a.event_id=e.event_id
    RETURNING a.event_id,a.request_id,a.tenant_id,a.disposition,a.lease_token;
END $$;

CREATE FUNCTION company_configuration.cp_complete_iam_ack(p_event uuid, p_token uuid)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, pg_temp AS $$
DECLARE changed integer;
BEGIN
    IF p_event IS NULL OR p_token IS NULL THEN
        RAISE EXCEPTION 'Missing acknowledged delivery lease' USING ERRCODE='42501';
    END IF;
    UPDATE company_configuration.privileged_iam_ack_outbox
    SET state='DELIVERED',lease_token=NULL,lease_until=NULL,
        delivered_at=clock_timestamp(),error_code=NULL
    WHERE event_id=p_event AND lease_token=p_token AND state='IN_FLIGHT'
      AND lease_until > clock_timestamp();
    GET DIAGNOSTICS changed = ROW_COUNT;
    IF changed <> 1 THEN
        RAISE EXCEPTION 'Stale IAM delivery lease' USING ERRCODE='42501';
    END IF;
END $$;

CREATE FUNCTION company_configuration.cp_fail_iam_ack(
    p_event uuid,p_token uuid,p_error text
) RETURNS text LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog,pg_temp AS $$
DECLARE prior integer;
DECLARE decision text;
BEGIN
    IF p_event IS NULL OR p_token IS NULL OR p_error NOT IN (
        'NETWORK_ERROR','HTTP_REJECTED','SOURCE_UNAVAILABLE','UNKNOWN'
    ) OR p_error IS NULL THEN
        RAISE EXCEPTION 'Invalid delivery failure classification' USING ERRCODE='42501';
    END IF;
    SELECT attempts INTO prior
    FROM company_configuration.privileged_iam_ack_outbox
    WHERE event_id=p_event AND lease_token=p_token AND state='IN_FLIGHT'
      AND lease_until > clock_timestamp() FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Stale IAM delivery lease' USING ERRCODE='42501';
    END IF;
    decision := CASE WHEN prior>=5 OR p_error='HTTP_REJECTED' THEN 'DEAD' ELSE 'RETRY' END;
    UPDATE company_configuration.privileged_iam_ack_outbox
    SET state=decision,lease_token=NULL,lease_until=NULL,error_code=p_error,
        next_attempt_at=clock_timestamp() + (
            LEAST(300,(2 ^ LEAST(prior,8))::integer) * interval '1 second'
        )
    WHERE event_id=p_event;
    RETURN decision;
END $$;

REVOKE ALL ON FUNCTION company_configuration.cp_claim_iam_ack(integer) FROM PUBLIC;
REVOKE ALL ON FUNCTION company_configuration.cp_complete_iam_ack(uuid,uuid) FROM PUBLIC;
REVOKE ALL ON FUNCTION company_configuration.cp_fail_iam_ack(uuid,uuid,text) FROM PUBLIC;
