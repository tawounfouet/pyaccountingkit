-- L02-07l: operational metrics and independently approved DEAD-letter re-drive.
-- The delivery account can view only aggregated metrics, never the raw outbox.
-- The recovery account can inspect scoped DEAD metadata and submit approved
-- redrives. Claimed identities are NOT cryptographically verified in PostgreSQL.
ALTER TABLE company_configuration.privileged_iam_ack_outbox
ADD COLUMN redrive_count integer NOT NULL DEFAULT 0 CHECK (redrive_count BETWEEN 0 AND 2);

CREATE TABLE company_configuration.privileged_iam_ack_redrive_decisions (
    decision_id uuid PRIMARY KEY,
    event_id uuid NOT NULL REFERENCES company_configuration.privileged_iam_ack_outbox(event_id),
    request_id uuid NOT NULL,
    tenant_id text NOT NULL,
    redrive_number integer NOT NULL CHECK (redrive_number BETWEEN 1 AND 2),
    actor_id text NOT NULL CHECK (actor_id <> ''),
    approver_id text NOT NULL CHECK (approver_id <> '' AND approver_id <> actor_id),
    approval_reference text NOT NULL UNIQUE CHECK (approval_reference <> ''),
    evidence_reference text NOT NULL CHECK (evidence_reference <> ''),
    reason_code text NOT NULL CHECK (
        reason_code IN ('PROVIDER_RECOVERED','INCIDENT_REVIEWED','DELIVERY_RESTORED')
    ),
    previous_error_code text,
    decided_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (event_id,redrive_number)
);
CREATE TRIGGER forbid_privileged_redrive_decision_change
BEFORE UPDATE OR DELETE ON company_configuration.privileged_iam_ack_redrive_decisions
FOR EACH ROW EXECUTE FUNCTION company_configuration.forbid_evidence_mutation();
REVOKE ALL ON company_configuration.privileged_iam_ack_redrive_decisions FROM PUBLIC;

CREATE FUNCTION company_configuration.cp_iam_ack_metrics()
RETURNS TABLE (
    pending bigint, in_flight bigint, retry bigint, delivered bigint,
    dead bigint, stale_leases bigint, due_count bigint, oldest_open_seconds bigint
) LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
    SELECT
        count(*) FILTER (WHERE state='PENDING'),
        count(*) FILTER (WHERE state='IN_FLIGHT'),
        count(*) FILTER (WHERE state='RETRY'),
        count(*) FILTER (WHERE state='DELIVERED'),
        count(*) FILTER (WHERE state='DEAD'),
        count(*) FILTER (
            WHERE state='IN_FLIGHT' AND lease_until <= clock_timestamp()
        ),
        count(*) FILTER (
            WHERE state IN ('PENDING','RETRY') AND next_attempt_at <= clock_timestamp()
        ),
        COALESCE(max(
            EXTRACT(epoch FROM (clock_timestamp()-created_at))::bigint
        ) FILTER (WHERE state NOT IN ('DELIVERED','DEAD')), 0)
    FROM company_configuration.privileged_iam_ack_outbox
$$;
REVOKE ALL ON FUNCTION company_configuration.cp_iam_ack_metrics() FROM PUBLIC;

CREATE FUNCTION company_configuration.cp_list_dead_iam_acks(p_tenant text, p_limit integer)
RETURNS TABLE (
    event_id uuid, request_id uuid, tenant_id text, disposition text,
    attempts integer, redrive_count integer, error_code text, created_at timestamptz
) LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
BEGIN
    IF p_tenant IS NULL OR p_tenant='' OR btrim(p_tenant) <> p_tenant
       OR p_limit IS NULL OR p_limit < 1 OR p_limit > 20 THEN
        RAISE EXCEPTION 'Invalid dead-letter inspection scope' USING ERRCODE='42501';
    END IF;
    RETURN QUERY
        SELECT a.event_id,a.request_id,a.tenant_id,a.disposition,
               a.attempts,a.redrive_count,a.error_code,a.created_at
        FROM company_configuration.privileged_iam_ack_outbox AS a
        WHERE a.tenant_id=p_tenant AND a.state='DEAD'
        ORDER BY a.created_at,a.event_id LIMIT p_limit;
END $$;
REVOKE ALL ON FUNCTION company_configuration.cp_list_dead_iam_acks(text,integer)
FROM PUBLIC;

CREATE FUNCTION company_configuration.cp_redrive_dead_iam_ack(
    p_event uuid,p_request uuid,p_tenant text,p_actor text,p_approver text,
    p_approval text,p_reason text,p_evidence text
) RETURNS integer LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,pg_temp AS $$
DECLARE
    item record;
    next_count integer;
BEGIN
    IF p_event IS NULL OR p_request IS NULL
       OR p_tenant IS NULL OR p_tenant='' OR btrim(p_tenant) <> p_tenant
       OR p_actor IS NULL OR p_actor='' OR btrim(p_actor) <> p_actor
       OR p_approver IS NULL OR p_approver='' OR btrim(p_approver) <> p_approver
       OR p_approver=p_actor
       OR p_approval IS NULL OR p_approval='' OR length(p_approval)>128
       OR p_evidence IS NULL OR p_evidence='' OR length(p_evidence)>256
       OR p_reason IS NULL OR p_reason NOT IN (
          'PROVIDER_RECOVERED','INCIDENT_REVIEWED','DELIVERY_RESTORED'
       ) THEN
        RAISE EXCEPTION 'Invalid independently approved re-drive scope'
            USING ERRCODE='42501';
    END IF;
    SELECT a.* INTO item
    FROM company_configuration.privileged_iam_ack_outbox AS a
    WHERE a.event_id=p_event FOR UPDATE;
    IF NOT FOUND OR item.request_id IS DISTINCT FROM p_request
       OR item.tenant_id IS DISTINCT FROM p_tenant
       OR item.state <> 'DEAD' OR item.redrive_count >= 2 THEN
        RAISE EXCEPTION 'No eligible scoped DEAD delivery for re-drive'
            USING ERRCODE='42501';
    END IF;
    next_count := item.redrive_count+1;
    -- Decision evidence and the queue transition MUST commit together.
    INSERT INTO company_configuration.privileged_iam_ack_redrive_decisions (
        decision_id,event_id,request_id,tenant_id,redrive_number,
        actor_id,approver_id,approval_reference,evidence_reference,
        reason_code,previous_error_code
    ) VALUES (
        pg_catalog.gen_random_uuid(),p_event,p_request,p_tenant,next_count,
        p_actor,p_approver,p_approval,p_evidence,p_reason,item.error_code
    );
    UPDATE company_configuration.privileged_iam_ack_outbox
    SET state='RETRY', attempts=0,redrive_count=next_count,
        next_attempt_at=clock_timestamp(),lease_token=NULL,lease_until=NULL,
        error_code=NULL,delivered_at=NULL
    WHERE event_id=p_event;
    RETURN next_count;
END $$;
REVOKE ALL ON FUNCTION company_configuration.cp_redrive_dead_iam_ack(
    uuid,uuid,text,text,text,text,text,text
) FROM PUBLIC;
