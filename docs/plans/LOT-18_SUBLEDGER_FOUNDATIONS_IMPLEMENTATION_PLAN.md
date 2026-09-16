# LOT-18 — Subledger Foundations Implementation Plan

> **Projet** : PyAccountingKit  
> **Lot** : LOT-18 — Subledger Foundations  
> **Target line** : `0.4.0a1`  
> **Baseline** : stable `0.3.0` (`93421d66eb867bf16e21803a35070ff046f61f99`)  
> **Branche** : `feat/lot-18-subledger-foundations`

---

## 1. Objectif

LOT-18 introduit le socle de comptabilité auxiliaire sans créer un second General Ledger.

Le lot doit rendre représentables et vérifiables les concepts suivants :

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

La frontière canonique est :

```text
Operational / subledger state
        |
        | explicit accounting effect
        v
JournalEntryProposal / Posting Engine
        |
        v
General Ledger
```

Le sous-livre conserve le détail opérationnel ; le GL reste l'autorité des écritures postées.

---

## 2. Sources d'autorité

Par ordre de priorité :

1. `docs/ROADMAP.md`, section LOT-18 ;
2. `docs/specs/01_core-accounting/15_PYACCOUNTINGKIT_SUBLEDGERS_AND_OPERATIONAL_ACCOUNTING_ARCHITECTURE.md` ;
3. ADR `ADR-SUB-001` à `ADR-SUB-032` du registre canonique ;
4. invariants d'entité, monnaie, posting et traçabilité déjà qualifiés en `0.1.x` / `0.2.x` / `0.3.x` ;
5. `AGENTS.md` pour les règles de modification de la codebase.

En cas de divergence de vocabulaire, la roadmap LOT-18 actuelle prime sur les anciens exemples généraux.

---

## 3. Périmètre LOT-18

### 3.1 Inclus

- définition d'un sous-livre et instance entity-scoped ;
- représentation locale d'un tiers comptable via `SubledgerParty` ;
- référence externe de tiers via `PartyRef` ;
- référence auxiliaire distincte du code de compte ;
- modes `SUBLEDGER`, `EXTENDED_ACCOUNT_CODE`, `HYBRID` ;
- créances et dettes avec échéances ;
- représentation d'un `OpenItem` distinct d'une ligne GL ;
- séparation explicite état opérationnel / état comptable ;
- référence comptable postée explicite avant qu'un item soit considéré accounting-effective ;
- bindings de comptes collectifs versionnés/effective-dated ;
- résolution fail-closed d'un compte collectif dans le chart applicable ;
- policy auxiliaire versionnée/effective-dated ;
- isolation `AccountingEntity` ;
- invariants de devise et de somme des échéances ;
- tests unitaires/property et tests adversariaux de résolution.

### 3.2 Explicitement hors scope

LOT-19 garde :

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

Ne pas introduire dans LOT-18 :

- moteur de règlement ;
- allocation de paiements ;
- lettrage ;
- aging ;
- rapprochement sous-livre ↔ GL ;
- write-off ;
- FX settlement ;
- concurrence d'allocation ;
- API publique de haut niveau ;
- adapter ORM / SQLAlchemy / Django ;
- génération implicite de codes auxiliaires nationaux.

---

## 4. Invariants non négociables

### 4.1 Subledger != General Ledger

Un `Receivable`, `Payable`, `DueItem` ou `OpenItem` n'est jamais une `JournalEntry` / `JournalLine`.

Aucun objet subledger ne peut se substituer au Posting Engine.

### 4.2 Party != CompanyAccount

`SubledgerParty` porte une identité opérationnelle/comptable locale et éventuellement un `PartyRef` externe.

Il ne contient pas de code de compte comme identité primaire et ne doit pas être assimilé à `CompanyAccount`.

### 4.3 AuxiliaryReference != concatenated account code

```text
AuxiliaryReference(system, code)
```

reste distinct de :

```text
CompanyAccount.code
```

Aucune logique `CompteNum + CompAuxNum` n'est admise dans le core.

### 4.4 AccountingEntity isolation

Tous les objets d'une même opération auxiliaire doivent appartenir à la même entité :

```text
Subledger
Party
Receivable/Payable
DueItem
OpenItem
ControlAccountBinding
AuxiliaryAccountingPolicy
```

Tout mismatch échoue via la garde canonique d'entité.

### 4.5 Operational state != accounting state

Le cycle de vie opérationnel d'une créance/dette est distinct de son effet comptable.

LOT-18 introduit au minimum :

```text
OperationalItemStatus
  DRAFT
  OPEN
  CANCELLED

AccountingEffectStatus
  PENDING
  POSTED
  REVERSED
```

Un changement opérationnel ne doit jamais impliquer silencieusement un changement GL.

### 4.6 Accounting-effective requires a posted accounting reference

Un item ne peut être `AccountingEffectStatus.POSTED` que s'il porte une référence à une `JournalEntry` effectivement `POSTED`.

