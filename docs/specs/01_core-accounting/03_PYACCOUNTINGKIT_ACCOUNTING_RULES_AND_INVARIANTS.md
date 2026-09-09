# 03 - PyAccountingKit - Règles comptables et invariants

> **Projet** : PyAccountingKit  
> **Document** : `03_PYACCOUNTINGKIT_ACCOUNTING_RULES_AND_INVARIANTS.md`  
> **Documents parents** :  
> - `00_PYACCOUNTINGKIT_REQUIREMENTS_ANALYSIS.md`  
> - `01_PYACCOUNTINGKIT_PROJECT_VISION_AND_ARCHITECTURE.md`  
> - `02_PYACCOUNTINGKIT_DOMAIN_MODEL_AND_BOUNDED_CONTEXTS.md`  
> **Statut** : P0.4 - Spécification des règles et invariants  
> **Langue** : Français  
> **Objet** : Formaliser les règles comptables, invariants transactionnels, policies de période et de rattachement, principes doctrinaux, règles de posting et de reversal, contraintes de clôture, niveaux de normativité, codes d'erreur et exigences de test de PyAccountingKit.

---

# 1. Résumé exécutif

PyAccountingKit doit distinguer strictement plusieurs catégories de règles.

Toutes les règles rencontrées en comptabilité ne sont pas des **invariants universels**.

Le framework doit savoir différencier :

```text
UNIVERSAL_ACCOUNTING_INVARIANT

DOMAIN_POLICY

REGULATORY_RULE

REFERENCE_SPECIFIC_RULE

ACCOUNTING_METHOD

PRESENTATION_RULE

ANALYTICAL_DEFINITION

CONTROL

HEURISTIC
```

Cette distinction est essentielle.

Par exemple :

```text
SUM(debit) = SUM(credit)
```

est un invariant structurel du moteur en partie double.

En revanche :

```text
prudence
continuité
permanence des méthodes
coût historique
juste valeur
rattachement particulier d'une charge
méthode de valorisation des stocks
```

ne doivent pas être codés comme des constantes universelles du Posting Engine.

L'ouvrage de comptabilité étudié présente explicitement plusieurs principes comme des choix ou oppositions de modèles : séparation/unicité des périodes, coûts/valeurs, rattachement/non-rattachement, prudence/imprudence, coût historique/coût réévalué, continuité/non-continuité et permanence/non-permanence. fileciteturn14file1L346-L376

PyAccountingKit doit donc protéger les **invariants du moteur** tout en rendant les **méthodes comptables configurables, versionnées et explicables**.

---

# 2. Sources utilisées

Le présent document s'appuie sur quatre familles de sources.

## 2.1 Référence fonctionnelle CFA FRA

Le projet CFA FRA formalise déjà :

```text
source comptable canonique
partie double
workflow DRAFT -> VALIDATED -> POSTED
immutabilité
reversal
période ouverte
contrôles de ligne
audit
clôture
```

Le MVP définit notamment `JournalEntry + JournalLine + Account + AccountingPeriod` comme données canoniques et traite grand livre, balances et états financiers comme projections calculées. fileciteturn13file0L75-L101

Il impose également l'immutabilité des écritures postées et la correction par reversal puis nouvelle écriture. fileciteturn13file0L105-L131

---

## 2.2 Corpus doctrinal comptable

L'ouvrage *Comptabilité générale - Système français et normes IFRS* est utilisé pour :

- distinguer les principes comptables ;
- identifier les questions de périodicité ;
- formaliser le rattachement ;
- comprendre prudence, continuité et permanence ;
- distinguer coût et valeur ;
- préparer les futures policies de mesure.

Il ne constitue pas la source réglementaire actuelle de PyAccountingKit.

---

## 2.3 `regulatory-accounting-data-framework`

Ce projet reste la source de vérité réglementaire structurée.

Il fournit notamment les standards, éditions, relations, plans effectifs et mappings qualifiés.

Une comparaison structurelle EBNL/SYSCOHADA indique explicitement qu'un code identique n'est pas une preuve d'équivalence sémantique, que l'approbation automatique d'un crosswalk est désactivée et qu'une revue humaine peut être requise. fileciteturn15file7L1795-L1812

---

## 2.4 Sources analytiques

Les méthodes SIG, CAF, FRNG, BFR et ratios relèvent du bounded context `Financial Analysis`.

Elles ne sont pas des invariants du write-side comptable.

---

# 3. Hiérarchie de normativité

PyAccountingKit doit qualifier chaque règle avec un `RuleKind`.

```python
class RuleKind(Enum):
    UNIVERSAL_ACCOUNTING_INVARIANT = "universal_accounting_invariant"
    DOMAIN_POLICY = "domain_policy"
    REGULATORY_RULE = "regulatory_rule"
    REFERENCE_SPECIFIC_RULE = "reference_specific_rule"
    ACCOUNTING_METHOD = "accounting_method"
    PRESENTATION_RULE = "presentation_rule"
    ANALYTICAL_DEFINITION = "analytical_definition"
    CONTROL = "control"
    HEURISTIC = "heuristic"
```

Ordre d'autorité lorsqu'une décision doit être prise :

```text
1. invariant structurel du moteur

2. référentiel réglementaire versionné
   si la règle est dans son domaine d'applicabilité

3. AccountingPolicySet explicitement sélectionné

4. configuration de l'organisation

5. méthode doctrinale qualifiée

6. heuristique / suggestion
```

Une heuristique ne peut jamais supplanter une règle réglementaire.

---

# 4. Métadonnées obligatoires d'une règle

Toute règle exécutable ou contrôlable doit pouvoir être décrite par :

```text
RuleId
RuleCode
RuleKind
version
scope
effective_from
effective_to
severity
enforcement_stage
source / provenance
human_validation_required
parameters
```

Exemple conceptuel :

```python
AccountingRuleDefinition(
    code="ENTRY_BALANCED",
    kind=RuleKind.UNIVERSAL_ACCOUNTING_INVARIANT,
    version="1",
    enforcement_stage=EnforcementStage.VALIDATE_AND_POST,
)
```

