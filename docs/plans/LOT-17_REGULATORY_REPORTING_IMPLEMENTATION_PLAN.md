# LOT-17 — Regulatory Reporting Implementation Plan

> **Projet** : PyAccountingKit  
> **Lot** : LOT-17 — Regulatory Reporting  
> **Target line** : `0.3.0b2 -> 0.3.0`  
> **Baseline** : `0.3.0b1` / LOT-16 Financial Statements Engine  
> **Statut** : plan d'implémentation exécutable  
> **Branche** : `feat/lot-17-regulatory-reporting`

---

## 1. Objectif

LOT-17 transforme les projections financières qualifiées de LOT-16 en reporting réglementaire versionné, validé, rejouable et exportable sans créer une seconde source comptable.

La chaîne canonique est :

```text
Posted Accounting Data
        |
        v
TrialBalance / Snapshot
        |
        v
FinancialStatementEngine              LOT-16
        |
        v
FinancialStatementResult
        |
        v
ReportSnapshot
        |
        +-------------------------------+
        |                               |
        v                               v
RegulatoryReportingProfile     ReferenceReportingModel
        |                               |
        +---------------+---------------+
                        |
                        v
               Regulatory Mapping
                        |
                        v
              Regulatory Validation
                        |
                        v
                Regulatory Report
                        |
                        v
             RegulatoryExportDefinition
                        |
                        v
              RegulatoryExportArtifact
                        |
                        v
               ReportEvidenceBundle
```

Principe central :

```text
Regulatory Reporting
    = projection / validation / export
    != accounting mutation
```

Un exporter ne recalcule jamais la comptabilité et ne contourne jamais le `FinancialStatementEngine`.

---

## 2. Sources d'autorité

L'implémentation doit respecter, par ordre fonctionnel :

1. `docs/ROADMAP.md` — scope, dépendances, gates et DoD LOT-17 ;
2. `docs/specs/03_reporting-analytics/13_PYACCOUNTINGKIT_FINANCIAL_STATEMENTS_AND_REGULATORY_REPORTING_ARCHITECTURE.md` ;
3. `docs/specs/04_integration-infra/19_PYACCOUNTINGKIT_REGULATORY_FRAMEWORK_INTEGRATION_MATRIX.md` ;
4. `docs/specs/04_integration-infra/05_PYACCOUNTINGKIT_ACCOUNTING_REFERENCE_DATA_ARCHITECTURE.md` et les ADR de reference snapshots ;
5. LOT-16 (`FinancialStatementResult`, `ReportSnapshot`, mappings, contrôles) ;
6. `AccountingReferenceProviderProtocol` comme frontière d'accès aux référentiels ;
7. les datasets réglementaires qualifiés présents dans `docs/referentiels/` / `resources/` uniquement comme données de référence, jamais comme dépendance framework du domaine.

---

## 3. Scope canonique LOT-17

Le scope roadmap est conservé sans extension opportuniste :

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

LOT-17 doit également fournir les primitives minimales nécessaires pour :

- appliquer un profil réglementaire versionné à un `ReportSnapshot` ;
- mapper les lignes d'état financier vers les nœuds d'un modèle réglementaire ;
- exécuter des validations réglementaires déterministes ;
- générer un modèle de rapport réglementaire indépendant d'un format de rendu ;
- exporter sans recalcul comptable ;
- pinner les versions et checksums nécessaires au replay ;
- produire les preuves de provenance et de qualification.

---

## 4. Non-objectifs

LOT-17 ne doit pas dériver vers :

- XBRL complet ou moteur générique de taxonomie externe ;
- moteur fiscal français exhaustif ;
- conformité DGFiP déclarative globale ;
- IFRS disclosure engine complet ;
- consolidation ;
- ratios financiers / SIG / CAF / FRNG / BFR ;
- subledgers ;
- génération PDF/Excel avancée ;
- mutation du ledger ;
- création automatique de comptes ou mappings ;
- auto-validation de hints réglementaires candidats.

Ces sujets restent hors du bounded context ou appartiennent aux lots suivants.

---

## 5. Invariants non négociables

### 5.1 Source comptable unique

