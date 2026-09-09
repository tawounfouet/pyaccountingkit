# Répertoire de Données — PyAccountingKit (`data/`)

Ce répertoire regroupe les jeux de données de démonstration, le cache d'adapters et les zones de travail locales.  
Il applique une **frontière architecturale étanche** avec le moteur comptable, les référentiels normatifs et les tests.

---

## 1. Règles Cardinales de Sécurité & d'Architecture

> [!CAUTION]
> **Ne jamais déposer de données comptables de production réelles ou confidentielles dans ce répertoire.**  
> Tout jeu de données versionné dans `data/samples/` doit être strictement synthétique ou anonymisé.

1. **Pas de duplication des référentiels réglementaires** :
   Les normes comptables officielles (PCG 2026, SYSCOHADA, OHADA EBNL, etc.) sont la propriété exclusive du framework amont [`regulatory-accounting-data-framework`](../resources/regulatory-accounting-data-framework/).  
   Aucun fichier normatif d'autorité ne doit être stocké en dur dans `data/`.
2. **Consommation via Ports & Adaptateurs** :
   Le domaine `src/pyaccountingkit/domain/` ne lit jamais directement de fichiers dans `data/`. Toute consommation de données passe par le port [`AccountingReferenceProvider`](../src/pyaccountingkit/ports/references.py) et ses adaptateurs dans [`src/pyaccountingkit/adapters/regulatory/`](../src/pyaccountingkit/adapters/regulatory/).
3. **Séparation nette avec la suite de tests** :
   - `data/samples/` : données pédagogiques publiques pour la documentation, exemples et tutoriels.
   - `tests/fixtures/` : entrées déterministes et minimales réservées à l'exécution de la suite de tests.
   - `tests/golden/` : oracles de comportement et attentes certifiées (CFA FRA, conformité FEC, bilans).

---

## 2. Structure du Répertoire

```text
data/
├── README.md                 # Le présent document de gouvernance
│
├── samples/                  # Jeux de données démonstratifs et pédagogiques (VERSIONNÉS)
│   ├── accounting/           # Écritures et balances types pour tutoriels
│   ├── fec/                  # Échantillons FEC conformes et non conformes pour tests manuels
│   ├── bank/                 # Relevés bancaires types pour démo de rapprochement
│   ├── subledgers/           # Fichiers clients/fournisseurs et lettrage
│   ├── reconciliation/       # Cas d'appariement exact, partiel ou ambigu
│   └── consolidation/        # Balances d'entités mère/filiales pour démo multi-sociétés
│
├── local/                    # Données de travail local du développeur (.gitignore - NON VERSIONNÉ)
├── cache/                    # Snapshots temporaires et cache d'adaptateurs (.gitignore - NON VERSIONNÉ)
└── generated/                # Sorties de scripts et artefacts de démonstration (.gitignore - NON VERSIONNÉ)
```

---

## 3. Détail des Rôles

| Sous-dossier | Versionné Git | Contenu & Usage |
| :--- | :---: | :--- |
| `data/samples/` | **Oui** | Données synthétiques publiques pour les exemples du README, tutoriels, démonstrateurs CLI et quickstarts. |
| `data/local/` | **Non** | Espace de travail libre pour les développeurs, fichiers ad hoc ou scénarios d'exploration locale. |
| `data/cache/` | **Non** | Cache technique temporaire, jetable et non autoritatif (ex: snapshots de référentiels téléchargés par l'adaptateur HTTP/S3). |
| `data/generated/` | **Non** | Fichiers produits localement lors de l'exécution de scripts de démonstration ou d'exports de test. |
