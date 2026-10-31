# L06-08 — Registre ADR-CAL-01…10 (décisions ouvertes)

**Date de revue :** 31 octobre 2026  
**Contexte :** PyAccountingKit / Company Configuration / Fiscal Calendar & Period Management  
**Statut :** `RND_DECISION_REGISTER — ALL OPEN / NONE APPROVED`  
**Référence structurée :** [L06_08_FISCAL_CALENDAR_ADR_REGISTER.json](L06_08_FISCAL_CALENDAR_ADR_REGISTER.json)

## Convention de gouvernance

Ce registre est un **outil de préparation de décisions**, **pas** un ensemble d’ADR acceptées. Il distingue soigneusement : (1) la question normative proposée dans le document source `14` §20 ; (2) les options à étudier ; (3) une orientation **non contraignante** dérivée des démonstrateurs R&D ; (4) les critères de preuve manquants avant décision. Aucune proposition ne doit être convertie en `ACCEPTED` automatiquement par une CI verte, une approbation implicite ou un simple commentaire GitHub.

**Circuit de décision proposé (à approuver séparément) :** auteur technique → revue architecture → revue accounting/normative → revue IAM/sécurité pour actions critiques → décideur compétent → enregistrement d’un ADR signée/datée, liée à un SHA exact de spécification et de tests ; les rôles listés ci-dessous ne sont **pas des approbations déjà obtenues**.

**Références :** `14_COMPANY_CONFIGURATION_FISCAL_CALENDAR_AND_PERIOD_MANAGEMENT.md` §§4–21 ; `10_COMPANY_CONFIGURATION_INTEGRATION_CONTRACTS.md` C10-Q04 ; `17_COMPANY_CONFIGURATION_CONFIGURATION_LIFECYCLE_AND_GOVERNANCE.md` §§7–12 ; `18` temporalité ; `19` sécurité. Toutes les références sont des cibles documentaires ; les PR #88–94 en démontrent uniquement des modèles candidats.

## Tableau de décision

| ADR | Question source | Priorité | Statut | Preuve candidate |
|---|---|---|---|---|
| `ADR-CAL-01` | Calendrier partagé ou par book | HIGH | **OPEN** | #89, #94 |
| `ADR-CAL-02` | Frontière agrégat définition et état | HIGH | **OPEN** | #88, #90, #91 |
| `ADR-CAL-03` | Ajustements: modèle et sélection | HIGH | **OPEN** | #88, #89 |
| `ADR-CAL-04` | Granularité des locks | CRITICAL | **OPEN** | #90, #92, #93 |
| `ADR-CAL-05` | Workflow SOFT_CLOSED/CLOSED/ARCHIVED | HIGH | **OPEN** | #90, #93 |
| `ADR-CAL-06` | Réouverture et dérogations | CRITICAL | **OPEN** | #90, #91 |
| `ADR-CAL-07` | Autorité clôture et posting guard | BLOCKER | **OPEN** | #90, #92, #93 |
| `ADR-CAL-08` | Stratégie sérialisation / fencing | BLOCKER | **OPEN** | #93 |
| `ADR-CAL-09` | Sémantique bitemporelle des périodes | HIGH | **OPEN** | #89, #90, #94 |
| `ADR-CAL-10` | Règles calendaires par référentiel et juridiction | HIGH | **OPEN** | #88, #94 |

## Analyse détaillée des dix décisions

### ADR-CAL-01 — Calendrier partagé ou par book

