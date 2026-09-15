# AGENTS.md — PyAccountingKit

PyAccountingKit est un moteur comptable Python en partie double, à architecture
hexagonale, piloté par spécifications, ADR, plans d'implémentation et quality
gates.

Ce fichier contient les **règles obligatoires pour tout coding agent**
(OpenCode, Codex, assistants IDE, scripts autonomes). Elles priment sur les
raccourcis de confort et sur les anciens patterns encore présents dans des tests
ou des fixtures.

> Principe directeur : **ne jamais obtenir un build vert en affaiblissant un
> invariant métier ou architectural**. Si un nouvel invariant casse un ancien
> test, adapter le test, sa fixture, son générateur ou son appelant.

---

## 1. Démarrage obligatoire de chaque tâche

Avant toute modification :

1. lire `pyproject.toml` pour connaître la **version réelle** du package ;
2. vérifier la branche Git active et le lot/milestone en cours ;
3. lire le plan concerné dans `docs/plans/` ;
4. lire la ou les specs concernées dans `docs/specs/` ;
5. rechercher les ADR applicables avant toute décision structurante ;
6. inspecter les usages actuels du symbole à modifier dans **tout le repo**.

Ne jamais raisonner à partir d'une ancienne étape du projet. Le dépôt a dépassé
le bootstrap historique `0.0.1` ; toute règle conditionnée à une ancienne
version doit être vérifiée contre la version présente dans `pyproject.toml`.

Commande utile avant un refactor :

```bash
rg "NomDuSymbole|ancien_constructeur|ancien_protocole" src tests scripts docs
```

Si une signature publique/interne change, la migration de **tous** les appelants
fait partie du même changement.

---

## 2. Commandes canoniques

Installation :

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
```

Boucle locale minimale :

```bash
python -m ruff format src tests scripts
python -m ruff check src tests scripts
python -m ruff format --check src tests scripts
python -m mypy src
python -m pytest tests/unit tests/property tests/contract -v --tb=short
```

Qualification canonique :

```bash
python scripts/qualify_release.py
```

Qualification comptable étendue avant merge de milestone/release :

```bash
python scripts/qualify_release.py --full
```

Le mode `--full` ajoute, lorsqu'elles existent, les suites `integration`,
`golden`, `replay` et `concurrency`. Une PR de milestone ne doit pas être
considérée mergeable sur la seule base de la boucle core si ces suites sont
applicables au changement.

Gates statiques rapides :

```bash
python scripts/qualify_release.py --skip-tests --skip-package
```

Hygiène / package :

```bash
bash scripts/check_hygiene.sh
python scripts/verify_package.py
```

Parité sécurité avec `.github/workflows/security.yml` :

```bash
python -m pip install pip-audit "bandit[toml]"
python -m pip_audit
python -m bandit -r src/ -c pyproject.toml
```

---

## 3. Règle absolue avant commit / push

**Ne pas utiliser GitHub Actions comme formatter, linter ou premier runner de
tests.**

Avant tout push, l'agent doit exécuter localement, dans cet ordre :

```text
1. ruff format
2. ruff check
3. ruff format --check
4. mypy
5. tests unit/property/contract
6. qualify_release.py
7. qualify_release.py --full pour milestone/release ou changements cross-lot
8. security checks si le changement touche src/, dépendances, packaging ou CI
```

Aucun commit/push ne doit être produit avec un échec connu dans cette séquence.

Après une correction issue de la CI, rejouer **la chaîne complète**, pas
uniquement le test qui échouait.

Éviter les séries de micro-commits du type « fix lint », « fix format », « fix
one test » lorsque ces erreurs auraient été détectées localement. Une PR de
travail peut contenir plusieurs commits, mais chaque commit poussé doit être
cohérent et les gates locales doivent avoir été exécutées.

---

## 4. Architecture — contraintes non négociables

Direction générale :

```text
adapters  ───────► application ───────► domain
   │                    │                  │
   └──────────────► ports ◄────────────────┘
                         │
                        core
