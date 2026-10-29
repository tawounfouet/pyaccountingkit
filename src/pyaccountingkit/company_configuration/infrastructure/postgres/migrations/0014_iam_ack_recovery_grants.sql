-- FND-C03 / L02-07n: prevent direct recovery-role bypass of Python approvals.
-- A distinct independently operated approval writer must first commit a
-- short-lived, exact-scope, one-use grant. The recovery role may ONLY consume.
-- This is NOT database-side Ed25519 verification, nor a production IdP.
-- Migration 0013 is deliberately immutable; replace its routine here.
CREATE TABLE company_configuration.privileged_iam_ack_recovery_grants (
    approval_reference text PRIMARY KEY CHECK (
        approval_reference <> '' AND length(approval_reference) <= 128
    ),
    event_id uuid NOT NULL,
    request_id uuid NOT NULL,
    tenant_id text NOT NULL CHECK (tenant_id <> '' AND btrim(tenant_id)=tenant_id),
    redrive_number integer NOT NULL CHECK (redrive_number BETWEEN 1 AND 2),
    actor_id text NOT NULL CHECK (actor_id <> '' AND btrim(actor_id)=actor_id),
    approver_id text NOT NULL CHECK (
        approver_id <> '' AND btrim(approver_id)=approver_id
        AND approver_id <> actor_id
    ),
    evidence_reference text NOT NULL CHECK (
        evidence_reference <> '' AND length(evidence_reference)<=256
    ),
    reason_code text NOT NULL CHECK (
        reason_code IN ('PROVIDER_RECOVERED','INCIDENT_REVIEWED','DELIVERY_RESTORED')
    ),
    expires_at timestamptz NOT NULL,
    granted_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (event_id, redrive_number)
);
CREATE TRIGGER forbid_privileged_recovery_grant_change
BEFORE UPDATE OR DELETE ON company_configuration.privileged_iam_ack_recovery_grants
FOR EACH ROW EXECUTE FUNCTION company_configuration.forbid_evidence_mutation();
REVOKE ALL ON company_configuration.privileged_iam_ack_recovery_grants FROM PUBLIC;

CREATE TABLE company_configuration.privileged_iam_ack_recovery_consumptions (
    approval_reference text PRIMARY KEY REFERENCES
        company_configuration.privileged_iam_ack_recovery_grants(approval_reference),
    event_id uuid NOT NULL,
    redrive_number integer NOT NULL,
    consumed_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (event_id, redrive_number)
);
CREATE TRIGGER forbid_privileged_recovery_consumption_change
BEFORE UPDATE OR DELETE ON company_configuration.privileged_iam_ack_recovery_consumptions
FOR EACH ROW EXECUTE FUNCTION company_configuration.forbid_evidence_mutation();
REVOKE ALL ON company_configuration.privileged_iam_ack_recovery_consumptions FROM PUBLIC;

-- Only a distinct recovery-approval writer may mint a capability.
-- The caller must have already verified signed, current, independent approval.
-- The database separately checks scope, DEAD state, bounded expiry, and
-- one-use number. No caller-provided SQL role names or trusted GUCs.
CREATE FUNCTION company_configuration.cp_grant_iam_ack_redrive(
    p_event uuid, p_request uuid, p_tenant text, p_actor text, p_approver text,
    p_approval text, p_reason text, p_evidence text, p_expires timestamptz
) RETURNS integer LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,pg_temp AS $$
DECLARE
    item record;
    next_count integer;
    now_at timestamptz;