```text
JournalEntry -> Ledger -> TrialBalance -> FinancialStatement -> RegulatoryReport
```

Il est interdit de produire un montant réglementaire directement depuis des écritures ou comptes en contournant LOT-16, sauf futur mécanisme explicitement documenté comme source de reporting alternative.

### 5.2 Isolation AccountingEntity

Tout objet participant à une même exécution réglementaire doit appartenir à la même `AccountingEntity`.

Doivent échouer fail-closed :

- report snapshot d'une autre entité ;
- profil d'une autre entité lorsqu'il est entity-scoped ;
- mapping réglementaire d'une autre entité ;
- evidence bundle mélangeant plusieurs entités.

### 5.3 Reference snapshot obligatoire

Tout `RegulatoryReportingProfile` exécutable doit pinner :

```text
reference_snapshot_id
reference_snapshot_checksum
framework / standard
edition / version
```

La résolution depuis « latest/current » est interdite pendant une exécution ou un replay.

### 5.4 Structure officielle != hint candidat

Les datasets peuvent fournir :

```text
official reporting structure
+
candidate account / statement hints
```

Ces dimensions restent séparées.

Si :

```text
account_hints_executable = false
```

alors aucun hint ne peut devenir automatiquement un mapping exécutable.

Si :

```text
human_validation_required = true
```

alors le statut initial doit rester candidat / review-required.

### 5.5 Mapping explicite et fail-closed

Un nœud obligatoire sans mapping valide doit générer une erreur ou un résultat de validation bloquant selon le profil.

Aucune heuristique basée uniquement sur l'égalité des codes n'est autorisée.

### 5.6 Renderer != exporter != moteur de calcul

```text
RegulatoryReportBuilder
    calcule / assemble le modèle réglementaire

Renderer
    transforme un modèle déjà calculé en représentation

Exporter
    produit un artefact et ses preuves
```

Ni renderer ni exporter ne doivent :

- relire le ledger pour recalculer des montants ;
- modifier des mappings ;
- modifier un snapshot ;
- appliquer une logique comptable cachée.

### 5.7 Déterminisme

À inputs pinnés identiques :

```text
same report checksum
same validation results
same export payload checksum
same evidence checksum
```

Les timestamps de génération peuvent différer mais ne doivent pas contaminer le checksum métier canonique.

---

## 6. Modèle de domaine cible

### 6.1 RegulatoryReportingProfile

Fichier cible :

`src/pyaccountingkit/domain/reporting/regulatory_profile.py`

Proposition :

```text
RegulatoryReportingProfile
|-- profile_id
|-- accounting_entity_id?        # None si profil global réutilisable
|-- code
|-- framework
|-- jurisdiction
|-- edition
|-- version
|-- status
|-- reference_snapshot_id
|-- reference_snapshot_checksum
|-- financial_statement_definition_ids
|-- regulatory_mapping_set_id
|-- export_definition_ids
|-- effective_from
|-- effective_to?
|-- metadata
|-- checksum
```

Statuts recommandés :

```text
DRAFT
REVIEW_REQUIRED
VALIDATED
ACTIVE
SUPERSEDED
ARCHIVED
```

Seuls les profils explicitement exécutables (`ACTIVE` selon la policy retenue) peuvent produire un rapport courant.

### 6.2 ReferenceReportingModel

Le domaine ne doit pas dépendre directement du package de données externe.

Introduire un modèle canonique minimal :

```text
ReferenceReportingModel
|-- model_id
|-- framework
|-- edition
|-- reference_snapshot_id
|-- reference_snapshot_checksum
|-- nodes
|-- relations
|-- source_metadata
|-- checksum
```

Chaque nœud :

```text
ReferenceReportingNode
|-- node_id
|-- code
|-- label
|-- node_type
|-- parent_node_id?
|-- order
|-- required
|-- value_type
|-- sign / presentation metadata
|-- human_validation_required
|-- account_hints_executable
|-- provenance
```

### 6.3 Regulatory mapping

Conserver la séparation :

```text
CompanyAccount -> StatementLine        LOT-16
StatementLine -> ReferenceReportingNode LOT-17
```

Objets cibles :

