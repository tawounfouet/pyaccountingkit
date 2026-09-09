# Dépôt legacy PCEMF / AMIFOND

Ce dossier est volontairement vide dans le ZIP.

Pour exécuter la migration `0.2.0`, fournir le **répertoire racine de l'ancien dépôt `regulatory-data`** contenant idéalement :

```text
datasets/
  pcemf_2010_v0_raw.json
  pcemf_2010_v1_structure.json
  pcemf_2010_v2_annotated.json
  pcemf_2010_v3_reporting.json
  pcemf_2010_v4_prudential.json
  syscohada_2017_v0_raw.json
  syscohada_2017_v1_structure.json
  pcemf_syscohada_v5_crosswalk_registry.json

rag/syscohada-guide/v1/index.json

crosswalks/pcemf2010-syscohada2017/v1/
  manifest.json
  candidates.json
  approved.json
  reviews/review_decisions.json

validation/anomalies/
  ...

# selon le nom réel retenu dans la release G
datasets/amifond_v6_business_enrichment.json
```

Validation :

```bash
regdata pcemf-legacy-validate /chemin/vers/regulatory-data
```

Validation stricte contre les invariants historiques :

```bash
regdata pcemf-legacy-validate /chemin/vers/regulatory-data --strict
```

Migration :

```bash
regdata pcemf-migrate /chemin/vers/regulatory-data .
```

Le migrateur **copie les artefacts canoniques byte-for-byte**. Les métadonnées de migration vivent dans un sidecar séparé.
