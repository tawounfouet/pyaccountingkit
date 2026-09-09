# Architecture PCG 2026

```text
Plan de comptes PDF
       ↓
Plan Markdown
       ↓
V0 RAW
       ↓
V1 STRUCTURE
       ├─────────────────────────────┐
       │                             │
Règlement consolidé                 │
       ↓                             │
Article Registry                     │
       ↓                             │
V2 Functioning Evidence              │
       │                             │
       ├────────────┐                │
       │            │                │
Recueil ANC         │                │
  ├→ IR1..IR5       │                │
  ├→ RAG index      │                │
  └→ IR4 reporting ─┴→ V3 Reporting │
                                      │
                                      ▼
                              Crosswalk / Business
                              dans phases ultérieures
```

## Pourquoi le Recueil n'est pas utilisé comme une source unique

Le Recueil réunit réglementation et doctrine. Le framework conserve donc explicitement deux niveaux :

```text
Article ANC réglementaire
≠
IR1/IR2/IR3/IR4/IR5 infra-réglementaire
```

Un résultat RAG peut citer la doctrine mais ne la transforme pas automatiquement en obligation réglementaire.