```text
RegulatoryStatementMapping
RegulatoryMappingSet
RegulatoryMappingStatus
RegulatoryMappingProvenance
```

Champs clés :

```text
mapping_id
statement_line_code
reference_node_id
allocation Decimal
status
provenance
review_required
effective_from/effective_to
```

Les mappings `CANDIDATE` / `REVIEW_REQUIRED` sont non exécutables.

### 6.4 Regulatory report

Le rapport calculé doit être indépendant du format d'export :

```text
RegulatoryReport
|-- accounting_entity_id
|-- profile_id / version
|-- framework / edition
|-- reference_snapshot_id
|-- source_report_snapshot_id
|-- source_report_checksum
|-- mapping_set_id / version / checksum
|-- as_of
|-- nodes
|-- validations
|-- checksum
```

Chaque valeur :

```text
RegulatoryNodeValue
|-- node_id
|-- code
|-- label
|-- amount?
|-- text_value?
|-- comparative_amount?
|-- source_statement_lines
|-- provenance
```

### 6.5 Regulatory validation

Objets recommandés :

```text
RegulatoryValidationRule
RegulatoryValidationResult
RegulatoryValidationReport
```

Sévérités :

```text
INFO
WARNING
ERROR
BLOCKING
```

Statuts :

```text
PASS
FAIL
NOT_APPLICABLE
```

Contrôles initiaux :

- nœuds obligatoires présents ;
- mapping obligatoire complet ;
- références pinnées et cohérentes ;
- profil effectif à `as_of` ;
- candidats non exécutés ;
- flags `human_validation_required` conservés ;
- allocations = 1 lorsque one-to-many ;
- contrôle de totaux/relation lorsqu'exposé par le modèle de référence ;
- source report snapshot non stale lorsque le profil l'exige.

### 6.6 RegulatoryExportDefinition

```text
RegulatoryExportDefinition
|-- export_definition_id
|-- code
|-- version
|-- profile_id
|-- renderer_id
|-- media_type
|-- schema_version
|-- effective_from/effective_to
|-- required_node_ids
|-- metadata
|-- checksum
```

Le domaine définit le contrat, pas l'I/O concrète.

### 6.7 RegulatoryExportArtifact

```text
RegulatoryExportArtifact
|-- artifact_id
|-- accounting_entity_id
|-- regulatory_report_checksum
|-- profile_id / profile_version
|-- reference_snapshot_id
|-- export_definition_id / version
|-- media_type
|-- payload_checksum
|-- generated_at
|-- payload
|-- metadata
```

Le `payload_checksum` doit être calculé sur les octets réellement exportés.

### 6.8 ReportEvidenceBundle

```text
ReportEvidenceBundle
|-- evidence_id
|-- accounting_entity_id
|-- report_snapshot_checksum
|-- regulatory_report_checksum
|-- profile_checksum
|-- reference_snapshot_id/checksum
|-- regulatory_mapping_checksum
|-- export_definition_checksum
|-- export_artifact_checksum
|-- validation_checksum
|-- source_refs
|-- checksum
```

But : rendre le résultat audit/replay-friendly sans inclure une dépendance à un framework de persistence.

---

## 7. Ports et frontières hexagonales

### 7.1 ReferenceReportingModelProviderProtocol

Nouveau port recommandé :

`src/pyaccountingkit/ports/regulatory_reporting.py`

```python
class ReferenceReportingModelProviderProtocol(Protocol):
    def get_reporting_model(
        self,
        *,
        reference_snapshot_id: str,
        framework: str,
        edition: str,
        model_code: str,
    ) -> ReferenceReportingModel: ...
```

Le provider doit échouer fail-closed si les coordonnées exactes ne sont pas trouvées.

### 7.2 RegulatoryRendererProtocol

```python
class RegulatoryRendererProtocol(Protocol):
    renderer_id: str

    def render(
        self,
        report: RegulatoryReport,
        definition: RegulatoryExportDefinition,
    ) -> bytes: ...
```

Le renderer est pur autant que possible.

### 7.3 Pas de port de posting

LOT-17 est read-side. Aucun `PostingOrchestrator`, repository de journal ou UoW comptable ne doit être nécessaire pour construire un rapport réglementaire depuis un snapshot.