- **Statut : OPEN — aucun arbitrage ni approbation.** Priorité : **HIGH**. Rôles à consulter : Accounting Architect, Domain Owner, Legal/Normative Reviewer.
- **Options à comparer :** (1) Calendrier détenu par book ; (2) Définition partagée, affectation explicite versionnée par book ; (3) Organisation racine avec héritage implicite.
- **Orientation de travail NON contraignante :** Étudier une définition partageable uniquement par affectation book/version unique et datée; interdire l'héritage implicite.
- **Risques / conséquences :** La réutilisation économise des définitions mais exige une isolation des statuts et locks par book.
- **Preuves R&D disponibles :** [PR #89](https://github.com/tawounfouet/pyaccountingkit/pull/89) ; [PR #94](https://github.com/tawounfouet/pyaccountingkit/pull/94) ; il ne s'agit ni de preuves de conformité comptable ni de validation de transactions de production.
- **Critères pour décider :**
  - [ ] Décider ownership / cardinalités et périmètres
  - [ ] Prouver unicité book+date+known_at avec contrainte persistée
  - [ ] Tester réaffectation et non-fuite de statut/lock PCG–IFRS
- **Gates / fonctionnalités bloquées par la décision :** `G6 publication`, `G10 consumers`.
- **Décision signée, auteur, date, justification, alternatives écartées :** **NON RENSEIGNÉS**.

### ADR-CAL-02 — Frontière agrégat définition et état

- **Statut : OPEN — aucun arbitrage ni approbation.** Priorité : **HIGH**. Rôles à consulter : Domain Architect, Persistence Architect, Accounting Owner.
- **Options à comparer :** (1) Agrégat unique calendrier+état ; (2) Séparer version de définition et contrôles de périodes ; (3) Agrégat unique par book et période.
- **Orientation de travail NON contraignante :** Étudier la séparation de définition immuable et état mutable, avec un protocole d'intégrité transactionnelle explicite.
- **Risques / conséquences :** Séparer favorise scalabilité et historique, mais exige cohérence des références et ACL.
- **Preuves R&D disponibles :** [PR #88](https://github.com/tawounfouet/pyaccountingkit/pull/88) ; [PR #90](https://github.com/tawounfouet/pyaccountingkit/pull/90) ; [PR #91](https://github.com/tawounfouet/pyaccountingkit/pull/91) ; il ne s'agit ni de preuves de conformité comptable ni de validation de transactions de production.
- **Critères pour décider :**
  - [ ] Choisir ownership états/locks/transitions
  - [ ] Fixer frontières transactionnelles et locks SQL
  - [ ] Qualifier atomicité historique/audit/outbox
- **Gates / fonctionnalités bloquées par la décision :** `G6 publication`, `G6 state workflow`.
- **Décision signée, auteur, date, justification, alternatives écartées :** **NON RENSEIGNÉS**.

### ADR-CAL-03 — Ajustements: modèle et sélection

- **Statut : OPEN — aucun arbitrage ni approbation.** Priorité : **HIGH**. Rôles à consulter : Accounting Approver, Normative Layer Owner, Runtime Owner.
- **Options à comparer :** (1) Périodes ordinaires et ajustements séparés ; (2) Périodes avec kind et sélection explicite ; (3) Pseudo-période annuelle de clôture.
- **Orientation de travail NON contraignante :** Garder l'identité typée et la sélection explicite des périodes ADJUSTMENT; règles d'éligibilité et droits par norme à décider.
- **Risques / conséquences :** Risque de comptabilisation d'ajustements sans droits, double interprétation des dates et conventions PCG/IFRS/OHADA.
- **Preuves R&D disponibles :** [PR #88](https://github.com/tawounfouet/pyaccountingkit/pull/88) ; [PR #89](https://github.com/tawounfouet/pyaccountingkit/pull/89) ; il ne s'agit ni de preuves de conformité comptable ni de validation de transactions de production.
- **Critères pour décider :**
  - [ ] Validation des juridictions/référentiels et période 13/ADJ
  - [ ] Contrat de référence au book et à l'ordinaire cible
  - [ ] Cas négatifs sans permission ni fallback
- **Gates / fonctionnalités bloquées par la décision :** `G6 special periods`, `G10 consumers`.
- **Décision signée, auteur, date, justification, alternatives écartées :** **NON RENSEIGNÉS**.

### ADR-CAL-04 — Granularité des locks

- **Statut : OPEN — aucun arbitrage ni approbation.** Priorité : **CRITICAL**. Rôles à consulter : Accounting Operations, Security Architect, Execution Owner.
- **Options à comparer :** (1) Lock global au book ; (2) Locks book+journal+source+operation ; (3) Politique dynamique par taxonomie de postings.
- **Orientation de travail NON contraignante :** Étudier des locks orthogonaux et explicitement applicables, mais exiger un inventaire complet autoritatif au moment du COMMIT.
- **Risques / conséquences :** Un lock scoped mal interprété entraîne déni indu ou posting interdit; lecture staleable insuffisante.
- **Preuves R&D disponibles :** [PR #90](https://github.com/tawounfouet/pyaccountingkit/pull/90) ; [PR #92](https://github.com/tawounfouet/pyaccountingkit/pull/92) ; [PR #93](https://github.com/tawounfouet/pyaccountingkit/pull/93) ; il ne s'agit ni de preuves de conformité comptable ni de validation de transactions de production.
- **Critères pour décider :**
  - [ ] Définir taxonomie de lock et opération/journal/source
  - [ ] Choisir règles de priorité, exceptions et fail-closed
  - [ ] Tester autorité, inventaire complet et contention SQL
- **Gates / fonctionnalités bloquées par la décision :** `G6 posting guard`, `G10 C10-Q04`.
- **Décision signée, auteur, date, justification, alternatives écartées :** **NON RENSEIGNÉS**.

### ADR-CAL-05 — Workflow SOFT_CLOSED/CLOSED/ARCHIVED

- **Statut : OPEN — aucun arbitrage ni approbation.** Priorité : **HIGH**. Rôles à consulter : Accounting Operations, Accounting Architect, Auditor.
- **Options à comparer :** (1) Statuts simplifiés OPEN/CLOSED ; (2) Workflow complet avec SOFT_CLOSED et ARCHIVED ; (3) Statuts distincts par juridiction et book.
- **Orientation de travail NON contraignante :** Conserver la liste comme candidate; ne pas déduire posting éligible de OPEN sans lock ni politique.
- **Risques / conséquences :** Transitions multiples et décisions de soft close rendent l'audit et la gouvernance sensibles.
- **Preuves R&D disponibles :** [PR #90](https://github.com/tawounfouet/pyaccountingkit/pull/90) ; [PR #93](https://github.com/tawounfouet/pyaccountingkit/pull/93) ; il ne s'agit ni de preuves de conformité comptable ni de validation de transactions de production.
- **Critères pour décider :**
  - [ ] Approuver graphe de transitions et droits par rôle
  - [ ] Spécifier soft-close et archivage/irréversibilité
  - [ ] Tests de transition CAS, événements et audit immuable
- **Gates / fonctionnalités bloquées par la décision :** `G6 state workflow`.
- **Décision signée, auteur, date, justification, alternatives écartées :** **NON RENSEIGNÉS**.

### ADR-CAL-06 — Réouverture et dérogations

- **Statut : OPEN — aucun arbitrage ni approbation.** Priorité : **CRITICAL**. Rôles à consulter : Accounting Approver, Security Owner, Audit Owner.
- **Options à comparer :** (1) Réouverture à simple motif ; (2) Workflow d'approbation séparé avec SoD et expiration ; (3) Dérogation temporaire ciblée et exceptionnelle.
- **Orientation de travail NON contraignante :** Étudier une autorisation distincte, motivée, bornée, à approbations indépendantes et revalidation au COMMIT.
- **Risques / conséquences :** Le dossier L06-03 ne contient que déclarations non exécutantes; aucun approveur authentifié.
- **Preuves R&D disponibles :** [PR #90](https://github.com/tawounfouet/pyaccountingkit/pull/90) ; [PR #91](https://github.com/tawounfouet/pyaccountingkit/pull/91) ; il ne s'agit ni de preuves de conformité comptable ni de validation de transactions de production.
- **Critères pour décider :**
  - [ ] Documenter rôle/SoD, motifs, quorum, durée, révocation
  - [ ] Signer et relier approval exact digest/period/actor
  - [ ] Prouver réouverture et posting sans contournement ni audit perdu
- **Gates / fonctionnalités bloquées par la décision :** `G6 reopening`, `Security #71`.
- **Décision signée, auteur, date, justification, alternatives écartées :** **NON RENSEIGNÉS**.

### ADR-CAL-07 — Autorité clôture et posting guard

- **Statut : OPEN — aucun arbitrage ni approbation.** Priorité : **BLOCKER**. Rôles à consulter : Security Architect, Ledger/Execution Owner, Domain Architect.
- **Options à comparer :** (1) Company Configuration autorité de contrôle, Ledger enforce ; (2) Ledger propriétaire de statut/lock ; (3) Protocole coordonné inter-services.
- **Orientation de travail NON contraignante :** Définir l'autorité unique et la frontière de garde COMMIT; clarifier la référence source 'ADR-CC-007' contre le registre global 'ADR-CC-07' qui ne décrit pas ce sujet.
- **Risques / conséquences :** Risque critique : consultation C10 et commande Ledger décorrélées, acteur/issuer signé indisponible, contournement des droits.
- **Preuves R&D disponibles :** [PR #90](https://github.com/tawounfouet/pyaccountingkit/pull/90) ; [PR #92](https://github.com/tawounfouet/pyaccountingkit/pull/92) ; [PR #93](https://github.com/tawounfouet/pyaccountingkit/pull/93) ; il ne s'agit ni de preuves de conformité comptable ni de validation de transactions de production.
- **Critères pour décider :**
  - [ ] Réconcilier les références ADR-CC-007/ADR-CC-07 avec décision documentée
  - [ ] Tracer propriétaire de vérité, signataire, ACL et responsabilité COMMIT
  - [ ] Prouver aucune insertion sans décision d'acteur/issuer indépendante
- **Gates / fonctionnalités bloquées par la décision :** `G3 security issue #71`, `G6 commit`, `G10`.
- **Décision signée, auteur, date, justification, alternatives écartées :** **NON RENSEIGNÉS**.

### ADR-CAL-08 — Stratégie sérialisation / fencing

- **Statut : OPEN — aucun arbitrage ni approbation.** Priorité : **BLOCKER**. Rôles à consulter : Persistence Architect, Ledger/Execution Owner, Security Reviewer.
- **Options à comparer :** (1) Transaction même DB avec verrouillage partagé ; (2) Fencing token monotone vérifié au COMMIT ; (3) Protocole distribué coordonné et prouvé.
- **Orientation de travail NON contraignante :** Sélectionner après ADR-CAL-07 un mécanisme unique vérifiable avec deux véritables writers concurrents; les traces L06-06 sont seulement symboliques.
- **Risques / conséquences :** Les stratégies multistore sans atomicité peuvent exposer une fenêtre TOCTOU même avec CI verte.
- **Preuves R&D disponibles :** [PR #93](https://github.com/tawounfouet/pyaccountingkit/pull/93) ; il ne s'agit ni de preuves de conformité comptable ni de validation de transactions de production.
- **Critères pour décider :**
  - [ ] Choisir isolation, lock order, retries, timeouts, rollback
  - [ ] Exécuter deux connexions SQL et barrières close/post dans deux ordres
  - [ ] Démontrer aucun journal après clôture, y compris crash et redelivery
- **Gates / fonctionnalités bloquées par la décision :** `G6 CAL-INV-10`, `G6 CAL-SC-09`, `Security #71`.
- **Décision signée, auteur, date, justification, alternatives écartées :** **NON RENSEIGNÉS**.

### ADR-CAL-09 — Sémantique bitemporelle des périodes

- **Statut : OPEN — aucun arbitrage ni approbation.** Priorité : **HIGH**. Rôles à consulter : Temporal Data Architect, Accounting Reviewer, Runtime Owner.
- **Options à comparer :** (1) Versions immuables et intervalles effectifs/connus ; (2) Correction in-place avec journal d'audit ; (3) Append-only avec supersession et snapshots signés.
- **Orientation de travail NON contraignante :** Privilégier un historique append-only et des snapshots immuables, sans confondre known_at du rejeu et contrôle actuel au COMMIT.
- **Risques / conséquences :** Le rejeu R&D ne prouve pas snapshots SQL ni provenance signée; rétroactivité et fuseaux doivent être arbitré.
- **Preuves R&D disponibles :** [PR #89](https://github.com/tawounfouet/pyaccountingkit/pull/89) ; [PR #90](https://github.com/tawounfouet/pyaccountingkit/pull/90) ; [PR #94](https://github.com/tawounfouet/pyaccountingkit/pull/94) ; il ne s'agit ni de preuves de conformité comptable ni de validation de transactions de production.
- **Critères pour décider :**
  - [ ] Définir recorded_at/published_at/as_of/known_at/commit_at
  - [ ] Contrainte d'exclusion et reprise après correction rétroactive
  - [ ] Signer/qualifier replay, absence de fallback et rétention des snapshots
- **Gates / fonctionnalités bloquées par la décision :** `G6 replay`, `G9 governance`, `G10 consumers`.
- **Décision signée, auteur, date, justification, alternatives écartées :** **NON RENSEIGNÉS**.

### ADR-CAL-10 — Règles calendaires par référentiel et juridiction

- **Statut : OPEN — aucun arbitrage ni approbation.** Priorité : **HIGH**. Rôles à consulter : Accounting Normative Expert, Accounting Owner, RuleSet Owner.
- **Options à comparer :** (1) Contraintes configurées par juridiction ; (2) Contraintes par framework PCG/IFRS/OHADA ; (3) Combinaison juridiction×book×référentiel avec résolution versionnée.
- **Orientation de travail NON contraignante :** Exiger validation normative indépendante des durées/périodes d'ajustement et des collisions de référentiels; ne pas prendre les noms PCG_RND/IFRS_RND pour des attestations.
- **Risques / conséquences :** Le cœur accepte exercices décalés et variabilité mais n'atteste aucune conformité légale.
- **Preuves R&D disponibles :** [PR #88](https://github.com/tawounfouet/pyaccountingkit/pull/88) ; [PR #94](https://github.com/tawounfouet/pyaccountingkit/pull/94) ; il ne s'agit ni de preuves de conformité comptable ni de validation de transactions de production.
- **Critères pour décider :**
  - [ ] Définir matrice des conventions par pays et framework
  - [ ] Séparer contrat de Normative Layer des règles métier locales
  - [ ] Tester P01..P13/4-4-5/ADJ avec avis comptable et règles versionnées
- **Gates / fonctionnalités bloquées par la décision :** `G6 normative`, `G7 policies`, `G10 consumers`.
- **Décision signée, auteur, date, justification, alternatives écartées :** **NON RENSEIGNÉS**.

## Points de synchronisation inter-ADR

1. **ADR-CAL-07 → ADR-CAL-08 :** fixer d’abord la **source autoritative du contrôle** et la responsabilité du Ledger ; choisir ensuite la sérialisation/fencing correspondant à cette frontière.
2. **ADR-CAL-01 → ADR-CAL-02 → ADR-CAL-09 :** ownership des calendriers, frontière d’agrégats, puis correction/rejeu temporel ; ne pas permettre qu’un partage de définition implique un partage de locks par défaut.
3. **ADR-CAL-03 + ADR-CAL-10 :** la sélection explicite d’une période d’ajustement reste insuffisante sans politiques et validations normatives distinctes.
4. **ADR-CAL-04 + ADR-CAL-05 + ADR-CAL-06 :** verrouillage, workflow SOFT_CLOSED/CLOSED, puis réouverture/approbation ; ces trois décisions doivent produire des scénarios négatifs cohérents.
5. **Référence contradictoire à vérifier :** le texte `14` §3 et §20 associe `ADR-CC-007` à l’autorité de clôture/posting. La roadmap Company Configuration cite cependant `ADR-CC-07` pour le langage sûr des RuleSets (L07) ; aucun identifiant inter-domaine commun ne doit être supposé. Une **correction d’index et un owner de décision** sont requis avant de fusionner ou prétendre clore ADR-CAL-07. Le dossier ne renumérote pas rétroactivement les sources.

## Gating et décisions de sécurité

**Sécurité #71 : OPEN ; G3 : HOLD_SECURITY ; G0/G1/G2 : PENDING_REVIEW ; G4/G5/G6 : NOT_APPROVED.** La vraie clôture, les locks, la publication signée, les snapshots historiques opposables et la validation finale à `Ledger COMMIT` nécessitent des preuves distinctes de la CI R&D et des véritables ADR acceptées.

### État de sortie de ce registre

- [x] Les **10 ADR-CAL** de `14` §20 sont inventoriées une seule fois.
- [x] Pour chacune : options, recommandation NON contraignante, compromis, rôles reviewers, critères vérifiables, PR preuves candidates et dépendances.
- [x] Les deux décisions bloquantes de commit `ADR-CAL-07/08` sont identifiées.
- [x] L'ambiguïté `ADR-CC-007` / `ADR-CC-07` est déclarée.
- [ ] Tenue d'une revue et d'un procès-verbal de décision indépendante.
- [ ] Signature/approbation et ADR définitives, ni créées ni simulées ici.
- [ ] G6_GO, qui exige notamment publication/audit/outbox persistés, `GetPeriodStatus` autoritatif et garde au commit.

**Document frère :** [L06_08_RND_CONSOLIDATION_AND_PRODUCTION_GAPS.md](L06_08_RND_CONSOLIDATION_AND_PRODUCTION_GAPS.md).
