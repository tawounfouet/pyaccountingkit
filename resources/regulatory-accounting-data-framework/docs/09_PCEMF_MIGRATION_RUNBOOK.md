# Runbook — migration du dépôt PCEMF/AMIFOND

## 1. Préparer l'environnement

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[pdf,dev]"
```

## 2. Auditer le dépôt legacy

```bash
regdata pcemf-legacy-validate ../regulatory-data   --output validation/review/pcemf_legacy_precheck.json
```

## 3. Exécuter le contrôle strict

```bash
regdata pcemf-legacy-validate ../regulatory-data --strict
```

Un mismatch n'est jamais corrigé automatiquement.

## 4. Migrer

```bash
regdata pcemf-migrate ../regulatory-data .
```

Cibles :

```text
datasets/raw/
datasets/structured/
datasets/annotated/
datasets/reporting/
datasets/prudential/
datasets/crosswalk/
datasets/business/
rag/indexes/
validation/anomalies/
validation/review/
```

## 5. Vérifier les hashes

Le rapport de migration contient pour chaque artefact :

```text
source_path
target_path
sha256
bytes
migration_mode = byte_for_byte_copy
```

## 6. Exécuter les tests

```bash
pytest -q
```

## 7. Étape suivante

Après import du vrai dépôt AMIFOND :

1. reprendre les 75 tests historiques dans le framework ;
2. comparer les sorties byte-for-byte ;
3. déplacer progressivement le code générique des pipelines historiques vers `framework/` ;
4. conserver des adapters PCEMF uniquement pour les particularités documentaires.
