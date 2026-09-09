# 17 - PyAccountingKit - Stratégie de release et de versioning

> **Projet** : PyAccountingKit  
> **Document** : `17_PYACCOUNTINGKIT_RELEASE_AND_VERSIONING_STRATEGY.md`  
> **Documents parents** :
> - `00_PYACCOUNTINGKIT_REQUIREMENTS_ANALYSIS.md`
> - `01_PYACCOUNTINGKIT_PROJECT_VISION_AND_ARCHITECTURE.md`
> - `02_PYACCOUNTINGKIT_DOMAIN_MODEL_AND_BOUNDED_CONTEXTS.md`
> - `03_PYACCOUNTINGKIT_ACCOUNTING_RULES_AND_INVARIANTS.md`
> - `04_PYACCOUNTINGKIT_ACCOUNTING_POLICIES_RECOGNITION_AND_MEASUREMENT_ARCHITECTURE.md`
> - `05_PYACCOUNTINGKIT_ACCOUNTING_REFERENCE_DATA_ARCHITECTURE.md`
> - `06_PYACCOUNTINGKIT_COMPANY_CHART_OF_ACCOUNTS_AND_NUMBERING_ARCHITECTURE.md`
> - `07_PYACCOUNTINGKIT_LEDGER_POSTING_AND_REVERSAL_ARCHITECTURE.md`
> - `08_PYACCOUNTINGKIT_CLOSING_ACCRUALS_PROVISIONS_AND_ADJUSTMENTS_ARCHITECTURE.md`
> - `09_PYACCOUNTINGKIT_CONTROLS_AUDIT_AND_TRACEABILITY_ARCHITECTURE.md`
> - `10_PYACCOUNTINGKIT_PERSISTENCE_CONCURRENCY_AND_ADAPTER_CONTRACTS.md`
> - `11_PYACCOUNTINGKIT_TESTING_AND_QUALITY_STRATEGY.md`
> - `12_PYACCOUNTINGKIT_ACCOUNTING_IMPORT_AND_FEC_ADAPTER_ARCHITECTURE.md`
> - `13_PYACCOUNTINGKIT_FINANCIAL_STATEMENTS_AND_REGULATORY_REPORTING_ARCHITECTURE.md`
> - `14_PYACCOUNTINGKIT_FINANCIAL_ANALYSIS_AND_INDICATORS_ARCHITECTURE.md`
> - `15_PYACCOUNTINGKIT_SUBLEDGERS_AND_OPERATIONAL_ACCOUNTING_ARCHITECTURE.md`
> - `16_PYACCOUNTINGKIT_PUBLIC_API_DESIGN.md`
> **Statut** : P1.6 - Stratégie de release, versioning et compatibilité  
> **Langue** : Français  
> **Objet** : Définir la politique SemVer de PyAccountingKit, les phases alpha/beta/RC/stable, le gel de l'API publique, les contrats d'adapters, la compatibilité avec les datasets réglementaires, les migrations, la dépréciation, les gates de release, les artefacts de publication et les règles de maintenance.

---

# 1. Résumé exécutif

PyAccountingKit manipule plusieurs dimensions de version qui ne doivent jamais être confondues :

```text
Framework Version
Regulatory Dataset Release
Accounting Standard Edition
Public API Contract Version
Adapter Contract Version
Persistence Schema Version
Snapshot Schema Version
Import Adapter Version
Statement Definition Version
Policy Definition Version
Company Chart Version
Reporting Profile Version
Analytical Definition Version
```

La stratégie de release repose sur un principe central :

```text
Package version
    !=
Regulatory version
    !=
Accounting policy version
    !=
Database schema version
    !=
Public API contract version
```

PyAccountingKit utilise **Semantic Versioning** pour le package :

```text
MAJOR.MINOR.PATCH
```

et des pré-releases :

```text
0.1.0a1
0.1.0b1
0.1.0rc1
0.1.0
```

La release stable ne signifie pas :

```text
"les règles réglementaires n'évolueront plus"
```

Elle signifie :

```text
"la surface publique et les contrats de compatibilité annoncés
sont stabilisés selon la politique de versioning"
```

---

# 2. Objectifs

Cette stratégie doit permettre de :

1. versionner le framework sans coupler sa version aux référentiels comptables ;
2. gérer plusieurs standards/éditions simultanément ;
3. stabiliser l'API publique avant 1.0 ;
4. versionner les contrats d'adapters ;
5. gérer les migrations DB sans ambiguïté ;
6. conserver la reproductibilité des snapshots historiques ;
7. publier des pré-releases qualifiées ;
8. définir des gates stricts pour RC et stable ;
9. documenter les breaking changes ;
10. encadrer les dépréciations ;
11. supporter les hotfixes ;
12. maintenir les branches de maintenance ;
13. versionner les artefacts réglementaires ;
14. éviter les upgrades réglementaires silencieux ;
15. gérer la compatibilité Python / Django / SQLAlchemy / PostgreSQL ;
16. générer des manifests de release auditables ;
17. fournir une politique claire aux adapter authors ;
18. fournir une politique claire aux utilisateurs du framework ;
19. permettre les corrections réglementaires sans casser les snapshots historiques ;
20. préparer la transition vers `1.0.0`.

---

# 3. Non-objectifs

Ce document ne définit pas :

```text
le contenu exact de chaque release future

le calendrier commercial

la politique de support payant

les SLA

la stratégie de déploiement cloud d'une application cliente

la politique de versioning d'un ERP consommateur
```

---

# 4. Dimensions de version

## 4.1 Framework Version

Exemple :

```text
pyaccountingkit 0.5.0
```

Mesure :

```text
code du framework
API publique
capabilities
adapters intégrés
```

---

## 4.2 Regulatory Dataset Release

