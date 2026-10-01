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

## Standalone consumer bootstrap

When no separate live-consumer repository exists yet, generate a reviewed standalone seed from
the frozen Sprint-7 oracle:

```bash
python scripts/bootstrap_cfa_fra_live_consumer.py \
  --destination ../cfa-fra-live
```

The default is a dry-run. Materialization requires:

```bash
python scripts/bootstrap_cfa_fra_live_consumer.py \
  --destination ../cfa-fra-live \
  --write
```

The command verifies the current Git tree of the bundled oracle against the qualified LOT-25 SHA,
copies the tree without modifying the source, adds the compatible PyAccountingKit dependency,
fixes only the proven login redirect defect and writes
`PYACCOUNTINGKIT_CONSUMER_BOOTSTRAP.json`.

The generated seed is deliberately not live evidence. It remains
`UNBOUND_UNTIL_PUBLISHED` with cutover `NOT_STARTED` until it has its own reviewed repository
identity and real cutover observations.

## Verified consumer publication handoff

After the standalone seed has been initialized and published as its own Git repository, review
the exact publication before changing the canonical binding:

```bash
python scripts/run_cfa_fra_consumer_publication.py \
  plan \
  --consumer-root ../cfa-fra-live \
  --repository OWNER/cfa-fra-live \
  --observed-at 2026-10-01T07:00:00Z \
  --producer manual-review \
  --plan-output publication-plan.json
```

Then apply the reviewed plan. The first apply is a dry-run:

```bash
python scripts/run_cfa_fra_consumer_publication.py \
  apply \
  --consumer-root ../cfa-fra-live \
  --plan publication-plan.json
```

Only an explicit `--write` promotes `CONSUMER_BINDING.json` to BOUND. Apply fails if the
consumer HEAD, origin, branch, worktree, bootstrap provenance or canonical binding changed after
review.

## Live consumer repository binding

Before producing release-grade live evidence, bind the actual consumer in
`../CONSUMER_BINDING.json`. Until that repository is verified, keep the canonical file
`UNBOUND`.

A release-grade BOUND state must pin:

```text
repository        owner/name
repository_url    https://github.com/owner/name
default_branch    exact branch name
revision_sha      exact 40-character lowercase Git SHA
environment       production
observed_at       UTC timestamp
producer          evidence producer identity
```

The release gate requires the bound `revision_sha` to match the revision sealed in
`legacy-retirement-completion.json`. Do not infer the live repository from a related project
or from code similarity.

## 0.6.0rc1 live retirement materialization

b23 makes the `release/*` qualification fail closed unless the canonical live cutover is
materialized here. Before promoting `0.6.0rc1`, the directory must contain the three verified
cutover artifacts referenced by `RETIREMENT_EVIDENCE.json` plus the reviewed L26-C retirement
chain:

```text
consumer-e2e.json
legacy-identities.json
regulatory-authority.json

legacy-retirement-plan.json
legacy-retirement-execution.json
legacy-retirement-completion.json
```

The plan must be generated only after canonical MIG-13 readiness is READY. Retirement itself is
performed in the live consumer repository, never by PyAccountingKit. The execution file records
the checksummed post-cutover observation for each of the 39 reviewed components. The completion
file is generated from that exact plan and execution evidence.

On a `release/*` pull request, CI reconstructs canonical live readiness from the actual test and
PostgreSQL adapter results plus the three verified cutover records. It then revalidates the
committed plan/execution evidence, regenerates the completion proof and requires the regenerated
JSON to match `legacy-retirement-completion.json` exactly before release-candidate qualification
can start.

Do not copy fixture evidence from `tests/fixtures/` into this directory.
\n