---

# 5. Niveaux d'enforcement

Une règle peut être appliquée à différents moments.

```text
ON_CREATE
ON_UPDATE
ON_VALIDATE
ON_POST
ON_REVERSE
ON_CLOSE
ON_IMPORT
ON_REPORT
ON_ANALYZE
DIAGNOSTIC_ONLY
```

Le fait qu'une règle existe ne signifie pas qu'elle bloque toutes les opérations.

---

# 6. Invariant fondamental - partie double

## INV-ENTRY-001 - Équilibre débit / crédit

Toute écriture qui atteint l'état `VALIDATED` ou `POSTED` doit respecter :

```text
SUM(debit) = SUM(credit)
```

CFA FRA pose explicitement cette règle comme condition de validité d'une écriture. fileciteturn13file2L436-L452

### Classification

```text
RuleKind:
UNIVERSAL_ACCOUNTING_INVARIANT
```

### Enforcement

```text
ON_VALIDATE
ON_POST
ON_IMPORT
```

### Erreur

```text
UnbalancedEntryError
code = ENTRY_UNBALANCED
```

---

# 7. Invariants des lignes comptables

CFA FRA formalise les contraintes suivantes sur une ligne :

```text
debit >= 0
credit >= 0
NOT (debit > 0 AND credit > 0)
```

fileciteturn13file2L426-L432

PyAccountingKit généralise ces règles.

---

## INV-LINE-001 - Montant non négatif

```text
debit >= 0
credit >= 0
```

Classification :

```text
UNIVERSAL_ACCOUNTING_INVARIANT
```

---

## INV-LINE-002 - Débit XOR crédit

Une ligne ne peut pas porter simultanément un débit positif et un crédit positif.

```text
NOT (
    debit > 0
    AND
    credit > 0
)
```

Classification :

```text
UNIVERSAL_ACCOUNTING_INVARIANT
```

---

## INV-LINE-003 - Ligne non nulle lors de la validation

Une ligne comptable validée ne doit pas être :

```text
debit = 0
AND
credit = 0
```

Classification :

```text
DOMAIN_POLICY
```

Cette règle est retenue comme policy générique du framework.

Elle peut être structurellement évitée en représentant la ligne par :

```text
PostingAmount(
    side = DEBIT | CREDIT,
    amount > 0
)
```

---

## INV-LINE-004 - Devise cohérente

Lorsque le ledger n'utilise qu'une devise fonctionnelle :

```text
line.functional_amount.currency
=
ledger.functional_currency
```

Classification :

```text
UNIVERSAL_ACCOUNTING_INVARIANT
dans le modèle fonctionnel retenu
```

Les règles de multi-devise détaillées seront spécifiées séparément.

---

# 8. Nombre minimal de lignes

CFA FRA contrôle explicitement qu'une écriture possède au moins deux lignes avant validation. fileciteturn14file5L1337-L1357

## INV-ENTRY-002

```text
len(entry.lines) >= 2
```

Classification :

```text
DOMAIN_POLICY
```

Cette policy est retenue comme règle de base du framework.

Elle n'est pas nécessaire pour représenter un draft intermédiaire.

En conséquence :

```text
DRAFT
    peut temporairement avoir < 2 lignes

VALIDATED
POSTED
    doivent avoir >= 2 lignes
```

---

# 9. Cycle de vie d'une écriture

Le cycle cible est :

```text
DRAFT
  |
  | validate
  v
VALIDATED
  |
  | post
  v
POSTED
  |
  | reverse
  v
REVERSED
```

CFA FRA distingue `DRAFT`, `VALIDATED`, `POSTED` et `REVERSED`. fileciteturn13file1L271-L299

---

## INV-STATE-001 - Pas de posting direct depuis DRAFT

Transition interdite :

```text
DRAFT -> POSTED
```

Classification :

```text
DOMAIN_POLICY
```

---

## INV-STATE-002 - Posting uniquement depuis VALIDATED

Précondition :

```text
entry.status == VALIDATED
```

Classification :

```text
DOMAIN_POLICY
```

---

## INV-STATE-003 - Reversal uniquement d'une écriture postée

Précondition :

```text
entry.status == POSTED
```

Classification :

```text
DOMAIN_POLICY
```

Une policy future pourra préciser les cas de reversal multiples ou partiels.

Par défaut :

```text
un original POSTED
    ->
au plus une reversal définitive active
```

---

# 10. Immutabilité des écritures postées

CFA FRA impose qu'une écriture `POSTED` soit immuable. fileciteturn13file5L1304-L1310

## INV-IMM-001

Une écriture postée ne peut plus subir de mutation métier directe.

Sont interdits :

```text
changer la date comptable
changer le journal
changer le compte d'une ligne
changer debit / credit
ajouter une ligne
supprimer une ligne
changer le libellé ayant valeur comptable
```

Classification :

```text
UNIVERSAL_ACCOUNTING_INVARIANT
pour le modèle append-oriented choisi par PyAccountingKit
```

---

## Mutations techniques autorisées

Le framework peut autoriser des métadonnées purement techniques non comptables si elles sont explicitement séparées :

```text
indexation
cache
projection state
technical correlation metadata
```

Elles ne font pas partie de l'écriture comptable elle-même.

---

# 11. Règle de correction - reversal + replacement

CFA FRA exige que l'écriture originale demeure inchangée, qu'une écriture de contre-passation soit créée et que l'opération soit auditée. fileciteturn14file5L1361-L1400

## INV-REV-001 - Original inchangé

```text
original_entry
    remains immutable
```

---

## INV-REV-002 - Reversal reliée à l'original

```text
reversal.reversal_of
=
original.id
```

---

## INV-REV-003 - Symétrie des mouvements

Pour une reversal intégrale :

```text
original.debit
    -> reversal.credit

original.credit
    -> reversal.debit
```

---

## INV-REV-004 - Reversal comme nouvelle écriture

La contre-passation possède :

```text
new JournalEntryId
new EntryNumber
new PostingDate
audit metadata
```

Elle ne réutilise jamais l'identité de l'écriture originale.

---

# 12. Date de reversal