Exemple conceptuel :

```text
regulatory-accounting-data-framework release 2026.09
```

Mesure :

```text
état versionné du corpus réglementaire
```

---

## 4.3 Accounting Standard Edition

Exemples :

```text
fr-pcg:2026
ohada-syscohada:2017
fr-nonprofit:2026
ohada-ebnl:2023
```

---

## 4.4 Public API Contract Version

Exemple :

```text
PUBLIC_API_VERSION = "1"
```

Cette version ne remplace pas SemVer ; elle sert aux consommateurs souhaitant vérifier un contrat d'extension ou un manifest.

---

## 4.5 Adapter Contract Version

Exemple :

```text
ADAPTER_CONTRACT_VERSION = "1"
```

---

## 4.6 Persistence Schema Version

Géré par :

```text
Django migrations
Alembic
```

selon l'adapter.

---

## 4.7 Snapshot Schema Version

Chaque snapshot sérialisé doit indiquer :

```text
schema_version
```

---

## 4.8 Policy Version

Exemple :

```text
DepreciationPolicy v2
```

---

## 4.9 Statement Definition Version

Exemple :

```text
BalanceSheetDefinition v3
```

---

## 4.10 Company Chart Version

Exemple :

```text
Chart MAIN v4
```

---

# 5. Principe de découplage

Interdit :

```text
PyAccountingKit 2026
```

comme seule façon de représenter PCG 2026.

Correct :

```text
Framework:
    PyAccountingKit 0.6.0

Reference:
    fr-pcg:2026

Dataset:
    regulatory release X

Company Chart:
    v3

Policy Set:
    v5
```

---

# 6. Semantic Versioning

Format :

```text
MAJOR.MINOR.PATCH
```

---

# 7. MAJOR

Incrémenter MAJOR pour :

```text
breaking public API
breaking public behavior
breaking adapter contract
breaking serialized contract if no compatibility path
removed deprecated stable API
major domain semantic contract change
```

Exemple :

```text
1.4.2 -> 2.0.0
```

---

# 8. MINOR

Incrémenter MINOR pour :

```text
new backward-compatible feature
new optional adapter
new public method
new supported regulatory capability
new non-breaking DTO optional field
new report renderer
new analytical definition package
```

Exemple :

```text
1.4.2 -> 1.5.0
```

---

# 9. PATCH

Incrémenter PATCH pour :

```text
bug fix
performance fix
documentation fix
non-breaking adapter correction
security fix
regulatory data interpretation fix if framework API unchanged
```

Exemple :

```text
1.4.2 -> 1.4.3
```

---

# 10. Pre-release identifiers

Utiliser PEP 440 :

```text
aN
bN
rcN
```

---

# 11. Alpha

Exemple :

```text
0.2.0a1
```

Signifie :

```text
feature scope still moving
API may change
migration may change
not production qualified
```

---

# 12. Beta

Exemple :

```text
0.2.0b1
```

Signifie :

```text
feature scope largely complete
API nearing freeze
integration qualification in progress
```

---

# 13. Release Candidate

Exemple :

```text
0.2.0rc1
```

Signifie :

```text
feature freeze
public API freeze candidate
migration path frozen
full qualification required
only bug/security/regulatory correctness fixes allowed
```

---

# 14. Stable

Exemple :

```text
0.2.0
```

Signifie :

```text
all stable gates pass
no known BLOCKER/CRITICAL
public API contract published
migration path documented
artifacts signed/checksummed
```

---

# 15. Dev releases

Option :

```text
0.2.0.devN
```

pour CI/nightly.

Non publiées comme user-facing milestones sauf besoin.

---

# 16. Post releases

Éviter si possible :

```text
0.2.0.post1
```

pour corrections de code.

Préférer :

```text
0.2.1
```

---

# 17. Politique 0.x

Avant `1.0.0`, PyAccountingKit peut encore effectuer des breaking changes dans une MINOR.

Exemple :

```text
0.4.x -> 0.5.0
```

peut être breaking.

Mais cette liberté doit être progressivement réduite.

---

# 18. Stabilité 0.x

Politique recommandée :

```text
0.1.x - foundations
0.2.x - core accounting stabilization
0.3.x - reporting / imports stabilization
0.4.x - adapters / public API hardening
0.5.x - API freeze candidate
0.9.x - 1.0 qualification line
1.0.0 - stable public contract
```

Cette séquence est indicative.

---

# 19. API freeze avant 1.0

Au plus tard à :

```text
0.9.0b1
```

ou milestone équivalent, la surface publique principale doit être figée.

---

# 20. Freeze scope

Le freeze couvre :

```text
public symbols
method names
required arguments
return semantics
public error codes
stable enums
adapter contracts
snapshot schema contracts
```

---

# 21. Ce qui peut encore changer en RC

Uniquement :

```text
bug fixes
security fixes
documentation
non-breaking validation clarification
performance
compatibility bug
```

---

# 22. Ce qui ne doit pas changer en RC

```text
new major feature
renamed public method
new mandatory argument
database model redesign
major policy semantic rewrite
adapter contract redesign
```

---

# 23. Public API Manifest

Chaque RC/stable doit publier :

```text
PUBLIC_API_MANIFEST.json
```

---

# 24. Manifest contenu

```text
framework_version
public_api_version
symbols
signatures
public error codes
stable enum values
```

---

# 25. API diff gate

Comparer :

```text
current candidate
vs
previous stable
```

---

# 26. Breaking diff

Si version MAJOR inchangée :

```text
release gate FAIL
```

---

# 27. Public Error Codes Manifest

Publier :

```text
PUBLIC_ERROR_CODES.json
```

---

# 28. Adapter Contract Manifest

Publier :

```text
PORT_CONTRACT_MANIFEST.json
```