La création de cette référence doit vérifier :

- `EntryStatus.POSTED` ;
- `posted_at` présent ;
- entité attendue cohérente ;
- entry id conservé explicitement.

### 4.7 Due-item reconciliation at creation

Pour `Receivable` et `Payable` :

```text
sum(due_item.original_amount) == original_amount
```

et :

- au moins une échéance ;
- même devise ;
- même entité ;
- chaque `DueItem.source_subledger_item_id` pointe vers son parent ;
- montants strictement positifs.

LOT-18 n'implémente pas encore la diminution d'`open_amount` par règlement.

### 4.8 OpenItem != JournalEntryLine

`OpenItem` est une projection auxiliaire issue d'un `DueItem` accounting-effective.

Il conserve :

- l'identité du due item ;
- l'identité du parent receivable/payable ;
- le tiers ;
- le sous-livre ;
- le montant ouvert ;
- la date d'échéance ;
- la référence d'écriture postée.

Il ne copie pas une `JournalLine` et n'est pas adressé par un line id GL.

### 4.9 Control account resolution is explicit and fail-closed

La résolution doit dépendre au minimum de :

```text
entity_id
subledger_id
accounting_date
party_type?
currency?
```

et sélectionner un `ControlAccountBinding` actif/effectif.

- zéro candidat -> `ControlAccountNotConfiguredError` ;
- plusieurs candidats de même spécificité -> `AmbiguousControlAccountError` ;
- compte absent/inactif/non-postable dans le chart applicable -> échec explicite ;
- aucun numéro national n'est hardcodé.

### 4.10 Auxiliary policy is explicit

`AuxiliaryAccountingPolicy` choisit le mode auxiliaire ; elle ne fabrique pas implicitement un compte.

Un mode `EXTENDED_ACCOUNT_CODE` ou `HYBRID` peut autoriser un futur mécanisme de code policy, mais LOT-18 ne doit pas inventer une convention nationale.

---

## 5. Modèle cible

### 5.1 Primitives

```text
SubledgerType
  ACCOUNTS_RECEIVABLE
  ACCOUNTS_PAYABLE
  OTHER

AuxiliaryMode
  SUBLEDGER
  EXTENDED_ACCOUNT_CODE
  HYBRID

SubledgerStatus
  ACTIVE
  INACTIVE

SubledgerPartyType
  CUSTOMER
  SUPPLIER
  BOTH
  OTHER

OperationalItemStatus
AccountingEffectStatus
BindingStatus
AuxiliaryPolicyStatus
```

### 5.2 SubledgerDefinition

```text
SubledgerDefinition
|-- definition_id
|-- code
|-- label
|-- subledger_type
|-- default_auxiliary_mode
|-- effective_from
|-- effective_to?
```

### 5.3 Subledger

```text
Subledger
|-- subledger_id
|-- entity_id
|-- definition
|-- status
```

### 5.4 SubledgerParty / PartyRef

```text
PartyRef
|-- system
|-- value

SubledgerParty
|-- party_id
|-- entity_id
|-- party_type
|-- display_name
|-- external_ref?
|-- auxiliary_reference?
|-- status
```

### 5.5 AuxiliaryReference

```text
AuxiliaryReference
|-- system
|-- code
|-- label?
```

### 5.6 PostedAccountingReference

```text
PostedAccountingReference
|-- entity_id
|-- entry_id
|-- posted_at
```

Factory uniquement depuis une `JournalEntry` POSTED + entité explicitement validée.

### 5.7 Receivable / Payable

```text
Receivable | Payable
|-- id
|-- entity_id
|-- subledger_id
|-- party_id
|-- source_document_ref
|-- original_amount
|-- accounting_date
|-- due_items
|-- operational_status
|-- accounting_status
|-- accounting_reference?
```

### 5.8 DueItem

```text
DueItem
|-- due_item_id
|-- entity_id
|-- source_subledger_item_id
|-- due_date
|-- original_amount
|-- open_amount
```

Au LOT-18 : `open_amount == original_amount` à la création.

### 5.9 OpenItem

```text
OpenItem
|-- open_item_id
|-- entity_id
|-- subledger_id
|-- party_id
|-- source_item_id
|-- due_item_id
|-- due_date
|-- original_amount
|-- open_amount
|-- accounting_reference
```

Construction autorisée uniquement depuis un parent accounting-effective et un due item cohérent.

### 5.10 ControlAccountBinding

```text
ControlAccountBinding
|-- binding_id
|-- entity_id
|-- subledger_id
|-- company_account_id
|-- party_type?
|-- currency_code?
|-- effective_from
|-- effective_to?
|-- status
```

### 5.11 AuxiliaryAccountingPolicy

```text
AuxiliaryAccountingPolicy
|-- policy_id
|-- entity_id
|-- subledger_id
|-- version
|-- auxiliary_mode
|-- status
|-- effective_from
|-- effective_to?
|-- require_auxiliary_reference
```

