# 06 - PyAccountingKit - Architecture du plan comptable d'entreprise et de la codification

> **Projet** : PyAccountingKit  
> **Document** : `06_PYACCOUNTINGKIT_COMPANY_CHART_OF_ACCOUNTS_AND_NUMBERING_ARCHITECTURE.md`  
> **Documents parents** :
> - `00_PYACCOUNTINGKIT_REQUIREMENTS_ANALYSIS.md`
> - `01_PYACCOUNTINGKIT_PROJECT_VISION_AND_ARCHITECTURE.md`
> - `02_PYACCOUNTINGKIT_DOMAIN_MODEL_AND_BOUNDED_CONTEXTS.md`
> - `03_PYACCOUNTINGKIT_ACCOUNTING_RULES_AND_INVARIANTS.md`
> - `04_PYACCOUNTINGKIT_ACCOUNTING_POLICIES_RECOGNITION_AND_MEASUREMENT_ARCHITECTURE.md`
> - `05_PYACCOUNTINGKIT_ACCOUNTING_REFERENCE_DATA_ARCHITECTURE.md`
> **Statut** : P0.7 - Architecture du `Company Chart of Accounts` et de la codification  
> **Langue** : Français  
> **Objet** : Définir la transformation d'un référentiel réglementaire en plan comptable d'entreprise, la modélisation des comptes d'entreprise, les politiques de codification de longueur fixe ou variable, la segmentation, les auxiliaires, les règles de génération, les bindings réglementaires et les contraintes permettant d'éviter de transformer une convention de plan comptable en invariant universel.

---

# 1. Résumé exécutif

Le plan comptable réglementaire et le plan comptable d'une organisation sont deux objets différents.

```text
ReferenceAccountPlan
        |
        v
CompanyChartGenerationPolicy
        |
        v
CompanyChartOfAccounts
        |
        v
CompanyAccount
        |
        v
RegulatoryAccountBinding
        |
        v
ReferenceAccount
```

Un référentiel fournit notamment :

```text
une structure
des identifiants réglementaires
des codes de référence
des libellés
une hiérarchie
des comptes obligatoires / optionnels
des règles ou informations réglementaires
```

Une organisation doit pouvoir ajouter :

```text
sa propre longueur de compte
sa segmentation
ses sous-comptes
ses auxiliaires
ses codes banques
ses codes tiers
ses centres ou dimensions
ses conventions internes
```

PyAccountingKit ne doit donc jamais supposer :

```text
tous les comptes ont 6 chiffres

tous les comptes ont 8 chiffres

tous les comptes ont 9 chiffres

un code réglementaire est directement le code d'entreprise

la longueur du code définit sa sémantique

un préfixe donné a le même sens dans tous les référentiels

un zéro final possède partout la même signification
```

La règle centrale est :

```text
Reference Account
    = identité réglementaire

Company Account
    = identité opérationnelle de l'organisation

Account Code Policy
    = manière de construire / valider les codes d'entreprise
```

---

# 2. Apport doctrinal sur la codification

Le corpus comptable confirme que les conventions de codification sont liées au plan considéré.

Le plan comptable français décrit dans l'ouvrage utilise une **structure décimale** où le premier chiffre correspond à la classe et où les subdivisions reprennent le préfixe du compte parent.

Le même ouvrage présente également cette structure comme **adaptable**, avec plusieurs niveaux de développement et des compléments de codification indicatifs.

Il précise enfin que des groupes utilisant une classification par fonctions peuvent adopter une codification propre à l'entreprise, différente de la codification traditionnelle par nature.

La conséquence pour PyAccountingKit est fondamentale :

```text
les conventions numériques observées
dans un référentiel donné
ne deviennent jamais
des invariants universels du framework
```

---

# 3. Objectifs

Le bounded context `Company Chart of Accounts` doit permettre de :

1. créer un plan d'entreprise à partir d'un référentiel ;
2. préserver la liaison avec les comptes réglementaires ;
3. utiliser des codes d'entreprise de 6, 8, 9, 10 ou N caractères ;
4. utiliser une longueur fixe ou variable ;
5. supporter des schémas segmentés ;
6. supporter des codes numériques ou alphanumériques ;
7. spécialiser la longueur par famille de comptes ;
8. gérer les comptes collectifs ;
9. gérer la comptabilité auxiliaire ;
10. distinguer compte général et sous-ledger ;
11. permettre la création manuelle de comptes ;
12. garantir l'unicité et l'absence de cycles ;
13. versionner le plan ;
14. migrer le plan sans réécrire l'historique ;
15. permettre des stratégies de génération automatiques mais contrôlées ;
16. empêcher les inférences sémantiques non garanties par le référentiel.

---

# 4. Non-objectifs

Ce document ne définit pas :

```text
le Posting Engine
les règles détaillées de clôture
les règles FEC
les états financiers
les policies d'évaluation
la gestion complète des tiers
la gestion complète des immobilisations
la consolidation
```

Ces domaines consomment le plan comptable mais ne lui appartiennent pas.

---

# 5. Position dans l'architecture

```text
Accounting Reference Data
        |
        v
ReferenceAccountPlan
        |
        v
Company Chart of Accounts
        |
        +--> AccountCodePolicy
        +--> CompanyAccount
        +--> RegulatoryAccountBinding
        +--> AuxiliaryAccountingPolicy
        |
        v
Journal & Entries
        |
        v
Posting & Ledger
```

---

# 6. Distinction entre référentiel et plan d'entreprise

## Référentiel

```text
ReferenceAccount
|
+-- reference_account_id
+-- standard_id
+-- edition
+-- ref_code
+-- label
+-- parent_reference_account_id
```

## Plan d'entreprise

```text
CompanyAccount
|
+-- company_account_id
+-- chart_id
+-- code
+-- label
+-- parent_company_account_id?
+-- posting_allowed
+-- active
+-- reference_binding?
```

---

# 7. Exemple simple

Référence :

```text
account:fr-pcg:2026:512
code réglementaire : 512
label : Banques
```

Entreprise A :

```text
512001
```

Entreprise B :

```text
51200001
```

Entreprise C :

```text
512000001
```

Entreprise D :

```text
512-BNP-EUR
```

Les quatre peuvent être liés au même compte de référence lorsque leur configuration et leur mapping l'autorisent.

---

# 8. Principe : le code est une chaîne

```python
AccountCode = str
```

Jamais :

```python
AccountCode = int
```

Raisons :

```text
préserver les zéros
supporter l'alphanumérique
supporter les segments
éviter toute arithmétique accidentelle
```

---

# 9. Value Object - `AccountCode`

```text
AccountCode
|
+-- value
```

Invariants minimaux :

```text
non vide
trimmed selon policy
longueur autorisée
charset autorisé
format autorisé
```

---

# 10. `CompanyChartOfAccounts`

Aggregate Root de métadonnées :

```text
CompanyChartOfAccounts
|
+-- id
+-- accounting_entity_id
+-- code
+-- label
+-- version
+-- status
+-- reference_snapshot
+-- primary_standard?
+-- code_policy_id
+-- effective_from
+-- effective_to?
+-- metadata
```

---

# 11. Pourquoi le Chart ne contient pas tous les comptes comme enfants d'agrégat

Un plan peut contenir :

