# PyAccountingKit - Implementation Roadmap

> **Projet** : PyAccountingKit  
> **Document** : `PYACCOUNTINGKIT_IMPLEMENTATION_ROADMAP.md`  
> **Statut** : Roadmap d'implémentation de référence  
> **Langue** : Français  
> **Baseline architecturale** : documents `00` à `23` + registre de **785 ADR**  
> **Objet** : Transformer la documentation d'architecture PyAccountingKit en plan d'exécution concret : lots, versions, dépendances, Definition of Done et gates de qualité/release.

---

# 1. Résumé exécutif

La phase d'architecture est suffisamment complète pour basculer vers l'implémentation.

La stratégie proposée est :

```text
Architecture 00..23
      |
      v
Repository Bootstrap
      |
      v
Accounting Core
      |
      v
References / Policies / Company Chart
      |
      v
Imports / FEC / Reporting
      |
      v
Subledgers / Financial Analysis
      |
      v
Public API / Production Adapters
      |
      v
CFA FRA Migration / Regulatory Qualification
      |
      v
Reliability / API Freeze
      |
      v
PyAccountingKit 1.0.0
      |
      +--> 1.1 Reconciliation
      |
      +--> 1.2 Consolidation
```

Le P2.3 `Advanced Financial Analysis Boundaries` ne déclenche pas de moteur Corporate Finance dans PyAccountingKit.

```text
NPV / IRR / WACC / DCF / Valuation / Monte Carlo
    remain outside PyAccountingKit core
```

La roadmap comporte **39 lots `LOT-00` à `LOT-38`**.

> [!TIP]
> **Découpage opérationnel** : La présente feuille de route est traduite en **10 plans d'implémentation opérationnels** dans le dossier [`docs/plans/`](./plans/README.md) (`PLAN-00` à `PLAN-09`), chacun détaillant les chantiers techniques, les critères d'acceptation stricts (DoD), la matrice des gates et les scénarios de recette par release.

---

# 2. Principes de pilotage

## 2.1 Milestone-driven

Les releases ne sont pas pilotées par une date arbitraire.

Une version est publiée lorsque :

```text
scope complete
+
Definition of Done satisfied
+
required gates green
```

---

## 2.2 Les versions ne remplacent pas les lots

```text
Lot
    =
unité d'implémentation

Version
    =
milestone publiable regroupant plusieurs lots
```

---

## 2.3 Une release stable n'est jamais un simple tag

Une release stable exige :

```text
qualification
compatibility
replay
migration
package validation
release evidence
```

---

## 2.4 Core-first

Le coeur comptable est construit avant les couches :

```text
reporting
analysis
subledgers avancés
reconciliation
consolidation
```

---

## 2.5 InMemory-first, production adapters ensuite

Séquence :

```text
Domain
    ↓
Ports
    ↓
InMemory reference adapter
    ↓
Django/PostgreSQL
    ↓
SQLAlchemy/PostgreSQL
```

L'InMemory adapter sert de référence comportementale rapide.

Il ne qualifie pas la production.

---

## 2.6 Golden-by-design

Les golden scenarios CFA FRA commencent dès la baseline.

Ils ne doivent pas être ajoutés seulement à la fin.

---

## 2.7 No big-bang CFA FRA migration

Pattern :

```text
Strangler
```

et jamais :

```text
dual-write accounting mutations
```

---

# 3. Release train global

| Release | Nom | Lots principaux | Statut cible |
|---|---|---|---|
| `0.0.1` | Repository Bootstrap | `LOT-00` | bootstrap |
| `0.1.0` | Accounting Core Foundation | `LOT-01..09` | stable development milestone |
| `0.2.0` | References, Charts & Policies | `LOT-10..13` | stable |
| `0.3.0` | Imports & Reporting | `LOT-14..17` | stable |
| `0.4.0` | Subledgers & Financial Analysis | `LOT-18..20` | stable |
| `0.5.0` | Public API & Production Adapters | `LOT-21..24` | stable |
| `0.6.0` | CFA FRA Migration & Golden Parity | `LOT-25..26` | stable |
| `0.7.0` | Regulatory Production Qualification | `LOT-27` | stable |
| `0.8.0` | Reliability, Performance & Supply Chain | `LOT-28` | stable |
| `0.9.0` | API Freeze & 1.0 Qualification Baseline | `LOT-29` | freeze |
| `1.0.0` | Stable Public Core | `LOT-30` | production stable |
| `1.1.0` | Generic Reconciliation | `LOT-31..33` | post-1.0 extension |
| `1.2.0` | Consolidation | `LOT-34..37` | post-1.0 extension |
| non réservé | Corporate Finance Boundary Guards | `LOT-38` | architecture-only / optional bridge |

---

# 4. Pré-releases recommandées

La convention suit PEP 440 :

```text
aN
bN
rcN
stable
```

Exemple par release :

```text
0.3.0a1
0.3.0a2
0.3.0b1
0.3.0b2
0.3.0rc1
0.3.0
```

Les sous-jalons exacts peuvent évoluer.

La portée stable de la release ne change pas sans mise à jour de cette roadmap.

---

# 5. Vue des dépendances majeures

```text
LOT-00
   |
   v
LOT-01
   |
   +--> LOT-02 --> LOT-03 --> LOT-04
   |                           |
   |                           v
   +-----------------------> LOT-05
                               |
                               v
                            LOT-06
                           /      \
                          v        v
                      LOT-07     LOT-08
                          \        /
                           v      v
                            LOT-09
                               |
              +----------------+----------------+
              |                                 |
              v                                 v
           LOT-10                             LOT-14
              |                                 |
              v                                 v
           LOT-11                             LOT-15
              |
              v
           LOT-12
              |
              v
           LOT-13

LOT-07 + LOT-11 + LOT-08
        |
        v
      LOT-16
        |
        v
      LOT-17

LOT-03 + LOT-06 + LOT-08
        |
        v
      LOT-18
        |
        v
      LOT-19

LOT-07 + LOT-16 + LOT-08
        |
        v
      LOT-20

LOT-10..20
        |
        v
      LOT-21
        |
        v
      LOT-22
       /   \
      v     v
  LOT-23  LOT-24
      \     /
       v   v
      LOT-25
        |
        v
      LOT-26
        |
        v
      LOT-27
        |
        v
      LOT-28
        |
        v
      LOT-29
        |
        v
      LOT-30

POST-1.0

LOT-30
   |
   +--> LOT-31 --> LOT-32 --> LOT-33
   |
   +---------------------------> LOT-34
                                  |
                                  v
                               LOT-35
                                  |
                         LOT-33 -> LOT-36
                                  |
                                  v
                               LOT-37
```

---

# 6. Gate model

La stratégie de release existante définit :

```text
G0 Local
G1 PR
G2 Main
G3 Nightly
G4 RC
G5 Stable
```

Cette roadmap conserve ces gates.

---

# 7. G0 - Local Gate

Objectif :

```text
feedback développeur immédiat
```

Minimum :

```text
format
lint
type-check impacted modules
unit tests impacted modules
architecture import checks
```

Bloquant avant commit recommandé.

---

# 8. G1 - Pull Request Gate

