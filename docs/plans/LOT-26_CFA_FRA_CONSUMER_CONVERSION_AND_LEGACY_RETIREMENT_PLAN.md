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