```text
100 comptes
1 000 comptes
10 000 comptes
100 000 comptes
```

Charger tous les comptes dans un aggregate unique serait coûteux et inutile.

Décision :

```text
CompanyChartOfAccounts
    = aggregate de configuration / version

CompanyAccount
    = aggregate root indépendant
```

---

# 12. Statuts du chart

```text
DRAFT
ACTIVE
SUPERSEDED
ARCHIVED
```

---

# 13. Version du chart

Chaque modification structurelle significative peut produire :

```text
CompanyChartVersion
```

Exemple :

```text
chart v1
    2026-01-01 -> 2026-12-31

chart v2
    2027-01-01 -> ...
```

---

# 14. `CompanyAccount`

```text
CompanyAccount
|
+-- id
+-- accounting_entity_id
+-- chart_id
+-- code
+-- label
+-- parent_account_id?
+-- account_kind
+-- posting_allowed
+-- active
+-- valid_from
+-- valid_to?
+-- normal_balance?
+-- metadata
```

---

# 15. `CompanyAccountKind`

Premières valeurs :

```text
GENERAL
COLLECTIVE
AUXILIARY
MEMO
CONTROL
CUSTOM
```

La liste doit rester extensible.

---

# 16. Invariant - unicité du code

Dans un chart donné :

```text
(chart_id, account_code)
```

doit être unique.

---

# 17. Invariant - même chart pour parent/enfant

```text
child.chart_id
=
parent.chart_id
```

---

# 18. Invariant - absence de cycle

Interdit :

```text
A -> B -> C -> A
```

---

# 19. Invariant - pas d'auto-parent

```text
account.parent_account_id != account.id
```

---

# 20. Invariant - compte actif pour posting

Par défaut :

```text
active == true
```

pour recevoir un mouvement.

Cette exigence est contrôlée par le Posting Engine.

---

# 21. Invariant - compte postable

Un noeud organisationnel peut être non postable.

```text
posting_allowed = false
```

Exemple :

```text
512 - Banques
    |
    +-- 512001 - BNP
    +-- 512002 - SG
```

Le parent peut être non postable et les feuilles postables.

---

# 22. Compte parent et code

PyAccountingKit ne doit pas imposer universellement :

```text
child.code.startswith(parent.code)
```

Cette relation peut être requise par une `AccountCodePolicy`.

---

# 23. Pourquoi

Dans certains plans :

```text
la hiérarchie est codée dans le numéro
```

Dans d'autres :

```text
la hiérarchie est explicite
et le code n'est qu'une clé
```

Le framework doit supporter les deux.

---

# 24. `AccountCodePolicy`

Port / stratégie principale :

```python
class AccountCodePolicy(Protocol):

    def validate(
        self,
        code: AccountCode,
        context: AccountCodeContext,
    ) -> AccountCodeValidationResult:
        ...

    def generate(
        self,
        request: AccountCodeGenerationRequest,
    ) -> AccountCode:
        ...
```

---

# 25. Capacités d'une policy de code

```text
charset
min_length
max_length
fixed_length
segments
separator
padding
prefix rules
suffix rules
reserved patterns
parent-child rule
generation strategy
```

---

# 26. `AccountCodeContext`

```text
AccountCodeContext
|
+-- chart_id
+-- account_kind
+-- parent_account?
+-- reference_account?
+-- account_family?
+-- auxiliary_type?
+-- metadata
```

---

# 27. Types initiaux de policies

```text
NumericFixedLengthPolicy

NumericVariableLengthPolicy

SegmentedNumericPolicy

AlphanumericPolicy

ReferenceCompatiblePolicy

CompositeAccountCodePolicy

CustomAccountCodePolicy
```

---

# 28. `NumericFixedLengthPolicy`

Exemple :

```text
length = 8
charset = digits
```

Codes valides :

```text
51200001
40100015
60610000
```

---

# 29. Exemple 6 chiffres

```text
length = 6

512001
401001
606100
```

---

# 30. Exemple 9 chiffres

```text
length = 9

512000001
401000123
606100001
```

---

# 31. `NumericVariableLengthPolicy`

Exemple :

```text
min_length = 3
max_length = 12
```

Codes possibles :

```text
512
51201
512010001
```

La longueur n'est plus un invariant du chart.

---

# 32. `SegmentedNumericPolicy`

Exemple :

```text
512 | 01 | 0001
```

ou :

```text
512-01-0001
```

---

# 33. `AccountCodeSegment`

```text
AccountCodeSegment
|
+-- name
+-- length?
+-- min_length?
+-- max_length?
+-- charset
+-- required
+-- semantic_role?
+-- allowed_values?
```

---

# 34. Exemple de segmentation

```text
REFERENCE_ROOT : 3
ENTITY_SUBCODE : 2
DETAIL         : 4
```

Code :

```text
512010001
```

Représentation :

```text
512 | 01 | 0001
```

---

# 35. Segment séparateur

Le stockage canonique peut être :

```text
512010001
```

et l'affichage :

```text
512-01-0001
```

ou inversement.

La policy détermine :

```text
canonical format
display format
```

---

# 36. `AlphanumericPolicy`

Exemples :

```text
BANK-BNP-EUR
SUP-000123
CASH-PARIS-01
```

Le domaine ne doit pas supposer un code numérique.

---

# 37. Charset

Valeurs possibles :

```text
NUMERIC
ALPHABETIC
ALPHANUMERIC
CUSTOM_REGEX
```

---

# 38. Validation par regex

Une implementation custom peut utiliser :

```text
^[A-Z]{3}-\d{6}$
```

mais le regex reste une implementation de policy, pas un invariant du domaine.

---

# 39. Longueur par famille

Une entreprise peut imposer :

```text
comptes généraux : 6

clients : 9

fournisseurs : 9

banques : 8

immobilisations : 10
```

Le framework doit supporter cela.

---

# 40. `CompositeAccountCodePolicy`

```text
CompositeAccountCodePolicy
|
+-- rules
```

Chaque règle :

```text
if applicability matches
    use specific policy
```

---

# 41. `AccountCodePolicyBinding`

```text
AccountCodePolicyBinding
|
+-- applicability
+-- policy_id
+-- policy_version
+-- priority
```

---

# 42. Applicability

Exemples :

```text
account_kind == GENERAL

reference_root == 401

account_role == CUSTOMER

account_role == SUPPLIER

auxiliary_type == CUSTOMER

reference_concept == CASH
```

Les conditions basées sur un concept ne sont exécutables que si le binding conceptuel est validé.

---

# 43. Ne pas inférer un rôle via préfixe dans le core

Interdit :

```python
if code.startswith("401"):
    account_role = SUPPLIER
```

dans le domaine générique.

---

# 44. Usage autorisé du préfixe

Un préfixe peut être utilisé dans :

```text
ReferenceSpecificRule

CompanyAccountCodePolicy

SuggestionStrategy

MigrationHeuristic
```

lorsque son scope est explicite.

---

# 45. `ReferenceCompatiblePolicy`

Cas fréquent :

```text
CompanyAccount.code
commence par
ReferenceAccount.ref_code
```

Exemple :

```text
Reference 512

Company 51200101
```

Cette compatibilité peut être configurée mais n'est pas universelle.

---

# 46. Modes de génération du plan

