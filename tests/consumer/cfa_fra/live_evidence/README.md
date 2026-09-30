# CFA FRA live cutover evidence artifacts

This directory is the canonical materialization root for external CFA FRA cutover proofs.

A `PASS` record in `../RETIREMENT_EVIDENCE.json` must reference a file beneath this
directory using a safe relative path. Canonical CI resolves the path, reads the actual bytes
and verifies the declared lowercase SHA-256 before exposing any MIG-13 retirement boolean.

Do not place fabricated evidence here. Until a real live-consumer proof exists, keep the
corresponding manifest record `BLOCKED` with an explicit reason.


## Promotion workflow

Use the repository command instead of editing a PASS digest manually:

```bash
python scripts/promote_cfa_fra_cutover_evidence.py \
  legacy_identities \
  --artifact identity-migration.json \
  --source live-consumer-cutover \
  --observed-at 2026-09-30T12:30:00Z \
  --producer cfa-fra-cutover-pipeline
```

This is a dry-run and prints the candidate manifest. Re-run with `--write` only after
reviewing the generated attestation. The command computes the digest from the file itself,
verifies the resulting PASS and removes only the corresponding blocker.


## Required artifact schemas

A promoted identity artifact must declare:

```text
schema = cfa_fra_legacy_identity_migration/v1
kind   = legacy_identity_migration
```

and provide complete legacy-to-target mappings with `unresolved_records = 0`.

A promoted regulatory-authority artifact must declare:

```text
schema = cfa_fra_regulatory_authority_cutover/v1
kind   = regulatory_authority_cutover
```

and prove target-only routing, disabled local accounting authority, delegated
`effective_plan` and at least one provider-backed reference resolution.

A correct file hash alone is not evidence of either condition.