La date de reversal n'est pas nécessairement la date de l'écriture originale.

Elle doit respecter :

```text
ReversalDatePolicy
```

Exemples de stratégies futures :

```text
SAME_PERIOD_IF_OPEN
CURRENT_OPEN_PERIOD
NEXT_PERIOD
EXPLICIT_ALLOWED_DATE
```

Classification :

```text
DOMAIN_POLICY
```

---

# 13. Invariants de période

## INV-PER-001 - Date dans la période

Une écriture postée doit être liée à une période compatible avec sa date comptable.

```text
period.start_date
<=
entry.accounting_date
<=
period.end_date
```

Classification :

```text
DOMAIN_POLICY
```

---

## INV-PER-002 - Période ouverte pour posting normal

CFA FRA considère qu'une période fermée doit bloquer le posting. fileciteturn14file2L574-L584

Par défaut :

```text
OPEN
    -> posting autorisé

CLOSING
    -> posting dépend de PeriodPolicy / EntryType

CLOSED
LOCKED
    -> posting interdit
```

Classification :

```text
DOMAIN_POLICY
```

---

## INV-PER-003 - Ledger et période de même entité

```text
entry.entity_id
=
period.entity_id
=
journal.entity_id
=
account.entity_id
```

Classification :

```text
UNIVERSAL_ACCOUNTING_INVARIANT
dans le modèle multi-entités de PyAccountingKit
```

---

# 14. Séparation des exercices

L'ouvrage doctrinal distingue explicitement le principe de séparation des périodes/exercices et relie la comptabilité périodique au rattachement des charges et produits à la période concernée. fileciteturn14file9L1725-L1740

PyAccountingKit ne doit toutefois pas encoder cela comme une règle structurelle unique applicable à tous les modèles possibles.

## POL-PER-001 - Periodic Accounting Policy

Classification :

```text
ACCOUNTING_METHOD
+
DOMAIN_POLICY
```

Une configuration typique d'une comptabilité d'engagement adopte :

```text
periodic_result_measurement = true
accrual_accounting = true
```

Cette policy conditionne notamment :

```text
accruals
deferrals
cut-off
period-end adjustments
```

---

# 15. Rattachement des charges et produits

Le rattachement est traité dans le corpus doctrinal comme un principe de modèle comptable et non comme une propriété mathématique de la partie double. fileciteturn14file1L346-L376

## POL-ACC-001 - Accrual / Matching Policy

Classification :

```text
ACCOUNTING_METHOD
```

Le framework doit permettre :

```text
AccrualRecognitionPolicy
DeferralPolicy
MatchingPolicy
```

et non :

```python
if date < year_end:
    ...
```

codé directement dans le Posting Engine.

---

# 16. Prudence

L'ouvrage situe la prudence parmi les principes qui caractérisent un type de comptabilité et l'oppose conceptuellement à une logique d'imprudence. fileciteturn14file1L346-L376

## Décision PyAccountingKit

La prudence n'est **pas** un `UNIVERSAL_ACCOUNTING_INVARIANT`.

Classification :

```text
ACCOUNTING_METHOD
ou
REGULATORY_RULE
selon le contexte
```

Elle doit pouvoir influencer des policies spécialisées :

```text
ImpairmentPolicy
ProvisionRecognitionPolicy
InventoryWriteDownPolicy
LossRecognitionPolicy
```

Le Posting Engine ne contient pas de :

```python
if prudence:
    ...
```

---

# 17. Continuité d'exploitation

Le corpus doctrinal présente la continuité comme une hypothèse importante mais souligne qu'elle ne détermine pas à elle seule toutes les méthodes d'évaluation. fileciteturn14file8L1685-L1702

## POL-GC-001 - Going Concern Context

Classification :

```text
ACCOUNTING_METHOD
+
REGULATORY_RULE selon le contexte
```

Le framework doit représenter le contexte :

```text
GoingConcernStatus:
    GOING_CONCERN
    UNCERTAIN
    NON_GOING_CONCERN
```

sans en déduire automatiquement une méthode de mesure unique.

Les `MeasurementPolicy` déterminent les conséquences effectives.

---

# 18. Permanence des méthodes

Le corpus doctrinal explique que la permanence favorise la comparabilité dans le temps, tout en indiquant que ce principe n'est pas absolu et peut céder lors d'un changement justifié de système, de type ou de méthode. fileciteturn14file8L1703-L1715

## POL-CONS-001 - Consistency Policy

Classification :

```text
ACCOUNTING_METHOD
```

PyAccountingKit doit permettre :

```text
AccountingPolicySet version N
        |
        | explicit migration
        v
AccountingPolicySet version N+1
```

Le changement de méthode doit être :

```text
explicite
daté
versionné
audité
traçable
```

---

# 19. Coût, valeur et bases de mesure

Le corpus doctrinal distingue les systèmes orientés coût et valeur et souligne l'existence de plusieurs concepts de coût. fileciteturn14file9L1750-L1760

## POL-MEAS-001 - Measurement Basis

Classification :

```text
ACCOUNTING_METHOD
```

Value Object prévu :

```text
MeasurementBasis
```

Exemples futurs :

```text
HISTORICAL_COST
REVALUED_COST
FAIR_VALUE
VALUE_IN_USE
AMORTIZED_COST
NET_REALIZABLE_VALUE
CUSTOM
```

Cette liste ne constitue pas une autorisation réglementaire universelle.

La disponibilité d'une base dépend :

```text
ReferenceStandard
AccountingPolicySet
asset / liability category
effective date
```

---

# 20. Permanence et versioning des policies

Une policy utilisée pour générer une écriture doit être identifiable.

```text
policy_id
policy_version
effective_date
reference_snapshot
```

## INV-POL-001

Une `PolicyExecutionTrace` ne peut référencer une version ambiguë ou inexistante.

Classification :

```text
UNIVERSAL_ACCOUNTING_INVARIANT
du système de policy PyAccountingKit
```

---

# 21. Invariants des comptes

## INV-ACC-001 - Compte existant

Toute ligne validée doit référencer un `CompanyAccount` connu.