```text
REFERENCE_ONLY

PAD_TO_LENGTH

TEMPLATE_EXPANSION

RULE_BASED_EXPANSION

MANUAL

CUSTOM
```

---

# 47. `REFERENCE_ONLY`

Le système crée uniquement des comptes correspondant aux comptes de référence sélectionnés.

Exemple :

```text
ReferenceAccount 512
    ->
CompanyAccount 512
```

Ce mode est le plus prudent.

---

# 48. `PAD_TO_LENGTH`

Exemple :

```text
reference = 512
target_length = 8
padding = right
padding_char = 0

result = 51200000
```

---

# 49. Danger du padding

`PAD_TO_LENGTH` n'est autorisé que si la policy d'entreprise le permet.

Il ne doit jamais être le comportement universel par défaut.

---

# 50. `TEMPLATE_EXPANSION`

Exemple :

```text
reference_code = 512

template =
{reference}{bank_code:02}{sequence:03}
```

Résultat :

```text
51201001
```

---

# 51. `RULE_BASED_EXPANSION`

Exemple :

```text
for each configured bank:
    create account
```

Le framework reçoit des données d'entreprise et une policy.

Il ne crée pas automatiquement des banques ou tiers fictifs.

---

# 52. Mode par défaut recommandé

Pour P0 :

```text
REFERENCE_ONLY
```

avec création manuelle ou contrôlée des subdivisions.

---

# 53. `CompanyChartGenerationPolicy`

```text
CompanyChartGenerationPolicy
|
+-- source_selection
+-- inclusion_policy
+-- code_policy
+-- label_policy
+-- hierarchy_policy
+-- posting_policy
+-- binding_policy
+-- expansion_rules
```

---

# 54. `CompanyChartGenerationRequest`

```text
CompanyChartGenerationRequest
|
+-- accounting_entity_id
+-- reference_snapshot_id
+-- standard_id
+-- edition
+-- source_plan
+-- generation_policy
+-- desired_effective_date
```

---

# 55. `CompanyChartGenerator`

```python
class CompanyChartGenerator:

    def generate(
        self,
        request: CompanyChartGenerationRequest,
    ) -> CompanyChartGenerationResult:
        ...
```

---

# 56. `CompanyChartGenerationResult`

```text
CompanyChartGenerationResult
|
+-- chart
+-- accounts
+-- bindings
+-- warnings
+-- skipped_reference_nodes
+-- generation_trace
```

---

# 57. Sélection des comptes de référence

La source peut exposer :

```text
minimum account
optional account
class
group
account
```

La policy décide ce qui devient un `CompanyAccount`.

---

# 58. Un noeud de groupe n'est pas nécessairement un compte postable

Exemple :

```text
ReferenceNode
node_type = group
```

peut devenir :

```text
CompanyAccount
posting_allowed = false
```

ou ne pas être matérialisé selon la policy.

---

# 59. `ReferenceNodeInclusionPolicy`

```text
INCLUDE_ALL_ACCOUNTS

MINIMUM_PLAN_ONLY

POSTABLE_LEAVES_ONLY

CONFIGURED_SELECTION

CUSTOM
```

---

# 60. Inclusion et effective plan

Si `AccountingReferenceData` expose un effective plan :

```text
CompanyChartGenerator
```

doit travailler sur ce plan résolu.

Il ne rejoue pas les overlays.

---

# 61. `RegulatoryAccountBinding`

Chaque `CompanyAccount` peut être lié à un compte de référence.

```text
RegulatoryAccountBinding
|
+-- company_account_id
+-- reference_account_id
+-- reference_snapshot_id
+-- status
+-- binding_type
+-- provenance
```

---

# 62. Relation 1:N

Un compte réglementaire peut être relié à plusieurs comptes d'entreprise.

```text
ReferenceAccount 512
    |
    +--> CompanyAccount 512001
    +--> CompanyAccount 512002
    +--> CompanyAccount 512003
```

---

# 63. Relation N:1 côté entreprise

Par défaut, un compte d'entreprise possède un binding réglementaire principal.

Des mappings multiples peuvent être nécessaires pour :

```text
multi-standard reporting
migration
consolidation
```

Ils doivent être explicitement typés.

---

# 64. `BindingPurpose`

```text
PRIMARY_STATUTORY
SECONDARY_REPORTING
MIGRATION
CONSOLIDATION
ANALYTICAL
CUSTOM
```

---

# 65. Primary binding

Le chart doit pouvoir déclarer :

```text
primary_reference_standard
```

mais ne doit pas empêcher des mappings secondaires.

---

# 66. Binding immuable historiquement

Une écriture ancienne doit rester explicable avec le mapping applicable à sa date.

Une modification de binding doit être versionnée.

---

# 67. `RegulatoryAccountBindingVersion`

```text
RegulatoryAccountBindingVersion
|
+-- binding_id
+-- version
+-- effective_from
+-- effective_to?
+-- reference_account_id
```

---

# 68. Label du compte

Le label d'entreprise peut être différent du label réglementaire.

Exemple :

```text
Reference:
    512 - Banques

Company:
    512001 - BNP Paribas EUR
```

---

# 69. `AccountLabelPolicy`

Modes :

```text
COPY_REFERENCE_LABEL

REFERENCE_LABEL_PLUS_SUFFIX

COMPANY_DEFINED

TEMPLATE
```

---

# 70. Le label réglementaire reste accessible

Même si le label entreprise change :

```text
CompanyAccount
    |
    v
RegulatoryAccountBinding
    |
    v
ReferenceAccount.label
```

---

# 71. Comptes collectifs

Un compte collectif représente un regroupement de tiers ou sous-ledgers.

Exemple conceptuel :

```text
Trade Receivables Control Account
```

---

# 72. `CollectiveAccount`

Concept métier :

```text
CompanyAccount
account_kind = COLLECTIVE
```

avec policy :

```text
AuxiliaryAccountingPolicy
```

---

# 73. Comptabilité auxiliaire

Trois modes initiaux :

```text
SUBLEDGER

EXTENDED_ACCOUNT_CODE

HYBRID
```

---

# 74. Mode `SUBLEDGER`

```text
41100000
    = compte collectif

Customer subledger
    + customer A
    + customer B
    + customer C
```

Les codes clients n'allongent pas le compte général.

---

# 75. Mode `EXTENDED_ACCOUNT_CODE`

```text
411000001
411000002
411000003
```

Chaque tiers possède un compte général détaillé.

---

# 76. Mode `HYBRID`

```text
41100000
    = compte collectif

+
subledger detail

+
quelques comptes détaillés spéciaux
```

---

# 77. `AuxiliaryAccountingPolicy`

```text
AuxiliaryAccountingPolicy
|
+-- mode
+-- control_account_roles
+-- auxiliary_code_policy
+-- reconciliation_required
```

---

# 78. Les tiers ne sont pas des comptes réglementaires

Un client :

```text
Customer
```

n'est pas :

```text
ReferenceAccount
```

La comptabilité auxiliaire doit rester distincte.

---

# 79. `AuxiliaryAccountReference`

```text
AuxiliaryAccountReference
|
+-- auxiliary_type
+-- auxiliary_id
+-- control_company_account_id
```

---

# 80. Types auxiliaires

```text
CUSTOMER
SUPPLIER
EMPLOYEE
MEMBER
PARTNER
OTHER
```

