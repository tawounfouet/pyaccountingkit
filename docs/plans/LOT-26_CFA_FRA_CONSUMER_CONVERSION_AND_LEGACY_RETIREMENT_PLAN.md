# LOT-26 — CFA FRA Consumer Conversion & Legacy Engine Retirement

**Baseline:** `0.6.0a1` / LOT-25 merged at `3994543e11d9f97f1b75ccb7891ecdde25363732`  
**Target line:** `0.6.0b1 -> 0.6.0`

## Objective

Convert CFA FRA from an application that owns a duplicate accounting engine into a Django
consumer of the framework-neutral `AccountingApplication` facade.

LOT-26 is a strangler migration. It must preserve CFA FRA HTTP/UI concerns while transferring
accounting authority to PyAccountingKit service by service.

## Non-negotiable boundaries

- no runtime dependency on the bundled CFA FRA Django resource;
- no Django model, form, view, QuerySet or transaction primitive enters the domain/public API;
- no accounting mutation may be dual-written;
- read-side dual-run is allowed only as shadow comparison evidence;
- regulatory facts come from PyAccountingKit reference providers, never from a copied
  `FrameworkAccount` authority;
- legacy accounting code is removed only after consumer parity is proven;
- historical CFA FRA identities remain traceable.

## Migration architecture

```text
CFA FRA Django view/form
        |
        v
CFAFRACompatibilityAdapter
        |
        +-- mutation feature switch -------- LEGACY xor PYACCOUNTINGKIT
        |
        +-- read route ---------------------- LEGACY or PYACCOUNTINGKIT
        |          \
        |           +-- optional shadow dual-run comparison
        |
        +-- LegacyIdentityMap --------------- historical ID/provenance trace
        |
        v
AccountingApplication
```

The compatibility adapter is temporary. It exists to preserve old consumer service signatures
while calls move to the stable public facade.

## Initial conversion surface

Mutation routes:

- `post_entry -> accounting.entries.post`
- `reverse_entry -> accounting.entries.reverse`
- `execute_fec_import -> accounting.imports.execute`
- `close_period -> accounting.closing.close`

Read routes:

- `trial_balance -> accounting.ledger.trial_balance`
- `financial_statements -> accounting.statements.build`
- `run_controls -> accounting.controls.run`
- `effective_plan -> accounting.references.get_effective_plan`

## Mutation rule

For any operation, routing selects exactly one backend:

```text
LEGACY
or
PYACCOUNTINGKIT
```

There is intentionally no `DUAL_WRITE` state.

## Read dual-run rule

Selected reads may invoke legacy and PyAccountingKit in the same request for comparison.
The configured primary backend remains the user-visible result. The shadow result is used only
to emit a `DualRunObservation`; it does not mutate accounting state.

## Identity migration

`LegacyIdentityMap` records:

```text
legacy_type
legacy_id
target_type
target_id
source
source_checksum
```

Conflicting remaps fail closed. Re-registering the exact same mapping is idempotent.

## Phases

### L26-A — compatibility foundation / 0.6.0b1

- compatibility adapter;
- per-operation mutation/read routing;
- read-side dual-run observation;
- injectable legacy identity store with an in-memory reference implementation;
- fail-closed legacy-retirement gate;
- framework-neutral consumer contract tests.

### L26-B — consumer delegation / 0.6.0b2+

- preserve the real CFA FRA service signatures at the consumer boundary;
- translate legacy ORM identities through `LegacyIdentityStoreProtocol`;
- convert CFA FRA accounting services service-by-service;
- keep views/forms/permissions/HTMX in CFA FRA;
- switch regulatory lookup to provider-backed public references;
- add consumer E2E/smoke evidence.

The `0.6.0b2` slice covers actual posting, reversal, FEC execution and trial-balance selector
signatures. The `0.6.0b3` slice adds the real Sprint-6 financial-statement signatures through
an explicit `StatementTargetParametersFactory`: the consumer must supply canonical source and
mapping-set inputs, and legacy ORM objects are rejected if they leak back into the public call.

The `0.6.0b4` slice makes the Gate Consumer executable as a framework-neutral evidence
contract. It requires explicit PASS evidence for login, organization context, FEC import,
journal, ledger, balance, financial statements, controls, closing and exports. Missing,
failed or blocked evidence keeps `consumer_e2e_green` false and therefore blocks retirement.

