# ADR-CC-08M - Independently Signed DEAD-Letter Recovery Approval

**Status: PROPOSED, independent security review required. Not accepted.**

## Decision candidate

For manual IAM ACK `DEAD` re-drives, bind independent Ed25519-signed approval evidence to one exact approval reference, event UUID, request UUID, tenant, reason and incident evidence reference. Require a distinct authenticated operator signer and recovery checker signer, positive current-grant check, double-read freshness, and an unexpired proof. Reject forged, wrong-scope, altered, self-approved, unsigned or expired requests before restricted SQL. Use only the existing `cc_iam_recovery` capability after live PostgreSQL session-identity and grant checks.

## Rejected alternatives

- Treat a `VerifiedRedriveApproval` dataclass received from an API as authentication or approval: untrusted origin and mutable permission state.
- Reuse the operator's public key for the checker: a stolen key would permit self-approval.
- Assume DB owner-only SQL or successful Ed25519 tests prove a real IdP and a protected deployment: they do not.
- Assume signed JWS evidence alone authorizes an action without an independent current policy/grant check.

## Unresolved controls

A production independent approval service/source and issuer key lifecycle; online revocation and replay semantics; dedicated workload identity/mTLS and network policy; SQL credential containment and the remaining direct-call bypass; independent audit retention and evidence hash custody; incident-recovery sign-off; external provider contract; redrive metrics/alerts and restore drills. G0/G1/G2 and this ADR must be approved separately. No stable release or security acceptance implied.
