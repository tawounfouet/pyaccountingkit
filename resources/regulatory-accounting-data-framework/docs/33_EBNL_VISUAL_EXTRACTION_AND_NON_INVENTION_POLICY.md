# EBNL — Visual Extraction & Non-Invention Policy

## Pourquoi cette politique

Le PDF officiel du SYCEBNL est principalement image-based. Une chaîne OCR peut produire des erreurs sur les codes, signes, colonnes et tableaux. La release 0.7.1 privilégie donc l'ancrage à la page source.

## Règles

1. **Le PDF officiel est l'autorité.**
2. **Un OCR n'écrase jamais la source.**
3. **Une page peut être structurée sans être retranscrite intégralement.**
4. **Une règle débit/crédit narrative n'est pas automatiquement une règle exécutable.**
5. **Un modèle d'état visuel n'est pas reconstruit par supposition.**
6. **Toute extraction ligne/cellule future doit porter un statut de confiance et de revue.**

## Statuts recommandés

```text
visual_title_page_verified
visual_template_bound
source_range_bound
ocr_needs_human_review
visual_code_and_label_verified
human_reviewed
```

## Future extraction fine

Une version ultérieure peut ajouter :

```text
V2.1  transcription de chaque bloc Contenu / Commentaires
V2.2  extraction Débit / Crédit / Exclusions / Contrôles
V3.1  extraction ligne par ligne des 13 modèles
V3.2  extraction structurée de toutes les Notes annexes
```

Ces couches seront additives : elles ne modifieront pas l'identité V0/V1 ni les pages sources de 0.7.1.