---

## 8. Application services

### 8.1 RegulatoryReportingService

Responsabilités :

1. recevoir un `ReportSnapshot` ;
2. valider entité / date / profile status / effective date ;
3. résoudre le `ReferenceReportingModel` pinné ;
4. valider le snapshot de référence ;
5. appliquer uniquement un `RegulatoryMappingSet` exécutable ;
6. produire les `RegulatoryNodeValue` ;
7. exécuter les validations ;
8. produire un checksum déterministe ;
9. retourner un `RegulatoryReport` immuable.

### 8.2 RegulatoryExportService

Responsabilités :

1. recevoir un `RegulatoryReport` déjà calculé ;
2. vérifier la compatibilité avec `RegulatoryExportDefinition` ;
3. appeler le renderer configuré ;
4. calculer SHA-256 du payload ;
5. produire `RegulatoryExportArtifact` ;
6. produire `ReportEvidenceBundle`.

Interdit : recalculer les montants depuis le ledger ou la trial balance.

---

## 9. Reference upgrade plan

Un changement de référentiel n'écrase jamais l'historique.

Introduire :

```text
ReferenceUpgradePlan
|-- plan_id
|-- from_snapshot_id
|-- to_snapshot_id
|-- profile_id
|-- node_changes
|-- mapping_impacts
|-- validation_impacts
|-- requires_human_review
|-- status
|-- checksum
```

Workflow :

```text
new reference snapshot
        |
        v
compare reporting model
        |
        v
ReferenceUpgradePlan
        |
        +--> unchanged mappings
        +--> candidate migrations
        +--> review-required mappings
        +--> removed/added nodes
        |
        v
human validation
        |
        v
new RegulatoryReportingProfile version
```

Aucun upgrade ne modifie rétroactivement un report publié.

---

## 10. Découpage d'implémentation

### Step 1 — Errors and common enums

Créer les erreurs spécifiques avec codes stables :

```text
REGULATORY_PROFILE_NOT_ACTIVE
REGULATORY_PROFILE_NOT_EFFECTIVE
REGULATORY_REFERENCE_MISMATCH
REGULATORY_MAPPING_NOT_EXECUTABLE
REGULATORY_MAPPING_INCOMPLETE
REGULATORY_MODEL_NOT_FOUND
REGULATORY_VALIDATION_FAILED
REGULATORY_EXPORT_INCOMPATIBLE
REGULATORY_EXPORT_FAILED
REGULATORY_EVIDENCE_MISMATCH
REGULATORY_UPGRADE_REVIEW_REQUIRED
```

Ajouter au `PUBLIC_ERROR_CODES.json` uniquement à la fin du lot lorsque la surface est stabilisée.

### Step 2 — Regulatory profile aggregate

Implémenter `regulatory_profile.py` :

- lifecycle ;
- effective date ;
- reference snapshot pinning ;
- checksum ;
- entity scope optionnel et règles d'exécution.

Tests adversariaux : DRAFT, future, expired, wrong entity, wrong reference snapshot.

### Step 3 — Reference reporting model

Créer le modèle canonique + provider port + in-memory reference adapter.

Tester :

- structure officielle ;
- ordre déterministe ;
- parentage ;
- duplicate node ids/codes ;
- checksum ;
- snapshot mismatch ;
- unknown model fail-closed.

### Step 4 — Regulatory mappings

Implémenter `RegulatoryMappingSet` et mapping line -> reference node.

Tester :

- candidate non exécutable ;
- review-required non exécutable ;
- validated/executable ;
- one-to-many Decimal allocation ;
- unknown source line ;
- unknown target node ;
- entity mismatch ;
- effective dating.

### Step 5 — Regulatory reporting engine/service

Construire `RegulatoryReport` depuis un `ReportSnapshot` LOT-16.

Doit conserver :

```text
report snapshot checksum
statement definition coordinates
mapping coordinates
profile coordinates
reference snapshot coordinates
```

Qualification : PCG + SYSCOHADA fixtures minimales.

### Step 6 — Validation engine

Implémenter validation structurelle et réglementaire déterministe.

Les règles bloquantes doivent pouvoir empêcher l'export.

