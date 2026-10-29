# ADR-CC-08G - Delegated privileged control plane

**Status: PROPOSED. Independent architecture/security approval pending.**

## Decision candidate

Replace the schema-owner credentials **used by a fenced role execution adapter** with a dedicated non-privileged SQL login granted EXECUTE only on audited, schema-owner-controlled `SECURITY DEFINER` entry points. Use PostgreSQL authorization rather than a Python-only contract to enforce that runtime and tenant accounts cannot perform privileged DDL. Bind every call to a tenant, exact target LOGIN, request/actor/approval and an ACTIVE, unexpired fence. Transactions must retain fence row locks until DDL and CONSUMED evidence commit, including backend session termination attempts.

## Deployment contract still unimplemented

Production must segregate application runtime, delegated control plane, schema owner/provisioner and auditor. Only a limited private control-plane network may connect with the delegated login. No application worker, tenant or web process should possess owner credentials or call the delegated SQL routines. Manage service credentials in a real vault, disable insecure logging, enforce TLS, rotate/revoke credentials and verify backups, privilege drift and restore. Couple requests to independently signed IAM/SoD decisions with revocation propagation and acknowledgements.

## Threat and non-guarantees

A leaked delegated login can call these routines without per-operation IAM signatures: the SQL function validates the claimed identities and role scopes, **not cryptographic identity authenticity**. Database superusers/schema owner can bypass grants or alter functions. Session termination is a side effect that cannot be undone by rollback. Credential change, fence consumption, app audit and external IAM are not a single global transaction. PostgreSQL owner-only append-only evidence is not externally attested WORM.

## Acceptance

Perform independent source/security reviews of SQL `SECURITY DEFINER`, grants, search_path, malicious target names and SQL injection, role escalation, credential logging, pooling and transaction reuse; test a real deployed network boundary, independent IAM/SoD, revocation ACK, restore, failure modes and all G0/G1/G2 requirements before production qualification. This ADR is not approved by a passing CI alone.