Le framework ne doit pas imposer tous ces sous-ledgers en P0.

---

# 81. Séquence de génération client en `EXTENDED_ACCOUNT_CODE`

Exemple :

```text
reference root = 411
company root = 411000

customer sequence = 123

result = 411000123
```

La logique appartient à une policy explicite.

---

# 82. `AccountSequenceProvider`

Port éventuel :

```python
class AccountSequenceProvider(Protocol):

    def next_sequence(
        self,
        scope: AccountSequenceScope,
    ) -> str:
        ...
```

---

# 83. Concurrence de génération

La génération séquentielle doit résister à :

```text
deux créations simultanées
```

La garantie d'unicité est appliquée au niveau repository / transaction.

---

# 84. Collision

Si le code généré existe :

```text
AccountCodeCollisionError
```

Le moteur ne doit pas écraser le compte existant.

---

# 85. Séquences avec trous

Le domaine ne doit pas exiger :

```text
aucun trou numérique
```

sauf policy spécifique.

---

# 86. Réutilisation de code

Par défaut, un code historique désactivé ne doit pas être réattribué automatiquement.

Policy :

```text
AccountCodeReusePolicy
```

---

# 87. `AccountCodeReusePolicy`

Modes :

```text
NEVER

AFTER_ARCHIVAL

AFTER_RETENTION_PERIOD

EXPLICIT_APPROVAL
```

---

# 88. Désactivation

Un compte utilisé historiquement n'est pas supprimé.

Il devient :

```text
active = false
```

---

# 89. Suppression

La suppression physique n'est permise que si :

```text
compte jamais utilisé
et
aucune référence métier
```

selon repository policy.

---

# 90. `AccountUsagePort`

Le domaine peut vérifier :

```text
has_posted_entries(account_id)
```

sans dépendre de SQL.

---

# 91. Renommage

Un label peut être renommé selon policy.

Un code doit être traité beaucoup plus strictement.

---

# 92. Changement de code

Un changement de code sur un compte utilisé doit idéalement passer par :

```text
new CompanyAccount
+
migration / mapping
```

plutôt qu'une mutation historique silencieuse.

---

# 93. `AccountMigrationPlan`

```text
AccountMigrationPlan
|
+-- source_account_id
+-- target_account_id
+-- effective_date
+-- reason
+-- mapping
```

---

# 94. Versioning du chart

La migration globale :

```text
Chart v1
    ->
ChartMigrationPlan
    ->
Chart v2
```

---

# 95. `CompanyChartMigrationPlan`

```text
CompanyChartMigrationPlan
|
+-- source_chart_version
+-- target_chart_version
+-- effective_date
+-- account_mappings
+-- added_accounts
+-- retired_accounts
+-- code_changes
+-- binding_changes
+-- warnings
```

---

# 96. Référentiel mis à jour

Pipeline :

```text
ReferenceSnapshot v1
    |
    v
CompanyChart v1

new ReferenceSnapshot v2
    |
    v
ReferenceUpgradeImpact
    |
    v
CompanyChartMigrationPlan
    |
    v
CompanyChart v2
```

---

# 97. Aucun auto-upgrade silencieux

Un nouveau PCG ou un nouveau SYSCOHADA ne mute pas automatiquement :

```text
CompanyChartOfAccounts
```

---

# 98. Règles de prefix

Une convention telle que :

```text
class = first digit
```

peut exister dans une policy de référence.

Elle n'appartient pas à l'invariant de `AccountCode`.

---

# 99. Exemple PCG-specific

Une policy spécifique au PCG peut valider :

```text
reference account code
uses decimal hierarchical prefixes
```

mais cette règle doit être portée par :

```text
ReferenceSpecificAccountCodeRule
```

---

# 100. `ReferenceSpecificAccountCodeRule`

```text
ReferenceSpecificAccountCodeRule
|
+-- standard_id
+-- edition?
+-- rule_id
+-- validator
+-- provenance
```

---

# 101. Terminaison significative

Si un plan donne une signification aux chiffres terminaux :

```text
termination 0
termination 8
termination 9
```

PyAccountingKit ne généralise pas cette convention.

Elle reste :

```text
REFERENCE_SPECIFIC_RULE
```

---

# 102. Sémantique d'un segment

Un segment d'entreprise peut avoir un rôle interne :

```text
bank
branch
currency
location
counterparty
```

Cette sémantique est explicitement configurée.

---

# 103. Ne pas confondre segments et dimensions

Un code :

```text
512-01-0001
```

peut contenir un segment de site.

Mais une dimension comptable :

```text
CostCenter
```

est un autre concept.

---

# 104. Pourquoi séparer

Sinon :

```text
changer de centre
=
changer de compte
```

ce qui rend le chart artificiellement énorme.

---

# 105. `AccountCodeSegmentRole`

Valeurs possibles :

```text
REFERENCE
CATEGORY
COUNTERPARTY
LOCATION
CURRENCY
SEQUENCE
CUSTOM
```

---

# 106. Segments non sémantiques

Un segment peut être :

```text
SEQUENCE
```

sans signification métier.

---

# 107. Normalisation

`AccountCodePolicy` peut normaliser :

```text
spaces
case
separators
```

Exemple :

```text
bank-bnp-001
    ->
BANK-BNP-001
```

---

# 108. Principe de non-ambiguïté

La normalisation doit être déterministe.

Deux codes différents ne doivent pas devenir le même code sans détection de collision.

---

# 109. `NormalizedAccountCode`

```text
NormalizedAccountCode
|
+-- raw_value
+-- canonical_value
```

---

# 110. Codes réservés

Une policy peut déclarer :

```text
reserved_codes
reserved_prefixes
reserved_ranges
```

---

# 111. Ranges numériques

Des ranges peuvent être supportés par une policy numérique :

```text
100000 - 199999
```

mais ne sont jamais des invariants du framework.

---

# 112. Hiérarchie explicite

Même avec des codes hiérarchiques, la relation parent doit être persistée explicitement.

```text
parent_account_id
```

---

# 113. Pourquoi ne pas reconstruire le parent à chaque fois

Parce que :

```text
code policy peut évoluer
code peut ne pas être hiérarchique
segments peuvent contenir des données non hiérarchiques
```

---

# 114. `AccountHierarchyPolicy`

Modes :

```text
EXPLICIT_ONLY

PREFIX_CONSISTENT

REFERENCE_ALIGNED

CUSTOM
```

---

# 115. `EXPLICIT_ONLY`

La seule vérité est :

```text
parent_account_id
```

---

# 116. `PREFIX_CONSISTENT`

La policy vérifie :

```text
child canonical code
starts with parent canonical code
```

---

# 117. `REFERENCE_ALIGNED`

La hiérarchie d'entreprise suit une hiérarchie de référence jusqu'à un certain niveau, puis permet des subdivisions locales.

---

# 118. Subdivision locale

Exemple :

```text
Reference
512 Banques

Company
51200000 Banques
    |
    +-- 51201000 BNP
    |     |
    |     +-- 51201001 BNP EUR
    |     +-- 51201002 BNP USD
    |
    +-- 51202000 SG
```

---

# 119. `ReferenceAlignmentDepth`

La policy peut spécifier :

```text
align_to_reference_until_depth = N
```