```

Règles :

- `core/` contient les primitives transversales et ne dépend pas du métier ;
- `domain/` reste framework-free : aucun Django, SQLAlchemy, FastAPI, ORM ou I/O ;
- `application/` orchestre les use cases, transactions et ports ;
- `ports/` définit les contrats ;
- `adapters/` concrétise les ports ;
- `public/` représente la surface exposée et doit rester explicitement maîtrisée ;
- un adapter in-memory est une **référence comportementale**, pas une preuve de
  qualification production.

Ne pas injecter directement un agrégat concret dans un use case si un port de
résolution/versioning existe. Les frontières applicatives doivent dépendre du
contrat approprié.

---

## 5. Invariant architectural n°1 : AccountingEntity

Toute opération comptable est mono-entité et doit échouer en mode fail-closed
si deux objets de l'opération n'appartiennent pas à la même entité.

Chemins concernés notamment :

```text
AccountingEntity
   ├── Journal
   ├── AccountingPeriod
   ├── CompanyChart
   ├── CompanyChartOfAccounts
   ├── CompanyAccount
   ├── AccountingPolicySet
   ├── PolicyContext
   ├── JournalEntryProposal
   ├── AccountRole resolution
   ├── Posting
   ├── Reversal
   ├── Closing
   └── Accounting Import
```

Utiliser l'invariant canonique (`require_same_entity` /
`EntityScopeMismatchError`) plutôt que de dupliquer des comparaisons ad hoc.

Interdictions :

- ne jamais ignorer un `entity_id` reçu par une API ;
- ne jamais utiliser `entity_id` uniquement dans un message d'erreur ;
- ne jamais résoudre un rôle ou un chart sans vérifier l'entité ;
- ne jamais permettre à un compte d'une autre entité d'entrer dans un chart ;
- ne jamais poster avec un journal, une période et un chart appartenant à des
  entités différentes.

Tout nouveau use case comptable doit inclure au moins un test adversarial
cross-entity.

---

## 6. Journaux et partie double

Invariants obligatoires :

- `Money` utilise `Decimal`, jamais `float` ;
- débit et crédit d'une ligne sont mutuellement exclusifs ;
- une ligne `(debit=0, credit=0)` est **invalide dès la construction** ;
- une écriture doit contenir le nombre minimal de lignes requis ;
- `Σ débit == Σ crédit` avant posting ;
- une écriture `POSTED` est immuable ;
- une correction crée une nouvelle écriture de reversal/adjustment ;
- aucun raccourci ne doit permettre de muter directement une écriture postée.

### Règle spécifique aux property tests

Quand un invariant devient plus strict, Hypothesis peut révéler des fixtures qui
étaient historiquement valides mais ne le sont plus.

Exemple classique : une stratégie `integers(min_value=0, ...)` utilisée pour
construire directement une `JournalLine` peut produire `0`, donc une ligne
zéro/zéro désormais interdite.

Dans ce cas :

- contraindre la stratégie à produire des objets valides (`min_value=1`) pour
  les tests portant sur un autre invariant ;
- créer un test dédié de rejet pour le zéro ;
- **ne jamais retirer `ZeroLineError` pour faire repasser le property test**.

Principe général : les générateurs de propriétés doivent respecter les
préconditions du type qu'ils construisent, sauf lorsque la propriété testée est
précisément le rejet de ces préconditions.

---

## 7. Versioning du plan de comptes et résolution des rôles

Le chemin canonique est :

```text
AccountingEntity + AccountingDate
        │
        ▼
CompanyChart
        │
        ▼
CompanyChartVersion
        │
        ▼
CompanyChartOfAccounts
        │
        ├──► Posting
        └──► AccountRole resolution