ou :

```text
ADAPTER_CONTRACT_MANIFEST.json
```

---

# 29. Adapter contract stability

Un custom adapter compatible avec :

```text
contract v1
```

doit continuer à fonctionner sur les patch/minor annoncés compatibles.

---

# 30. Breaking adapter contract

Nécessite :

```text
new contract version
```

et généralement :

```text
framework MAJOR
```

après 1.0.

---

# 31. Adapter compatibility declaration

Exemple :

```text
adapter_contract:
    supported: ["1"]
```

---

# 32. Adapter qualification levels

```text
TEST_ONLY

REFERENCE

EXPERIMENTAL

PRODUCTION
```

---

# 33. Adapter release qualification

Un adapter `PRODUCTION` doit avoir :

```text
contract tests PASS
integration tests PASS
rollback tests PASS
concurrency tests PASS
migration tests PASS
performance smoke PASS
```

---

# 34. Database qualification

Le statut Production est lié à un backend concret.

Exemple :

```text
Django/PostgreSQL 16 -> PRODUCTION
Django/SQLite -> TEST_ONLY
```

---

# 35. Python support policy

Chaque stable line publie :

```text
minimum_python
maximum_tested_python
```

---

# 36. P1 recommendation

Supporter uniquement des versions Python maintenues et testées.

La liste exacte est fixée dans chaque release.

---

# 37. Dropping Python version

Après 1.0 :

```text
MINOR or MAJOR?
```

Recommandation :

```text
MINOR possible if dependency ecosystem standard,
but announce in advance
```

Pour une politique stricte :

```text
treat as breaking ecosystem change
```

---

# 38. Django compatibility

Chaque release documente :

```text
supported Django versions
```

---

# 39. SQLAlchemy compatibility

Même principe.

---

# 40. PostgreSQL compatibility

Même principe.

---

# 41. Compatibility Matrix

Publier :

```text
COMPATIBILITY_MATRIX.md/json
```

---

# 42. Exemple

```text
PyAccountingKit 1.2.x

Python:
    3.12
    3.13

Django:
    5.x

SQLAlchemy:
    2.x

PostgreSQL:
    15+
```

Exemple non normatif.

---

# 43. Regulatory compatibility

La version du framework ne suffit pas à indiquer quels standards sont disponibles.

Publier :

```text
REGULATORY_COMPATIBILITY_MATRIX.json
```

---

# 44. Exemple

```text
fr-pcg:
    edition: 2026
    capabilities:
        structure: supported
        reporting: supported

ohada-syscohada:
    edition: 2017
    capabilities:
        structure: supported
        reporting: supported
```

---

# 45. Important

Support signifie :

```text
capability explicitly qualified
```

et non :

```text
all possible accounting rules of that jurisdiction are fully automated
```

---

# 46. Capability granularity

Pour chaque standard :

```text
structure
effective_plan
relations
concepts
reporting_structure
executable_reporting_mapping
policies
imports
exports
```

---

# 47. Regulatory data release pinning

Une release stable peut annoncer :

```text
tested with regulatory dataset release R
```

mais l'application peut pinner une autre release compatible.

---

# 48. No implicit regulatory upgrade

Mettre à jour PyAccountingKit ne doit pas automatiquement changer :

```text
active reference snapshot
```

d'une entité.

---

# 49. Regulatory upgrade flow

```text
install new dataset

create new reference snapshot

impact analysis

migration plan

review

activate new chart/profile/policies
```

---

# 50. Regulatory patch correction

Si le corpus de référence corrige une erreur :

```text
new dataset release
```

---

# 51. Historical snapshots

Ne sont jamais réécrits.

---

# 52. Framework support for old snapshots

Le framework doit continuer à pouvoir :

```text
read / inspect
```

des snapshots historiques selon sa compatibility policy.

---

# 53. Snapshot schema versioning

Chaque snapshot :

```text
schema_version
```

---

# 54. Snapshot migration

Deux stratégies :

```text
reader compatibility

explicit snapshot migration
```

---

# 55. Published snapshot

Ne doit pas être "migré" destructivement.

---

# 56. Preferred

Conserver payload historique et utiliser :

```text
version-aware reader
```

---

# 57. Snapshot read support window

P1 recommandation :

```text
current + previous major schema
```

à définir précisément avant 1.0.

---

# 58. Persistence schema version

La DB évolue avec migrations.

---

# 59. Schema migration policy

Toute release qui change le schema doit inclure :

```text
migration
migration tests
upgrade notes
rollback strategy or explicit no-downgrade statement
post-migration controls
```

---

# 60. Data migration

Distincte de schema migration.

---

# 61. Migration classification

```text
SCHEMA_ONLY

DATA_BACKFILL

SEMANTIC_DATA_MIGRATION

INDEX_ONLY

DESTRUCTIVE
```

---

# 62. Destructive migration

Après 1.0 :

```text
major release
```

sauf si données concernées sont purement techniques et migration transparente.

---

# 63. Expand / Contract

Recommandé pour production :

```text
expand
deploy compatible code
backfill
contract
```

---

# 64. Downgrade

Pas obligatoirement supporté.

Chaque migration doit déclarer :

```text
reversible: true/false
```

---

# 65. Application rollback

Même si DB downgrade non supporté, la stratégie de déploiement doit documenter :

```text
compatible previous app version?
```

---

# 66. Migration gate

Avant release stable :

```text
upgrade from previous stable
```

doit être testé.

---

# 67. Fresh install gate

Toujours tester :

```text
fresh schema
```

---

# 68. Data fixture gate

Tester :

```text
realistic historical fixtures
```

---

# 69. Post-migration controls

Exécuter :

```text
TRIAL_BALANCE_BALANCED
audit integrity
snapshot checksum checks
reference snapshot consistency
```

