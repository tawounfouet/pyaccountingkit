# Main Branch Protection Closure Runbook

This runbook closes the only remaining external blocker recorded by
`LOT-00.9 - Final Qualification`.

## Current blocker

```text
MAIN_BRANCH_PROTECTION_UNENFORCED
```

Repository-side CI, Security, package, release and resource-governance controls are already
qualified. GitHub server-side protection for `main` must still be enabled and verified.

## Required GitHub credential

Use a fine-grained GitHub token scoped to:

```text
repository: tawounfouet/pyaccountingkit
repository permission: Administration — Read and write
```

Do not commit the token and do not store it in project files.

Export it only for the administration command:

```bash
export PYAK_GITHUB_ADMIN_TOKEN="<token>"
```

## Canonical policy

The script applies and verifies:

```text
branch: main

require pull request before merge            YES
required approving reviews                   0
strict status checks                         YES
required check: Canonical CI gate            YES
required check: Dependency audit             YES
required check: Static security analysis     YES
enforce rules for administrators             YES
allow force pushes                           NO
allow branch deletion                        NO
require conversation resolution              YES
require linear history                       YES
```

The zero-review setting is intentional for the current single-maintainer repository: changes must
flow through pull requests and pass all required automated checks without making self-approval an
impossible merge requirement.

## Apply protection

```bash
python scripts/configure_main_branch_protection.py apply
```

The command uses GitHub's authenticated branch-protection API and immediately verifies the returned
server policy.

## Verify protection later

```bash
python scripts/configure_main_branch_protection.py check
```

This command is read-only but still requires an Administration-readable token because GitHub's
branch-protection endpoint is an administration API.

## Promote LOT-00 status after successful verification

Only after `check` passes:

```bash
python scripts/configure_main_branch_protection.py promote-status
python scripts/validate_lot00_remediation_status.py --require-complete
```

The promotion command:

- re-reads the live GitHub protection policy;
- refuses promotion if any required control is missing;
- changes `observed_protected` to `true`;
- closes `MAIN_BRANCH_PROTECTION_UNENFORCED`;
- promotes `LOT-00.9` to `COMPLETE`;
- promotes overall LOT-00 status to `COMPLETE`;
- leaves every release/publication claim unchanged and false.

Commit the resulting status update through a normal pull request and require final CI + Security
green on the exact reviewed head.

## Security notes

- Never place the administration token in `.env`, workflow YAML, issue text or repository files.
- Prefer a short-lived fine-grained token limited to this repository.
- Revoke the token after the server-side configuration is complete if it was created solely for
  this one-time operation.
- Do not weaken the policy to make the closure validator pass.