```

`CompanyChartResolverProtocol` est l'autorité de résolution du chart
opérationnel applicable à une entité et une date.

`AccountRoleResolverProtocol` doit utiliser cette même autorité, afin que
posting et policy/proposal ne divergent jamais sur la version du plan de
comptes.

Interdictions :

- ne pas réintroduire un simple mapping global `AccountRole -> account_code`
  ignorant l'entité ou la date ;
- ne pas injecter `CompanyChartOfAccounts` directement dans
  `PostingOrchestrator` si le contrat attendu est un resolver versionné ;
- ne pas dupliquer une deuxième logique de sélection des versions du chart ;
- ne pas perdre `chart_id`, `chart_version` ou `reference_snapshot_id` dans la
  trace applicative.

### Migration d'API/protocole

Lorsqu'un constructeur change, par exemple d'un agrégat brut vers un resolver :

1. implémenter le nouveau port/adapter ;
2. rechercher tous les constructeurs/usages existants ;
3. mettre à jour **production + tests + builders + E2E** dans la même tranche ;
4. exécuter les tests complets ;
5. supprimer/encapsuler l'ancien chemin uniquement après migration des appelants.

Préférer les arguments nommés pour les constructeurs structurants afin de
rendre les changements de signature plus explicites.

---

## 8. Policy engine — comportement fail-closed

`AccountingPolicySet`, `PolicyContext`, `PolicyApplicability` et
`PolicyResolutionService` doivent rester déterministes et fail-closed.

Pour une exécution `CURRENT` :

- l'entité du context doit correspondre à celle du policy set ;
- le policy set doit être `ACTIVE` ;
- la date doit appartenir à la fenêtre d'effet ;
- standard, édition et snapshot doivent être compatibles ;
- une valeur runtime requise absente ne doit **jamais** matcher silencieusement ;
- une ambiguïté de résolution doit lever une erreur explicite.

Pour un `HISTORICAL_REPLAY` :

- le mode doit être explicite ;
- les versions et snapshots historiques doivent être pinés ;
- le replay doit rester reproductible.

### Fixtures de policy tests

Un test destiné à exercer une résolution normale doit construire un policy set
valide pour ce mode. Si l'exécution normale exige `ACTIVE`, une fixture `DRAFT`
ne doit pas être conservée par accident.

Les statuts non actifs doivent apparaître dans des tests **de rejet** ou des
scénarios explicites de replay, pas dans les happy paths.

---

## 9. JournalEntryProposal et policies de mesure

Une `JournalEntryProposal` est un contrat comptable, pas un sac de lignes
partiellement valides.

Règles :

- montant strictement positif sur chaque ligne proposée ;
- devise cohérente ;
- au moins le nombre minimal de lignes ;
- équilibre débit/crédit avant conversion vers `JournalEntry` ;
- policy traces cohérentes avec `entity_id` et `accounting_date` ;
- la proposal ne poste jamais directement.

Le chemin cible est :

```text
Policy / Measurement
        │
        ▼
JournalEntryProposal
        │
        ▼
AccountRoleResolverProtocol
        │
        ▼
ProposalPostingOrchestrator
        │
        ▼
JournalEntry
        │
        ▼