Aucune validation ne doit muter le report.

### Step 7 — Renderer/exporter separation

Implémenter :

- `RegulatoryRendererProtocol` ;
- renderer JSON canonique comme référence comportementale ;
- éventuellement CSV tabulaire seulement si le modèle s'y prête sans perte ;
- `RegulatoryExportService` ;
- artifact SHA-256.

Le JSON canonique sert de première qualification, pas de promesse d'API publique stable.

### Step 8 — Evidence bundle

Créer `ReportEvidenceBundle` et prouver le lien :

```text
ReportSnapshot
+ Profile
+ ReferenceSnapshot
+ MappingSet
+ Validation
+ ExportDefinition
+ Payload
```

Le bundle doit être immutable et checksummé.

### Step 9 — Reference upgrade planning

Implémenter le diff minimal entre deux modèles réglementaires :

- added node ;
- removed node ;
- changed required flag ;
- changed hierarchy ;
- changed human-validation flags ;
- mapping impacts.

Toute ambiguïté devient `requires_human_review=True`.

### Step 10 — Golden / replay / safety qualification

Ajouter :

```text
tests/unit/domain/test_regulatory_profile.py
tests/unit/domain/test_regulatory_reporting.py
tests/unit/domain/test_regulatory_validation.py
tests/unit/domain/test_regulatory_export.py
tests/unit/domain/test_reference_upgrade_plan.py
tests/contract/test_reference_reporting_provider.py
tests/golden/regulatory/test_pcg_regulatory_reporting.py
tests/golden/regulatory/test_syscohada_regulatory_reporting.py
tests/replay/test_regulatory_report_replay.py
```

Scénario replay canonique :

```text
same TrialBalance source
same ReportSnapshot
same RegulatoryReportingProfile
same ReferenceReportingModel
same RegulatoryMappingSet
same ExportDefinition
        |
        v
same RegulatoryReport checksum
same validation checksum
same payload checksum
same evidence checksum
```

### Step 11 — Release metadata 0.3.0b2

Mettre à jour :

```text
pyproject.toml
README.md
CHANGELOG.md
PUBLIC_API_MANIFEST.json
PUBLIC_ERROR_CODES.json
ADAPTER_CONTRACT_MANIFEST.json
REGULATORY_COMPATIBILITY_MATRIX.json
```

La matrice doit distinguer :

```text
reference structure qualification
regulatory reporting engine qualification
framework-specific golden qualification
production regulatory compliance claim
```

Ne jamais transformer une qualification technique alpha/beta en déclaration juridique de conformité.

### Step 12 — 0.3.0 release qualification

LOT-17 ouvre la route vers `0.3.0rc1`, mais la stable nécessite un gate transverse distinct :

```text
LOT-14 Generic Import
LOT-15 FEC Adapter
LOT-16 Financial Statements
LOT-17 Regulatory Reporting
        |
        v
end-to-end golden/replay qualification
        |
        v
0.3.0rc1
        |
        v
0.3.0 stable
```

---

## 11. File inventory cible

### Domain

```text
src/pyaccountingkit/domain/reporting/regulatory_profile.py
src/pyaccountingkit/domain/reporting/reference_reporting_model.py
src/pyaccountingkit/domain/reporting/regulatory_mapping.py
src/pyaccountingkit/domain/reporting/regulatory_report.py
src/pyaccountingkit/domain/reporting/regulatory_validation.py
src/pyaccountingkit/domain/reporting/regulatory_export.py
src/pyaccountingkit/domain/reporting/report_evidence.py
src/pyaccountingkit/domain/reporting/reference_upgrade.py
```

### Ports

```text
src/pyaccountingkit/ports/regulatory_reporting.py
```

### Application

```text
src/pyaccountingkit/application/reporting/regulatory_reporting_service.py
src/pyaccountingkit/application/reporting/regulatory_export_service.py
```

### Reference adapters

```text
src/pyaccountingkit/adapters/in_memory/reference_reporting_model_provider.py
src/pyaccountingkit/adapters/regulatory/json_renderer.py
```

Le placement final peut être ajusté pour respecter les conventions déjà présentes, mais les frontières domain / application / port / adapter ne doivent pas être fusionnées.