Obligatoire pour merge :

```text
G0
+
full unit tests impacted domains
+
property tests impacted invariants
+
contract tests impacted ports
+
documentation/API examples
+
ADR impact check
+
migration review if schema changed
```

---

# 9. G2 - Main Gate

Après merge :

```text
full unit suite

full property suite

all adapter-neutral contract tests

InMemory integration

package build smoke

public import smoke

architecture dependency gates
```

---

# 10. G3 - Nightly Gate

Ajoute :

```text
real PostgreSQL

Django integration

SQLAlchemy integration

concurrency race suite

golden CFA FRA

regulatory golden fixtures

replay tests

migration tests

performance regression smoke
```

---

# 11. G4 - Release Candidate Gate

Doit inclure :

```text
full test matrix

real PostgreSQL

Django qualification

SQLAlchemy qualification

concurrency suite

migration suite

golden suite

replay suite

public API diff

adapter contract diff

snapshot schema diff

error-code diff

package build

wheel install

sdist install

clean environment

docs build

release qualification manifest
```

---

# 12. G5 - Stable Gate

Exige :

```text
G4 green

0 BLOCKER

0 CRITICAL

no critical flaky tests

release notes complete

migration guide complete where applicable

public API manifest frozen

compatibility matrix published

regulatory matrix published when relevant

artifact checksums generated

tag immutable

publication smoke green
```

---

# 13. Gates spécialisés

En complément de `G0..G5`.

## `GA` - Architecture Gate

```text
adapters -> application -> domain

domain imports no Django

domain imports no SQLAlchemy

domain imports no FastAPI

no forbidden cross-bounded-context dependency
```

---

## `GC` - Accounting Correctness Gate

```text
double-entry

Money Decimal

posted immutability

reversal semantics

period rules

no bypass posting

multi-entity isolation
```

---

## `GP` - Persistence/Concurrency Gate

```text
UoW atomicity

rollback

optimistic conflict

pessimistic lock capability

idempotency

unique constraints

outbox atomicity

critical race tests
```

---

## `GR` - Regulatory Gate

```text
reference IDs preserved

snapshot checksum

negative constraints preserved

candidate != executable

human-review flags preserved

no code-equality semantic inference
```

---

## `GI` - Import/FEC Gate

```text
raw source preservation

checksum

parser contract

balance

idempotence

rollback

no silent row drop

lineage
```

---

## `GS` - Snapshot/Replay Gate

```text
inputs pinned

definitions pinned

policies pinned

output checksum

replay deterministic
```

---

## `GAPI` - Public API Gate

```text
public import smoke

typed public surface

public errors translated

manifest diff

no ORM leakage

optional dependencies isolated
```

---

## `GM` - Migration Gate

```text
fresh install

upgrade from previous stable

data backfill

rollback/no-downgrade status

post-migration controls

snapshot preservation
```

---

## `GSEC` - Security/Supply Chain Gate

```text
dependency audit

secret scan

package integrity

wheel/sdist validation

SBOM/provenance where enabled

no sensitive payload logs
```

---

# 14. Definition of Done - Global Lot DoD

Un lot n'est `DONE` que lorsque tous les éléments applicables sont satisfaits.

```text
[ ] scope du lot explicitement fermé

[ ] architecture/ADR mapping identifié

[ ] code placé dans le bon bounded context

[ ] domain free of framework-specific imports

[ ] public/internal boundary respectée

[ ] type hints complets sur la surface exposée

[ ] Money uses Decimal

[ ] Clock utilisé pour le temps métier

[ ] multi-entity scoping testé si applicable

[ ] unit tests green

[ ] property tests green pour invariants applicables

[ ] contract tests green pour ports applicables

[ ] integration tests green pour adapters applicables

[ ] concurrency tests green si mutation critique

[ ] golden tests green si comportement CFA/regulatory impliqué

[ ] replay tests green si snapshot/policy/version concerné

[ ] documentation technique mise à jour

[ ] examples/samples exécutables

[ ] public error codes documentés si ajoutés

[ ] migration incluse/testée si schema modifié

[ ] changelog/release note fragment ajouté si user-visible

[ ] aucun BLOCKER / CRITICAL ouvert sur le lot

[ ] gate minimal du lot green
```

---

# 15. Definition of Done - Mutation comptable

Pour toute feature qui écrit une donnée comptable :

```text
[ ] transaction boundary explicit

[ ] idempotency semantics defined

[ ] concurrency behavior defined

[ ] audit event emitted/persisted as designed

[ ] rollback leaves no partial accounting

[ ] no posted mutation path

[ ] correction/reversal path tested

[ ] period race tested

[ ] entity isolation tested
```

---

# 16. Definition of Done - Snapshot

```text
[ ] immutable after publication

[ ] source refs pinned

[ ] policy/definition versions pinned

[ ] checksum present

[ ] freshness/staleness semantics implemented

[ ] replay tested

[ ] supersession preserves history

[ ] drill-down/provenance available
```

---

# 17. Definition of Done - Adapter Production

Un adapter ne peut être déclaré `PRODUCTION` que si :

```text
[ ] contract suite green

[ ] integration suite green

[ ] real backend qualification green

[ ] concurrency suite green

[ ] migration suite green

[ ] rollback semantics green

[ ] performance smoke green

[ ] clean install with extra green

[ ] optional dependency failure is explicit

[ ] adapter contract version declared
```

---

# 18. Definition of Done - Regulatory Capability

```text
[ ] dataset/source identity pinned

[ ] artifact checksum verified

[ ] structure contract validated

[ ] provenance retained

[ ] negative constraints retained

[ ] human-review flags retained

[ ] candidate mappings cannot execute silently

[ ] capability status explicit

[ ] golden fixture green

[ ] REGULATORY_COMPATIBILITY_MATRIX updated
```

---

# 19. Definition of Done - Import Adapter

```text
[ ] SourceArtifact preserved

[ ] raw records preserved

[ ] source checksum preserved

[ ] normalized records traceable

[ ] mapping explicit

[ ] validation report complete

[ ] import plan deterministic/checksummed

[ ] stale plan rejected

[ ] idempotency green

[ ] rollback green

[ ] duplicate policy explicit

[ ] no silent coercion/drop

[ ] reconciliation totals green
```

---

# 20. Definition of Done - Stable Release

```text
[ ] all included lots DONE

[ ] G5 green

[ ] release checklist complete

[ ] no BLOCKER/CRITICAL

[ ] compatibility matrix published

[ ] qualification manifest generated

[ ] package artifacts checksummed

[ ] wheel + sdist install green

[ ] docs correspond to released API

[ ] migration path documented

[ ] public tag created once and immutable
```

---

# 21. LOT-00 - Repository Bootstrap & Architecture Safety Net

**Target** : `0.0.1`

## Scope

```text
repository

src layout

pyproject.toml

package metadata

README

license

tests structure

docs structure

CI

lint

format

typing

py.typed

dependency boundary tests

basic release workflow

CFA FRA baseline capture hooks
```

## Target structure