selon contexte.

---

# 70. Policy versioning

Les policies métier ont leur propre version.

---

# 71. Policy change non-breaking framework

Une nouvelle policy peut être livrée dans MINOR.

---

# 72. Policy semantic change

Ne doit pas remplacer silencieusement une active policy.

---

# 73. Correct

```text
Policy v1
Policy v2
```

coexistent.

---

# 74. Deprecated policy

Peut être marquée :

```text
DEPRECATED
```

mais doit rester lisible pour replay historique.

---

# 75. Statement Definition versioning

Même principe.

---

# 76. Analytical Definition versioning

Même principe.

---

# 77. Company Chart versioning

App-level, non package SemVer.

---

# 78. Reporting Profile versioning

App-level, non package SemVer.

---

# 79. Import Adapter versioning

Chaque adapter peut exposer :

```text
adapter_id
adapter_version
```

---

# 80. Parser semantic change

Incrémenter adapter_version.

---

# 81. Same package, different adapter version

Possible.

---

# 82. FEC adapter compatibility

Publier :

```text
supported source schema variants
```

---

# 83. Import replay

Historical import run pins :

```text
adapter version
source checksum
mapping snapshot
policy snapshot
```

---

# 84. Deprecation policy

Une API stable ne doit pas disparaître sans phase de dépréciation.

---

# 85. Deprecation steps

```text
1. mark deprecated in docs
2. emit DeprecationWarning
3. provide replacement
4. maintain during defined window
5. remove in major release
```

---

# 86. Deprecation window

Après 1.0 :

```text
at least one MINOR
```

recommandé.

Mieux :

```text
two MINOR releases or documented support window
```

---

# 87. Error code deprecation

Même rigueur.

---

# 88. Enum value deprecation

Possible mais délicat.

Préférer conserver jusqu'à MAJOR.

---

# 89. Adapter protocol deprecation

Publier migration guide.

---

# 90. Warning class

Utiliser :

```text
PyAccountingKitDeprecationWarning
```

ou `DeprecationWarning` documenté.

---

# 91. No silent alias forever

Un alias temporaire doit avoir une date/version de suppression.

---

# 92. Changelog

Chaque release publie :

```text
CHANGELOG.md
```

---

# 93. Changelog sections

```text
Added
Changed
Deprecated
Removed
Fixed
Security
Regulatory
Migration
Adapters
```

---

# 94. Regulatory changelog

Important d'isoler :

```text
Regulatory
```

des changements de framework.

---

# 95. Release Notes

Pour chaque release :

```text
summary
user impact
breaking changes
migration actions
supported environments
regulatory impact
known issues
```

---

# 96. Breaking change note

Doit inclure :

```text
before
after
migration
reason
```

---

# 97. Migration Guide

Pour MAJOR et breaking pre-1.0 :

```text
MIGRATION_<FROM>_TO_<TO>.md
```

---

# 98. Release branches

Stratégie recommandée :

```text
main
release/x.y
hotfix/x.y.z optional
```

---

# 99. Main

Contient la prochaine development line.

---

# 100. Release branch

Créée à partir de :

```text
feature freeze / RC
```

---

# 101. Hotfix branch

Optionnelle.

---

# 102. Tagging

Tags immuables :

```text
v0.5.0a1
v0.5.0b1
v0.5.0rc1
v0.5.0
```

---

# 103. Never retag

Interdit :

```text
delete and recreate v0.5.0
```

---

# 104. Yanking

Si une release PyPI est gravement cassée :

```text
yank
```

plutôt que remplacer.

---

# 105. Hotfix

Publier :

```text
0.5.1
```

---

# 106. Patch branch support

Après 1.0, maintenir au moins la dernière stable minor selon capacité.

---

# 107. LTS

Non défini P1.

Peut être ajouté plus tard.

---

# 108. Security releases

Patch prioritaire.

---

# 109. Security embargo

Process organisationnel, hors détail P1.

---

# 110. CVE

Si applicable, documenter.

---

# 111. Dependency security

Run :

```text
dependency audit
```

before stable.

---

# 112. Supply chain

Release stable doit générer :

```text
wheel
sdist
checksums
SBOM optional/recommended
provenance
```

---

# 113. Build isolation

Build in clean environment.

---

# 114. Reproducible artifact target

Même source tag devrait produire des artefacts reproductibles dans la mesure supportée.

---

# 115. Artifact checksums

Publier :

```text
SHA-256
```

---

# 116. Signing

Recommended:

```text
trusted publishing / Sigstore
```

selon pipeline choisi.

---

# 117. PyPI publishing

Use trusted publisher if available.

---

# 118. TestPyPI

RC or pre-release can be validated there.

---

# 119. Clean install gate

Avant PyPI stable :

```text
install wheel in clean env
```

---

# 120. Sdist install gate

Same.

---

# 121. Extras install gate

Tester :

```text
core
django
sqlalchemy
all supported extras
```

---

# 122. Package metadata

Vérifier :

```text
name
version
license
requires-python
dependencies
optional-dependencies
classifiers
```

---

# 123. `py.typed`

Required if typing support advertised.

---

# 124. API docs artifact

Build docs from release tag.

---

# 125. Documentation versioning

Docs should have version selector after 1.0 if feasible.

---

# 126. Release gates hierarchy

Reuse quality strategy:

```text
G0 Local
G1 PR
G2 Main
G3 Nightly
G4 RC
G5 Stable
```

---

# 127. RC gate

