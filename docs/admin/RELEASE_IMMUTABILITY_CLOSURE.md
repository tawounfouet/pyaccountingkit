# Release Immutability Closure Runbook

This runbook closes the G5 external control required before `v0.7.0`.

## Required repository setting

GitHub release immutability must be enabled **before** the stable release is published.

UI path:

```text
Repository
  -> Settings
  -> General
  -> Releases
  -> Enable release immutability
```

After enabling it, verify the repository setting and update:

`docs/audits/G5_EXTERNAL_CONTROLS.json`

to:

```json
{
  "required": true,
  "observed_enabled": true,
  "status": "COMPLETE"
}
```

Then close `IMMUTABLE_RELEASES_UNVERIFIED` in the same file.

## Why this is fail-closed

Release immutability applies only to future releases. Therefore `v0.7.0` must not be created first and protected later.

The release workflow also verifies the published release with `gh release verify`, but that is a post-publication integrity assertion, not a substitute for the pre-tag G5 control.