```text
pyaccountingkit/
├── src/pyaccountingkit/
│   ├── core/
│   ├── domain/
│   ├── application/
│   ├── ports/
│   ├── adapters/
│   ├── integrations/
│   └── public/
├── tests/
│   ├── unit/
│   ├── property/
│   ├── contract/
│   ├── integration/
│   ├── concurrency/
│   └── golden/
├── examples/
├── docs/
└── pyproject.toml
```

## Dependencies

```text
none
```

## Required gates

```text
G0
G1
G2
GA
```

## DoD spécifique

```text
[ ] pip install -e . works

[ ] import pyaccountingkit works

[ ] no mandatory Django/SQLAlchemy dependency

[ ] architecture import test green

[ ] CI green on clean repository

[ ] wheel builds

[ ] baseline CFA FRA scenario inventory started
```

---

# 22. LOT-01 - Core Primitives

**Target line** : `0.1.0a1`

## Scope

```text
Money

CurrencyCode

typed IDs

AccountingDate helpers

Clock

IdFactory

Revision

IdempotencyKey

base errors

ObjectRef

Result metadata primitives
```

## Dependencies

```text
LOT-00
```

## Required gates

```text
G0 G1 G2
GA GC
```

## DoD spécifique

```text
[ ] Money rejects float

[ ] Decimal arithmetic deterministic

[ ] Clock injectable

[ ] IDs distinct from business codes

[ ] serialization primitives tested
```

---

# 23. LOT-02 - Entity, Fiscal Year, Periods & Journals

**Target line** : `0.1.0a1`

## Scope

```text
AccountingEntity

FiscalYear

AccountingPeriod

period status

Journal

journal activation

entity scoping
```

## Dependencies

```text
LOT-01
```

## Gates

```text
GA GC
```

## DoD

```text
[ ] periods resolve deterministically

[ ] closed-period invariant representable

[ ] every accounting object carries entity scope

[ ] journal active/inactive semantics tested
```

---

# 24. LOT-03 - Company Chart Base

**Target line** : `0.1.0a2`

## Scope

```text
CompanyChartOfAccounts

CompanyAccount

AccountCode

active/inactive

parent hierarchy

AccountRole basics
```

## Dependencies

```text
LOT-01
LOT-02
```

## Gates

```text
GA GC
```

## DoD

```text
[ ] CompanyAccount.code is string

[ ] no universal numeric-length assumption

[ ] no reference prefix semantics hardcoded

[ ] account uniqueness domain rule defined
```

---

# 25. LOT-04 - JournalEntry Aggregate & Accounting Invariants

**Target line** : `0.1.0a2`

## Scope

```text
JournalEntry

JournalEntryLine

DRAFT

VALIDATED

POSTED

REVERSED

double-entry

line invariants

minimum lines

Money semantics
```

## Dependencies

```text
LOT-01
LOT-02
LOT-03
```

## Gates

```text
GA GC
```

## DoD

```text
[ ] JournalEntry is Aggregate Root

[ ] JournalLine cannot mutate accounting independently

[ ] SUM debit == SUM credit invariant

[ ] debit/credit mutually exclusive

[ ] posted mutation rejected

[ ] property suite green
```

---

# 26. LOT-05 - Persistence Ports & InMemory Reference Adapter

**Target line** : `0.1.0b1`

## Scope

```text
Repository ports

UnitOfWork

UnitOfWorkFactory

PersistenceCapabilities

QueryConsistency

InMemory repositories

rollback

revision conflicts

IdempotencyStore foundation

Outbox foundation
```

## Dependencies

```text
LOT-01
LOT-04
```

## Gates

```text
GA GP
```

## DoD

```text
[ ] repositories expose domain objects only

[ ] rollback tested

[ ] revision conflict tested

[ ] unique constraints behavior emulated

[ ] same UoW contract reusable by DB adapters
```

---

# 27. LOT-06 - Posting & Reversal

**Target line** : `0.1.0b1`

## Scope

```text
ValidateEntry

PostEntry

ReverseEntry

posting sequence port

atomic mutation

idempotence

audit hooks

outbox hooks
```

## Dependencies

```text
LOT-02
LOT-04
LOT-05
```

## Gates

```text
GA GC GP
```

## DoD

```text
[ ] no DRAFT -> POSTED shortcut in normal path

[ ] posting validates account/journal/period

[ ] exactly one posting under duplicate requests

[ ] reversal creates a new inverse entry

[ ] original remains immutable

[ ] transaction rollback leaves no partial state
```

---

# 28. LOT-07 - Journal, General Ledger & Trial Balance

**Target line** : `0.1.0b2`

## Scope

```text
JournalQuery

GeneralLedgerQuery

running balance

opening balances

TrialBalance

TrialBalanceSnapshot

BEFORE_ADJUSTMENTS

ADJUSTED

POST_CLOSING

drill-down
```

## Dependencies

```text
LOT-04
LOT-05
LOT-06
```

## Gates

```text
GA GC GS
```

## DoD

```text
[ ] only posted accounting contributes

[ ] deterministic ordering

[ ] TB debit == credit

[ ] signed balance convention explicit

[ ] snapshot checksum deterministic

[ ] drill-down to JournalEntryLine
```

---

# 29. LOT-08 - Controls, Audit, Provenance & Traceability

**Target line** : `0.1.0b2`

## Scope

```text
ControlDefinition

ControlRun

ControlResult

ControlGate

AuditEvent

ActorContext

ProvenanceRef

Evidence

LineageEdge

TraceContext

CanonicalHasher

ReproducibilityEnvelope foundation
```

## Dependencies

```text
LOT-01
LOT-05
LOT-06
LOT-07
```

## Gates

```text
GA GC GP GS
```

## DoD

```text
[ ] controls versioned

[ ] audit append-oriented

[ ] provenance distinct from audit

[ ] lineage queryable

[ ] failed control history immutable

[ ] canonical checksum stable
```

---

# 30. LOT-09 - Closing, Adjustments & Opening

**Target line** : `0.1.0rc1 -> 0.1.0`

## Scope

```text
ClosingRun

OPEN -> REVIEW -> CLOSING -> CLOSED

close gate

AdjustmentProposal

cut-off foundations

closing entries

temporary accounts policy

reopen

opening balances

ClosingEvidenceBundle
```

## Dependencies

```text
LOT-02
LOT-05
LOT-06
LOT-07
LOT-08
```

## Gates

```text
G3
G4 for rc
G5 for 0.1.0
GA GC GP GS
```

## DoD

```text
[ ] close vs posting race tested

[ ] blocking controls prevent close

[ ] reopen preserves previous evidence

[ ] adjustment does not mutate posted source

[ ] opening generation traceable

[ ] 0.1 core scenario passes end-to-end
```

---

# 31. Release 0.1.0 - Accounting Core Foundation

## Included lots

```text
LOT-01..LOT-09
```

## Required scenario

```text
create entity
create period
create company accounts
create journal
create balanced entry
validate
post
read journal
read general ledger
build trial balance
reverse entry
run controls
close period
reject posting after close
```

## Stable gate

```text
G5
```

---

# 32. LOT-10 - Accounting Reference Provider & Snapshots

**Target line** : `0.2.0a1`

## Scope