Must include:

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
package build
clean install
docs build
```

---

# 128. Stable gate

Requires:

```text
RC green
0 BLOCKER
0 CRITICAL
no critical flaky tests
release notes complete
migration guide complete
public API manifest frozen
compatibility matrix published
checksums generated
```

---

# 129. Regulatory stable gate

If release claims new regulatory support:

```text
reference fixture PASS
snapshot PASS
mapping safety PASS
human-review flags preserved
golden report PASS
```

---

# 130. Import adapter stable gate

If new import adapter:

```text
contract PASS
golden PASS
rollback PASS
idempotency PASS
concurrency PASS
```

---

# 131. Adapter Production gate

As defined earlier.

---

# 132. Public API diff

Automated.

---

# 133. Snapshot schema diff

Automated if possible.

---

# 134. Error code diff

Automated.

---

# 135. Migration diff

Must be manually reviewed.

---

# 136. Release qualification manifest

Generate :

```text
RELEASE_QUALIFICATION_MANIFEST.json
```

---

# 137. Manifest fields

```text
framework_version
git_commit
build_timestamp
python_versions
adapter_qualifications
database_qualifications
public_api_version
adapter_contract_version
regulatory_compatibility
test_summary
golden_checksums
artifact_checksums
migration_status
```

---

# 138. Test Qualification Manifest

Can include:

```text
test counts
coverage
concurrency status
replay status
```

---

# 139. Regulatory Support Manifest

Optional:

```text
REGULATORY_SUPPORT_MANIFEST.json
```

---

# 140. Build provenance

Capture:

```text
commit
tag
builder
dependencies lock hash
```

---

# 141. Dependency locking

Runtime library dependencies should not necessarily pin exact patch versions for consumers.

But release qualification uses a lockfile.

---

# 142. `requirements.lock`

Used for deterministic CI/release environment.

---

# 143. Consumer dependency ranges

Use compatible ranges.

---

# 144. Avoid over-pinning

Library should not force unnecessary exact versions.

---

# 145. Upper bounds

Use when real incompatibility known.

---

# 146. Dependency bump classification

A dependency update can be PATCH if no public effect.

---

# 147. Dependency major bump

May require MINOR/MAJOR depending impact.

---

# 148. Optional dependencies

Version compatibility documented per extra.

---

# 149. Release cadence

No fixed calendar required.

Use milestone-driven releases.

---

# 150. Release readiness

Driven by:

```text
scope complete
quality gates
API stability
migration readiness
```

not arbitrary date.

---

# 151. Feature flags

Experimental features can ship disabled / marked experimental.

---

# 152. Experimental API

Can evolve faster.

---

# 153. Marking experimental

Doc + type metadata if desired.

---

# 154. Stable core vs experimental extension

A stable package may contain:

```text
stable core
experimental optional feature
```

if clearly isolated.

---

# 155. Breaking experimental API

Can occur in MINOR if documented.

---

# 156. But

Do not label core accounting primitives experimental after 1.0.

---

# 157. Core stability scope for 1.0

Must include at least:

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

---

# 158. Recommended 1.0 checklist

```text
core accounting stable
public API frozen
adapter contract v1 frozen
Django/PostgreSQL Production-qualified
SQLAlchemy/PostgreSQL Production-qualified or clearly scoped
FEC adapter qualified if advertised
reference integration qualified
reporting snapshot stable
migration path stable
docs complete
```

---

# 159. 1.0 does not require every future module

Not necessary:

```text
Consolidation
Advanced Reconciliation
Corporate Finance extensions
all possible standards
```

---

# 160. Backward compatibility after 1.0

PATCH:

```text
no breaking public changes
```

MINOR:

```text
backward-compatible additions
```

MAJOR:

```text
breaking changes allowed with migration guide
```

---

# 161. Behavioral compatibility

Even if signature unchanged, changing accounting result semantics can be breaking.

---

# 162. Example

If:

```text
same valid entry input
```

suddenly produces different posting semantics due to framework logic:

```text
potential breaking change
```

---

# 163. Regulatory semantic change

Different case.

If a new reference dataset changes rules:

```text
new reference/policy version
```

should be explicit, not hidden as framework behavior.

---

# 164. Bug fix vs breaking semantics

A correctness bug may require changing result.

Handle via:

```text
PATCH with explicit release note
```

if clearly a bug and prior behavior invalid.

For high-impact accounting behavior, consider MINOR and migration note even if technically bug fix.

---

# 165. Severity-based release classification

```text
low-risk bug -> PATCH
high-impact accounting correction -> PATCH or MINOR with explicit qualification
new behavior opt-in -> MINOR
breaking default behavior -> MAJOR after 1.0
```

---

# 166. Default changes

Changing a default can be breaking.

---

# 167. Example

Changing:

```text
undefined ratio handling
```

from:

```text
UNDEFINED
```

to:

```text
ZERO
```

is breaking semantics.

---

# 168. New enum value

Usually MINOR.

---

# 169. Removed enum value

MAJOR.

---

# 170. New public error subclass

MINOR.

---

# 171. Removed error code

MAJOR.

---

# 172. New optional DTO field

MINOR.

---

# 173. New required DTO field

MAJOR.

---

# 174. Serialized snapshot field

Requires schema version strategy.

---

# 175. Migration compatibility policy

Each stable release must support upgrade from:

```text
immediately previous stable MINOR
```

minimum.

---

# 176. Recommended

Support upgrade from last two minor lines if feasible.

---

# 177. Skip-version upgrade

Must be tested or documented unsupported.

---

# 178. Example

```text
1.2 -> 1.4
```

may require stepping through:

```text
1.3
```

if not directly qualified.

---

# 179. Upgrade guide

State exact path.

---

# 180. Roll-forward preference

For production failures after schema migration, prefer:

```text
fix forward
```

if downgrade unsafe.

---

# 181. Snapshot backward read

Readers should reject unsupported schema explicitly.

---

# 182. `UnsupportedSnapshotSchemaError`

---

# 183. Adapter mismatch

`AdapterContractMismatchError`.

---

# 184. Regulatory mismatch

`ReferenceDatasetCompatibilityError`.

---

# 185. Version compatibility objects

Potential:

```text
FrameworkCompatibility
AdapterCompatibility
ReferenceCompatibility
```

---

# 186. Runtime compatibility check

`AccountingApplication` can expose:

```python
accounting.check_compatibility()
```

advanced API.

---

# 187. Startup validation

Can verify:

```text
adapter contract
persistence schema
reference provider capability
```

---

# 188. Do not block runtime for unused optional capability

Capability-aware.

---

# 189. Example

If no regulatory reporting is used, missing reporting model capability need not block core entries.

---

# 190. Compatibility strictness

```text
STRICT
WARN
OFF
```

technical runtime config possible.

---

# 191. P1 recommendation

Production defaults:

```text
STRICT
```

for mandatory contracts.

---

# 192. Release channels

Conceptual:

```text
nightly
alpha
beta
rc
stable
```

---

# 193. Installation pre-release

Users opt-in:

```bash
pip install --pre pyaccountingkit
```

---

# 194. Stable users

Do not receive pre-release by default.

---

# 195. Nightly

Optional separate index/build artifact.

---

# 196. Release notes badges

Indicate:

```text
EXPERIMENTAL
BETA
RC
STABLE
```

---

# 197. RC feedback

No scope expansion.

Only:

```text
bugs
compatibility
docs clarity
```

---

# 198. Release ownership

A release should have one owner/approver.

---

# 199. Release checklist sign-off

Record:

```text
technical approval
quality approval
regulatory support review if applicable
```

---

# 200. Auditability of release process

Keep CI artifacts for stable tags.

---

# 201. Artifact retention

Long-term for stable:

```text
qualification manifest
checksums
SBOM
test summaries
golden checksums
```

---

# 202. Golden fixtures and releases

Golden fixture versions must be pinned.

---

# 203. Golden update

Requires review and reason.

---

# 204. Replay qualification

Stable release should replay selected historical snapshots.

---

# 205. Replay mismatch

Blocks release if unexplained.

---

# 206. Performance regression

Stable gate can block severe regressions on critical paths.

---

# 207. Performance threshold

Use baseline relative threshold.

---

# 208. Breaking performance regression

Not SemVer breaking, but release quality issue.

---

# 209. Changelog automation

Can derive entries from conventional commits/labels.

---

# 210. But

Accounting/regulatory impacts require human editorialization.

---

# 211. Conventional commit mapping

Optional:

```text
feat:
fix:
perf:
refactor:
docs:
test:
build:
ci:
```

---

# 212. Breaking marker

```text
BREAKING CHANGE:
```

---

# 213. Regulatory marker

Possible label:

```text
regulatory
```

---

# 214. Migration marker

```text
migration
```

---

# 215. Release PR

Recommended.

Contains:

```text
version bump
changelog
release notes
compatibility matrices
manifests
```

---

# 216. Version source

Single source of truth.

Recommended:

```text
pyproject.toml
```

or dynamic SCM versioning, but choose one.

---

# 217. Avoid duplicate versions

No manual mismatch between:

```text
pyproject.toml
__version__
docs
```

---

# 218. `__version__`

Generated/read from package metadata if possible.

---

# 219. Version bump tool

Optional:

```text
hatch
uv
bump-my-version
```

Tool choice not semantic.

---

# 220. Release checklist

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

# 221. Hotfix checklist

```text
reproduce defect
add regression test
patch minimal scope
run impacted full gates
publish PATCH
update changelog
```

---

# 222. Security hotfix

May bypass normal cadence but not correctness gates.

---

# 223. Regulatory urgent correction

Same principle.

---

# 224. Regulatory correction strategy

If source reference is wrong:

```text
new dataset release
```

If adapter interpretation is wrong:

```text
framework/import adapter patch
```

If policy formula is wrong:

```text
new policy version / framework fix
```

---

# 225. Historical impact assessment

Every high-impact correction asks:

```text
Which historical snapshots are affected?
Which reports should be rebuilt?
Which imports should be reprocessed?
Which policies should be superseded?
```

---

# 226. No silent rebuild

User/application decides.

---

# 227. Release note impact class

Possible:

```text
NO_DATA_IMPACT

