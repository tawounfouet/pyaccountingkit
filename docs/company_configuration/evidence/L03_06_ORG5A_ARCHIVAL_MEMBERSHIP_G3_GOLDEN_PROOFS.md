# L03 — ORG-5a G3 Golden Proofs: Company Archival and Membership Validity

**Date:** 2026-10-30  
**Périmètre:** Company Configuration standalone en R&D (pas certification production).  
**Lignée de PR:** [#35](https://github.com/tawounfouet/pyaccountingkit/pull/35) → [#37](https://github.com/tawounfouet/pyaccountingkit/pull/37) → [#38](https://github.com/tawounfouet/pyaccountingkit/pull/38) → [#39](https://github.com/tawounfouet/pyaccountingkit/pull/39) → [#40](https://github.com/tawounfouet/pyaccountingkit/pull/40) → [#41](https://github.com/tawounfouet/pyaccountingkit/pull/41).  
**Référence fonctionnelle:** `11_COMPANY_CONFIGURATION_ORGANIZATION_AND_LEGAL_ENTITY_MODEL.md` et le suivi [L03/G3 #36](https://github.com/tawounfouet/pyaccountingkit/issues/36).

## 1. Règle métier retenue pour ORG-5a

**ARCHIVED est un état de connaissance enregistré, pas une date juridique d'effet rétroactive.**

Une société ne peut pas devenir `ARCHIVED` si une dernière révision de membership possède une période ouverte ou encore valide après la **date UTC de l'enregistrement d'archivage**. Les périodes sont demi-ouvertes : un membership dont `valid_to` égale la date de référence ne bloque pas l'archivage. Les memberships futurs encore enregistrés bloquent également.

Tout `INSERT` d'une révision de membership sur une société déjà `ARCHIVED` est refusé, même si l'appel contourne le service applicatif. Ce choix fail-closed interdit aussi une correction rétroactive après archivage : une vraie régularisation exige une procédure dédiée, non encore livrée.

## 2. Mécanisme SQL 0018 (additif)

- `guard_org_company_archive()` lit **uniquement la dernière révision de chaque membership** par `tenant_id + membership_id`; teste sa date de fin par rapport au jour UTC de l'archivage.
- `guard_org_membership_company()` vérifie l'existence de la société dans le bon tenant et reconstruit son dernier état depuis les révisions de cycle de vie.
- Les deux triggers prennent le **même advisory lock transactionnel** fondé sur `(tenant_id,company_id)`, en complément du contrôle des révisions, pour sérialiser les deux écritures concurrentes.
- Les droits `PUBLIC` d'exécution des fonctions sont révoqués. Les politiques RLS et les restrictions sur les révisions antérieures sont inchangées.
- Les 17 migrations précédentes sont intactes; l'inventaire monte à **18**.

La règle est éprouvée sous PostgreSQL mais ne remplace pas une authentification réelle d'opérateur ou une qualification de production.

## 3. Scénarios exécutables

| Test PostgreSQL | Résultat attendu |
|---|---|
| Archivage avec membership ouvert | Échec SQL et **aucune** nouvelle révision/audit/outbox |
| Fin de membership au plus tard au jour UTC d'archivage | Archivage autorisé, historique des memberships inchangé |
| Ajout futur sous société déjà archivée | Échec SQL; aucune nouvelle affiliation |
| Archive/affiliation simultanés | **Une seule opération validée**; pas d'état final incohérent |
| Archivage direct en SQL malgré membership futur | Refus par trigger, même hors application |

## 4. Preuves CI — checkpoint du code

Au commit de code `9fec89e4c632134f2acca4099cd0831cdaf73619`, quatre workflows GitHub Actions ont conclu **SUCCESS** pour Python **3.11** et **3.12** :

| Workflow | Résultat par version | GitHub |
|---|---|---|
| Python CI / Ruff | **323 passed, 23 skipped** | [#41005252076](https://github.com/tawounfouet/pyaccountingkit/actions/runs/41005252076) |
| PostgreSQL integration / Ruff | **167 passed** | [#41005251948](https://github.com/tawounfouet/pyaccountingkit/actions/runs/41005251948) |
| Migration recovery | **6 passed** | [#41005251886](https://github.com/tawounfouet/pyaccountingkit/actions/runs/41005251886) |
| Wheel/sdist/isolated import | **18 migrations SQL exactes** | [#41005251923](https://github.com/tawounfouet/pyaccountingkit/actions/runs/41005251923) |

Cette preuve est propre au SHA cité; tout nouveau commit (y compris documentaire) doit être requalifié sur son SHA final avant de prétendre à une qualification exacte de la PR.

## 5. Registre des écarts et décisions ouvertes G3

| Priorité R&D | Écart | Décision / prochain chantier |
|---|---|---|
| **P0 avant production** | Le rôle runtime peut faire certains `INSERT` directs sur des tables métier et de preuves, hors Application Service; transaction métier + audit/outbox non obligatoires pour ces chemins | **ORG-5b** : durcir les permissions SQL et imposer des points d'écriture audités vérifiables; tests négatifs des credentials |
| **P1** | Parent `legal_entities` garanti à l'insertion par trigger, pas par FK physique, et des opérations `TRUNCATE` de propriétaire peuvent créer des orphelins | ADR de cutover FK / lifecycle parent; compatibilité des tests et procédures de reprise |
| **P1** | L'archivage est lié au jour UTC enregistré, sans date juridique effective explicite | ADR de temporalité de statut et rétroactivité, avec cas d'exception |
| **P1** | Fusion/cession/scission et succession juridique non modélisées de bout en bout | Scénarios ORG-5 golden, traçabilité des relations et décisions |
| **P1** | Pas encore de contrat C10 externe pour `OrganizationTargetKind` ni d'outbox publisher qualifié | Contract testing, garanties d'authenticité et de rejeu séparées |
| **P2** | Le statut métier de certaines registrations reste la valeur initiale en table; lecture courante via projection des révisions | APIs de lecture consolidées et reconstruction as-known publique, avec tests |

**Décision de clôture:** `ORG-5a = CI-QUALIFIED_R_AND_D`, `G3 = IN_PROGRESS`. La conformité au périmètre R&D ne vaut ni approbation de sécurité de production, ni version stable. Le package reste `0.0.0` non publié; `main` n'intègre pas encore ces PR empilées.