```text
ReferenceStandard

ReferenceNode

ReferenceHierarchy

AccountingReferenceProvider

LocalFilesystem adapter

Package adapter

InMemory adapter

ReferenceSnapshot

checksums

capabilities

negative constraints
```

## Dependencies

```text
LOT-01
LOT-05
LOT-08
```

## Gates

```text
GA GR GS
```

## DoD

```text
[ ] regulatory IDs preserved exactly

[ ] hierarchy consumed from explicit dataset fields

[ ] negative constraints first-class

[ ] provider paths absent from domain

[ ] snapshot replayable
```

---

# 33. LOT-11 - Company Chart Numbering, Generation & Regulatory Binding

**Target line** : `0.2.0a1`

## Scope

```text
AccountCodePolicy

NumericFixedLength

NumericVariableLength

SegmentedNumeric

Alphanumeric

Custom

REFERENCE_ONLY

PAD_TO_LENGTH

TEMPLATE_EXPANSION

RegulatoryAccountBinding

chart versions

chart migration plan
```

## Dependencies

```text
LOT-03
LOT-10
```

## Gates

```text
GA GR
```

## DoD

```text
[ ] PCG 512 can map to multiple company code formats

[ ] company code != regulatory ID

[ ] no universal prefix inference

[ ] mapping candidates separated from active binding

[ ] migration preserves historical chart versions
```

---

# 34. LOT-12 - Policy Set, Resolution & Recognition

**Target line** : `0.2.0b1`

## Scope

```text
AccountingPolicySet

PolicyBinding

PolicyApplicability

PolicyResolutionService

RecognitionPolicy

RecognitionDecision

ambiguity fail-closed

policy trace
```

## Dependencies

```text
LOT-01
LOT-08
LOT-10
LOT-11
```

## Gates

```text
GA GC GR GS
```

## DoD

```text
[ ] recognition separate from measurement

[ ] policy ambiguity explicit

[ ] policy version pinned

[ ] reference data not treated as policy

[ ] historical policy remains replayable
```

---

# 35. LOT-13 - Measurement Policies & JournalEntryProposal

**Target line** : `0.2.0b1 -> 0.2.0`

## Scope

```text
MeasurementPolicy

MeasurementBasis

ValuationProvider

depreciation policy foundation

impairment policy foundation

inventory measurement foundation

accrual/provision proposal

JournalEntryProposal
```

## Dependencies

```text
LOT-12
LOT-06
LOT-08
```

## Gates

```text
G4/G5
GA GC GS
```

## DoD

```text
[ ] measurement never posts directly

[ ] proposal goes through normal posting

[ ] Decimal preserved

[ ] external valuation input traceable

[ ] policy snapshot pinned
```

---

# 36. Release 0.2.0 - References, Charts & Policies

```text
LOT-10..LOT-13
```

Stable requires:

```text
GR green

Reference provider contract green

PCG/SYSCOHADA/Non-Profit safety fixtures green where advertised

policy replay green

chart migration green
```

---

# 37. LOT-14 - Generic Accounting Import Engine

**Target line** : `0.3.0a1`

## Scope

```text
SourceArtifact

AccountingImportBatch

RawImportRecord

NormalizedImportRecord

ImportIssue

SourceEntryKey

mapping layers

ImportPlan

dry-run

plan checksum

execution modes

checkpoints

reprocessing
```

## Dependencies

```text
LOT-05
LOT-06
LOT-08
LOT-09
LOT-11
```

## Gates

```text
GA GI GP GS
```

## DoD

```text
[ ] import core is source-format neutral

[ ] no adapter-specific field in generic domain

[ ] raw preservation

[ ] deterministic plan

[ ] stale plan rejection

[ ] no bypass posting invariants
```

---

# 38. LOT-15 - FEC Adapter

**Target line** : `0.3.0a2`

## Scope

```text
FEC parser

FEC source schema

CompAuxNum / CompAuxLib preservation

EcritureLet / DateLet preservation

FEC validation controls

grouping strategy

duplicate candidate warning

TRUSTED_POSTED_HISTORY_IMPORT

reconciliation report
```

## Dependencies

```text
LOT-14
LOT-06
LOT-08
LOT-11
```

## Gates

```text
GI GC GP GS
```

## DoD

```text
[ ] raw FEC lines traceable

[ ] same file idempotent

[ ] no auto-delete duplicate

[ ] no automatic CompteNum + CompAuxNum concatenation

[ ] import failure rolls back chosen transaction scope

[ ] debit/credit totals reconciled
```

---

# 39. LOT-16 - Financial Statements Engine

**Target line** : `0.3.0b1`

## Scope

```text
FinancialStatementDefinition

StatementLineDefinition

formula DSL

dependency graph

StatementAccountMapping

StatementMappingSet

FinancialStatementEngine

Balance Sheet

Income Statement

Cash Flow

ReportSnapshot

drill-down

comparatives
```

## Dependencies

```text
LOT-07
LOT-08
LOT-11
```

## Gates

```text
GA GC GS
```

## DoD

```text
[ ] reports are projections

[ ] formula cycle rejected

[ ] candidate mapping != active mapping

[ ] balance-sheet control

[ ] cash-flow reconciliation

[ ] report snapshot immutable after publication

[ ] drill-down to TB/ledger
```

---

# 40. LOT-17 - Regulatory Reporting

**Target line** : `0.3.0b2 -> 0.3.0`

## Scope

```text
RegulatoryReportingProfile

ReferenceReportingModel adapter

RegulatoryExportDefinition

RegulatoryExportArtifact

ReportEvidenceBundle

reference upgrade plan

official structure vs candidate hints

renderer/exporter separation
```

## Dependencies

```text
LOT-10
LOT-11
LOT-16
LOT-08
```

## Gates

```text
G4/G5
GR GS GAPI
```

## DoD

```text
[ ] reporting profile pins reference snapshot

[ ] account_hints_executable=false enforced

[ ] human_validation_required preserved

[ ] exporter does not recalculate accounting

[ ] export checksum/evidence present
```

---

# 41. Release 0.3.0 - Imports & Reporting

Stable gate additionally requires:

```text
FEC contract/golden/rollback/idempotency/concurrency green

statement golden suite green

regulatory mapping safety green

report replay green
```

---

# 42. LOT-18 - Subledger Foundations

**Target line** : `0.4.0a1`

## Scope

```text
Subledger

SubledgerDefinition

SubledgerParty

PartyRef

AuxiliaryReference

Receivable

Payable

DueItem

OpenItem

ControlAccountBinding

AuxiliaryAccountingPolicy

SUBLEDGER

EXTENDED_ACCOUNT_CODE

HYBRID
```

## Dependencies

```text
LOT-03
LOT-05
LOT-06
LOT-08
```

## Gates

```text
GA GC GP
```

## DoD

```text
[ ] subledger != GL

[ ] open item != JournalEntryLine

[ ] operational state distinct from accounting state

[ ] accounting-effective item linked to posted accounting

[ ] control account resolved explicitly
```

---

# 43. LOT-19 - Settlements, Allocations, Matching & Aging

**Target line** : `0.4.0a2`

## Scope