NEW_DATA_ONLY

HISTORICAL_RECOMPUTATION_RECOMMENDED

MIGRATION_REQUIRED
```

---

# 228. `ReleaseImpactClass`

Useful in release metadata.

---

# 229. Known issues

Stable release can ship with MINOR issues only if documented.

---

# 230. BLOCKER/CRITICAL

Not allowed.

---

# 231. Deprecation manifest

Optional:

```text
DEPRECATIONS.json
```

---

# 232. Fields

```text
symbol
deprecated_in
replacement
removal_not_before
```

---

# 233. Version support policy

After 1.0, define:

```text
current minor
previous minor
```

or a wider window.

---

# 234. P1 recommendation

Start with:

```text
latest stable minor
+
previous stable minor security/critical fixes when feasible
```

---

# 235. Maintenance release

Patch releases may target old branch.

---

# 236. Forward port

Fixes should generally be forward-ported to main.

---

# 237. Cherry-pick discipline

Document commit references.

---

# 238. Breaking change proposal

Before MAJOR:

```text
ADR
migration plan
deprecation history
API diff
```

---

# 239. ADR linkage

`20_PYACCOUNTINGKIT_ADR_REGISTER.md` should reference release/versioning ADRs.

---

# 240. Release ADRs

| ID | Décision |
|---|---|
| ADR-REL-001 | PyAccountingKit utilise Semantic Versioning |
| ADR-REL-002 | Les pré-releases utilisent PEP 440 `a`, `b`, `rc` |
| ADR-REL-003 | Framework version et standard edition sont découplés |
| ADR-REL-004 | Regulatory dataset release est une dimension distincte |
| ADR-REL-005 | Public API contract possède un manifest versionné |
| ADR-REL-006 | Adapter contract possède sa propre version |
| ADR-REL-007 | Persistence schema version reste propre à l'adapter |
| ADR-REL-008 | Snapshot schema version est explicitement stockée |
| ADR-REL-009 | Les reference snapshots actifs ne changent jamais silencieusement |
| ADR-REL-010 | Une nouvelle policy version ne réécrit pas l'historique |
| ADR-REL-011 | Une nouvelle StatementDefinition version ne réécrit pas les reports historiques |
| ADR-REL-012 | Les import adapter versions sont pinées dans les batches |
| ADR-REL-013 | Le gel de l'API publique intervient avant `1.0.0` |
| ADR-REL-014 | Une RC est feature-frozen |
| ADR-REL-015 | Aucun BLOCKER/CRITICAL n'est accepté en stable |
| ADR-REL-016 | Les adapters Production sont qualifiés backend par backend |
| ADR-REL-017 | SQLite ne qualifie pas une persistence Production |
| ADR-REL-018 | Toute release stable publie une compatibility matrix |
| ADR-REL-019 | Toute release stable publie un qualification manifest |
| ADR-REL-020 | Toute release stable est taggée immuablement |
| ADR-REL-021 | Une release PyPI n'est jamais remplacée ; elle est yanked si nécessaire |
| ADR-REL-022 | Les corrections de code utilisent PATCH plutôt que `.postN` |
| ADR-REL-023 | Les migrations sont testées depuis la stable précédente |
| ADR-REL-024 | Les migrations destructives exigent une gouvernance renforcée |
| ADR-REL-025 | Les published snapshots ne sont jamais migrés destructivement |
| ADR-REL-026 | Les dépréciations stable précèdent toute suppression |
| ADR-REL-027 | Les error codes publics suivent la même discipline que l'API |
| ADR-REL-028 | Les golden fixture updates exigent une revue |
| ADR-REL-029 | Les high-impact accounting fixes documentent l'impact historique |
| ADR-REL-030 | Les dependency extras sont qualifiés séparément |
| ADR-REL-031 | Le core install reste indépendant des ORMs optionnels |
| ADR-REL-032 | `py.typed` fait partie de l'artefact stable si typing annoncé |
| ADR-REL-033 | Les RC et stable construisent wheel + sdist |
| ADR-REL-034 | Les artefacts publiés reçoivent des checksums SHA-256 |
| ADR-REL-035 | La publication utilise un environnement de build propre |
| ADR-REL-036 | Les changes réglementaires sont distingués des changes framework dans le changelog |
| ADR-REL-037 | Les breaking behavioral semantics sont traitées comme breaking API après 1.0 |
| ADR-REL-038 | Une correction réglementaire ne modifie pas silencieusement les snapshots historiques |
| ADR-REL-039 | `1.0.0` stabilise le core, pas nécessairement tous les modules futurs |
| ADR-REL-040 | Toute montée MAJOR dispose d'un migration guide |

---

# 241. Critères d'acceptation P1.6

```text
[ ] SemVer défini