---

## INV-ACC-002 - Compte actif

CFA FRA exige un compte actif lors de la validation. fileciteturn14file5L1337-L1357

Classification :

```text
DOMAIN_POLICY
```

---

## INV-ACC-003 - Compte postable

Un compte non postable ne peut recevoir directement de mouvements.

```text
account.posting_allowed == true
```

Classification :

```text
DOMAIN_POLICY
```

---

## INV-ACC-004 - Même entité

```text
account.entity_id
=
entry.entity_id
```

Classification :

```text
UNIVERSAL_ACCOUNTING_INVARIANT
```

---

# 22. Invariants du journal

## INV-JRN-001 - Journal existant et actif

CFA FRA inclut le journal actif parmi les contrôles de validation. fileciteturn14file5L1337-L1357

Classification :

```text
DOMAIN_POLICY
```

---

## INV-JRN-002 - Même entité

```text
journal.entity_id
=
entry.entity_id
```

---

## INV-JRN-003 - Type de journal

Le type de journal peut limiter les types d'opérations via :

```text
JournalPostingPolicy
```

Classification :

```text
DOMAIN_POLICY
```

Ce n'est pas un invariant universel.

---

# 23. Numérotation des écritures

La numérotation doit être traitée par :

```text
EntryNumberingPolicy
```

Exigences minimales :

```text
stabilité après posting
unicité dans le scope défini
traçabilité
```

Scopes possibles :

```text
entity
journal
fiscal year
period
journal + fiscal year
```

Classification :

```text
DOMAIN_POLICY
ou
REGULATORY_RULE
```

---

# 24. Validation vs Posting

PyAccountingKit sépare explicitement les deux opérations.

## Validation

Répond à :

```text
L'écriture satisfait-elle les règles nécessaires
pour devenir comptabilisable ?
```

## Posting

Répond à :

```text
Cette écriture validée peut-elle devenir définitive maintenant ?
```

CFA FRA exécute validation de période puis validation d'écriture avant passage à `POSTED`. fileciteturn14file5L1314-L1333

---

# 25. Contrat `validate(entry)`

Le validateur P0 doit contrôler au minimum :

```text
ENTRY_HAS_MINIMUM_LINES
LINE_AMOUNT_VALID
DEBIT_OR_CREDIT_ONLY
ENTRY_NON_ZERO
ACCOUNT_EXISTS
ACCOUNT_ACTIVE
ACCOUNT_POSTABLE
JOURNAL_ACTIVE
DATE_WITHIN_PERIOD
PERIOD_ACCEPTS_VALIDATION
SAME_ACCOUNTING_ENTITY
ENTRY_BALANCED
```

Résultat :

```text
ValidationResult
    valid
    issues[]
```

La validation doit pouvoir être exécutée sans persister l'écriture.

---

# 26. Contrat `post(entry)`

Préconditions P0 :

```text
entry.status == VALIDATED

period accepts posting

journal active

accounts active / postable

entry balanced

entity scopes coherent
```

Résultat :

```text
entry.status = POSTED
posted_at = Clock.now()
```

Effets associés :

```text
DomainEvent: JournalEntryPosted
AuditEvent: ENTRY_POSTED
```

---

# 27. Atomicité du posting

Le posting est une transaction logique unique.

```text
check preconditions
+
transition state
+
persist
+
audit
=
atomic operation
```

Le framework doit empêcher :

```text
double posting
lost update
partially persisted entry
```

La technologie de verrouillage appartient aux adapters.

---

# 28. Concurrence

Le contrat métier peut utiliser :

```text
expected_version
revision
state precondition
```

Adapter Django :

```text
transaction.atomic
select_for_update
```

Adapter SQLAlchemy :

```text
transaction
SELECT FOR UPDATE
```

Le domaine ne dépend d'aucune de ces APIs.

---

# 29. Contrat `reverse(entry)`

Préconditions :

```text
original.status == POSTED
reversal date authorized
reversal period accepts posting
no conflicting active reversal
```

Production :

```text
new JournalEntry
reversal_of = original.id
debit / credit swapped
source_reference preserved or linked
```

Puis :

```text
validate reversal
post reversal
mark original REVERSED
audit
```

Le marquage de l'originale comme `REVERSED` ne signifie pas que ses mouvements disparaissent.

---

# 30. Source comptable canonique

PyAccountingKit adopte :

```text
POSTED JournalEntry
+
JournalEntryLine
```

comme source transactionnelle de restitution.

CFA FRA précise que grand livre, balances et états financiers doivent être calculés depuis la source canonique plutôt que stockés comme copies indépendantes. fileciteturn13file0L75-L91

---

## INV-LED-001 - Projection reconstructible

Tout solde comptable doit pouvoir être reconstruit depuis les lignes postées.

Classification :

```text
DOMAIN_INVARIANT
```

---

# 31. Règle de solde signé

CFA FRA utilise :

```text
signed_balance = debit - credit
```

pour son moteur interne de grand livre. fileciteturn14file10L1799-L1815

PyAccountingKit peut conserver cette convention **interne** comme policy de projection :

```text
LedgerSignedBalanceConvention
```

Classification :

```text
DOMAIN_POLICY
```

Cette convention ne doit pas être confondue avec la `normal_balance` économique d'un compte.

---

# 32. Balance et égalité globale

CFA FRA contrôle également :

```text
SUM(soldes débiteurs)
=
SUM(soldes créditeurs)
```

dans la balance. fileciteturn14file10L1917-L1933

Classification :

```text
CONTROL
```

Pourquoi pas `UNIVERSAL_ACCOUNTING_INVARIANT` ?

Parce que la balance est une projection.

Si ce contrôle échoue alors que les écritures sources sont équilibrées, cela signale généralement :

```text
bug de projection
filtre incohérent
corruption
périmètre incomplet
```

---

# 33. Variantes de balance

CFA FRA distingue :

```text
BEFORE_ADJUSTMENTS
ADJUSTED
POST_CLOSING
```

avec des types d'écritures inclus différents. fileciteturn14file10L1817-L1887

Classification :

