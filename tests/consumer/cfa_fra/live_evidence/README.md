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


## Generation workflow

b17 separates **observation sources** from **evidence artifacts**.

Use the generator with an exported source observation:

```bash
python scripts/generate_cfa_fra_cutover_artifact.py \
  legacy_identities \
  --source identity-source.json \
  --artifact legacy-identities.json
```

The default is a dry-run. Add `--write` to materialize the artifact beneath the configured
artifact root. Replacing an existing artifact additionally requires `--overwrite`.

For identity evidence, `expected_legacy_records` must come from an independent legacy
population count; it is not inferred from the migrated mappings. For regulatory authority,
the observation must already demonstrate target-only routing and replacement of local
reference authority.

Generation does **not** edit `RETIREMENT_EVIDENCE.json`. Promotion remains a separate,
reviewable action through `promote_cfa_fra_cutover_evidence.py`.


## Reviewed pipeline workflow

b18 provides a two-step orchestration layer:

```bash
python scripts/run_cfa_fra_cutover_evidence_pipeline.py \
  plan legacy_identities \
  --source identity-source.json \
  --artifact legacy-identities.json \
  --evidence-source live-consumer-cutover \
  --observed-at 2026-09-30T15:00:00Z \
  --producer cfa-fra-cutover-pipeline \
  --plan-output identity-plan.json
```

Review the serialized plan before applying it:

```bash
python scripts/run_cfa_fra_cutover_evidence_pipeline.py \
  apply --plan identity-plan.json
```

The apply step verifies that the current retirement manifest still matches the fingerprint
captured by the plan. Any intervening change requires a new plan. It also recomputes the
promotion result and requires it to match the reviewed candidate manifest exactly.


## Consumer E2E evidence

b19 adds:

```text
schema = cfa_fra_consumer_e2e_cutover/v1
kind   = consumer_e2e_cutover
```

The artifact must contain exactly one PASS result for all ten mandatory Gate Consumer
scenarios, each with a `sha256:<64 lowercase hex>` provenance checksum. Missing, duplicate,
BLOCKED or FAIL scenarios invalidate the artifact.

The bundled Sprint-7 test harness remains useful as frozen regression evidence, but a live
consumer artifact is the retirement proof consumed by MIG-13.