BEGIN
    IF session_user <> 'cc_iam_approval_writer'
       OR p_event IS NULL OR p_request IS NULL
       OR p_tenant IS NULL OR p_tenant='' OR btrim(p_tenant)<>p_tenant
       OR p_actor IS NULL OR p_actor='' OR btrim(p_actor)<>p_actor
       OR p_approver IS NULL OR p_approver='' OR btrim(p_approver)<>p_approver
       OR p_actor=p_approver
       OR p_approval IS NULL OR p_approval='' OR length(p_approval)>128
       OR p_evidence IS NULL OR p_evidence='' OR length(p_evidence)>256
       OR p_reason IS NULL OR p_reason NOT IN (
          'PROVIDER_RECOVERED','INCIDENT_REVIEWED','DELIVERY_RESTORED'
       ) OR p_expires IS NULL THEN
        RAISE EXCEPTION 'Unauthorized scoped IAM recovery approval'
            USING ERRCODE='42501';
    END IF;
    now_at := clock_timestamp();
    IF p_expires <= now_at OR p_expires > now_at + interval '5 minutes' THEN
        RAISE EXCEPTION 'Unacceptable IAM recovery approval expiry'
            USING ERRCODE='42501';
    END IF;
    SELECT a.* INTO item
    FROM company_configuration.privileged_iam_ack_outbox AS a
    WHERE a.event_id=p_event FOR UPDATE;
    IF NOT FOUND OR item.request_id IS DISTINCT FROM p_request
       OR item.tenant_id IS DISTINCT FROM p_tenant
       OR item.state <> 'DEAD' OR item.redrive_count >= 2 THEN
        RAISE EXCEPTION 'No eligible DEAD delivery for approval'
            USING ERRCODE='42501';
    END IF;
    next_count := item.redrive_count+1;
    INSERT INTO company_configuration.privileged_iam_ack_recovery_grants (
        approval_reference,event_id,request_id,tenant_id,redrive_number,
        actor_id,approver_id,evidence_reference,reason_code,expires_at
    ) VALUES (
        p_approval,p_event,p_request,p_tenant,next_count,
        p_actor,p_approver,p_evidence,p_reason,p_expires
    );
    RETURN next_count;
END $$;
REVOKE ALL ON FUNCTION company_configuration.cp_grant_iam_ack_redrive(
    uuid,uuid,text,text,text,text,text,text,timestamptz
) FROM PUBLIC;

-- Keep the 0013 procedure signature for consumer compatibility but now
-- require the independently issued and exact-match capability, consuming
-- it atomically alongside the existing immutable decision and queue state.
CREATE OR REPLACE FUNCTION company_configuration.cp_redrive_dead_iam_ack(
    p_event uuid,p_request uuid,p_tenant text,p_actor text,p_approver text,
    p_approval text,p_reason text,p_evidence text
) RETURNS integer LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,pg_temp AS $$
DECLARE
    item record;
    ticket record;
    next_count integer;
BEGIN
    IF session_user <> 'cc_iam_recovery'
       OR p_event IS NULL OR p_request IS NULL
       OR p_tenant IS NULL OR p_tenant='' OR btrim(p_tenant)<>p_tenant
       OR p_actor IS NULL OR p_actor='' OR btrim(p_actor)<>p_actor
       OR p_approver IS NULL OR p_approver='' OR btrim(p_approver)<>p_approver
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
    SELECT g.* INTO ticket
    FROM company_configuration.privileged_iam_ack_recovery_grants AS g
    WHERE g.approval_reference=p_approval FOR UPDATE;
    IF NOT FOUND
       OR ticket.event_id IS DISTINCT FROM p_event
       OR ticket.request_id IS DISTINCT FROM p_request
       OR ticket.tenant_id IS DISTINCT FROM p_tenant
       OR ticket.actor_id IS DISTINCT FROM p_actor
       OR ticket.approver_id IS DISTINCT FROM p_approver
       OR ticket.evidence_reference IS DISTINCT FROM p_evidence
       OR ticket.reason_code IS DISTINCT FROM p_reason
       OR ticket.redrive_number IS DISTINCT FROM next_count
       OR ticket.expires_at <= clock_timestamp() THEN
        RAISE EXCEPTION 'Missing, expired or mismatched independent recovery grant'
            USING ERRCODE='42501';
    END IF;
    -- Unique consumption prevents ticket replay; all writes share this tx.
    INSERT INTO company_configuration.privileged_iam_ack_recovery_consumptions (
        approval_reference,event_id,redrive_number
    ) VALUES (p_approval,p_event,next_count);
    INSERT INTO company_configuration.privileged_iam_ack_redrive_decisions (
        decision_id,event_id,request_id,tenant_id,redrive_number,
        actor_id,approver_id,approval_reference,evidence_reference,
        reason_code,previous_error_code
    ) VALUES (
        pg_catalog.gen_random_uuid(),p_event,p_request,p_tenant,next_count,
        p_actor,p_approver,p_approval,p_evidence,p_reason,item.error_code
    );
    UPDATE company_configuration.privileged_iam_ack_outbox
    SET state='RETRY',attempts=0,redrive_count=next_count,
        next_attempt_at=clock_timestamp(),lease_token=NULL,lease_until=NULL,
        error_code=NULL,delivered_at=NULL
    WHERE event_id=p_event;
    RETURN next_count;
END $$;
REVOKE ALL ON FUNCTION company_configuration.cp_redrive_dead_iam_ack(
    uuid,uuid,text,text,text,text,text,text
) FROM PUBLIC;