```text
Settlement

SettlementAllocation

partial/full settlement

many-to-many allocation

matching candidates

validated matching

PaymentTerm

DueDateRule

AgingPolicy

AgingSnapshot

SubledgerReconciliation
```

## Dependencies

```text
LOT-18
LOT-06
LOT-07
LOT-08
```

## Gates

```text
GC GP GS
```

## DoD

```text
[ ] no over-allocation

[ ] settlement reversal traceable

[ ] write-off requires accounting proposal/policy

[ ] aging basis explicit

[ ] buckets partition eligible items

[ ] subledger/control account reconciliation green
```

---

# 44. LOT-20 - Financial Analysis

**Target line** : `0.4.0b1 -> 0.4.0`

## Scope

```text
FinancialIndicatorDefinition

FinancialRatioDefinition

AnalysisDefinitionSet

FinancialAnalysisEngine

SIG

EBE

EBITDA

CAF

FRNG

BFRE

BFRHE

BFR

Net Treasury

historical ratios

trends

diagnostics

AnalysisSnapshot

CalculationTrace
```

## Dependencies

```text
LOT-07
LOT-08
LOT-16
LOT-10
optional LOT-18/19 for subledger analytics
```

## Gates

```text
G4/G5
GA GS
```

## DoD

```text
[ ] analysis is read-only

[ ] undefined denominator != zero

[ ] missing required input => INDETERMINATE

[ ] EBE != EBITDA

[ ] definitions versioned

[ ] AnalysisSnapshot immutable

[ ] no NPV/IRR/WACC/DCF in core
```

---

# 45. Release 0.4.0 - Subledgers & Financial Analysis

Stable gate additionally requires:

```text
settlement allocation property suite

subledger/GL reconciliation golden

analysis golden

trend/replay green

Corporate Finance boundary architecture guard
```

---

# 46. LOT-21 - Public API Facade

**Target line** : `0.5.0a1`

## Scope

```text
AccountingApplication

references

charts

entries

ledger

closing

controls

imports

statements

reporting

analysis

subledgers

public DTOs

public errors

Page

CommandContext
```

## Dependencies

```text
LOT-10..20
```

## Gates

```text
GA GAPI
```

## DoD

```text
[ ] no ORM objects returned

[ ] commands explicit

[ ] queries framework-neutral

[ ] public DTOs immutable by default

[ ] error codes machine-readable

[ ] core-only import succeeds
```

---

# 47. LOT-22 - Extension API, Manifests & Compatibility Contracts

**Target line** : `0.5.0a2`

## Scope

```text
public protocols

UnitOfWorkFactory public extension contract

AccountingReferenceProvider public contract

renderer/exporter contracts

adapter contract version

PUBLIC_API_MANIFEST

PUBLIC_ERROR_CODES

ADAPTER_CONTRACT_MANIFEST

runtime capabilities

py.typed
```

## Dependencies

```text
LOT-21
LOT-05
LOT-10
LOT-14
LOT-16
```

## Gates

```text
GAPI GA
```

## DoD

```text
[ ] extension API separate from user API

[ ] public symbol list explicit

[ ] manifest generation deterministic

[ ] optional extras don't affect core import

[ ] adapter mismatch produces typed error
```

---

# 48. LOT-23 - Django/PostgreSQL Adapter

**Target line** : `0.5.0b1`

## Scope

```text
Django models

mappers

repositories

DjangoUnitOfWork

query adapters

migrations

transaction.atomic

select_for_update

revision updates

PostgreSQL indexes
```

## Dependencies

```text
LOT-05..22
```

## Gates

```text
GP G3 G4
```

## DoD

```text
[ ] repository contract green

[ ] UoW contract green

[ ] real PostgreSQL

[ ] posting vs close race green

[ ] double reversal race green

[ ] migration fresh/upgrade green

[ ] adapter extra clean install green
```

---

# 49. LOT-24 - SQLAlchemy/PostgreSQL Adapter

**Target line** : `0.5.0b2 -> 0.5.0`

## Scope

```text
SQLAlchemy tables

mappers

repositories

SessionUnitOfWork

query adapters

Alembic migrations

with_for_update

optimistic revisions
```

## Dependencies

```text
LOT-05..22
```

## Gates

```text
GP G4 G5
```

## DoD

```text
[ ] same semantic contract as InMemory/Django

[ ] real PostgreSQL

[ ] concurrency suite green

[ ] migration suite green

[ ] no ORM leak in public API
```

---

# 50. Release 0.5.0 - Public API & Production Adapters

Stable requires:

```text
public API manifest published

error-code manifest published

adapter contract manifest published

Django/PostgreSQL qualified

SQLAlchemy/PostgreSQL qualified or explicitly scoped

core-only + extras install green
```

---

# 51. LOT-25 - CFA FRA Golden Baseline & Parity Qualification

**Target line** : `0.6.0a1`

## Scope

```text
CFA FRA component inventory

golden scenario inventory

behavioral baseline

normalized golden fixtures

posting parity

reversal parity

FEC parity

ledger parity

statement parity

closing parity
```

## Important

La capture des golden scenarios commence dès `LOT-00`.

`LOT-25` est la **qualification consolidée**, pas le premier contact avec CFA FRA.

## Dependencies

```text
LOT-06
LOT-07
LOT-09
LOT-15
LOT-16
LOT-20
LOT-23
```

## Gates

```text
GC GI GS
CFA golden suite
```

## DoD

```text
[ ] golden fixtures independent of CFA runtime

[ ] every intentional divergence classified

[ ] baseline evidence checksummed

[ ] accounting parity green

[ ] FEC parity green

[ ] ledger/reporting parity green
```

---

# 52. LOT-26 - CFA FRA Consumer Conversion & Legacy Engine Retirement

**Target line** : `0.6.0b1 -> 0.6.0`

## Scope

```text
CFAFRACompatibilityAdapter

service-by-service strangler

public API delegation

Django consumer integration

read-side dual-run where useful

mutation feature switch

legacy engine retirement
```

## Dependencies

```text
LOT-21
LOT-23
LOT-25
```

## Gates

```text
G4 G5
CFA consumer E2E
```

## DoD

```text
[ ] no mutation dual-write

[ ] CFA views/forms remain consumer concerns

[ ] accounting services delegate to PyAccountingKit

[ ] regulatory authority replaced by provider

[ ] legacy engine removed only after parity

[ ] historical IDs/provenance traceable
```

---

# 53. LOT-27 - Regulatory Capability Production Qualification

**Target line** : `0.7.0`

## Scope

```text
ReferenceCapabilitySet

RegulatoryFrameworkIntegrationProfile

qualification records

REGULATORY_COMPATIBILITY_MATRIX

PCG qualification

Non-Profit effective plan qualification

SYSCOHADA qualification

OHADA relation/negative constraints

EBNL/SYSCOHADA crosswalk safety

PCEMF relation safety

neutral concepts safety
```

## Dependencies

```text
LOT-10
LOT-11
LOT-17
LOT-22
LOT-23
LOT-24
```

## Gates

```text
GR G4 G5
```

## DoD

