# ADR-CC-08 candidate supplement - tenant-bound PostgreSQL login

**State:** PROPOSED, pending reviewer and approval, does not supersede Security Model 19.

**Problem:** Custom PostgreSQL session variables are settable by clients, therefore cannot independently authorize tenant scope in a shared database role.

**Decision candidate:** Provision a unique PostgreSQL *login credential per tenant and service category*, with owner-controlled `session_user` to tenant mapping. RLS references only the bound login, not a user-controlled GUC. The login role is NOINHERIT, NOSUPERUSER, NOCREATEROLE, NOBYPASSRLS, with least-privilege table grants. Non-mapped logins fail closed.

**Alternatives deferred:** independently trusted proxy with signed tenant assertions; database-per-tenant deployment; hardened SECURITY DEFINER API with fully revoked direct table access. These may better fit large multi-tenant scale or different operational models.

**Positive consequences:** documented spoof resistance at the database boundary; role separation and direct SQL RLS protection; clear authorization test contract.

**Costs/tradeoffs:** potentially large role/credential count; distinct connection pools and rotation paths; operational entitlement management; trusted schema owner with security-sensitive binding controls. The role binding does not authorize company/entity/book nor user actions.

**Mandatory follow-up:** independent security review, production secret rotation and revocation, cross-process pool isolation, privileged role hardening, C10 integration tests, ADR approval and gate evidence before production.
