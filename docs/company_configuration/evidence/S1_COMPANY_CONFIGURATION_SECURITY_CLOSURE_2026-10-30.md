# PyAccountingKit — S1 : frontière de confiance / décision de confinement #71

**Date :** 2026-10-30  
**Objet :** S1_COMPANY_CONFIGURATION_SECURITY_CLOSURE_2026-10-30.md  
**Statut technique :** `HOLD_SECURITY` — périmètre L03 en quarantaine sur cette branche, **PAS un correctif IAM**, **PAS un GO**, **PAS une décision indépendante signée**.  
**Source Git :** `e8be4691b06b7bf105edba01d7a9ba3b63e96782` (PR #70)  
**Issue de référence :** [#71](https://github.com/tawounfouet/pyaccountingkit/issues/71) ; gate [#36](https://github.com/tawounfouet/pyaccountingkit/issues/36).  
**Règle :** branche distincte, PR brouillon, aucune mutation de `main`, aucune fermeture de #71.

## 1. Constat de confiance

L03 possède quatre familles SQL d'issuers (Company, Registry, Lifecycle, Membership), neuf preuves différées de révocation de login au COMMIT (migration `0027`), une projection des epochs de grants (migration `0028`) et des reçus de décisions IAM signées (migration `0029`). Ces composants n'imposent **pas** l'appariement, par commande, de la signature de l'acteur et d'une décision IAM signée indépendante jusque dans chaque fonction d'écriture SQL.

Un rôle de type issuer pourtant autorisé par PostgreSQL peut invoquer les sept commandes sans fournir de preuve IAM individuelle persistée et non falsifiable. Un `TrustedPrincipal`, un identifiant d'acteur textuel, un GUC, un `ActorGrantEpochReference` construit en Python ou le simple `session_user` ne résolvent pas cette faille.

Les tests verts sur le SHA de #70 **ne prouvent pas** un service IAM production, un SLA de révocation distante ou l'absence de contournement des sept writes SQL.

## 2. Décision S1 : confinement fail-closed plutôt qu'approbation artificielle

La correction cryptographique complète de #71 n'est **pas qualifiée**. En application du plan anti-boucle, la seule disposition sûre à ce stade est **HOLD_SECURITY** et le **blocage technique** du chemin métier concerné.

La migration additive `0030_org_s1_hold_security.sql` installe une garde `BEFORE INSERT OR UPDATE OR DELETE` sur **15 tables** : toutes les tables de domaine Organization et leurs tables de request/audit/outbox. La garde déclenche `SQLSTATE 42501` sans accepter d'exception depuis une requête, un rôle SQL, une variable de session ou un témoin Python. Elle s'exécute **avant** les validations d'émetteur historiques, y compris lorsque le chemin est appelé via une fonction `SECURITY DEFINER`.

La protection s'applique aux sept opérations suivantes, réparties en quatre familles :

| Famille | Action | Surfaces protégées |
|---|---|---|
| Company | `RegisterCompany` | `organizational_companies` et `organization_command_*` |
| Registry | `RegisterEstablishment` | `organizational_establishments` et `organization_command_*` |
| Registry | `RegisterLegalIdentifier` | `organizational_legal_identifiers` et `organization_command_*` |
| Lifecycle | `TransitionCompany` | `organizational_company_revisions` et `organization_lifecycle_*` |
| Lifecycle | `TransitionEstablishment` | `organizational_establishment_revisions` et `organization_lifecycle_*` |
| Membership | `AssignOrganizationMembership` | `organizational_membership_revisions` et `organization_membership_*` |
| Membership | `EndOrganizationMembership` | `organizational_membership_revisions` et `organization_membership_*` |

Les 15 tables sont listées de manière **exhaustive et explicite** dans `0030`. `0001–0029` ne sont pas réécrites.

### Menaces couvertes par le confinement

- Issuer SQL valide mais absence d'une preuve IAM individuelle, révoquée ou forgée : écriture interdite.
- Fonction `*_controlled` historique : ses INSERT de domaine/provenance ne peuvent aboutir.
- Insertion directe sur une table Organization ou un registre de preuves avec un compte SQL disposant de DML : refus.
- Réutilisation d'un nonce, d'un digest ou d'un acteur Python inventé : aucune écriture organisationnelle n'est possible, indépendamment de cette donnée.
- Aucun événement request/audit/outbox de succès n'est durablement enregistré après un rejet d'insertion sur les surfaces en quarantaine.

### Limites et risques résiduels explicites

1. **Confinement ≠ appariement.** Aucun couple commande signée / décision IAM n'est encore validé au COMMIT ; #71 reste ouvert.
2. **Le propriétaire du schéma ou un superuser PostgreSQL** peut, par nature, modifier ou désactiver des triggers ; les connexions de production à privilèges DDL/superuser restent hors de la garantie de la garde. Ne jamais exposer ces identifiants à une application.
3. **Données historiques** : la migration n'efface pas les écritures passées, les jetons déjà consommés ou les décisions antérieures ; leur audit reste nécessaire.
4. **R&D et fonctionnalités** : les 7 écritures métier sont rendues indisponibles, y compris pour des tests positifs L03 ; aucun `GO_RND` de ce parcours ne peut être prononcé dans cet état.
5. **Intégration** : aucune migration n'a été exécutée ici sur une base de données réelle ; la CI PG16 doit produire la preuve. Aucun déploiement, aucune sauvegarde ni restauration de production n'est revendiqué.
6. **Externes IAM** : identité réelle, contrôle des clés, séparation des DSN, propagation des révocations et mesure du SLA continuent de relever du chantier de production.
7. **Autres mutations L02** : le confinement couvre uniquement les 15 tables L03 répertoriées ; il ne prétend pas bloquer toute l'infrastructure L00-L02 ni toutes les formes d'administration DDL.

## 3. Vérifications attendues

- [ ] CI PostgreSQL 16 sur Python 3.11 et 3.12 pour une installation fraîche `0001–0030`.
- [ ] 15/15 tables possèdent le trigger `a00_s1_hold_security`, actif et avant écriture.
- [ ] 15/15 tentatives `INSERT DEFAULT VALUES` échouent avec `42501` sur une base jetable.
- [ ] Contrôle de révocation `PUBLIC EXECUTE` du garde ; tous les comptes métier sont dépourvus de DDL.
- [ ] Récupération `0013→0030`, idempotence, rollback et dump/restore en base jetable.
- [ ] Parité SHA-256 source/wheel/sdist sur **30** migrations.
- [ ] Confirmation par audit externe des anciennes fonctions et des voies directes, y compris les droits hérités.
- [ ] Revue DBA/sécurité indépendante et signature actuelle du HOLD/approbation du périmètre.

Les workflows L03 qui exigent des commandes d'écriture **réussies** peuvent naturellement échouer sur cette branche `HOLD`. **Ne pas désactiver ou sauter ces tests pour obtenir artificiellement une CI verte** : il faut les qualifier de incompatibles avec le confinement, non les citer comme preuves d'un GO G3.

## 4. Sortie contrôlée du HOLD

Le confinement reste en place tant qu'un correctif complet (sur une autre branche/candidat) n'a pas démontré :

1. Signature de commande organisationnelle vérifiée indépendamment de la décision IAM ; clés, issuer, audience, challenge owner, nonce, acteur, tenant, action, cible et digest strictement appariés.
2. Autorisation SQL owner-only, per-command et one-use, reliée durablement à un reçu de décision valide et epoch courante ; contrôles obligatoires au COMMIT pour les sept actions.
3. Anciennes fonctions, GRANTs de rôle, direct DML et chemins UoW incapables de contourner la vérification.
4. Tests adversariaux (intertenant, acteur, version, cible, digest, JTI, révocation, concurrence, rollback), restore/migration, SQL posture et revue humaine indépendante au SHA exact.

**Ne jamais supprimer cette garde manuellement sur la branche HOLD, ni réécrire `0030` après application.** Une réouverture doit passer par une migration **additive `0031+`**, une revue explicite et des preuves exact-head (sur une base jetable puis sur la cible autorisée).

## 5. Décision et continuation

**Décision d'ingénierie proposée : `S1_HOLD_SECURITY`.** Elle signifie : aucun GO G3, aucune fusion automatique, aucune publication, aucune exposition opérationnelle de ces sept écritures. Elle **ne vaut pas** approbation ou signature d'un reviewer sécurité indépendant.

**Suite :** conserver #71 OPEN ; ouvrir un examen S2 de la pile L03 et des cinq divergences sans introduire cette quarantaine dans un candidat prétendu fonctionnel ; réconcilier les gates G0–G2 ; développer L04 uniquement dans un R&D séparé qui ne réutilise pas ces écritures privilégiées. Une réouverture de #71 suppose une décision de périmètre explicite, jamais une nouvelle cascade automatique `G3-C02b...`.