```text
[ ] qualification is per capability

[ ] no unsupported standard capability fabricated

[ ] non-profit hints remain non-executable

[ ] OHADA inheritance constraints green

[ ] concepts with missing bindings remain unresolved

[ ] compatibility matrix included in release
```

---

# 54. LOT-28 - Reliability, Performance, Security & Supply Chain

**Target line** : `0.8.0`

## Scope

```text
performance baselines

large FEC qualification

ledger query performance

high-volume subledger read paths

structured logging

metrics

tracing hooks

security scan

dependency audit

package provenance

wheel/sdist qualification

SBOM if adopted

fault injection / rollback qualification
```

## Dependencies

```text
LOT-01..27
```

## Gates

```text
G3 G4 G5
GSEC GP
```

## DoD

```text
[ ] critical paths benchmarked

[ ] no O(N²) obvious hot path on primary use cases

[ ] no sensitive accounting payload in default logs

[ ] dependency audit green

[ ] clean build reproducible enough for release qualification

[ ] rollback/failure scenarios green
```

---

# 55. LOT-29 - API Freeze, Migration & Replay Hardening

**Target line** : `0.9.0`

## Scope

```text
public API freeze

adapter contract freeze candidate

error-code freeze

snapshot schema compatibility

migration from prior stable lines

historical replay matrix

deprecations

docs freeze

1.0 compatibility matrix

release manifests
```

## Dependencies

```text
LOT-01..28
```

## Gates

```text
G4 G5
GAPI GM GS GR
```

## DoD

```text
[ ] no undocumented public symbol drift

[ ] API manifest frozen

[ ] adapter contract v1 candidate frozen

[ ] migration from previous stable green

[ ] replay selected historical snapshots green

[ ] 0 BLOCKER/CRITICAL

[ ] 1.0 migration guide drafted
```

---

# 56. LOT-30 - PyAccountingKit 1.0.0 Final Qualification & Publication

**Target** : `1.0.0rc1 -> 1.0.0`

## Scope

Aucun nouveau feature scope majeur.

```text
final qualification

release evidence

documentation

packaging

tagging

publishing
```

## Dependencies

```text
LOT-29
```

## Required gates

```text
G4
then
G5
```

## 1.0 required minimum

Conformément à la stratégie de release, la stabilité couvre au minimum :

```text
Money

Entries API

Posting / Reversal semantics

Ledger / Trial Balance

Reference snapshot contract

Company chart contract

UnitOfWork extension contract

Public error hierarchy

Snapshot base semantics
```

La roadmap vise en plus à qualifier les capacités déjà implémentées :

```text
Closing

FEC

Statements

Regulatory Reporting

Financial Analysis

Subledgers
```

## 1.0 DoD

```text
[ ] core accounting stable

[ ] public API frozen

[ ] adapter contract v1 frozen

[ ] Django/PostgreSQL Production-qualified

[ ] SQLAlchemy/PostgreSQL Production-qualified or explicitly scoped

[ ] FEC adapter qualified if advertised

[ ] reference integration qualified

[ ] reporting snapshots stable

[ ] migration path stable

[ ] docs complete

[ ] full golden suite green

[ ] full replay suite green

[ ] 0 BLOCKER/CRITICAL

[ ] immutable v1.0.0 tag

[ ] wheel/sdist published successfully
```

---

# 57. Ce qui n'est PAS requis pour 1.0

La stratégie d'architecture a explicitement placé hors prérequis 1.0 :

```text
Generic Advanced Reconciliation

Consolidation

Corporate Finance

all possible standards
```

Cela permet de stabiliser le coeur sans attendre les P2.

---

# 58. LOT-31 - Reconciliation Foundations & Exact Matching

**Target line** : `1.1.0a1`

## Scope

```text
ReconciliationDefinition

ReconciliationSourceDefinition

ReconciliationSourceSnapshot

ReconciliationItem

normalization

ReconciliationScope

ReconciliationRun

MatchingPolicy

exact identity matching

reference matching

composite key matching
```

## Dependencies

```text
LOT-30
LOT-07
LOT-08
LOT-18
LOT-21
```

## Gates

```text
GA GS
```

## DoD

```text
[ ] source snapshots pinned

[ ] candidate != match

[ ] deterministic strategy ordering

[ ] provenance retained

[ ] source sign policy explicit
```

---

# 59. LOT-32 - Partial/Tolerance Matching, Differences & Resolution

**Target line** : `1.1.0a2/b1`

## Scope

```text
one-to-many

many-to-one

many-to-many

partial allocations

tolerance policies

ambiguity

ReconciliationDifference

ResolutionCase

JournalEntryProposal integration

match reversal
```

## Dependencies

```text
LOT-31
LOT-05
LOT-06
```

## Gates

```text
GC GP GS
```

## DoD

```text
[ ] no over-allocation

[ ] tolerance != write-off

[ ] explained != resolved

[ ] ambiguity fail-closed

[ ] accounting correction only via proposal/posting
```

---

# 60. LOT-33 - Bank, Subledger/GL, Intercompany & Reconciliation Qualification

**Target line** : `1.1.0b2 -> 1.1.0`

## Scope

```text
Bank reconciliation source contract

Subledger/GL

Intercompany

External Confirmation

Import Control

ReconciliationSnapshot

sign-off

replay

performance qualification
```

## Dependencies

```text
LOT-32
LOT-15
LOT-18
LOT-19
LOT-23
LOT-24
```

## Gates

```text
G4 G5
GP GS
```

## DoD

```text
[ ] bank golden suite

[ ] subledger/GL golden suite

[ ] IC mismatch golden suite

[ ] external artifact provenance

[ ] snapshot immutable

[ ] replay green

[ ] consolidation can consume match evidence
```

---

# 61. Release 1.1.0 - Generic Reconciliation

Post-1.0 backward-compatible extension.

```text
Reconciliation matches/explains.

Posting owns accounting correction.

Consolidation owns eliminations.
```

---

# 62. LOT-34 - Consolidation Group, Scope, Ownership, Packages & Group Chart

**Target line** : `1.2.0a1`

## Scope

```text
Group

ConsolidationScope

ConsolidationEntity

OwnershipEdge

OwnershipGraph

ControlPolicy

ConsolidationMethodPolicy

ConsolidationPeriod

EntityReportingPackage

GroupChartOfAccounts

GroupAccountMapping
```

## Dependencies

```text
LOT-30
LOT-07
LOT-10
LOT-11
LOT-12
LOT-16
LOT-21
```

## Gates

```text
GA GS
```

## DoD

```text
[ ] group != entity

[ ] ownership != control

[ ] scope versioned

[ ] accepted package immutable

[ ] local->group mapping explicit

[ ] no prefix mapping
```

---

# 63. LOT-35 - Currency Translation, Group Policies & Consolidation Ledger

**Target line** : `1.2.0a2`

## Scope

```text
CurrencyTranslationPolicy

ExchangeRateProvider

CurrencyTranslationSnapshot

TranslatedTrialBalance

GroupAccountingPolicySet

PolicyAlignmentAssessment

ConsolidationAdjustment

ConsolidationEntry

ConsolidationLine

ConsolidationLedger
```

## Dependencies

```text
LOT-34
LOT-05
LOT-08
```

