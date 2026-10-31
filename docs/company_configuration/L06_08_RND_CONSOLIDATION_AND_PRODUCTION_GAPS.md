# L06-08 — Consolidation R&D Fiscal Calendar, qualification et écarts de production

**Date :** 31 octobre 2026  
**Projet :** PyAccountingKit / Company Configuration  
**Périmètre :** L06-01 à L06-07, **R&D exclusivement**. Le dossier de consolidation **n’ajoute aucun moteur comptable opérationnel**.  
**Documents de référence :** `14_COMPANY_CONFIGURATION_FISCAL_CALENDAR_AND_PERIOD_MANAGEMENT.md` §§12, 16, 17, 20 et 21 ; `10_COMPANY_CONFIGURATION_INTEGRATION_CONTRACTS.md` (`C10-Q04`) ; `17` (gouvernance) ; `18` (temporalité) ; `19` (IAM et audit) ; `20` (SQL).  
**Registres associés :** [ADR-CAL-01..10](L06_08_FISCAL_CALENDAR_ADR_REGISTER.md), [ADR JSON](L06_08_FISCAL_CALENDAR_ADR_REGISTER.json), [preuve CI JSON](L06_08_RND_EVIDENCE_AND_GATE_LEDGER.json), [matrice source CAL-INV/CAL-SC](L06_07_CAL_INVARIANTS_AND_SCENARIOS_COVERAGE.json).

## 1. Conclusion de qualification

**Les sept incréments L06 ont des prototypes R&D et des preuves GitHub Actions 4/4 vertes sur le SHA exact de chacune des sept PR ouvertes en brouillon.** Il ne s'agit **pas** de la qualification de la cible `CAL-L1…CAL-L7` du document source : les exit criteria portant sur des contraintes SQL persistées, des transitions gouvernées, un vrai publisher/Outbox, un vrai `GetPeriodStatus`, un posting guard transactionnel et l'E2E multi-subledgers **ne sont pas satisfaits**.

```text
 L06-01  Domain kernel (dates, years, periods)
    ↓
 L06-02  Unpublished versions + dated book assignment candidates
    ↓
 L06-03  Read-only candidate state / locks / transition declarations
    ↓
 L06-04  Unapproved publication, audit and Outbox INTENTS
    ↓
 L06-05  STRICT non-authoritative C10-Q04-shaped JSON simulation
    ↓
 L06-06  SYMBOLIC close/post ordering, no actual SQL/COMMIT fencing
    ↓
 L06-07  Multi-book fixture replay and gap matrix, no real E2E
    ↓
 L06-08  Consolidated ADR/EVIDENCE REVIEW (THIS PR; no runtime change)

     All above = engineering R&D      ≠  G6_GO / live posting authority
```

## 2. Chaîne des PR et preuves exact-head

**Stack observée au 31 octobre 2026 :** #88 basée sur `main`, puis #89→#88, #90→#89, #91→#90, #92→#91, #93→#92 et #94→#93 ; chaque PR est **OPEN / DRAFT / UNMERGED**. `main` reste `acdee98ca2736d79e17174f510ac767defd90db8`. La nouvelle PR de consolidation, empilée sur #94, ne fusionne aucun de ces travaux.