---

# 120. Génération basée sur `ref_code`

Le generator peut utiliser :

```text
reference.ref_code
```

comme input.

Il ne modifie pas :

```text
reference.reference_account_id
```

---

# 121. Codes alphanumériques et référentiel numérique

Exemple :

```text
Reference 512
Company BANK-BNP-EUR
```

Le lien reste possible grâce à :

```text
RegulatoryAccountBinding
```

---

# 122. Validation du lien

Le binding ne dépend donc pas de :

```text
code equality
prefix equality
same length
```

---

# 123. `AccountRole`

Les policies métier peuvent cibler :

```text
BANK_ACCOUNT
CUSTOMER_CONTROL
SUPPLIER_CONTROL
DEPRECIATION_EXPENSE
ACCUMULATED_DEPRECIATION
```

sans connaître le code exact.

---

# 124. `CompanyAccountRoleBinding`

```text
CompanyAccountRoleBinding
|
+-- account_id
+-- role
+-- effective_from
+-- effective_to?
```

---

# 125. Role != regulatory binding

```text
AccountRole
    = rôle dans les policies de l'entreprise

ReferenceAccount
    = identité réglementaire
```

Un compte peut posséder les deux.

---

# 126. Plusieurs rôles

Un compte peut potentiellement porter :

```text
plusieurs rôles compatibles
```

selon la configuration.

---

# 127. `AccountRoleResolutionService`

Utilisé par :

```text
Accounting Policies & Measurement
```

pour générer les écritures sans code en dur.

---

# 128. Numérotation et FEC

Le format du plan d'entreprise doit être indépendant du FEC.

L'adapter FEC mappe :

```text
CompteNum
    ->
CompanyAccount.code
```

selon sa policy d'import.

---

# 129. Longueur FEC != longueur du core

Le core ne doit jamais dériver sa limite de longueur d'un format d'import.

---

# 130. Index de recherche

Les adapters de persistence peuvent indexer :

```text
chart_id + canonical_code
label
reference_account_id
account_role
active
```

---

# 131. Recherche par code

```python
account = account_repository.get_by_code(
    chart_id=chart_id,
    code=AccountCode("51200001"),
)
```

---

# 132. Recherche par référence

```python
accounts = account_repository.list_by_reference_account(
    reference_account_id="account:fr-pcg:2026:512",
)
```

---

# 133. Recherche par rôle

```python
account = account_role_resolver.resolve(
    role=AccountRole.BANK_ACCOUNT,
    context=...
)
```

---

# 134. Repository

```python
class CompanyAccountRepository(Protocol):

    def get(self, account_id: CompanyAccountId) -> CompanyAccount:
        ...

    def get_by_code(
        self,
        chart_id: CompanyChartId,
        code: AccountCode,
    ) -> CompanyAccount | None:
        ...

    def list_children(
        self,
        parent_id: CompanyAccountId,
    ) -> tuple[CompanyAccount, ...]:
        ...

    def save(self, account: CompanyAccount) -> None:
        ...
```

---

# 135. Chart Repository

```python
class CompanyChartRepository(Protocol):

    def get(
        self,
        chart_id: CompanyChartId,
    ) -> CompanyChartOfAccounts:
        ...

    def get_active_for_entity(
        self,
        entity_id: AccountingEntityId,
        at_date: date,
    ) -> CompanyChartOfAccounts:
        ...
```

---

# 136. Binding Repository

```python
class RegulatoryAccountBindingRepository(Protocol):

    def get_primary_binding(
        self,
        company_account_id: CompanyAccountId,
        at_date: date,
    ) -> RegulatoryAccountBinding | None:
        ...
```

---

# 137. Unit of Work

Création de compte :

```text
validate code
check uniqueness
check parent
persist account
persist binding
audit
commit
```

dans une transaction logique.

---

# 138. Domain Events

```text
CompanyChartCreated
CompanyChartActivated
CompanyChartSuperseded

CompanyAccountCreated
CompanyAccountRenamed
CompanyAccountActivated
CompanyAccountDeactivated
CompanyAccountRetired

RegulatoryAccountBound
RegulatoryAccountBindingSuperseded

AccountRoleBound

CompanyChartMigrationPlanned
```

---

# 139. Audit

Actions sensibles :

```text
chart creation
chart activation
account creation
account code change
binding change
account deactivation
migration
```

doivent être auditées.

---

# 140. `AccountCreationTrace`

```text
AccountCreationTrace
|
+-- account_id
+-- generated_or_manual
+-- code_policy_id
+-- code_policy_version
+-- generation_inputs
+-- reference_account_id?
+-- actor
+-- created_at
```

---

# 141. Fail-closed

Cas bloquants :

```text
duplicate code

invalid code format

ambiguous code policy

missing required binding

unknown reference account

forbidden candidate mapping

parent in another chart

hierarchy cycle

ambiguous account role

sequence collision
```

---

# 142. Erreurs métier

```text
CompanyChartError
|
+-- ChartNotFoundError
+-- ChartNotActiveError
+-- ChartVersionConflictError
|
+-- CompanyAccountError
|   +-- AccountCodeInvalidError
|   +-- AccountCodeDuplicateError
|   +-- AccountCodeCollisionError
|   +-- AccountHierarchyCycleError
|   +-- CrossChartParentError
|   +-- AccountNotPostableError
|
+-- AccountCodePolicyError
|   +-- AccountCodePolicyNotFoundError
|   +-- AmbiguousAccountCodePolicyError
|   +-- AccountCodeGenerationError
|
+-- RegulatoryBindingError
|   +-- ReferenceAccountNotFoundError
|   +-- RegulatoryBindingNotValidatedError
|
+-- AuxiliaryAccountingError
    +-- UnknownControlAccountError
```

---

# 143. Tests P0 - AccountCode

```text
test_account_code_is_string

test_numeric_fixed_length_accepts_valid_code

test_numeric_fixed_length_rejects_wrong_length

test_numeric_variable_length_accepts_6_8_9

test_alphanumeric_policy_accepts_configured_format

test_segmented_policy_builds_canonical_code
```

---

# 144. Tests P0 - unicité

```text
test_same_code_cannot_exist_twice_in_same_chart

test_same_code_can_exist_in_different_charts
```

---

# 145. Tests P0 - hiérarchie

```text
test_parent_must_belong_to_same_chart

test_account_cannot_parent_itself

test_hierarchy_cycle_is_rejected
```

---

# 146. Tests P0 - binding réglementaire

```text
test_company_account_preserves_reference_binding

test_multiple_company_accounts_can_bind_same_reference_account

test_binding_does_not_require_code_equality

test_binding_does_not_require_same_length
```

---

# 147. Tests P0 - génération

```text
test_reference_only_generation

test_padding_generation_is_policy_driven

test_manual_subdivision_preserves_reference_binding

test_generator_uses_effective_reference_plan
```

---

# 148. Tests P0 - non-universalité

```text
test_company_code_may_be_6_digits

test_company_code_may_be_8_digits

test_company_code_may_be_9_digits

test_company_code_may_be_more_than_9_digits

test_company_code_may_be_alphanumeric
```

---

# 149. Tests de préfixe

```text
test_prefix_parent_rule_only_applies_when_policy_requires_it
```

et :