---

## 6. Résolution du compte collectif

Ajouter un port applicatif :

```text
ControlAccountResolverProtocol
```

et un résultat :

```text
ResolvedControlAccount
|-- binding_id
|-- account_id
|-- account_code
|-- entity_id
|-- subledger_id
|-- chart_id
|-- chart_version
|-- reference_snapshot_id
```

Adapter de référence :

```text
InMemoryControlAccountResolver
```

Il réutilise `CompanyChartResolverProtocol` ; il ne duplique pas la résolution de version de chart.

---

## 7. Découpage d'implémentation

### Step 1 — erreurs et primitives

- taxonomie d'erreurs subledger stable ;
- enums de type/mode/status ;
- tests de validation.

### Step 2 — SubledgerDefinition / Subledger

- invariants de code/label/dates ;
- instance entity-scoped ;
- effective-date helpers.

### Step 3 — PartyRef / SubledgerParty / AuxiliaryReference

- identité tiers distincte des comptes ;
- validations non-empty ;
- auxiliary reference sans concaténation implicite.

### Step 4 — AuxiliaryAccountingPolicy

- lifecycle minimal ;
- effective dating ;
- entity/subledger scope ;
- modes auxiliaires explicites.

### Step 5 — ControlAccountBinding

- lifecycle/effective dating ;
- filtre partner type/currency ;
- tests absence/ambiguïté.

### Step 6 — InMemoryControlAccountResolver

- réutilisation du `CompanyChartResolverProtocol` ;
- vérification compte présent, actif, postable et entity-safe ;
- trace chart/version/snapshot dans `ResolvedControlAccount`.

### Step 7 — PostedAccountingReference

- factory depuis `JournalEntry` POSTED ;
- rejet DRAFT/VALIDATED/REVERSED ;
- entity guard explicite.

### Step 8 — DueItem

- Money positif ;
- `open_amount == original_amount` au LOT-18 ;
- parent/entity scope.

### Step 9 — Receivable / Payable

- due-item totals ;
- devise unique ;
- séparation opérationnel/comptable ;
- transition explicite vers accounting-effective avec `PostedAccountingReference`.

### Step 10 — OpenItem

- factory depuis due item + parent POSTED ;
- aucune dépendance à `JournalLine` ;
- lineage explicite vers item/due item/entry.

### Step 11 — qualification property/adversarial

- sommes des échéances ;
- cross-entity rejection ;
- control-account ambiguity ;
- draft accounting reference rejection ;
- OpenItem impossible avant accounting-effective ;
- exact effective-date boundaries.

### Step 12 — manifests/docs/release `0.4.0a1`

- error manifest ;
- adapter contract manifest pour resolver ;
- README / CHANGELOG ;
- version bump uniquement après gates vertes ;
- qualification Python 3.11/3.12/3.13 + package + Security.

---

## 8. Fichiers cibles

Proposition initiale :

```text
src/pyaccountingkit/domain/subledgers/
  __init__.py
  primitives.py
  subledger.py
  parties.py
  auxiliary.py
  accounting_reference.py
  due_item.py
  receivable.py
  payable.py
  open_item.py
  control_account.py
  policy.py

src/pyaccountingkit/ports/
  control_account_resolution.py

src/pyaccountingkit/adapters/in_memory/
  control_account_resolver.py

tests/unit/domain/subledgers/
  test_foundations.py
  test_receivables_payables.py
  test_open_items.py

tests/unit/adapters/in_memory/
  test_control_account_resolver.py

tests/property/
  test_subledger_due_item_properties.py
```

L'arborescence peut être regroupée si cela améliore la cohésion sans mélanger les bounded contexts.

---

## 9. Definition of Done LOT-18

Roadmap :

```text
[x target] subledger != GL
[x target] open item != JournalEntryLine
[x target] operational state distinct from accounting state
[x target] accounting-effective item linked to posted accounting
[x target] control account resolved explicitly
```

Compléments indispensables :

```text
[ ] entity isolation adversarial tests
[ ] due-item total invariant
[ ] currency consistency
[ ] no implicit account-code concatenation
[ ] control-account resolution exact/effective/fail-closed
[ ] chart version/snapshot trace preserved
[ ] no settlement/allocation/matching/aging scope creep
[ ] Ruff + strict mypy
[ ] unit + property + contract/regression suites
[ ] Python 3.11/3.12/3.13
[ ] package qualification
[ ] Security gate
```

---

## 10. Release boundary

`0.4.0a1` signifie : **fondations de sous-livre qualifiées**, pas comptabilité auxiliaire complète.

La séquence attendue reste :

```text
0.4.0a1  LOT-18 foundations
0.4.0a2  LOT-19 settlements / allocations / matching / aging
0.4.0b1+ LOT-20 financial analysis
0.4.0    stable
```

Aucune fonctionnalité LOT-19 ne sera utilisée pour faire artificiellement paraître LOT-18 plus complet qu'il ne l'est.
