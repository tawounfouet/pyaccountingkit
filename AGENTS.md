# AGENTS.md — PyAccountingKit

Kit comptable Python (partie double) en architecture hexagonale, piloté par documentation. Aucun code n'est écrit avant que sa spec et son plan ne soient posés : **d'abord `docs/`, ensuite le code**.

## Commandes

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"        # dev = pytest, pytest-timeout, ruff, mypy, hypothesis

ruff check src/ tests/         # lint (rules E,F,I,B,UP)
ruff format --check src/ tests/
mypy src/                      # strict (pyproject)
pytest tests/unit tests/property tests/contract   # G0/G1 core
```

- Full suite (`tests/{integration,concurrency,replay,migration,golden,performance}`) touche PostgreSQL/adapter réel : ce sont des gates **G3/Nightly**, pas la boucle locale.
- Les manifests racine (`PUBLIC_API_MANIFEST.json`, `PUBLIC_ERROR_CODES.json`, `ADAPTER_CONTRACT_MANIFEST.json`, `REGULATORY_COMPATIBILITY_MATRIX.json`) sont **générés** par `scripts/generate_*` — ne pas les éditer à la main.
- `scripts/validate_architecture.py` = guard d'import-architecture (gate GA).

## Architecture (contraintes non négociables du `GA`)

Direction stricte `adapters → application → domain`. **`domain` n'importe JAMAIS Django, SQLAlchemy, FastAPI.** Dépendance dirigée vers les `ports/`, concrétisation dans `adapters/`.

- `core/` : primitives (Money, Currency, Clock, Revision, Idempotency) — aucun dépendance métier/ORM.
- `domain/` : modèle métier pur, framework-free (subdivisé par bounded context : journals, charts, references, policies, ledger, closing, controls, audit, traceability, imports, reporting, analysis, subledgers, reconciliation, consolidation).
- `application/` : use-cases, orchestre domain + ports.
- `ports/` : contrats (repositories, unit_of_work, references, valuation, exchange_rates, artifacts, audit, outbox, queries, reconciliation).
- `adapters/` : `in_memory` (**référence comportementale, ne qualifie PAS la production**), puis `django`, `sqlalchemy`, `regulatory`, `imports/fec`, `reconciliation`.
- `integrations/` : glue vers `cfa_fra` et `regulatory_framework`.
- `public/` : seul surface exposée, stable et dûment typée.

## Cores invariants (`GC`, `GP`, `GI`)

- `Money` = **Decimal uniquement, jamais de float** (arrondi intermédiaire interdit).
- `Clock` injectable pour le temps métier — pas de `datetime.now()` direct dans le domaine.
- Idempotence par clé, `Revision` pour verrou optimiste ; mutation comptable = transaction atomique + rollback sans état partiel.
- Écriture `POSTED` = **immuable** ; correction/contrepassation crée une **nouvelle** écriture inverse, ne mute jamais la source. Aucun chemin `DRAFT → POSTED` court-circuité.
- Équilibre `Σ débit == Σ crédit`, débit/crédit mutuellement exclusifs, multi-entité isolée.
- Bounded contexts étanches : pas de dépendance transversale interdite.

## Données & réglementaire

- `domain/` ne lit **jamais** `data/` ni les référentiels directement. Toute consommation passe par le port `AccountingReferenceProvider` (`ports/references.py`) + `adapters/regulatory/*`.
- Les normes officielles (PCG 2026, SYSCOHADA, OHADA EBNL, CEMAC…) vivent **uniquement** dans `resources/regulatory-accounting-data-framework/` (framework amont). Ne pas dupliquer de fichier normatif dans `data/`.
- `data/` : `samples/` versionné (synthétique), `local/`, `cache/`, `generated/` gitignorés (jamais de data comptable réelle/confidentielle — `.gitignore` exclut `*.private.*`).
- Séparation tests : `tests/fixtures/` = entrées déterministes ; `tests/golden/` = oracles certifiés (CFA FRA, réglementaire) ; `data/samples/` = démo publique.

## Comportement & migrations CFA FRA

- `resources/cfa_fra_django_mvp_sprint_7/` = **oracle comportemental** de l'ancien moteur Django. Parité **au centime** exigée (`GM`), pas d'approximation.
- Migration pattern **Strangler**, jamais de dual-write de mutations comptables.
- Datasets réglementaires canalisés dans `docs/referentiels/datasets/` + schémas JSON de validation `docs/referentiels/schemas/`.

## Versioning & quality gates

Milestones pilotés par **scope + DoD + gates** (jamais par date). `0.0.1 → 1.0.0` puis `1.1.0` (réconciliation), `1.2.0` (consolidation) ; pre-releases PEP 440 (`aN`, `bN`, `rcN`).

- Gates `G0` (hygiène) → `G1` (domaine pur) → `G2` (adaptateurs in-memory) → `G3` (PostgreSQL réel) → `G4` (parité API) → `G5` (release). Spécialisées : `GA` invariants, `GC` rounding, `GP` concurrence, `GR` conformité, `GI` immutabilité, `GS` snapshot/replay, `GAPI` surface API, `GM` parité migration, `GSEC` supply-chain.
- Une release stable n'est **jamais un simple tag** : qualification + compatibilité + replay + migration + validation package + evidence.
- Détails opérationnels par release dans `docs/plans/PLAN-00…09` (DoD, matrice gates, scénarios de recette).

## Docs (source de vérité)

- `docs/specs/` : 24 specs canoniques (00–23) + `INDEX.md` (priorités P0.1–P2.3) + registre des **785 ADR** (`20_PYACCOUNTINGKIT_ADR_REGISTER.md`) — consulter l'ADR avant toute décision structurante.
- `docs/ROADMAP.md` : 39 lots `LOT-00…38`, matrice des gates, DoD.
- `docs/plans/` : plans d'implémentation par jalon. Commits/conventions : voir `CONTRIBUTING.md` (Conventional Commits).

## Conventions

- Docs et commentaires en **français** ; identifiants de code en anglais. Fichiers génériques de doc (`*.md` hors `/docs/`) souvent bilingues.
- La matière couvrant tous les projets est dans `~/.config/opencode/AGENTS.md` (agents, commandes, skills) — ne pas la dupliquer ici.