```text
test_core_does_not_infer_supplier_role_from_401_prefix
```

---

# 150. Tests auxiliaires

```text
test_subledger_mode_does_not_require_extended_account_code

test_extended_account_mode_can_generate_unique_auxiliary_codes

test_hybrid_mode_is_explicit
```

---

# 151. Property-based tests

Exemples :

```text
for any generated code:
    policy.validate(code).valid == true

for any active chart:
    canonical codes are unique

for any hierarchy:
    no cycle exists

for any company account:
    its parent, if present, belongs to same chart
```

---

# 152. Golden test - 6 chiffres

Configuration :

```text
fixed length = 6
reference = 512
strategy = PAD_TO_LENGTH
```

Expected :

```text
512000
```

uniquement si la policy spécifie cette convention.

---

# 153. Golden test - 8 chiffres

```text
51200000
```

---

# 154. Golden test - 9 chiffres

```text
512000000
```

---

# 155. Golden test - segmenté

Template :

```text
{reference:3}{bank:2}{sequence:4}
```

Inputs :

```text
reference = 512
bank = 01
sequence = 0001
```

Expected :

```text
512010001
```

---

# 156. Golden test - alphanumérique

```text
BANK-BNP-EUR
```

binding :

```text
account:fr-pcg:2026:512
```

Le mapping reste valide si la policy l'autorise.

---

# 157. Exemple - fournisseurs

Référence :

```text
401
```

Entreprise :

```text
401000000
    compte collectif

401000123
    fournisseur X

401000124
    fournisseur Y
```

Ce modèle n'est qu'une configuration possible.

---

# 158. Alternative fournisseurs en subledger

```text
401000
    compte collectif

Supplier subledger:
    SUP-00123
    SUP-00124
```

Le chart général reste plus compact.

---

# 159. Exemple - banques

Entreprise choisissant 8 chiffres :

```text
51200000  Banques
51201000  BNP
51201001  BNP EUR
51201002  BNP USD
51202000  Société Générale
```

---

# 160. Exemple - immobilisations

Entreprise choisissant 10 chiffres :

```text
2183000000
2183000001
2183000002
```

Cela ne modifie pas l'identité réglementaire de référence.

---

# 161. Exemple de policy composite

```yaml
account_code_policy:
  default:
    type: numeric_fixed
    length: 6

  overrides:
    - scope:
        auxiliary_type: CUSTOMER
      policy:
        type: numeric_fixed
        length: 9

    - scope:
        auxiliary_type: SUPPLIER
      policy:
        type: numeric_fixed
        length: 9

    - scope:
        account_role: BANK_ACCOUNT
      policy:
        type: numeric_fixed
        length: 8
```

---

# 162. Exemple segmenté

```yaml
policy:
  type: segmented_numeric
  segments:
    - name: reference
      length: 3

    - name: branch
      length: 2

    - name: detail
      length: 4
```

---

# 163. Configuration declarative

Les policies simples peuvent être configurées en :

```text
YAML
JSON
Python
```

sans rendre le coeur dépendant de YAML.

---

# 164. Public API - créer un chart

```python
chart = accounting.charts.create(
    entity_id=entity_id,
    reference=StandardRef(
        standard_id="fr-pcg",
        edition="2026",
    ),
    code_policy=NumericFixedLengthPolicy(
        length=8,
    ),
)
```

---

# 165. Public API - créer un compte

```python
account = accounting.accounts.create(
    chart_id=chart.id,
    code="51201001",
    label="BNP EUR",
    reference_account_id=(
        "account:fr-pcg:2026:512"
    ),
)
```

---

# 166. Public API - génération

```python
result = accounting.charts.generate(
    entity_id=entity_id,
    reference_snapshot=snapshot,
    policy=generation_policy,
)
```

---

# 167. Public API - subdivision

```python
child = accounting.accounts.create_child(
    parent_account_id=bank_root.id,
    code_generation={
        "bank": "01",
        "sequence": "0001",
    },
    label="BNP EUR",
)
```

---

# 168. API indépendante du référentiel

La même API doit fonctionner avec :

```text
fr-pcg:2026
ohada-syscohada:2017
ohada-ebnl:2023
fr-nonprofit:2026
custom internal reference
```

si le provider expose le plan requis.

---

# 169. Package cible

```text
src/pyaccountingkit/domain/chart/
|
+-- chart.py
+-- account.py
+-- account_code.py
+-- account_kind.py
+-- hierarchy.py
+-- regulatory_binding.py
+-- account_role.py
+-- migration.py
|
+-- code_policies/
|   +-- protocol.py
|   +-- numeric_fixed.py
|   +-- numeric_variable.py
|   +-- segmented_numeric.py
|   +-- alphanumeric.py
|   +-- composite.py
|   +-- reference_compatible.py
|
+-- generation/
|   +-- policy.py
|   +-- request.py
|   +-- result.py
|
+-- auxiliary/
    +-- policy.py
    +-- reference.py
```

---

# 170. Application package

```text
application/charts/
|
+-- create_chart.py
+-- generate_chart.py
+-- activate_chart.py
+-- create_account.py
+-- deactivate_account.py
+-- bind_reference_account.py
+-- bind_account_role.py
+-- plan_migration.py
```

---

# 171. Ports

```text
CompanyChartRepository
CompanyAccountRepository
RegulatoryAccountBindingRepository
AccountRoleBindingRepository
AccountSequenceProvider
AccountUsagePort
AccountingReferenceProvider
AuditPort
UnitOfWork
```

---

# 172. Persistence indexes

Recommandations :

```text
UNIQUE(chart_id, canonical_code)

INDEX(reference_account_id)

INDEX(parent_account_id)

INDEX(accounting_entity_id, active)

INDEX(account_role)
```

---

# 173. Concurrence

Création simultanée :

```text
validate
generate code
check uniqueness
insert
```

doit être transactionnelle.

La contrainte unique de persistence constitue la dernière ligne de défense.

---

# 174. Idempotence de génération

Une génération de chart peut recevoir :

```text
generation_id
```

et une clé d'idempotence.

---

# 175. `ChartGenerationFingerprint`

Peut inclure :

```text
entity
reference snapshot
generation policy version
code policy version
effective date
```

---

# 176. Re-génération

Une seconde exécution identique doit :

```text
retourner le résultat existant
ou
échouer explicitement
```

selon la policy.

Elle ne doit pas dupliquer tous les comptes.

---

# 177. Imports de plan existant

Une entreprise peut déjà disposer d'un plan.

Pipeline :

```text
Existing Chart File
    |
    v
Chart Import Adapter
    |
    v
CompanyAccount candidates
    |
    v
Reference Mapping
    |
    v
Validation
    |
    v
CompanyChartOfAccounts
```

---

# 178. Import != génération

```text
generation
    = part d'un référentiel

import
    = part d'un plan d'entreprise existant
```

Les deux peuvent converger vers le même modèle.

---

# 179. Mapping d'un plan importé

Modes :

```text
MANUAL
VALIDATED_RULE
CANDIDATE
```

Une correspondance par préfixe est une candidate si elle n'est pas garantie.

---

# 180. Assistant de mapping

PyAccountingKit peut fournir :

```text
ReferenceMappingSuggestionService
```

mais les suggestions restent distinctes des bindings validés.

---

# 181. `MappingSuggestion`

