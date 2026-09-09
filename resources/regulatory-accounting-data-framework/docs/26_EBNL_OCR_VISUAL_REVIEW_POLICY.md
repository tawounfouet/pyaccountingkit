# Politique de revue OCR — OHADA EBNL

## Autorité

```text
PDF scan = autorité visuelle
Markdown OCR = transcription dérivée
```

## Trois catégories

### 1. Ligne visuellement corrigée

Exemple :

```text
OCR : $023 Actions non cotées
PDF : 5023 Actions non cotées
```

Le dataset utilise `5023` et conserve l'OCR dans `label_ocr` / provenance.

### 2. Ligne structurellement valide mais libellé non intégralement relu

Le code et la forme sont acceptés, mais :

```text
review_status = ocr_structurally_valid_label_unproofread
confidence = 0.85
```

### 3. Anomalie imprimée dans la source

Exemple `4555`.

Le framework ne la "répare" pas.

```text
source_code_ambiguous = true
```

## Interdit

- corriger par simple intuition ;
- remplacer un libellé EBNL par le libellé SYSCOHADA ;
- déduire une équivalence sémantique de l'égalité des numéros.
