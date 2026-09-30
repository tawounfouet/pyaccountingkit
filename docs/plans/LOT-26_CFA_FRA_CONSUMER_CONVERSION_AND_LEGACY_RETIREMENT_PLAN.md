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
- legacy identity map;
- framework-neutral consumer contract tests.

### L26-B — consumer delegation

- convert CFA FRA accounting services service-by-service;
- keep views/forms/permissions/HTMX in CFA FRA;
- switch regulatory lookup to provider-backed public references;
- add consumer E2E/smoke evidence.

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
- [ ] historical IDs/provenance traceable;
- [ ] consumer smoke/E2E green;
- [ ] legacy engine removed/deactivated only after parity;
- [ ] `0.6.0` stable cross-lot qualification green.
