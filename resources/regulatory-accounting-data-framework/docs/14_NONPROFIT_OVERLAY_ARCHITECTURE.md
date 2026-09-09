# Architecture de l'overlay Non-Profit

## Héritage

```text
                 fr-pcg:2026
                      │
                      │ Art. 320-1
                      ▼
               base account graph
                      │
              ┌───────┴────────┐
              │                │
        inherited account   Art. 320-2
                               │
                    additions / overrides
                               │
                               ▼
                    fr-nonprofit:2026
```

## Exemples

### Code 102

PCG :

```text
102 - Fonds fiduciaires
```

Non-lucratif :

```text
102 - Fonds propres sans droit de reprise
```

La plateforme conserve donc un `label_or_semantic_override`.

### Groupe 19

Le groupe :

```text
19 - Fonds dédiés ou reportés
```

est une addition sectorielle.

## Règle de provenance

```text
hérité du PCG               -> derived + base source
ajout / override ANC 2018-06 -> official source
ORCOM                         -> practitioner secondary
```

ORCOM ne peut jamais devenir la provenance canonique d'un compte.