---

## 12. API design rules

- utiliser `Decimal` pour toute allocation ;
- utiliser les value objects existants pour entity/date/money ;
- dataclasses immuables (`frozen=True`, `slots=True`) pour snapshots/results/artifacts ;
- checksums SHA-256 sur sérialisation canonique déterministe ;
- aucun `datetime.now()` direct dans le domaine ; utiliser un `Clock` côté application si nécessaire ;
- aucun `eval()` ;
- aucun import Django/SQLAlchemy/FastAPI dans core/domain/ports ;
- pas de code réglementaire spécifique hardcodé comme vérité universelle ;
- ne pas utiliser `account_code == reference_node_code` comme mapping implicite ;
- ne pas transformer un candidate hint en mapping validé ;
- toute erreur exécutable doit être typée et stable.

---

## 13. Gates LOT-17

Roadmap :

```text
G4/G5
GR GS GAPI
```

Pendant développement, appliquer également :

```text
GA
GC (absence de mutation/bypass)
GSEC
```

Commandes minimales avant push :

```bash
python -m ruff format src tests scripts
python -m ruff check src tests scripts
python -m ruff format --check src tests scripts
python -m mypy src
python -m pytest tests/unit tests/property tests/contract tests/golden tests/replay tests/concurrency -v --tb=short
python scripts/qualify_release.py --full
python -m bandit -r src/ -c pyproject.toml
python -m pip_audit
```

---

## 14. Definition of Done LOT-17

Le lot ne peut être mergé que si :

```text
[ ] RegulatoryReportingProfile versionné et effectif
[ ] profile pins exact reference snapshot id + checksum
[ ] ReferenceReportingModel accessible par port
[ ] official structure séparée des candidate hints
[ ] account_hints_executable=false exécuté comme contrainte fail-closed
[ ] human_validation_required préservé de bout en bout
[ ] candidate / review-required mappings non exécutables
[ ] StatementLine -> ReferenceReportingNode mapping explicite
[ ] AccountingEntity isolation testée
[ ] RegulatoryReport immutable/checksummé
[ ] validation report immutable/checksummé
[ ] renderer/exporter ne recalculent aucune donnée comptable
[ ] export payload checksum présent
[ ] ReportEvidenceBundle complet/checksummé
[ ] reference upgrade plan préserve historique et demande review si ambigu
[ ] PCG golden green
[ ] SYSCOHADA golden green
[ ] replay réglementaire déterministe green
[ ] CI Python 3.11/3.12/3.13 green
[ ] quality gates green
[ ] package qualification green
[ ] Security/dependency audit green
[ ] manifests + README + CHANGELOG alignés sur 0.3.0b2
[ ] aucune claim de conformité réglementaire non qualifiée
```

---

## 15. Critères de sortie vers 0.3.0rc1

Après merge de LOT-17, créer un gate de qualification transverse `0.3.0` couvrant :

```text
FEC source
  -> Generic Import
  -> Posting
  -> Trial Balance
  -> Financial Statements
  -> Report Snapshot
  -> Regulatory Profile
  -> Regulatory Report
  -> Validation
  -> Export Artifact
  -> Evidence Bundle
```

avec :

```text
no silent row drop
no cross-entity leakage
no candidate auto-execution
no stale-reference execution
no reporting recalculation in exporter
full checksum chain
replay deterministic
```

La release stable `0.3.0` ne sera déclarée que lorsque ce parcours end-to-end et les gates G4/G5 applicables seront verts.

---

## 16. Ordre de travail recommandé

```text
1. errors/enums
2. RegulatoryReportingProfile
3. ReferenceReportingModel + provider port
4. RegulatoryMappingSet
5. RegulatoryReportingService
6. RegulatoryValidation
7. ExportDefinition + renderer port
8. RegulatoryExportService
9. ReportEvidenceBundle
10. ReferenceUpgradePlan
11. golden/replay/adversarial tests
12. metadata 0.3.0b2
13. PR qualification + merge
14. 0.3.0rc1 cross-lot qualification
```

Aucune implémentation de format réglementaire supplémentaire ne doit précéder la stabilisation de cette chaîne générique.