[ ] PEP 440 pre-release défini

[ ] alpha / beta / rc / stable définis

[ ] politique 0.x définie

[ ] critères de 1.0 définis

[ ] framework version distincte des standards

[ ] regulatory dataset release distincte

[ ] public API contract version défini

[ ] adapter contract version défini

[ ] persistence schema version distincte

[ ] snapshot schema version défini

[ ] policy versioning défini

[ ] statement definition versioning défini

[ ] analytical definition versioning défini

[ ] import adapter versioning défini

[ ] public API freeze défini

[ ] PUBLIC_API_MANIFEST défini

[ ] PUBLIC_ERROR_CODES manifest défini

[ ] ADAPTER/PORT contract manifest défini

[ ] compatibility matrix définie

[ ] regulatory compatibility matrix définie

[ ] migration policy définie

[ ] fresh install + upgrade gates définis

[ ] published snapshots non destructivement migrés

[ ] deprecation policy définie

[ ] changelog format défini

[ ] release notes requirements définis

[ ] tag immutability définie

[ ] yanking policy définie

[ ] hotfix policy définie

[ ] security patch path défini

[ ] RC gate défini

[ ] stable gate défini

[ ] regulatory qualification gate défini

[ ] adapter Production gate défini

[ ] release qualification manifest défini

[ ] wheel/sdist build défini

[ ] checksum publication définie

[ ] dependency extras qualification définie

[ ] high-impact accounting correction process défini
```

---

# 242. Ordre d'implémentation recommandé

## REL-00 - Version primitives

```text
FrameworkVersion
PublicApiVersion
AdapterContractVersion
SchemaVersion
```

---

## REL-01 - Version source of truth

```text
pyproject version
__version__
build metadata
```

---

## REL-02 - API manifest

```text
PUBLIC_API_MANIFEST.json
```

---

## REL-03 - Error manifest

```text
PUBLIC_ERROR_CODES.json
```

---

## REL-04 - Adapter contract manifest

```text
ADAPTER_CONTRACT_MANIFEST.json
```

---

## REL-05 - Compatibility matrices

```text
runtime compatibility
regulatory compatibility
```

---

## REL-06 - Migration qualification

```text
fresh install
upgrade previous stable
post-migration controls
```

---

## REL-07 - Release qualification manifest

```text
RELEASE_QUALIFICATION_MANIFEST.json
```

---

## REL-08 - Build pipeline

```text
wheel
sdist
clean install
checksums
```

---

## REL-09 - Pre-release pipeline

```text
alpha
beta
rc
```

---

## REL-10 - Stable publishing

```text
tag
PyPI
docs
release notes
```

---

## REL-11 - Hotfix workflow

```text
patch branch
regression test
publish
```

---

## REL-12 - 1.0 freeze

```text
API freeze
adapter contract v1
migration compatibility
full golden/replay
```

---

# 243. Exemple de roadmap de version

Une progression possible :

```text
0.1.0a1
    foundations

