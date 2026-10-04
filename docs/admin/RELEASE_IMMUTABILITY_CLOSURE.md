# Release Immutability Closure Runbook

This runbook closes the G5 external control required before `v0.7.0`.

## External control

GitHub release immutability must be enabled and positively verified **before** the stable release is
created.

GitHub exposes the repository control through:

```text
GET /repos/{owner}/{repo}/immutable-releases
PUT /repos/{owner}/{repo}/immutable-releases
```

The read endpoint requires repository `Administration: read`; activation requires
`Administration: write`.

## Required credential

Use a short-lived fine-grained GitHub token scoped to:

```text
repository: tawounfouet/pyaccountingkit
repository permission: Administration — Read and write
```

Export it only for the administration command:

```bash
export PYAK_GITHUB_ADMIN_TOKEN="<token>"
```

Never commit or paste this token into repository files, issues, pull requests or workflow YAML.

## One-command G5 closure

When both external controls are ready to be administered, prefer the orchestrator:

```bash
python scripts/close_g5_external_controls.py close
```

It executes branch protection and release immutability in fail-closed order, verifies both live
GitHub states before writing evidence, and never creates a tag, package publication or GitHub
Release.

Use the individual scripts below only for targeted diagnosis or partial administration.

## Apply and verify

The canonical repository-side tool is:

```text
scripts/configure_release_immutability.py
```

Enable the server-side control and immediately verify it:

```bash
python scripts/configure_release_immutability.py apply
```

Verify it later without changing the repository setting:

```bash
python scripts/configure_release_immutability.py check
```

A disabled repository remains fail-closed. The GitHub read endpoint returns `404` when immutable
releases are not enabled; the script normalizes that state to `enabled=false` and refuses
promotion.

## Promote the G5 evidence record

Only after the live `check` succeeds:

```bash
python scripts/configure_release_immutability.py promote-status
python scripts/validate_stable_gate.py
```

The promotion command re-reads the live GitHub state before modifying
`docs/audits/G5_EXTERNAL_CONTROLS.json`. It then:

- sets `observed_enabled=true`;
- sets the immutable-release control to `COMPLETE`;
- records whether the policy is enforced by the repository owner;
- closes `IMMUTABLE_RELEASES_UNVERIFIED`;
- keeps every release/publication claim `false`.

Commit that evidence update through the normal pull-request path. The other G5 external control,
main-branch protection, remains independently required.

## UI fallback

If API administration is unavailable, the repository owner can enable the setting in:

```text
Repository
  -> Settings
  -> General
  -> Releases
  -> Enable release immutability
```

The UI action alone is not sufficient evidence. Run the authenticated `check` and
`promote-status` commands afterward.

## Publication boundary

Release immutability protects a release only after it is published. Draft releases remain mutable.
The release workflow therefore:

1. creates the GitHub Release as a draft;
2. uploads the exact sealed assets;
3. publishes the fully populated release;
4. verifies the resulting GitHub release attestation with `gh release verify`.

The post-publication verification is an integrity assertion, not a substitute for this pre-tag G5
control.

## Safety

Do not create `v0.7.0`, publish PyPI `0.7.0`, or publish the stable GitHub Release until both
external G5 controls are positively attested and the exact stable-candidate head passes the
canonical G5 gate.