The `0.6.0b5` slice executes the frozen Sprint-7 Django test harness in canonical CI.
Organization context, FEC, journal, ledger/balance, financial statements and exports are
backed by real upstream pytest suites.

The `0.6.0b6` slice adds request-level login evidence externally to the frozen resource.
The runner initializes the snapshot's SQLite test settings and proves that authentication
creates a valid session when a safe explicit `next` URL is supplied. It also proves a real
consumer defect in the frozen configuration: `LOGIN_REDIRECT_URL = "dashboard"` does not
resolve because the route is namespaced as `analytics:dashboard`. Login remains BLOCKED
until the consumer fixes that redirect, alongside controls and closing.

The `0.6.0b7` slice adds the target-only controls consumer bridge. Sprint 7 has controls
persistence objects and a dashboard but no executable legacy controls service, so the bridge
does not invent one: `run_controls` must route to PyAccountingKit, dual-run is forbidden,
canonical organization/fiscal-year identity is enforced, and control-set/scope parameters are
provided through an explicit consumer factory. `controls` remains BLOCKED in Gate Consumer
until the real CFA FRA dashboard delegates through this bridge.

The `0.6.0b8` slice adds the target-only closing consumer bridge. Sprint 7 contains
`ClosingRun`/`ClosingEntryLink` persistence placeholders but no executable closing service,
so no legacy mutation path is fabricated. `close_period` must route to PyAccountingKit,
the period identity is resolved canonically, and the consumer provides control-run,
trial-balance and optional opening-balance inputs through an explicit closing parameter
factory. `closing` remains BLOCKED until the actual consumer delegates through this bridge.

The `0.6.0b9` slice implements MIG-11 on the framework side. The real Django bridge exposes
a target-only `effective_plan` operation backed by `AccountingApplication.references`;
fallback and dual-run against CFA FRA's local `FrameworkAccount` authority fail closed.
`LegacyRetirementEvidence` now requires `regulatory_authority_replaced=True`, preventing
legacy retirement until the consumer has actually stopped treating its local referential
tables as accounting authority.

The `0.6.0b10` slice defines the final MIG-12 cutover profile. `MigrationRouting.target_only()`
routes every mutation/read to PyAccountingKit with no shadow reads, and
`build_target_only_consumer_bridge(...)` constructs a consumer bridge that accepts no legacy
service dependencies. This makes the no-fallback state structural before MIG-13 deletion is
considered.

The `0.6.0b11` slice makes MIG-13 readiness executable in canonical CI. It composes the
exact Python/adapters/consumer job results with target-only routing plus explicit external
proofs for persisted legacy identities and regulatory-authority replacement. The current
decision is expected to remain BLOCKED on consumer E2E, live identity migration and live
reference-authority cutover; any silent change to that blocker set fails qualification.

The `0.6.0b12` slice freezes the retirement scope itself. A machine-readable inventory
classifies live-consumer equivalents as duplicate engine code to retire, Django endpoints to
rewire, persistence/provenance to migrate, application concerns to keep, or frozen oracle
evidence. Canonical CI validates this inventory before the MIG-13 readiness job can run.

The `0.6.0b13` slice hardens the external evidence boundary. Live identity-migration and
regulatory-authority proofs use an attestable schema: PASS requires an artifact reference,
SHA-256 digest, UTC observation timestamp and producer; BLOCKED requires a reason. MIG-13
readiness derives its booleans from these validated records, preventing a bare JSON boolean
from authorizing legacy retirement.

### L26-C — retirement

Only after parity and consumer gates are green:

- deactivate duplicate posting/reversal/FEC/reporting/control logic;
- remove obsolete legacy engine paths;
- preserve migration identity/audit evidence;
- qualify cross-lot `0.6.0rc1`, then promote `0.6.0` stable with no new behavior.

## Gates

- G4 — golden parity retained;
- G5 — migration/consumer integration;
- CFA consumer E2E;
- Python 3.11 / 3.12 / 3.13;
- Ruff / strict mypy;
- package qualification;
- Django/PostgreSQL and SQLAlchemy/PostgreSQL qualification;
- Security.

## Definition of done

- [ ] no mutation dual-write;
- [ ] CFA views/forms remain consumer concerns;
- [ ] accounting services delegate to PyAccountingKit;
- [ ] regulatory authority replaced by provider;
- [ ] read-side dual-run evidence available where useful;
- [ ] historical IDs/provenance traceable through an injectable identity store;
- [ ] consumer smoke/E2E green;
- [ ] retirement gate proves no remaining legacy route or active dual-run;
- [ ] legacy engine removed/deactivated only after parity;
- [ ] `0.6.0` stable cross-lot qualification green.