## Gates

```text
GC GP GS
```

## DoD

```text
[ ] entity ledger never mutated

[ ] rates pinned

[ ] no universal translation rate rule

[ ] consolidation entries double-entry

[ ] group ledger separate
```

---

# 64. LOT-36 - Intercompany Eliminations, Investment, Goodwill & NCI

**Target line** : `1.2.0b1`

## Scope

```text
IntercompanyPosition

Reconciliation evidence integration

EliminationCandidate

balance elimination

revenue/expense elimination

dividend elimination

unrealized profit architecture

InvestmentEliminationCase

AcquisitionContext

GoodwillMeasurement

NonControllingInterest

GroupResultAttribution
```

## Dependencies

```text
LOT-35
LOT-33
```

## Gates

```text
GC GP GS
```

## DoD

```text
[ ] matching != elimination

[ ] elimination idempotent

[ ] no duplicate elimination

[ ] goodwill policy-driven

[ ] NCI policy-driven

[ ] parent + NCI attribution reconciles
```

---

# 65. LOT-37 - Consolidated Trial Balance, Statements, Snapshot & Qualification

**Target line** : `1.2.0b2 -> 1.2.0`

## Scope

```text
ConsolidationRun

ConsolidatedTrialBalance

Consolidated statement source

reuse FinancialStatementEngine

ConsolidationSnapshot

EvidenceBundle

close/reopen

staleness

drill-down

replay

concurrency qualification
```

## Dependencies

```text
LOT-36
LOT-16
LOT-20
LOT-23
LOT-24
```

## Gates

```text
G4 G5
GC GP GS
```

## DoD

```text
[ ] consolidated TB balanced

[ ] statements reuse generic engine

[ ] full drill-down to entity JournalEntryLine

[ ] published snapshot immutable

[ ] source reopen marks downstream stale

[ ] replay green

[ ] close/package concurrency green
```

---

# 66. Release 1.2.0 - Consolidation

Stable P2 consolidation release.

It does not change the individual-ledger semantics stabilized in 1.0.

---

# 67. LOT-38 - Advanced Financial Analysis Boundary Guards

**Target** : no runtime release reserved

## Scope

```text
architecture scope classification

Corporate Finance dependency guards

optional FinancialFactsSnapshot contract

optional FinancialFactsProvider

historical risk definitions only if required
```

## Dependencies

```text
LOT-20
LOT-21
```

## DoD

```text
[ ] no WACC in PyAccountingKit analysis

[ ] no NPV/IRR/DCF in core

[ ] no market-data mandatory dependency

[ ] no stochastic simulation dependency

[ ] no InvestmentProject aggregate in accounting domain
```

## Version policy

If only architecture/tests are added :

```text
no dedicated feature release required
```

If `FinancialFactsSnapshot` becomes public after 1.0 :

```text
next backward-compatible MINOR
```

No version number is reserved in advance.

---

# 68. Lot Dependency Matrix

| Lot | Depends on |
|---|---|
| `00` | - |
| `01` | `00` |
| `02` | `01` |
| `03` | `01,02` |
| `04` | `01,02,03` |
| `05` | `01,04` |
| `06` | `02,04,05` |
| `07` | `04,05,06` |
| `08` | `01,05,06,07` |
| `09` | `02,05,06,07,08` |
| `10` | `01,05,08` |
| `11` | `03,10` |
| `12` | `01,08,10,11` |
| `13` | `06,08,12` |
| `14` | `05,06,08,09,11` |
| `15` | `06,08,11,14` |
| `16` | `07,08,11` |
| `17` | `08,10,11,16` |
| `18` | `03,05,06,08` |
| `19` | `06,07,08,18` |
| `20` | `07,08,10,16` |
| `21` | `10..20` |
| `22` | `05,10,14,16,21` |
| `23` | `05..22` applicable contracts |
| `24` | `05..22` applicable contracts |
| `25` | `06,07,09,15,16,20,23` |
| `26` | `21,23,25` |
| `27` | `10,11,17,22,23,24` |
| `28` | `01..27` |
| `29` | `01..28` |
| `30` | `29` |
| `31` | `07,08,18,21,30` |
| `32` | `05,06,31` |
| `33` | `15,18,19,23,24,32` |
| `34` | `07,10,11,12,16,21,30` |
| `35` | `05,08,34` |
| `36` | `33,35` |
| `37` | `16,20,23,24,36` |
| `38` | `20,21` |

---

# 69. Architecture document -> implementation lots

| Document | Lots principaux |
|---|---|
| `00 REQUIREMENTS` | tous |
| `01 VISION & ARCHITECTURE` | `00..38` |
| `02 DOMAIN MODEL` | `01..20`, `31..37` |
| `03 RULES & INVARIANTS` | `01,04,06,07,09,13,15,18,19,35,36` |
| `04 POLICIES` | `12,13,35,36` |
| `05 REFERENCE DATA` | `10,11,17,27` |
| `06 COMPANY CHART` | `03,11` |
| `07 LEDGER/POSTING` | `04,06,07` |
| `08 CLOSING` | `09` |
| `09 CONTROLS/AUDIT` | `08`, transversal |
| `10 PERSISTENCE` | `05,23,24`, transversal |
| `11 TESTING` | transversal |
| `12 IMPORT/FEC` | `14,15` |
| `13 STATEMENTS/REPORTING` | `16,17` |
| `14 FINANCIAL ANALYSIS` | `20` |
| `15 SUBLEDGERS` | `18,19` |
| `16 PUBLIC API` | `21,22` |
| `17 RELEASE/VERSIONING` | `28,29,30`, transversal |
| `18 CFA FRA MIGRATION` | `25,26` |
| `19 REGULATORY MATRIX` | `27` |
| `20 ADR REGISTER` | transversal governance |
| `21 CONSOLIDATION` | `34..37` |
| `22 RECONCILIATION` | `31..33` |
| `23 ADVANCED FINANCE BOUNDARIES` | `38` |

---

# 70. Recommended branch / delivery rhythm

Default :

```text
main
    |
    +--> feature/lot-XX-...
    |
    +--> release/0.x
```

Each lot should be merged through PR and gate `G1`.

At release freeze :

```text
release/x.y
```

is created if maintenance needs justify it.

---

# 71. Recommended commit discipline

Useful labels :

```text
feat
fix
perf
refactor
docs
test
build
ci

regulatory
migration
breaking
```

Accounting/regulatory impacts still require human-written release notes.

---

# 72. Definition of Ready for a lot

Before implementation begins :

```text
[ ] architecture source identified

[ ] dependent lots DONE

[ ] unresolved ADR conflicts = 0

[ ] public/internal scope clear

[ ] domain objects identified

[ ] ports identified

[ ] golden scenario identified if applicable

[ ] migration impact understood

[ ] gate profile selected
```

---

# 73. Lot states

```text
PLANNED

READY

IN_PROGRESS

BLOCKED

CODE_COMPLETE

QUALIFYING

DONE

RELEASED
```

---

# 74. `DONE` != `RELEASED`

A lot can be :

```text
DONE
```

inside main while its enclosing version is not yet :

```text
RELEASED
```

---

