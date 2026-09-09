# Ajouter un standard

1. Créer `standards/<standard_id>/<edition>/manifest.yaml`.
2. Déclarer les documents sources, rôles et SHA-256.
3. Déclarer les capabilities.
4. Copier les sources officielles dans `sources/`.
5. Convertir vers Markdown si nécessaire.
6. Construire V0 puis V1.
7. N'ajouter un adapter que pour les particularités du standard (codes groupés, plages, italique, colonnes, syntaxe de mapping, etc.).
8. Ajouter les invariants spécifiques dans `tests/`.