| Incrément | R&D livré | PR | SHA exact | Python 3.11 et 3.12 | CI |
|---|---|---|---|---:|---|
| `L06-01` | Fiscal Calendar Domain Kernel | [#88](https://github.com/tawounfouet/pyaccountingkit/pull/88) | `3003192495d0` | 346 pass, 19 skip par version | 4/4 SUCCESS |
| `L06-02` | Candidate Versions & Book Assignments | [#89](https://github.com/tawounfouet/pyaccountingkit/pull/89) | `566939408835` | 378 pass, 19 skip par version | 4/4 SUCCESS |
| `L06-03` | Period Status, Locks & Diagnostics | [#90](https://github.com/tawounfouet/pyaccountingkit/pull/90) | `4762b5d21827` | 422 pass, 19 skip par version | 4/4 SUCCESS |
| `L06-04` | Publication, Audit & Outbox Intent Contracts | [#91](https://github.com/tawounfouet/pyaccountingkit/pull/91) | `8356d756accc` | 457 pass, 19 skip par version | 4/4 SUCCESS |
| `L06-05` | C10-Q04 Wire/Consumer Simulation | [#92](https://github.com/tawounfouet/pyaccountingkit/pull/92) | `b1fc7014afe0` | 498 pass, 19 skip par version | 4/4 SUCCESS |
| `L06-06` | Symbolic Close-vs-Post Fencing Model | [#93](https://github.com/tawounfouet/pyaccountingkit/pull/93) | `0c87bc0be811` | 528 pass, 19 skip par version | 4/4 SUCCESS |
| `L06-07` | Multi-Book Candidate Replay & Coverage | [#94](https://github.com/tawounfouet/pyaccountingkit/pull/94) | `f695eb70280a` | 560 pass, 19 skip par version | 4/4 SUCCESS |

Dans chaque cas les quatre workflows correspondent à `Python CI`, `PostgreSQL Foundation (L02 candidate)`, `Migration recovery (FND-C04)` et `Standalone Foundation package (FND-C06)`. Ils testent **Python 3.11 et 3.12**. Les tests PostgreSQL sont **134 pass par version**, la récupération **6 pass par version**, et les **14 migrations Foundation historiques** conservent leur parité SHA-256 entre source, wheel et sdist. **Aucune migration SQL L06 de publication, statut ou garde COMMIT n'a été livrée**.

### Liens de workflows sur le dernier SHA qualifié (#94)

- [Python CI, 560 tests pass / 19 skip, Ruff](https://github.com/tawounfouet/pyaccountingkit/actions/runs/41180422169)
- [PostgreSQL Foundation, 134 tests pass](https://github.com/tawounfouet/pyaccountingkit/actions/runs/41180422213)
- [Migration recovery, 6 tests pass](https://github.com/tawounfouet/pyaccountingkit/actions/runs/41180422272)
- [Wheel/sdist, 14 migrations historiques identiques](https://github.com/tawounfouet/pyaccountingkit/actions/runs/41180422160)

**Précision documentaire :** le fichier `L06_07_CAL_INVARIANTS_AND_SCENARIOS_COVERAGE.json` a été créé avant qualification, avec `ci_status: PENDING_EXACT_HEAD`. Ce champ désigne un **état historique du document** et n'est **pas** la preuve d'une CI encore bloquée. Les runs exacts ci-dessus, le commentaire de qualification #94 et le registre `L06_08_RND_EVIDENCE_AND_GATE_LEDGER.json` fixent l'état vérifié ultérieurement, sans réécrire rétroactivement le contenu du SHA #94.

## 3. Matrice de maturité: R&D versus production

| Frontière métier | Démonstration R&D | Toujours absent pour la vraie cible |
|---|---|---|
| Intervalles, années fiscales, périodes | L06-01 typage, invariants demi-ouverts, exercices décalés | Règles juridiques approuvées, exclusion SQL et migrations |
| Versions et affectations de livres | L06-02 identité exacte, as-of/known-at et checksum | Book légal vérifié, contraintes persistance et publication signée |
| États, clôtures et locks | L06-03 observations historisées et déclarations sans effet | Commandes Open/Close/Reopen/Lock gouvernées, status/locks autoritatifs |
| Publication, audit, Outbox | L06-04 intentions non exécutantes liées par digest | Transaction unique version+audit+Outbox, signature IAM et SoD |
| C10-Q04 | L06-05 JSON simulé strict qui refuse toujours posting | Production `GetPeriodStatus`, vraies locks applicables et control_version |
| Concurrence close/post | L06-06 ordre de séquence symbolique, compteur epoch | Vraies transactions simultanées, CAS/fencing SQL au COMMIT du Ledger |
| Multi-books et replay | L06-07 deux books candidats PCG_RND/IFRS_RND et reprise temporelle | Validation normative PCG/IFRS, vrais E2E et migrations/recovery L06 |

Cette table est volontairement conservatrice. Une suite de tests de simulation ne remplace ni une transaction, ni un processus de clôture comptable, ni l'autorisation d'un acteur signé.

## 4. Couverture des invariants et scénarios

L'index source `14` possède **CAL-INV-01…12**, **CAL-SC-01…20** et dix décisions **ADR-CAL-01…10**. La matrice [L06_07_CAL_INVARIANTS_AND_SCENARIOS_COVERAGE.json](L06_07_CAL_INVARIANTS_AND_SCENARIOS_COVERAGE.json) inventorie **12/12** invariants et **20/20** scénarios, mais ne dit **jamais** que tous sont prouvés live.

- `CANDIDATE_PARTIAL` signifie validation structurelle ou replay R&D uniquement ; les cas PCG/IFRS ne sont pas normativement certifiés.
- `NOT_IMPLEMENTED_LIVE` signifie absence de vraie autorité/posting/écriture SQL et d'acceptation comptable réelle.
- Notamment `CAL-INV-04/05/06/07/10/12` et `CAL-SC-06/07/08/09/10/11/15/16/17/20` **ne peuvent pas être cochés « acceptés en production »** sur la base de ces tests.

**Cas bloquant : CAL-SC-09**. Entre un `GetPeriodStatus` voyant OPEN et l'INSERT Ledger, ClosePeriod peut terminer ; il faut établir un ordre de sérialisation **sur la même frontière que le commit**, avec droit signé valide. L06-06 teste des séquences ordonnées symboliquement : aucun test de cette branche ne lance deux transactions SQL de clôture et de posting concurrentes.

## 5. Décisions à arbitrer — synthèse exécutive

Le registre complet est [L06_08_FISCAL_CALENDAR_ADR_REGISTER.md](L06_08_FISCAL_CALENDAR_ADR_REGISTER.md). **Les dix sont OPEN et aucun n'est signé.** La priorité absolue pour la production est :

1. **ADR-CAL-07 — source autoritative des statuts et responsabilité du posting guard.** Définir les acteurs, droits et la frontière `COMMIT`, en lien avec l'issue sécurité #71. **Ambiguïté d'index :** le source `14` évoque `ADR-CC-007` pour ce sujet, alors que la roadmap `ADR-CC-07` concerne la sûreté du langage des RuleSets (L07). Réconcilier le référentiel des identifiants avant toute décision publiée.
2. **ADR-CAL-08 — sérialisation et fencing close-vs-posting.** Choisir même DB/lock/epoch ou protocole coordonné ; démontrer avec deux writers réels, rollback, crash, retry et outbox.
3. **ADR-CAL-01/02/09 — multi-book, agrégats et bitemporalité.** Déterminer frontières SQL, contraintes d'exclusion, snapshots et corrections rétroactives.
4. **ADR-CAL-03/04/05/06/10 — ajustements, locks, états, réouvertures et normes.** Exiger expertise comptable/normative, contrôle SoD et audit avant toute activation.

**Aucune liste d'options ou « préférence » dans le registre n'est une ADR ACCEPTED.** Les owners y figurent comme rôles proposés pour revue, pas comme signataires déjà obtenus.

## 6. Gates, sécurité, travaux bloqués

| Gate / blocage | État | Impact |
|---|---|---|
| G0 / G1 / G2 | `PENDING_REVIEW` | Revue indépendante fondations |
| **G3** | **`HOLD_SECURITY`** | Acteur/issuer et autorité SQL COMMIT encore non prouvés |
| G4 / G5 | `NOT_APPROVED` | Book/COA et publication réelle non acceptés |
| **G6** | **`NOT_APPROVED`** | **Aucun Posting Guard / CalendarVersion publié en production** |
| [Issue #71](https://github.com/tawounfouet/pyaccountingkit/issues/71) | **OPEN** | Remédiation de sécurité séparée requise |

Conditions nécessaires pour un GO de production : décisions ADR enregistrées, source normative approuvée, approbations comptables/IAM indépendantes, sécurité #71 fermée **avec preuves contrôlées**, schéma L06 persisté et migré, publication version+audit+Outbox atomique, vrai C10-Q04, vrais tests de concurrence `ClosePeriod` contre `Ledger COMMIT`, tests E2E multi-subledgers et migrations/rollback/recovery dédiées à L06.

## 7. Plan de sortie ordonné

| Priorité | Travail suivant | Résultat exigé |
|---|---|---|
| P0 | Résoudre l'issue #71 et réconcilier ADR-CC-007/ADR-CC-07 | Preuve indépendante d'autorisation IAM/issuer SQL COMMIT |
| P0 | Décider ADR-CAL-07/08 | Autorité et mécanisme COMMIT clair, architecture approuvée |
| P0 | Consolider la chaîne de PR R&D #88→#94 | Revue indépendante et choix de stratégie de merge sans contournement de gates |
| P1 | Résoudre ADR-CAL-01/02/03/04/05/06/09/10 | Modèle cible normatif, states/locks/temporalité/SoD décidés |
| P1 | Implémenter/qualifier persistance L06 + audit/outbox réel | Transactions et migration/rollback/réconciliation fiables |
| P1 | Vérifier C10-Q04, Runtime, Ledger et tests de concurrence | Tests cross-service, close-vs-post, migrations et E2E réels |
| P2 | Préparer L07 Policies & RuleSets **R&D isolé** | Ne pas dépendre de fausses publications L06 ; pas de G7_GO précoce |

**Critère de sortie de cette PR de consolidation :** dossier ADR exhaustif et cohérent avec l'inventaire CI exact, matrice CAL traçable et tests de cohérence documentaire verts. **Pas** de G6_GO, de fusion main, de release stable ni d’autorisation de posting. La prochaine R&D peut démarrer sans maquiller les gates ; la réalisation de production reste indépendante.