0.1.0b1
    accounting core

0.1.0rc1
    accounting core qualification

0.1.0
    first stable development milestone

0.2.0
    references / charts / policies hardened

0.3.0
    imports / reporting

0.4.0
    analysis / subledgers

0.5.0
    public API stabilization

0.9.0
    1.0 release candidate line

1.0.0
    stable public core
```

Cette roadmap est indicative et doit rester pilotée par les gates.

---

# 244. Exemple de release RC

```text
Target:
    0.5.0rc1

Requirements:
    feature freeze
    API manifest
    adapter contract manifest
    all PostgreSQL concurrency tests green
    migration from 0.4.x green
    FEC golden suite green
    regulatory reference suite green
    docs complete
```

---

# 245. Exemple de patch réglementaire

```text
Problem:
    reporting adapter interprets a candidate hint as executable

Fix:
    enforce human_validation_required

Version:
    0.5.1

Impact:
    framework behavior corrected
    historical published snapshots unchanged
    affected reports may be regenerated explicitly
```

---

# 246. Exemple d'upgrade réglementaire

```text
Existing:
    fr-pcg:2026
    ReferenceSnapshot R1

New dataset:
    R2

Process:
    install dataset R2
    create ReferenceSnapshot R2
    run impact analysis
    create new ReportingProfile
    validate
    activate

No:
    mutate R1 in place
```

---

# 247. Exemple de breaking public API

Old:

```python
accounting.entries.finalize(...)
```

New:

```python
accounting.entries.post(...)
```

Before 1.0:

```text
possible in next 0.x MINOR with migration note
```

After 1.0:

```text
deprecate
then remove in MAJOR
```

---

# 248. Exemple de migration schema

```text
1.3.2 -> 1.4.0

Migration:
    add JournalEntry.revision

Steps:
    add nullable revision
    backfill deterministic revision
    enforce not-null
    run concurrency suite
    run accounting controls
```

---

# 249. Exemple de qualification release

```text
Framework:
    PASS

Public API diff:
    PASS

Adapter contract:
    PASS

Django/PostgreSQL:
    PRODUCTION

SQLAlchemy/PostgreSQL:
    PRODUCTION

FEC:
    PRODUCTION

Regulatory references:
    PASS

Golden:
    PASS

Replay:
    PASS

Migration:
    PASS
```

---

# 250. Matrice de versioning

| Élément | Version | Scope |
|---|---|---|
| Framework | SemVer | package |
| Standard | edition | réglementaire |
| Dataset | release id | corpus réglementaire |
| Public API | contract version | consommateurs |
| Adapter contract | contract version | adapter authors |
| DB schema | migration version | persistence |
| Snapshot | schema version | artefact historique |
| Policy | domain version | comportement |
| Statement Definition | definition version | reporting |
| Analysis Definition | definition version | analytique |
| Company Chart | business version | entité |
| Reporting Profile | business version | entité |

---

# 251. Matrice de release type

| Type | Features | Breaking | Production |
|---|---:|---:|---:|
| alpha | oui | oui | non |
| beta | limitées | encore possibles | non |
| rc | non | non souhaité | qualification |
| stable | gelées | selon SemVer | oui |

---

# 252. Matrice d'impact

| Changement | Version après 1.0 |
|---|---|
| Bug interne non breaking | PATCH |
| Nouvelle feature compatible | MINOR |
| Nouvelle policy optionnelle | MINOR |
| Nouveau adapter optionnel | MINOR |
| Breaking public API | MAJOR |
| Removal d'API dépréciée | MAJOR |
| Correction sécurité | PATCH |
| Correction accounting semantics clairement erronée | PATCH/MINOR selon impact |
| Nouveau standard edition support | MINOR |
| Nouveau regulatory dataset compatible | pas nécessairement framework bump |

---

# 253. Frontière avec le prochain document

Le prochain jalon recommandé est :

```text
18_PYACCOUNTINGKIT_CFA_FRA_EXTRACTION_AND_MIGRATION_MAP.md
```

Il devra formaliser :

```text
what is reusable from CFA FRA
what must be rewritten
what is a golden oracle
what belongs to adapters
what belongs to domain
migration sequence
evidence matrix
```

---

# 254. Conclusion

La stratégie de release de PyAccountingKit repose sur une séparation stricte des dimensions de version :

```text
Framework
Reference Dataset
Standard Edition
Policy
Statement Definition
Company Chart
Public API
Adapter Contract
Persistence Schema
Snapshot Schema
```

Les principes majeurs sont :

```text
SemVer for the package

PEP 440 for pre-releases

API freeze before stable

No silent regulatory upgrade

No silent policy replacement

No destructive historical snapshot migration

Adapter contracts are versioned

Database migrations are qualified

Public error codes are stable contracts

Stable tags are immutable

RC means feature freeze

Stable means qualification gates passed

1.0 stabilizes the core, not every future capability
```

Le P1.6 fournit ainsi le cadre de gouvernance nécessaire pour faire évoluer PyAccountingKit sans perdre la reproductibilité comptable, la compatibilité des adapters, la stabilité de l'API publique ni la traçabilité réglementaire.

---

**Prochain document recommandé :**

```text
18_PYACCOUNTINGKIT_CFA_FRA_EXTRACTION_AND_MIGRATION_MAP.md
```