The `0.6.0b14` slice makes external evidence cryptographically consumable by MIG-13.
A syntactically valid `PASS` is no longer sufficient: its artifact must be materialized
under the configured repository-local evidence root, resolve without path traversal and
match the declared SHA-256. The cutover-evidence CI job exposes only these verified booleans
to retirement-readiness; direct manifest status can no longer authorize legacy deletion.


The `0.6.0b15` slice adds the controlled evidence-promotion path. A live artifact must
already exist beneath the configured evidence root; the promotion API derives its SHA-256
from those bytes, creates and re-verifies the PASS attestation, and removes only the matching
MIG-13 evidence blocker. The CLI is dry-run by default and requires explicit `--write` for
atomic manifest replacement, preventing handwritten digests and accidental promotion.


The `0.6.0b16` slice adds semantic contracts for the two external cutover artifacts.
`legacy_identities` must prove complete, unique CFA FRA-to-PyAccountingKit identity
traceability with zero unresolved records. `regulatory_authority` must prove target-only
routing, disabled local authority, delegated effective-plan resolution and provider-backed
sample references. SHA verification remains necessary but is no longer sufficient; canonical
verification and controlled promotion require both cryptographic and semantic validity.


The `0.6.0b17` slice adds evidence producers on top of the b16 schemas. Legacy identity
proofs are generated from an identity-store snapshot and an independent expected legacy
population count, so an incomplete migrated set cannot silently describe itself as complete.
Regulatory-authority proofs are generated only from an observed target-only state with the
PyAccountingKit provider, disabled local authority, delegated effective-plan resolution and
provider-backed samples. Generation is deterministic, dry-run by default, schema-validated
before write and does not itself promote the retirement manifest.


The `0.6.0b18` slice composes observation-to-promotion as an explicitly reviewed pipeline.
The `plan` phase generates and validates evidence in isolation, simulates promotion and
serializes the exact artifact digest, source-manifest fingerprint, blocker transition and
candidate manifest. The `apply` phase consumes only that reviewed plan and fails closed if
the retirement manifest became stale, the artifact already exists without explicit overwrite,
the digest changed or the promoted manifest differs from the plan. Canonical CI proves both
identity and regulatory transitions against isolated fixture state without promoting live
CFA FRA evidence.


The `0.6.0b19` slice turns consumer E2E into the third attestable live-cutover artifact.
The schema requires exactly one PASS for each of the ten Gate Consumer scenarios and a
canonical provenance checksum per scenario. The frozen Sprint-7 harness remains a baseline
non-regression gate, while MIG-13 now takes its `consumer_e2e_green` retirement signal from
verified live evidence. Generation, cryptographic verification, promotion and the reviewed
plan/apply pipeline all accept `consumer_e2e`; canonical live state remains BLOCKED until
real consumer evidence is supplied.


The `0.6.0b20` slice starts L26-C without performing destructive retirement. A
`LegacyRetirementPlan` is generated only when MIG-13 is explicitly READY with target-only
routing, empty blocker sets and every evidence gate green. The plan fingerprints the exact
inventory/readiness inputs and converts each inventory disposition into a deterministic,
reviewable action. Duplicate engines are marked for retirement, rewired consumer boundaries
for verification, persistence for preservation/migration, consumer-owned concerns for keeping,
and every frozen-oracle test anchor for immutable preservation. Canonical CI qualifies this
planning capability against isolated READY fixture evidence while real live CFA FRA retirement
remains blocked.

The `0.6.0b21` slice adds a fail-closed verification boundary for retirement work executed
outside PyAccountingKit in the live CFA FRA consumer repository. The verifier rebuilds the exact
retirement plan from the current inventory/readiness inputs, rejects stale or substituted plans,
requires a live consumer revision distinct from the frozen oracle tree, and requires exactly one
checksummed post-cutover observation for every planned component. Duplicate engines must be
observed `RETIRED`, consumer endpoints `REWIRED`, persistence and frozen-oracle evidence
`PRESERVED`, and consumer-owned concerns `PRESENT`. A successful verification produces a
deterministic receipt; the framework still performs no deletion or repository mutation itself.
Canonical CI proves this contract only with isolated READY evidence and synthetic observations,
so the real CFA FRA retirement remains blocked until live evidence is supplied.
\n