PostingOrchestrator
```

Ne jamais contourner ce chemin en résolvant manuellement des comptes depuis un
mapping local dans un nouveau use case.

Les objets de mesure doivent également vérifier leurs invariants arithmétiques,
notamment `delta == new_amount - previous_amount` et les bornes de calcul
(dépréciation/amortissement, valeurs résiduelles, cumuls).

---

## 10. Posting, reversal et transaction atomique

Une mutation comptable applicative doit être atomique.

Pour `PostingOrchestrator`, les éléments suivants appartiennent au **même Unit
of Work** :

```text
JournalEntry persistence
+ state transition POSTED
+ audit event
+ outbox event
+ idempotency state
= one commit
```

Même exigence pour reversal et autres mutations structurantes.

Interdictions :

- ne pas écrire un audit externe avant le commit comptable ;
- ne pas publier l'outbox hors transaction ;
- ne pas marquer l'idempotency comme terminée si la mutation peut encore rollback ;
- ne pas laisser d'état partiel après exception.

Chaque orchestration transactionnelle doit avoir un test qui force un échec et
vérifie l'absence de nouvelle écriture, audit partiel, outbox partielle et clé
d'idempotence consommée à tort.

Le reference adapter in-memory doit lui aussi respecter l'isolation : un
rollback d'une transaction ne doit jamais restaurer un snapshot global qui
écraserait le commit d'une transaction concurrente.

---

## 11. Imports comptables — règles à respecter dès LOT-14

Le bounded context générique d'import ne connaît **aucun nom de colonne FEC**.
Les concepts `JournalCode`, `EcritureNum`, `CompteNum`, etc. appartiennent à
l'adapter FEC des lots suivants, pas à `domain/imports`.

Chaîne générique obligatoire :

```text
SourceArtifact
→ RawImportRecord
→ NormalizedImportRecord
→ Mapping / Grouping / Validation
→ ImportPlan
→ JournalEntry
→ PostingOrchestrator
```

Règles :

- l'artefact source est immutable et son SHA-256 est conservé ;
- raw et normalized restent distincts ;
- le regroupement par `SourceEntryKey` est déterministe ;
- account/journal mapping est explicite et fail-closed ;
- un candidate mapping n'est pas exécutable ;
- aucun account/journal inconnu n'est créé silencieusement ;
- `ImportPlan` est construit avant toute mutation ;
- dry-run ne mute jamais le core ;
- un plan stale ne s'exécute pas ;
- aucun record source ne peut être silently dropped ;
- l'exécution utilise le Posting normal, jamais un second posting engine ;
- import et period closing partagent les mêmes exigences de concurrence et
  transactionnalité.

---

## 12. Compatibilité lors des refactors

Après **toute** modification de constructeur, protocole, méthode publique,
dataclass structurante, enum/statut, invariant ou port, lancer une recherche
globale et traiter :

```text
src/
tests/unit/
tests/property/
tests/contract/
tests/integration/
tests/replay/
tests/golden/
tests/concurrency/
scripts/
docs exemples de code si applicables
```

Ne jamais supposer que « les nouveaux tests passent » suffit. Les tests
historiques et E2E font partie du contrat de non-régression.

---

## 13. Ruff / typing — règles de prévention

### Formatting

Toujours exécuter :

```bash
python -m ruff format src tests scripts
```

**avant** :

```bash
python -m ruff format --check src tests scripts
```

Un `ruff check` vert ne signifie pas que `ruff format --check` sera vert.

### B008 — appels dans les valeurs par défaut

Éviter les constructions d'objets dans les paramètres par défaut. Préférer une
constante de module ou `None` + initialisation dans le corps.

### Protocols

Suivre le formatting produit par Ruff pour les méthodes de protocol, y compris
la forme compacte `-> Type: ...` lorsque requise.

---

## 14. Sécurité

Les security checks sont des gates réelles, pas décoratives.

- `pip-audit` doit rester vert ;
- Bandit doit rester vert selon `pyproject.toml` ;
- utiliser `secrets`/UUID ou une stratégie sécurisée par défaut pour les
  identifiants non prédictibles ;
- réserver les sources déterministes injectées aux tests ;
- ne pas utiliser `assert` pour faire respecter des invariants runtime ;
- une suppression Bandit doit être ciblée, documentée et justifiée.

---

## 15. Données & réglementaire

- `domain/` ne lit **jamais** directement `data/` ni un référentiel ;
- toute consommation réglementaire passe par `AccountingReferenceProvider` et
  ses adapters ;
- les normes officielles restent dans les resources/frameworks amont ;
- `tests/golden/` contient les oracles qualifiés, pas des données métier réelles ;
- un statut `golden-qualified` signifie que les baselines couvertes sont
  qualifiées, pas que tout le reporting réglementaire du framework est complet.

---

## 16. Versioning & release governance

Milestones pilotés par **scope + Definition of Done + gates**, jamais par date.
Les prereleases utilisent PEP 440 (`aN`, `bN`, `rcN`).

Une release stable n'est jamais un simple bump/tag. Elle exige :

```text
architecture + lint + format + typing
unit/property/contract
applicable integration/golden/replay/concurrency
package verification
security
manifests cohérents
README / CHANGELOG alignés
```

Ne pas annoncer qu'un adapter in-memory qualifie la production ; ses tests
établissent une référence comportementale à réexécuter sur les futurs adapters
réels.

---

## 17. Docs — source de vérité

- `docs/specs/` : spécifications canoniques et ADR ;
- `docs/ROADMAP.md` : lots, DoD et gates ;
- `docs/plans/` : plans d'implémentation par release ;
- `CONTRIBUTING.md` : conventions de contribution et Conventional Commits.

Avant LOT-14 et suivants, ne pas coder à partir d'un exemple isolé dans un plan
si la spec canonique définit un invariant plus strict : **la spec/ADR prime**.

## Conventions

- docs/commentaires : français lorsque cela améliore la gouvernance ;
- identifiants de code : anglais ;
- commits : Conventional Commits ;
- ne pas dupliquer dans ce fichier des instructions génériques qui appartiennent
  à la configuration globale de l'agent.