```text
MappingSuggestion
|
+-- company_account_id
+-- candidate_reference_account_id
+-- confidence
+-- rationale
+-- status
```

---

# 182. Heuristiques de migration

Exemples autorisés :

```text
prefix similarity
label similarity
historic mapping
parent mapping
```

classification :

```text
HEURISTIC
```

---

# 183. Pas de semantic inference silencieuse

Même si :

```text
Company code = 512001
```

PyAccountingKit ne peut pas conclure universellement :

```text
Reference = 512 Banques
```

sans rule/binding applicable.

---

# 184. Usage des conventions du référentiel

Un adapter ou une `ReferenceSpecificRule` peut aider à produire ce candidat.

Le statut doit rester explicite.

---

# 185. Normal balance

`normal_balance` peut être porté par :

```text
CompanyAccount
Reference metadata
AccountRole
```

mais il ne doit pas être inféré universellement d'un numéro de classe.

---

# 186. Classification comptable

Les catégories :

```text
ASSET
LIABILITY
EQUITY
REVENUE
EXPENSE
```

doivent venir :

```text
d'un mapping validé
d'un concept validé
d'une configuration d'entreprise
```

pas d'un préfixe global du core.

---

# 187. Plan multi-référentiels

Une organisation peut avoir :

```text
un chart statutaire principal
+
des bindings secondaires
```

sans dupliquer tous ses comptes.

---

# 188. Group Chart

Le futur bounded context Consolidation pourra créer :

```text
GroupChartOfAccounts
```

distinct de `CompanyChartOfAccounts`.

---

# 189. Pas de Group Chart dans P0

P0 prépare uniquement les interfaces nécessaires :

```text
account mappings
secondary bindings
chart migration
```

---

# 190. Localization

Le code ne doit pas porter de logique de langue.

Les labels peuvent être :

```text
localized labels
```

dans un module futur.

---

# 191. `AccountDisplayLabel`

On peut prévoir :

```text
default_label
localized_labels
short_label
```

sans affecter le code.

---

# 192. Security / authorization

Le domaine ne gère pas les rôles utilisateurs.

L'application peut contrôler :

```text
qui peut créer un compte
qui peut changer un binding
qui peut activer une version de chart
```

---

# 193. Audit obligatoire pour changement de code

Un changement de code impacte potentiellement :

```text
imports
exports
interfaces
reporting
reconciliation
```

Il doit être audité.

---

# 194. Compatibilité API

Les policies de code sont des extensions.

Ajouter :

```text
NewAccountCodePolicy
```

ne doit pas modifier les contracts de `CompanyAccount`.

---

# 195. Versioning des policies de code

```text
AccountCodePolicyId
AccountCodePolicyVersion
```

doivent être conservés dans :

```text
chart
generation trace
account creation trace
```

---

# 196. Changement de code policy

Changer de :

```text
6 digits
```

à :

```text
9 digits
```

est une migration de chart, pas une simple option UI.

---

# 197. Exemple migration 6 -> 9

Avant :

```text
512001
512002
```

Après :

```text
512001000
512002000
```

ou tout autre résultat défini explicitement.

---

# 198. Pas de règle de padding implicite

Le framework ne doit pas choisir automatiquement :

```text
left padding
right padding
zeros
sequence
```

La migration doit fournir la transformation.

---

# 199. `AccountCodeTransformation`

```text
AccountCodeTransformation
|
+-- source_code
+-- target_code
+-- strategy
+-- reason
```

---

# 200. Compatibilité historique

Les écritures historiques conservent :

```text
account_id
```

Même si le display code change dans une version future, l'identité historique reste traçable.

---

# 201. Stratégie préférée - nouvelle version de compte

Pour les transformations majeures :

```text
old account retired
new account created
migration mapping
```

plutôt qu'une mutation destructive.

---

# 202. Reporting inter-version

Le reporting doit pouvoir consolider :

```text
old account
+
new account
```

via mapping de migration si une période comparative traverse le changement.

---

# 203. Anti-pattern - code entier

Interdit :

```python
account.code = 512001
```

---

# 204. Anti-pattern - longueur globale codée en dur

Interdit :

```python
assert len(account.code) == 8
```

dans `CompanyAccount`.

---

# 205. Anti-pattern - PCG universel

Interdit :

```python
account_class = int(code[0])
```

dans le coeur.

---

# 206. Anti-pattern - supplier via 401

Interdit :

```python
is_supplier = code.startswith("401")
```

hors scope de rule explicite.

---

# 207. Anti-pattern - code = reference ID

Interdit :

```text
CompanyAccount identity
=
regulatory code
```

---

# 208. Anti-pattern - cloning blind

Interdit :

```text
copy every reference node
make it postable
```

sans policy d'inclusion.

---

# 209. Anti-pattern - auxiliary encoded everywhere

Interdit de forcer :

```text
un compte général par tiers
```

pour toutes les organisations.

---

# 210. Anti-pattern - hierarchy inferred only from code

La hiérarchie doit être explicitement persistée.

---

# 211. Anti-pattern - renumber in place

Ne pas renuméroter massivement un plan utilisé sans :

```text
migration
audit
versioning
```

---

# 212. ADRs

| ID | Décision |
|---|---|
| ADR-COA-001 | `CompanyAccount.code` est une chaîne |
| ADR-COA-002 | La longueur d'un code n'est pas un invariant universel |
| ADR-COA-003 | Les conventions numériques d'un référentiel sont `REFERENCE_SPECIFIC_RULE` |
| ADR-COA-004 | `CompanyAccount` et `ReferenceAccount` sont des objets distincts |
| ADR-COA-005 | Un compte d'entreprise conserve un `RegulatoryAccountBinding` explicite |
| ADR-COA-006 | Un même `ReferenceAccount` peut être lié à plusieurs `CompanyAccount` |
| ADR-COA-007 | `CompanyChartOfAccounts` ne contient pas tous les comptes comme enfants d'agrégat |
| ADR-COA-008 | `CompanyAccount` est un Aggregate Root indépendant |
| ADR-COA-009 | Parent/enfant est une relation explicite, pas une inférence obligatoire par préfixe |
| ADR-COA-010 | Numeric fixed, numeric variable, segmented et alphanumeric sont supportés |
| ADR-COA-011 | La longueur peut varier par famille de comptes |
| ADR-COA-012 | `REFERENCE_ONLY` est le mode de génération prudent par défaut |
| ADR-COA-013 | `PAD_TO_LENGTH` n'est utilisé que par policy explicite |
| ADR-COA-014 | Compte collectif et compte auxiliaire sont distincts |
| ADR-COA-015 | `SUBLEDGER`, `EXTENDED_ACCOUNT_CODE` et `HYBRID` sont des modes différents |
| ADR-COA-016 | Les heuristiques de préfixe ne sont jamais des invariants universels |
| ADR-COA-017 | `AccountRole` est distinct du code et du binding réglementaire |
| ADR-COA-018 | Les changements majeurs de codification passent par une migration versionnée |
| ADR-COA-019 | Les codes retirés ne sont pas réutilisés automatiquement |
| ADR-COA-020 | Un nouveau référentiel ne mute pas silencieusement le chart actif |
| ADR-COA-021 | Le generator consomme les effective plans déjà résolus |
| ADR-COA-022 | L'unicité du code est garantie dans le scope du chart |
| ADR-COA-023 | L'absence de cycles de hiérarchie est un invariant |
| ADR-COA-024 | Les mappings candidats ne deviennent pas des bindings actifs sans validation |