# 75. Critical Path to 1.0

The minimum critical path is :

```text
00
→ 01
→ 02
→ 03
→ 04
→ 05
→ 06
→ 07
→ 08
→ 09
→ 10
→ 11
→ 12
→ 13
→ 14
→ 15
→ 16
→ 17
→ 18
→ 19
→ 20
→ 21
→ 22
→ 23/24
→ 25
→ 26
→ 27
→ 28
→ 29
→ 30
```

Some workstreams can run in parallel after interfaces stabilize.

---

# 76. Safe parallelization

## Can run in parallel

After `LOT-10/11` :

```text
Policies
Imports
Reporting
```

with stable contracts.

After `LOT-16` :

```text
Financial Analysis

Regulatory Reporting
```

After `LOT-21/22` :

```text
Django Adapter

SQLAlchemy Adapter
```

---

# 77. Work that should not be parallelized prematurely

Avoid implementing before upstream contracts stabilize :

```text
Django ORM schema before repository/domain contracts

FEC posting before generic import contract

Regulatory reporting before statement mapping safety

Consolidation before entity snapshot semantics

Generic reconciliation before subledger/ledger snapshot semantics
```

---

# 78. 1.0 End-to-End Qualification Scenario

A 1.0 release candidate should demonstrate :

```text
Reference Provider
    ↓
Reference Snapshot
    ↓
Company Chart
    ↓
Accounting Policy Set
    ↓
JournalEntry
    ↓
Validate
    ↓
Post
    ↓
Ledger
    ↓
Trial Balance
    ↓
Closing
    ↓
Financial Statements
    ↓
Regulatory Reporting
    ↓
Financial Analysis
```

plus :

```text
FEC Source
    ↓
Import Plan
    ↓
Posted Accounting
    ↓
Reconciliation of source totals
```

plus :

```text
Subledger Event
    ↓
Open Item
    ↓
Settlement
    ↓
GL Control Account Reconciliation
```

---

# 79. 1.0 Cross-Adapter Qualification

The same accounting scenarios must yield equivalent business semantics on :

```text
InMemory

Django/PostgreSQL

SQLAlchemy/PostgreSQL
```

Infrastructure-specific identifiers/timing may differ.

Accounting outcome must not.

---

# 80. 1.0 Concurrency Matrix

Minimum race suite :

```text
double posting

posting vs close

double reversal

duplicate account code

idempotent import execution

import vs close

settlement double allocation

close vs reopen

snapshot publish duplicate
```

---

# 81. 1.0 Golden Matrix

Minimum :

```text
CFA FRA posting

CFA FRA reversal

CFA FRA FEC

CFA FRA ledger

CFA FRA statements

CFA FRA closing

regulatory PCG structure

Non-Profit effective plan safety

OHADA negative constraints

financial-analysis core indicators
```

---

# 82. 1.0 Migration Matrix

Test at least :

```text
fresh install

previous stable -> candidate

schema changes

snapshot read compatibility

policy version coexistence

reference snapshot coexistence

chart version migration
```

---

# 83. Release checklist

Before stable publication :

```text
[ ] scope frozen

[ ] changelog updated

[ ] version bumped

[ ] API diff green

[ ] adapter contract diff green

[ ] migrations green

[ ] tests green

[ ] concurrency green

[ ] golden green

[ ] replay green

[ ] package build green

[ ] clean install green

[ ] docs green

[ ] compatibility matrix updated

[ ] regulatory matrix updated

[ ] qualification manifest generated

[ ] artifacts checksummed

[ ] tag created

[ ] publish successful
```

---

# 84. Release qualification artifacts

At RC/stable :

```text
PUBLIC_API_MANIFEST.json

PUBLIC_ERROR_CODES.json

ADAPTER_CONTRACT_MANIFEST.json

REGULATORY_COMPATIBILITY_MATRIX.json

RELEASE_QUALIFICATION_MANIFEST.json

CHANGELOG.md

release notes

artifact checksums
```

Optional :

```text
SBOM

DEPRECATIONS.json

REGULATORY_SUPPORT_MANIFEST.json
```

---

# 85. Stop-the-line conditions

Any of the following blocks an RC/stable :

```text
unbalanced posted accounting

posted mutation possible

period race violation

data loss on rollback

regulatory candidate executed without approval

reference negative constraint lost

snapshot replay mismatch unexplained

cross-entity leakage

duplicate accounting effect under idempotent retry

public API breaking diff without version impact

BLOCKER / CRITICAL issue
```

---

# 86. P2 release strategy

## Reconciliation

```text
1.1.0
```

is recommended after 1.0 because advanced/generic reconciliation is not a prerequisite for the stable accounting core.

---

## Consolidation

```text
1.2.0
```

is recommended after Reconciliation so Consolidation can reuse the generic matching/difference infrastructure rather than duplicate it.

The consolidation domain still owns :

```text
elimination accounting
```

---

## Corporate Finance

No PyAccountingKit release line is reserved.

If required, create a separate framework.

---

# 87. First implementation action

The first actionable delivery is :

```text
LOT-00
PyAccountingKit 0.0.1
Repository Bootstrap & Architecture Safety Net
```

The first commit set should contain only infrastructure/foundation scope, not accounting business features.

---

# 88. Suggested LOT-00 deliverables

```text
pyproject.toml

src/pyaccountingkit/__init__.py

src/pyaccountingkit/
    core/
    domain/
    application/
    ports/
    adapters/
    integrations/
    public/

tests/
    unit/
    property/
    contract/
    integration/
    concurrency/
    golden/

docs/

examples/

README.md

LICENSE

py.typed

CI workflow

architecture dependency test

quality configuration
```

---

# 89. `0.0.1` acceptance command sequence

Conceptual :

```text
clean checkout

install package

run format check

run lint

run type-check

run tests

build wheel

build sdist

install wheel in clean environment

import pyaccountingkit
```

Expected :

```text
all green
```

---

# 90. Final implementation roadmap summary

```text
0.0.1
    Bootstrap

0.1.0
    Accounting Core

0.2.0
    References / Charts / Policies

0.3.0
    Imports / FEC / Reporting

0.4.0
    Subledgers / Analysis

0.5.0
    Public API / Production Adapters

0.6.0
    CFA FRA Migration / Golden Parity

0.7.0
    Regulatory Qualification

0.8.0
    Reliability / Performance / Security

0.9.0
    API Freeze / Migration / Replay Hardening

1.0.0
    Stable Public Core

1.1.0
    Reconciliation

1.2.0
    Consolidation

future separate framework
    Corporate Finance
```

---

# 91. Conclusion

PyAccountingKit dispose maintenant d'un chemin d'implémentation ordonné et testable.

La règle de progression est :

```text
do not move to the next stable milestone
because code exists

move when
scope + DoD + gates
are green
```

Le prochain travail concret est donc :

```text
LOT-00
    ↓
PyAccountingKit 0.0.1
    ↓
Repository Bootstrap
```

avec comme première protection :

```text
architecture boundaries
+
quality tooling
+
clean package build
+
CFA FRA golden-baseline hooks
```

avant d'implémenter `Money`, les IDs et le domaine comptable.