The `0.6.0b22` slice seals the L26-C completion contract after execution verification.
`complete_legacy_retirement(...)` revalidates target-only MIG-13 readiness, empty blocker
sets, the exact reviewed retirement plan and the full b21 execution evidence before emitting a
deterministic completion proof. The proof seals inventory/readiness fingerprints, plan SHA,
execution-receipt SHA, consumer revision and action counts, and exposes
`ready_for_0_6_rc1=true` only when every condition remains true. The canonical live CFA FRA
state still cannot produce this completion proof while the three external cutover records remain
BLOCKED; CI uses isolated READY evidence solely to qualify the completion gate.
\n

The `0.6.0b23` slice binds L26-C completion to the real `0.6.0rc1` release gate.
`qualify_release.py` now defines explicit versioned RC evidence for the complete LOT-25/26
line, including the three canonical live cutover artifacts and the reviewed retirement
plan/execution/completion chain. On `release/*`, CI rebuilds MIG-13 readiness from the current
test, Django/PostgreSQL, SQLAlchemy/PostgreSQL and verified cutover states, refuses any remaining
blocker, revalidates the committed live plan and execution evidence, regenerates the completion
proof and requires exact equality with the committed completion artifact before RC qualification.
Normal development CI may still use isolated READY fixtures to prove the mechanics, but fixture
evidence is structurally incapable of promoting `0.6.0rc1`.
\n

The `0.6.0b24` slice adds a canonical live-consumer repository identity contract. A separate
`CONSUMER_BINDING.json` remains `UNBOUND` until the actual CFA FRA consumer repository has
been explicitly identified and a concrete production revision has been supplied. A BOUND record
pins GitHub `owner/name`, canonical repository URL, default branch, exact 40-hex revision,
environment, timestamp and producer. Normal CI validates either explicit state, while
`release/*` requires BOUND and requires the bound revision to equal the revision sealed by the
L26-C retirement completion proof. This prevents evidence from one codebase from being combined
with retirement evidence from another and avoids treating AMIFOND or any other adjacent project
as the consumer by inference.

The `0.6.0b25` slice closes the provenance gap discovered after b24: repository history proves
that the Sprint-7 application was imported directly into PyAccountingKit as a historical oracle,
while no separate canonical consumer repository origin is recorded. A deterministic bootstrap
now prepares a standalone consumer seed from that immutable tree without changing it. The
bootstrap verifies the exact oracle tree SHA, copies the application to an external destination,
adds the compatible PyAccountingKit dependency, applies only the already-qualified login redirect
fix, and writes a deterministic provenance manifest. It remains explicitly
`UNBOUND_UNTIL_PUBLISHED` with cutover `NOT_STARTED`. Publication, repository binding,
target-only rewiring, live evidence generation and retirement remain external reviewed steps.

The `0.6.0b26` slice makes publication itself attestable before canonical binding. The
publication handoff inspects the standalone consumer as an independent Git repository, requires a
clean top-level checkout on the reviewed default branch, normalizes and matches the GitHub origin,
pins the exact HEAD SHA, and revalidates `PYACCOUNTINGKIT_CONSUMER_BOOTSTRAP.json` against the
frozen Sprint-7 oracle and current bootstrap plan. A side-effect-free `plan` seals the current
UNBOUND binding fingerprint, verified publication payload and candidate BOUND state; `apply`
rechecks all three and fails closed on any repository or canonical-state drift. Binding schema v2
requires both `bootstrap_sha256` and `publication_sha256`, so repository identity can no longer
be separated from the provenance of the standalone seed that was actually published.

The `0.6.0b27` slice closes the lifecycle gap after initial publication. A live consumer cannot
remain pinned forever to its first published SHA because target-only rewiring, live evidence and
L26-C retirement necessarily create later commits, while the RC gate requires the canonical
binding revision to equal the revision sealed by retirement completion. Binding advancement is
therefore explicit and monotonic: the current BOUND revision must be an ancestor of the newly
observed clean HEAD, while repository identity, canonical GitHub URL, default branch, environment
and bootstrap provenance remain unchanged. Advancement uses its own reviewed plan/apply workflow
and fails closed on rollback, divergent history, no-op rebinding, repository substitution,
provenance drift or any consumer/binding change after review.

