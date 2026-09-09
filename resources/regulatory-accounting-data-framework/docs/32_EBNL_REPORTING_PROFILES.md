# OHADA EBNL — Reporting Profiles

## Principe

Le SYCEBNL n'impose pas un jeu d'états unique à toutes les entités. La release 0.7.1 introduit un objet `ReportingProfile`.

## 1. Associations et ordres professionnels

Source principale : chapitre commençant p. 345.

| Etat | Page modèle |
|---|---:|
| Bilan | 346 |
| Compte de résultat | 347 |
| Tableau des flux de trésorerie | 348 |
| Notes annexes | 349–396 |

## 2. Projets de développement et assimilés

Source principale : chapitre commençant p. 397.

| Etat | Page modèle |
|---|---:|
| Tableau emplois-ressources | 398 |
| Tableau d'exécution budgétaire | 399 |
| Tableau de réconciliation de trésorerie | 400 |
| Bilan | 401 |
| Compte d'exploitation | 402 |
| Notes annexes | 403–432 |

## 3. Système Minimal de Trésorerie

Source principale : chapitre commençant p. 433.

| Etat | Page modèle |
|---|---:|
| Bilan | 434 |
| Compte de résultat | 435 |
| Notes annexes | 435–438 |

L'Article 6 fournit les seuils liés aux ressources annuelles. La release stocke les cinq catégories de seuil à 30 000 000 XAF, mais ne crée aucune règle métier supplémentaire qui ne soit pas explicitement sourcée.

## Contrat de données

Un `ReportingProfile` sépare :

- l'applicabilité ;
- la liste des états ;
- la page officielle du modèle ;
- les Notes annexes ;
- le statut d'extraction ligne par ligne.

Les modèles visuels ne sont pas reconstruits silencieusement lorsqu'une lecture fiable de cellule n'est pas disponible.