```text
PRESENTATION_RULE
+
DOMAIN_POLICY
```

PyAccountingKit ne doit pas considérer la classification précise observée dans CFA FRA comme universelle.

Elle devient :

```text
TrialBalanceVariantPolicy
```

---

# 34. Règles de clôture

CFA FRA définit un workflow de clôture où les contrôles sont revus, les écritures de clôture générées, validées puis postées avant fermeture de la période. fileciteturn15file6L1721-L1753

La clôture ne doit donc pas être :

```text
period.status = CLOSED
```

sans orchestration.

---

## POL-CLOSE-001 - Closing Workflow

```text
Review Controls
    ->
Generate Adjustments / Closing Entries
    ->
Validate
    ->
Post
    ->
Build Post-closing Trial Balance
    ->
Close Period
```

Classification :

```text
DOMAIN_POLICY
```

---

# 35. Conditions de clôture

CFA FRA propose comme conditions bloquantes :

```text
balance non équilibrée
cash-flow non réconcilié
écritures DRAFT restantes
contrôles bloquants
```

fileciteturn15file6L1757-L1769

PyAccountingKit doit distinguer ce qui est générique de ce qui est configurable.

## P0 générique

```text
no blocking accounting controls

no unresolved DRAFT entries
if ClosingPolicy requires it
```

## Configurable

```text
cash-flow reconciliation required
temporary accounts closure required
specific regulatory controls
```

---

# 36. Après clôture

CFA FRA interdit le posting après fermeture. fileciteturn15file4L1045-L1076

## INV-CLOSE-001

```text
CLOSED / LOCKED
    -> ordinary posting prohibited
```

Classification :

```text
DOMAIN_POLICY
```

Une réouverture doit être explicite et auditée.

---

# 37. À-nouveaux / Opening balances

Le système doit distinguer :

```text
opening entries
normal entries
adjusting entries
closing entries
reversal entries
```

La génération des à-nouveaux appartient à :

```text
OpeningBalancePolicy
```

et non au coeur mathématique de la partie double.

---

# 38. Règles de prudence et écritures d'inventaire

Le principe de prudence doit être traduit uniquement à travers des policies qualifiées.

Exemple :

```text
ImpairmentPolicy
    may generate
ImpairmentEntryProposal
```

Puis :

```text
proposal
    ->
JournalEntry
    ->
validate
    ->
post
```

Le domain spécialisé ne contourne pas le Posting Engine.

---

# 39. Provisions

Les provisions relèvent du futur bounded context :

```text
Accruals & Provisions
```

Règles de reconnaissance et de mesure :

```text
ProvisionRecognitionPolicy
ProvisionMeasurementPolicy
```

Classification :

```text
ACCOUNTING_METHOD
REGULATORY_RULE
selon le contexte
```

Aucune formule universelle n'est codée dans le coeur P0.

---

# 40. Amortissements et dépréciations

Même principe pour :

```text
DepreciationPolicy
ImpairmentPolicy
```

Le futur bounded context `Fixed Assets` calcule les événements et montants.

Le coeur comptable :

```text
reçoit la proposition
valide les comptes / période / équilibre
poste l'écriture
```

---

# 41. Stocks

La valorisation des stocks relève de :

```text
InventoryValuationPolicy
```

Le futur bounded context `Inventory` ne doit pas être réduit à :

```text
if account.startswith("3"):
```

Les méthodes autorisées dépendent du référentiel et de la policy.

---

# 42. Continuité et changement de méthode

Un changement de contexte de continuité ou de méthode doit produire une trace de configuration.

```text
AccountingPolicySetChanged
```

et non une mutation silencieuse.

Exigences :

```text
old_policy_set
new_policy_set
effective_date
reason
actor
reference context
```

---

# 43. Permanence des méthodes et comparabilité

La permanence est traduite dans PyAccountingKit par une contrainte de gouvernance :

```text
same policy set
unless explicit change
```

et non par :

```text
policy can never change
```

Le corpus doctrinal souligne d'ailleurs que la permanence n'est pas absolue. fileciteturn14file8L1703-L1715

---

# 44. Règles de référentiel

## INV-REF-001 - Standard explicite

Une règle réglementaire doit être associée à :

```text
standard_id
edition
dataset_version
```

---

## INV-REF-002 - Pas d'équivalence par code seul

Le dataset de comparaison OHADA étudié désactive l'équivalence sémantique automatique fondée sur le code seul. fileciteturn15file7L1795-L1804

Classification :

```text
UNIVERSAL_DOMAIN_SAFETY_RULE
```

dans PyAccountingKit.

---

## INV-REF-003 - Mapping candidat non exécutable par défaut

```text
SUGGESTED / CANDIDATE
    !=
VALIDATED / EXECUTABLE
```

CFA FRA prévoit d'ailleurs une chaîne candidate -> suggestion -> validation humaine pour le mapping. fileciteturn15file4L988-L1007

---

# 45. Mappings de présentation

Le mapping d'un compte vers une ligne d'état n'est pas un invariant comptable.

Classification :

```text
PRESENTATION_RULE
```

Il doit pouvoir être :

```text
MANUAL
RULE
SUGGESTED
```

CFA FRA distingue ces types et conserve la validation. fileciteturn15file0L124-L163

---

# 46. Contrôles vs invariants

Une distinction stricte doit exister.

## Invariant

Si violé :

```text
l'état métier ne doit pas exister
ou
la transition doit échouer
```

Exemple :

```text
entry.posted and unbalanced
```

---

## Control

Si violé :

```text
le système produit un résultat de contrôle
```

et le `ClosingPolicy` ou une règle réglementaire décide éventuellement si cela bloque.

Exemple :

```text
cash-flow not reconciled
```

---

# 47. Sévérité des contrôles

```text
INFO
WARNING
ERROR
BLOCKING
```

La sévérité appartient à :

```text
ControlDefinition
```

et peut dépendre :

```text
standard
policy set
organization
process stage
```

---

# 48. Audit des mutations

CFA FRA prévoit notamment :