---

# 213. Critères d'acceptation P0.7

```text
[ ] CompanyChartOfAccounts est défini

[ ] CompanyAccount est défini comme Aggregate Root indépendant

[ ] AccountCode est une chaîne

[ ] NumericFixedLengthPolicy est spécifiée

[ ] NumericVariableLengthPolicy est spécifiée

[ ] SegmentedNumericPolicy est spécifiée

[ ] AlphanumericPolicy est spécifiée

[ ] CompositeAccountCodePolicy est spécifiée

[ ] les longueurs 6, 8, 9 et N sont possibles

[ ] la longueur peut varier par famille

[ ] code et référence réglementaire sont distincts

[ ] RegulatoryAccountBinding est explicite

[ ] 1 ReferenceAccount -> N CompanyAccounts est supporté

[ ] parent/enfant est explicite

[ ] parent doit appartenir au même chart

[ ] aucun cycle de hiérarchie n'est possible

[ ] un compte peut être non postable

[ ] REFERENCE_ONLY est disponible

[ ] PAD_TO_LENGTH est policy-driven

[ ] TEMPLATE_EXPANSION est défini

[ ] les auxiliaires peuvent utiliser SUBLEDGER

[ ] les auxiliaires peuvent utiliser EXTENDED_ACCOUNT_CODE

[ ] HYBRID est possible

[ ] le core ne contient aucun `startswith("401")`

[ ] le core n'infère pas la classe via le premier chiffre

[ ] le generator utilise l'effective plan

[ ] migration de chart est versionnée

[ ] changement de code policy n'est pas une simple mutation

[ ] les tests couvrent 6/8/9/N et alphanumérique
```

---

# 214. Ordre d'implémentation recommandé

## COA-00 - Primitives

```text
CompanyChartId
CompanyAccountId
AccountCode
CompanyChartVersion
CompanyAccountKind
```

---

## COA-01 - Aggregates

```text
CompanyChartOfAccounts
CompanyAccount
```

---

## COA-02 - Code Policies

```text
AccountCodePolicy
NumericFixedLengthPolicy
NumericVariableLengthPolicy
SegmentedNumericPolicy
AlphanumericPolicy
```

---

## COA-03 - Repositories

```text
CompanyChartRepository
CompanyAccountRepository
```

---

## COA-04 - Reference Bindings

```text
RegulatoryAccountBinding
BindingPurpose
binding repository
```

---

## COA-05 - Chart Generator

```text
CompanyChartGenerationPolicy
CompanyChartGenerator
REFERENCE_ONLY
PAD_TO_LENGTH
```

---

## COA-06 - Hierarchy

```text
parent rules
cycle detection
posting_allowed
```

---

## COA-07 - Account Roles

```text
AccountRole
CompanyAccountRoleBinding
AccountRoleResolutionService
```

---

## COA-08 - Auxiliary Accounting Basics

```text
AuxiliaryAccountingPolicy
SUBLEDGER
EXTENDED_ACCOUNT_CODE
HYBRID
```

---

## COA-09 - Migration

```text
CompanyChartMigrationPlan
AccountMigrationPlan
```

---

# 215. Démonstrateur P0.7

Scénario recommandé :

```text
1. Load fr-pcg:2026 reference snapshot

2. Resolve effective account plan

3. Create Entity A

4. Create chart A
      numeric fixed length = 6

5. Generate REFERENCE_ONLY chart

6. Subdivide reference account 512
      512001
      512002

7. Verify both bind to:
      account:fr-pcg:2026:512

8. Create Entity B

9. Create chart B
      numeric fixed length = 9

10. Generate / subdivide:
      512000001
      512000002

11. Verify same reference binding

12. Create Entity C
      segmented code policy

13. Generate:
      512-01-0001

14. Create Entity D
      alphanumeric policy

15. Create:
      BANK-BNP-EUR

16. Bind to same regulatory account

17. Verify:
      code equality is never required

18. Verify:
      all four charts can post
      through the same Accounting Core
```

---

# 216. Démonstrateur auxiliaire

```text
Entity A:
    mode = SUBLEDGER

    411000
        control account

    Customer:
        CUST-001


Entity B:
    mode = EXTENDED_ACCOUNT_CODE

    411000001
    411000002


Entity C:
    mode = HYBRID
```

Le framework doit supporter les trois sans modifier `JournalEntry`.

---

# 217. Impact sur le document suivant

Le prochain document est :

```text
07_PYACCOUNTINGKIT_LEDGER_POSTING_AND_REVERSAL_ARCHITECTURE.md
```

Il utilisera :

```text
CompanyAccount
AccountRole
AccountingPeriod
Journal
JournalEntry
```

et imposera notamment :

```text
account exists
account active
account posting_allowed
period accepts posting
entry balanced
validated before posting
posted entry immutable
reversal by new entry
```

---

# 218. Conclusion

PyAccountingKit doit dissocier définitivement :

```text
le sens réglementaire d'un compte

la structure du référentiel

le code choisi par l'entreprise

la hiérarchie opérationnelle

la comptabilité auxiliaire

le rôle utilisé par une policy
```

L'architecture cible est :

```text
ReferenceAccountPlan
        |
        v
CompanyChartGenerationPolicy
        |
        +--> AccountCodePolicy
        +--> InclusionPolicy
        +--> HierarchyPolicy
        |
        v
CompanyChartOfAccounts
        |
        v
CompanyAccount
        |
        +--> RegulatoryAccountBinding
        +--> AccountRoleBinding
        +--> AuxiliaryAccountingPolicy
        |
        v
Accounting Core
```

Les principes majeurs sont :

```text
Account code is a string

6 digits is valid

8 digits is valid

9 digits is valid

N digits is valid

alphanumeric is valid when configured

segmentation is configurable

reference code != company code

code equality is not required for binding

prefix semantics are not universal

reference-specific numeric conventions stay reference-specific

hierarchy is explicit

auxiliary accounting is configurable

chart migrations are versioned
```

Le framework peut ainsi représenter les usages de plans comptables très normés, tout en restant capable de supporter des conventions d'entreprise différentes et de futurs référentiels sans réécriture du coeur.

---

**Prochain document recommandé :**

```text
07_PYACCOUNTINGKIT_LEDGER_POSTING_AND_REVERSAL_ARCHITECTURE.md
```


---

## Sources et références documentaires du projet

- 📕 [Comptabilité Générale — Système français et normes IFRS](../../books/Comptabilite_Generale_Systeme_Francais_et_Normes_IFRS.md)
- 📂 [Référentiels réglementaires — Datasets](../../referentiels/datasets/)
- 📐 [Référentiels réglementaires — Schémas](../../referentiels/schemas/)
- 📦 [regulatory-accounting-data-framework](../../../resources/regulatory-accounting-data-framework/)

---

## Plans d'implémentation principaux

Ce document est couvert par les plans suivants :

- [PLAN-02 — References, Charts & Policies (0.2.0)](../../plans/PLAN-02_REFERENCES_CHARTS_POLICIES_0.2.0.md)
