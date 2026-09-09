# Gouvernance et revue

## Statuts

`UNVERIFIED`, `AUTO_VERIFIED`, `HUMAN_REVIEWED`, `OFFICIAL_SOURCE`, `REJECTED`, `DEPRECATED`.

## Crosswalk

Un candidat reste `pending_human_review` jusqu'à décision avec reviewer, date, justification et preuves.

## Posting rules

```text
CANDIDATE → BUSINESS_REVIEWED → ACCOUNTING_REVIEWED → APPROVED → EXECUTABLE
```

Le passage à `EXECUTABLE` doit être traité comme une promotion de release, pas comme un simple booléen.