```text
ENTRY_CREATED
ENTRY_VALIDATED
ENTRY_POSTED
ENTRY_REVERSED
PERIOD_CLOSED
PERIOD_REOPENED
```

fileciteturn13file5L966-L998

PyAccountingKit doit auditer toute transition irréversible ou sensible.

---

# 49. AuditEvent vs DomainEvent

```text
DomainEvent
    = signal métier interne

AuditEvent
    = preuve durable d'une opération
```

Ils peuvent être liés mais ne sont pas interchangeables.

---

# 50. Immutabilité de l'audit

## INV-AUD-001

Un `AuditEvent` publié est append-only.

Toute correction d'audit produit un nouvel événement explicatif.

---

# 51. Traçabilité des policies

Lorsqu'une policy génère un montant ou une écriture :

```text
PolicyExecutionTrace
    ->
JournalEntry / Proposal
```

La trace doit permettre de reconstruire :

```text
policy
version
inputs
calculation
result
effective context
reference snapshot
```

---

# 52. Decimal obligatoire

CFA FRA impose l'usage de `Decimal` pour éviter les erreurs financières liées aux floats. fileciteturn13file6L1251-L1259

## INV-MONEY-001

```text
float
    prohibited
for accounting amounts
```

Classification :

```text
DOMAIN_SAFETY_INVARIANT
```

---

# 53. Arrondi

L'arrondi doit appartenir à une policy :

```text
RoundingPolicy
```

Exemples de paramètres :

```text
currency scale
calculation scale
rounding mode
round at line / entry / report
```

Classification :

```text
DOMAIN_POLICY
ou
REGULATORY_RULE
```

---

# 54. Money et devise

Une opération entre montants de devises différentes doit exiger une conversion explicite.

Interdit :

```python
Money(100, "EUR") + Money(100, "USD")
```

sans `ExchangeRate`.

---

# 55. Règles d'import

Les imports ne peuvent contourner les invariants.

CFA FRA importe le FEC après parsing, contrôles, mapping et normalisation, puis crée des écritures postées. fileciteturn15file8L1910-L1938

PyAccountingKit doit imposer conceptuellement :

```text
external data
    ->
normalize
    ->
JournalEntry
    ->
validate
    ->
post
```

même si l'adapter optimise techniquement le traitement.

---

# 56. Idempotence d'import

Le FEC de CFA FRA utilise :

```text
organization
+
fiscal_year
+
sha256
```

comme clé fonctionnelle d'idempotence. fileciteturn15file8L1963-L1987

PyAccountingKit généralise :

```text
ImportIdempotencyPolicy
```

Classification :

```text
DOMAIN_POLICY
```

---

# 57. Règles d'analyse financière

Les indicateurs :

```text
SIG
EBE
CAF
FRNG
BFR
ratios
scores
```

ne sont pas des invariants du ledger.

Classification :

```text
ANALYTICAL_DEFINITION
```

Un calcul analytique erroné ne doit jamais modifier une écriture postée.

---

# 58. Invariant Financial Analysis

## INV-ANL-001 - Read-only

```text
Financial Analysis
    cannot mutate
Accounting Core
```

Classification :

```text
ARCHITECTURAL_INVARIANT
```

---

# 59. Invariant de provenance analytique

Une valeur analytique finalisée doit pouvoir conserver :

```text
definition_version
source_snapshot
parameters
generated_at
```

Classification :

```text
DOMAIN_INVARIANT
du bounded context Financial Analysis
```

---

# 60. Règles spécifiques aux futurs bounded contexts

## Inventory

Règles futures :

```text
inventory recognition
valuation method
write-down
physical inventory adjustment
```

Classification :

```text
ACCOUNTING_METHOD
REGULATORY_RULE
```

---

## Fixed Assets

```text
capitalization
useful life
depreciation
impairment
disposal
```

Classification :

```text
ACCOUNTING_METHOD
REGULATORY_RULE
```

---

## Accruals & Provisions

```text
recognition threshold
measurement
review
reversal
```

Classification :

```text
ACCOUNTING_METHOD
REGULATORY_RULE
```

---

## Consolidation

```text
scope
control
eliminations
goodwill
minority interests
translation
```

Classification :

```text
REGULATORY_RULE
ACCOUNTING_METHOD
PRESENTATION_RULE
```

Les écritures de consolidation ne modifient pas le ledger statutaire.

---

# 61. `RuleScope`

Value Object proposé :

```text
RuleScope
|
+-- accounting_entity_id?
+-- standard_id?
+-- edition?
+-- journal_type?
+-- account_type?
+-- account_pattern?
+-- entry_type?
+-- fiscal_year?
+-- effective_date_range?
```

Le scope doit être explicite pour éviter des règles globales implicites.

---

# 62. `RuleResult`

Résultat standard :

```text
RuleResult
|
+-- rule_code
+-- passed
+-- severity
+-- message
+-- expected
+-- actual
+-- evidence
+-- object_refs
```

---

# 63. Registre initial des règles P0

| Code | Type | Enforcement | Bloquant |
|---|---|---|---|
| `ENTRY_BALANCED` | Universal invariant | Validate/Post | Oui |
| `ENTRY_MIN_LINES` | Domain policy | Validate/Post | Oui |
| `ENTRY_NON_ZERO` | Domain policy | Validate/Post | Oui |
| `LINE_DEBIT_OR_CREDIT` | Universal invariant | Validate/Post | Oui |
| `LINE_NON_NEGATIVE` | Universal invariant | Create/Validate | Oui |
| `ACCOUNT_EXISTS` | Domain invariant | Validate/Post | Oui |
| `ACCOUNT_ACTIVE` | Domain policy | Validate/Post | Oui |
| `ACCOUNT_POSTABLE` | Domain policy | Validate/Post | Oui |
| `JOURNAL_ACTIVE` | Domain policy | Validate/Post | Oui |
| `DATE_WITHIN_PERIOD` | Domain policy | Validate/Post | Oui |
| `PERIOD_ACCEPTS_POSTING` | Domain policy | Post | Oui |
| `SAME_ACCOUNTING_ENTITY` | Universal invariant | Validate/Post | Oui |
| `VALIDATED_BEFORE_POST` | Domain policy | Post | Oui |
| `POSTED_IMMUTABLE` | Universal domain invariant | Update/Delete | Oui |
| `REVERSAL_LINK_REQUIRED` | Domain invariant | Reverse | Oui |
| `REVERSAL_PRESERVES_ORIGINAL` | Universal domain invariant | Reverse | Oui |
| `DECIMAL_ONLY` | Domain safety invariant | All | Oui |
| `NO_CODE_ONLY_SEMANTIC_EQUIVALENCE` | Domain safety rule | Mapping | Oui |
| `CANDIDATE_MAPPING_NOT_EXECUTABLE` | Domain safety rule | Reporting | Oui |

---

# 64. Registre initial des policies P0/P1

| Code | Catégorie | Priorité |
|---|---|---|
| `PERIODIC_ACCOUNTING_POLICY` | Accounting method | P0 |
| `ACCRUAL_MATCHING_POLICY` | Accounting method | P1 |
| `GOING_CONCERN_CONTEXT` | Accounting method | P1 |
| `CONSISTENCY_POLICY` | Accounting method | P0 |
| `MEASUREMENT_BASIS_POLICY` | Accounting method | P0 |
| `ROUNDING_POLICY` | Domain policy | P0 |
| `ENTRY_NUMBERING_POLICY` | Domain / regulatory | P0 |
| `REVERSAL_DATE_POLICY` | Domain policy | P0 |
| `CLOSING_POLICY` | Domain policy | P1 |
| `OPENING_BALANCE_POLICY` | Domain policy | P1 |
| `DEPRECIATION_POLICY` | Accounting method | P1/P2 |
| `IMPAIRMENT_POLICY` | Accounting method | P1/P2 |
| `PROVISION_POLICY` | Accounting method | P1 |
| `INVENTORY_VALUATION_POLICY` | Accounting method | P1/P2 |

---

# 65. Erreurs métier

Hiérarchie proposée :

```text
AccountingRuleError
|
+-- EntryRuleError
|   +-- UnbalancedEntryError
|   +-- InsufficientEntryLinesError
|   +-- ZeroEntryError
|   +-- InvalidEntryStateError
|
+-- JournalLineRuleError
|   +-- NegativeAmountError
|   +-- DebitAndCreditSetError
|   +-- ZeroLineError
|
+-- PeriodRuleError
|   +-- DateOutsidePeriodError
|   +-- ClosedPeriodError
|
+-- AccountRuleError
|   +-- UnknownAccountError
|   +-- InactiveAccountError
|   +-- NonPostableAccountError
|
+-- ReversalRuleError
|   +-- EntryNotPostedError
|   +-- AlreadyReversedError
|   +-- InvalidReversalDateError
|
+-- PolicyRuleError
|   +-- PolicyNotApplicableError
|   +-- UnknownPolicyVersionError
|
+-- ReferenceRuleError
    +-- NonExecutableMappingError
    +-- SemanticEquivalenceNotValidatedError
```

---

# 66. Fail-closed

Pour les règles comptables critiques :

```text
unknown
ambiguous
unvalidated
```

doit produire :

```text
explicit failure
```

et non :

```text
best guess
```

Exemples :

```text
unknown policy
unvalidated mapping
unknown exchange rate
ambiguous period
```

---

# 67. Tests unitaires d'invariants

Minimum :

```text
test_unbalanced_entry_cannot_validate
test_unbalanced_entry_cannot_post

test_line_cannot_have_both_debit_and_credit
test_line_amount_cannot_be_negative

test_entry_requires_minimum_lines_for_validation

test_post_requires_validated_status

test_posted_entry_is_immutable

test_closed_period_rejects_posting

test_entry_accounts_must_belong_to_same_entity

test_reversal_preserves_original
test_reversal_swaps_debit_credit
test_reversal_links_original

test_float_is_not_accepted_as_accounting_amount
```

---

# 68. Property-based tests

Les invariants se prêtent fortement aux tests de propriétés.

Exemples :

```text
for any balanced entry:
    total_debit == total_credit

for any posted entry:
    mutation attempts fail

for any complete reversal:
    original + reversal net movement == 0

for any trial balance built from balanced posted entries:
    total_debit == total_credit
```

---

# 69. Golden tests CFA FRA

Les comportements CFA FRA doivent devenir des scénarios de parité.

Le plan MVP demande notamment qu'une écriture déséquilibrée ne puisse pas être postée, qu'une écriture postée ne puisse pas être modifiée, qu'une extourne puisse être générée et qu'une période fermée bloque le posting. fileciteturn14file2L574-L600

Ces quatre comportements constituent des golden tests P0.

---

# 70. Tests des principes doctrinaux

Les principes tels que prudence, continuité ou permanence ne doivent pas être testés comme :

```text
global boolean invariant
```

Ils doivent être testés via les policies qui les implémentent.

Exemple :

```text
given ImpairmentPolicy version X
when inputs Y
then expected measurement Z
and expected PolicyExecutionTrace
```

---

# 71. Tests de changement de policy

Scénario :

```text
PolicySet v1 active until 2026-12-31
PolicySet v2 active from 2027-01-01
```

Le moteur doit sélectionner :

```text
v1
for 2026 accounting context

v2
for 2027 accounting context
```

et conserver la version utilisée.

---

# 72. Tests de sécurité réglementaire

Minimum :

```text
same account code across two standards
    must not imply semantic equivalence

candidate mapping
    must not execute if validation is required

expired policy
    must not execute outside validity period
```

---

# 73. Exemple - vente simple

```text
Debit 411... Client        1 200
Credit 706... Revenue      1 000
Credit VAT account           200
```

Le framework vérifie :

```text
debit = 1 200
credit = 1 200
```

mais la sélection exacte des comptes dépend :

```text
CompanyChartOfAccounts
Reference bindings
AccountingPolicySet
```

Le coeur ne code pas les numéros en dur.

---

# 74. Exemple - adjustment généré par policy

```text
Period-end event
    |
    v
AccrualPolicy
    |
    v
MeasurementResult = 10 000
    |
    v
JournalEntryProposal
    |
    v
Validate
    |
    v
Post
```

Le `PolicyExecutionTrace` conserve :

```text
policy version
input evidence
amount
date
generated entry id
```

---

# 75. Exemple - prudence sans règle universelle

Incorrect :

```python
if prudence:
    create_provision()
```

Correct :

```text
ProvisionRecognitionPolicy
    evaluates facts

ProvisionMeasurementPolicy
    computes amount

JournalEntryProposal
    generated

PostingEngine
    validates and posts
```

---

# 76. Exemple - permanence des méthodes

Incorrect :

```text
method can never change
```

Correct :

```text
PolicySet v1
    |
    | explicit, justified, audited transition
    v
PolicySet v2
```

avec :

```text
effective date
reason
actor
provenance
```

---

# 77. Exemple - reporting

Un mapping :

```text
CompanyAccount
    ->
StatementLine
```

n'est pas une règle de partie double.

Il appartient à :

```text
PRESENTATION_RULE
```

et peut être versionné indépendamment du ledger.

---

# 78. Exemple - Financial Analysis

```text
TrialBalance
    ->
FinancialStatement
    ->
IndicatorDefinition
    ->
EBE / CAF / Ratio
```

Un changement de formule analytique :

```text
does not alter
JournalEntry
```

---

# 79. ADRs du document

| ID | Décision |
|---|---|
| ADR-RULE-001 | Toutes les règles sont typées par `RuleKind` |
| ADR-RULE-002 | `SUM(debit) = SUM(credit)` est un invariant du moteur |
| ADR-RULE-003 | Débit et crédit simultanément positifs sur une ligne sont interdits |
| ADR-RULE-004 | `POSTED` est immutable |
| ADR-RULE-005 | Les corrections passent par reversal + replacement |
| ADR-RULE-006 | Posting normal interdit sur période fermée |
| ADR-RULE-007 | Les principes de prudence, continuité et permanence ne sont pas des invariants universels |
| ADR-RULE-008 | Le rattachement est une accounting method/policy |
| ADR-RULE-009 | Les bases de mesure appartiennent à `MeasurementPolicy` |
| ADR-RULE-010 | Toute policy exécutable est versionnée |
| ADR-RULE-011 | Toute policy automatisée doit être explicable par `PolicyExecutionTrace` |
| ADR-RULE-012 | Les imports ne contournent pas les règles de validation/posting |
| ADR-RULE-013 | Les mappings candidats ne sont pas exécutables par défaut |
| ADR-RULE-014 | L'égalité de code ne prouve pas l'équivalence sémantique |
| ADR-RULE-015 | Les états financiers et balances sont des projections |
| ADR-RULE-016 | Les définitions analytiques ne sont pas des règles comptables transactionnelles |
| ADR-RULE-017 | `Decimal` est obligatoire pour les montants comptables |
| ADR-RULE-018 | Les règles critiques suivent une stratégie fail-closed |

---

# 80. Critères d'acceptation P0.4

Le document est considéré correctement traduit dans le framework lorsque :

```text
[ ] RuleKind existe

[ ] les invariants P0 possèdent un code stable

[ ] une écriture déséquilibrée ne peut être validée/postée

[ ] une ligne ne peut avoir débit et crédit positifs simultanément

[ ] une écriture postée est immutable

[ ] une reversal crée une nouvelle écriture reliée à l'original

[ ] l'original reste inchangé

[ ] une période fermée bloque le posting normal

[ ] tous les objets transactionnels sont scopés par AccountingEntityId

[ ] les comptes et journaux doivent être actifs selon policy

[ ] Decimal est imposé

[ ] prudence n'est pas codée comme booléen global du Posting Engine

[ ] continuité ne détermine pas automatiquement une base de mesure

[ ] permanence est gérée par versioning / migration de policies

[ ] rattachement est implémentable par AccrualPolicy / MatchingPolicy

[ ] les mappings non validés sont fail-closed

[ ] les projections restent reconstructibles depuis les lignes postées

[ ] les tests unitaires / property tests couvrent les invariants

[ ] les golden tests CFA FRA couvrent posting, immutabilité, reversal et période fermée
```

---

# 81. Impacts sur les prochains documents

Ce document fixe les règles générales.

Il prépare directement :

```text
04_PYACCOUNTINGKIT_ACCOUNTING_POLICIES_RECOGNITION_AND_MEASUREMENT_ARCHITECTURE.md
```

qui devra détailler :

```text
AccountingPolicySet
RecognitionPolicy
MeasurementPolicy
PolicyApplicability
PolicyResolution
PolicyExecutionTrace
measurement bases
rounding
policy migration
```

Puis :

```text
05_PYACCOUNTINGKIT_ACCOUNTING_REFERENCE_DATA_ARCHITECTURE.md
```

qui devra préciser quelles règles proviennent du référentiel et comment leur version/provenance est conservée.

---

# 82. Conclusion

PyAccountingKit doit être strict sur ce qui constitue réellement un invariant et flexible sur ce qui constitue une méthode.

Le coeur protège :

```text
partie double
cohérence des lignes
cohérence d'entité
cycle de vie
immutabilité
reversal
périodes
traçabilité
Decimal
```

Les policies traitent :

```text
rattachement
mesure
prudence
continuité
permanence
amortissement
dépréciation
provisions
stocks
clôture
arrondi
numérotation
```

Les référentiels définissent :

```text
règles réglementaires
présentations
applicabilité
standards / éditions
```

Les contrôles vérifient :

```text
équilibres
réconciliations
conditions de clôture
qualité
```

Et l'analyse financière reste un read-side :

```text
SIG
CAF
FRNG
BFR
ratios
diagnostics
```

La règle d'architecture centrale devient donc :

```text
Invariant
    !=
Policy
    !=
Regulatory Rule
    !=
Presentation Rule
    !=
Control
    !=
Analytical Definition
```

---

**Prochain document recommandé :**

```text
04_PYACCOUNTINGKIT_ACCOUNTING_POLICIES_RECOGNITION_AND_MEASUREMENT_ARCHITECTURE.md
```
