# 30_PYACCOUNTINGKIT_UNCERTAINTY_RECOVERY_AND_EXTERNAL_EFFECTS.md

# PyAccountingKit — Uncertainty, Recovery & External Effects

> **Projet** : PyAccountingKit  
> **Document** : `30_PYACCOUNTINGKIT_UNCERTAINTY_RECOVERY_AND_EXTERNAL_EFFECTS.md`  
> **Statut** : Spécification d'architecture transverse — effets externes, outcomes ambigus, retry et recovery  
> **Version documentaire** : 1.0  
> **Date** : 22 octobre 2026  
> **Baseline observée** : PyAccountingKit `0.7.0rc1`  
> **Langue** : Français  

---

# 1. Objet du document

Ce document définit l'architecture cible de PyAccountingKit pour gérer :

```text
external effects
timeouts
connection loss
ambiguous commit outcomes
retries
idempotency
outbox delivery
reconciliation
recovery
manual intervention
```

Le principe central est :

> **`UNCERTAIN != FAILED`**

Lorsqu'un système externe ou une infrastructure transactionnelle ne permet pas de déterminer avec certitude si une opération a réussi, PyAccountingKit ne doit pas :

```text
assumer l'échec
puis répéter aveuglément l'effet
```

Il doit :

```text
marquer l'outcome comme UNCERTAIN
        ↓
interdire la répétition aveugle
        ↓
rechercher des preuves
        ↓
réconcilier l'état
        ↓
décider ensuite :
    SUCCEEDED
    FAILED_RETRYABLE
    FAILED_FINAL
    MANUAL_REVIEW
```

---

# 2. Pourquoi ce sujet est critique en comptabilité

Une opération comptable ou financière peut produire des effets qui ne sont pas simplement "rejouables".

Exemples :

```text
publier un événement
envoyer une instruction de paiement
exporter un fichier réglementaire
déposer un artifact
appeler une API distante
synchroniser un sous-livre externe
confirmer une écriture à un ERP
émettre un webhook
```

Si l'appel distant répond :

```text
timeout
```

cela ne signifie pas nécessairement :

```text
l'effet n'a pas eu lieu
```

Il peut signifier :

```text
la requête a échoué avant traitement
```

ou :

```text
la requête a été traitée
mais la réponse s'est perdue
```

Ces deux situations nécessitent des comportements opposés.

---

# 3. Principe fondamental

La machine d'état ne doit jamais confondre :

```text
FAILED
```

avec :

```text
UNKNOWN OUTCOME
```

La cible sémantique est :

```text
FAILURE
    = nous savons que l'effet n'a pas réussi

UNCERTAIN
    = nous ne savons pas si l'effet a réussi
```

---

# 4. Baseline existante — Atomicité locale

La codebase possède déjà une base solide pour les mutations locales.

Le `UnitOfWork` regroupe aujourd'hui notamment :

```text
entries
periods
journals
audit
idempotency
outbox
clock
```

avec :

```text
commit
rollback
```

---

# 5. Baseline — Django UnitOfWork

L'adapter Django utilise :

```text
transaction.atomic
```

et marque la transaction pour commit lorsque :

```text
uow.commit()
```

est appelé.

Le commit physique intervient à la sortie du contexte transactionnel.

---

# 6. Baseline — SQLAlchemy UnitOfWork

L'adapter SQLAlchemy utilise :

```text
Session.begin()
transaction.commit()
transaction.rollback()
```

dans la frontière UoW.

---

# 7. Baseline — Idempotency

La codebase possède :

```text
IdempotencyKey
```

dérivée de :

```text
scope
operation
SHA-256(payload)
```

et un port :

```text
IdempotencyStoreProtocol
```

avec :

```text
claim()
complete()
```

---

# 8. Baseline — Idempotency persistence

Les adapters actuels stockent essentiellement :

```text
claimed
completed
```

dans :

```text
pyak_idempotency
```

---

# 9. Baseline — Transactional Outbox

Le posting orchestre déjà dans la même UoW :

```text
business mutation
+
audit
+
outbox
+
idempotency
```

avant commit.

---

# 10. Baseline — Outbox persistence

Les adapters PostgreSQL possèdent :

```text
pyak_outbox
```

avec notamment :

```text
event_type
entity_id
payload
idempotency_key
```

---

# 11. Baseline — Spécification plus riche que le runtime actuel

La spécification de persistence existante prévoit déjà conceptuellement :

```text
IdempotencyStatus:
    RESERVED
    COMPLETED
    FAILED_RETRYABLE
    FAILED_FINAL
```

ainsi qu'une outbox avec :

```text
status
retry_count
correlation_id
aggregate_ref
```

et une classification :

```text
RETRYABLE
NON_RETRYABLE
```

---

# 12. Gap actuel

Le runtime observé n'implémente pas encore complètement :

```text
FAILED_RETRYABLE
FAILED_FINAL
UNCERTAIN
outbox delivery lifecycle
retry_count
next_attempt_at
external-effect reconciliation
```

Ce document formalise donc une **cible**, pas une prétendue capacité déjà disponible.

---

# 13. Autre gap — Public retryability

L'API publique expose déjà le champ :

```text
retryable: bool
```

mais la hiérarchie actuelle de `public/errors.py` n'implémente encore qu'une base où :

```text
retryable = False
```

par défaut.

Les erreurs opérationnelles retryables documentées dans les specs doivent encore être représentées concrètement.

---

# 14. External Effect

Concept cible :

```text
ExternalEffect
```

Un External Effect est :

> une action observable hors de la transaction locale PyAccountingKit et dont le résultat peut être impossible à annuler ou à connaître immédiatement.

---

# 15. Exemples d'External Effects

```text
message broker publication
webhook
HTTP API call
bank/payment instruction
remote ERP mutation
object storage upload
email notification
external regulatory submission
file transfer
```

---

# 16. Ce qui n'est pas un External Effect

Une mutation réalisée dans :

```text
la même transaction PostgreSQL
```

que l'aggregate principal n'est pas un effet externe du point de vue de cette transaction.

Exemple :

```text
JournalEntry
+
AuditEvent
+
OutboxMessage
```

dans la même transaction locale.

---

# 17. Local transaction vs external effect

```text
LOCAL TRANSACTION
    atomicity possible

EXTERNAL EFFECT
    distributed atomicity generally unavailable
```

---

# 18. No distributed transaction assumption

PyAccountingKit ne suppose pas :

```text
2PC
distributed transaction coordinator
global exactly-once
```

pour les systèmes externes.

---

# 19. External-effect safety model

La cible repose sur :

```text
local atomic intent
+
stable effect identity
+
idempotency where supported
+
at-least-once delivery
+
outcome classification
+
reconciliation
+
recovery
```

---

# 20. External Effect State Machine

États cibles :

```text
PLANNED
IN_PROGRESS
SUCCEEDED
FAILED_RETRYABLE
FAILED_FINAL
UNCERTAIN
RECONCILING
MANUAL_REVIEW
```

---

# 21. `PLANNED`

L'effet est enregistré mais aucun appel externe n'a encore commencé.

Safe retry :

```text
YES
```

---

# 22. `IN_PROGRESS`

L'appel a été démarré.

Aucune nouvelle tentative concurrente ne doit être admise sans coordination.

---

# 23. `SUCCEEDED`

Une preuve suffisante confirme que l'effet a réussi.

Exemples :

```text
HTTP 2xx with stable external operation ID
message broker ack with durable semantics
remote lookup confirms applied operation
```

---

# 24. `FAILED_RETRYABLE`

Nous savons que l'effet n'a pas réussi et qu'une nouvelle tentative est raisonnablement sûre.

Exemples :

```text
connection refused before request sent
503 before processing according to provider contract
lock timeout local before mutation
```

---

# 25. `FAILED_FINAL`

L'effet a échoué de façon déterministe.

Exemples :

```text
invalid request
business rejection
unsupported destination
authorization denied requiring configuration change
```

---

# 26. `UNCERTAIN`

Nous ne savons pas si l'effet a réussi.

Exemples :

```text
timeout after request bytes sent
connection reset after provider may have committed
commit acknowledgement lost
broker ack lost after possible publish
```

---

# 27. `RECONCILING`

PyAccountingKit recherche une preuve externe.

Exemples :

```text
GET operation by idempotency key
lookup external transaction ID
query broker delivery status
inspect object checksum
```

---

# 28. `MANUAL_REVIEW`

Le framework ne dispose pas de preuve suffisante pour conclure automatiquement.

Un opérateur doit intervenir.

---

# 29. State transitions

```text
PLANNED
   ↓
IN_PROGRESS
   ├──────────────→ SUCCEEDED
   ├──────────────→ FAILED_RETRYABLE
   ├──────────────→ FAILED_FINAL
   └──────────────→ UNCERTAIN
                       ↓
                  RECONCILING
                 /      |      \
                /       |       \
         SUCCEEDED   FAILED_*   MANUAL_REVIEW
```

---

# 30. Interdit

```text
UNCERTAIN
    ↓
blind automatic retry
```

sans réconciliation ou garantie d'idempotence externe suffisamment forte.

---

# 31. `EffectId`

Chaque effet externe possède une identité stable :

```text
EffectId
```

---

# 32. Properties

```text
same intended business effect
=
same EffectId
```

Un retry n'engendre pas un nouvel effet logique.

---

# 33. `AttemptId`

Chaque tentative technique possède :

```text
AttemptId
```

Relation :

```text
EffectId 1
    ├── Attempt 1
    ├── Attempt 2
    └── Attempt 3
```

---

# 34. Pourquoi EffectId != AttemptId

Cela permet de distinguer :

```text
one business intention
```

de :

```text
multiple technical attempts
```

---

# 35. Stable idempotency key

Lorsque le provider externe supporte une clé d'idempotence :

```text
external_idempotency_key
```

doit être stable pour toutes les tentatives du même `EffectId`.

---

# 36. Exemple

```text
EffectId = payment:entity-42:invoice-99

Attempt 1
    timeout

Attempt 2
    same provider idempotency key
```

Si le provider garantit réellement l'idempotence, la seconde tentative peut être sûre selon son contrat.

---

# 37. Idempotency strength

Tous les mécanismes d'idempotence ne sont pas équivalents.

Classer :

```text
NONE
LOCAL_ONLY
PROVIDER_BEST_EFFORT
PROVIDER_STRONG
QUERY_RECONCILABLE
```

---

# 38. `NONE`

Aucune garantie externe.

En cas d'UNCERTAIN :

```text
manual/reconciliation required
```

---

# 39. `LOCAL_ONLY`

PyAccountingKit empêche les doublons locaux mais ne sait pas empêcher un provider d'exécuter deux fois.

---

# 40. `PROVIDER_BEST_EFFORT`

Le provider accepte une clé mais ses garanties sont limitées :

```text
expiration
eventual consistency
undefined duplicate window
```

---

# 41. `PROVIDER_STRONG`

Le provider garantit :

```text
same key
+
same semantic request
=
same external operation
```

dans une fenêtre/documentation définie.

---

# 42. `QUERY_RECONCILABLE`

Le provider permet de rechercher l'opération par :

```text
idempotency key
external reference
business reference
```

---

# 43. Retry safety matrix

| Outcome | Strong external idempotency | Reconciliation available | Action |
|---|---:|---:|---|
| FAILED_RETRYABLE | n/a | n/a | retry bounded |
| FAILED_FINAL | any | any | no retry |
| UNCERTAIN | yes | yes | reconcile, then retry if unresolved policy allows |
| UNCERTAIN | yes | no | bounded retry only if provider contract proves safety |
| UNCERTAIN | no | yes | reconcile before retry |
| UNCERTAIN | no | no | manual review / stop |

---

# 44. Retry is a policy

Un retry n'est pas un comportement du domaine comptable.

Il appartient à :

```text
application runtime
worker
adapter
integration layer
```

---

# 45. Domain rule

Le domaine ne doit pas contenir :

```python
for _ in range(5):
    try_external_call()
```

---

# 46. Whole-operation retry

Pour une transaction locale :

```text
rollback
+
retry whole transaction
```

si :

```text
error is retryable
operation is idempotent
retry budget remains
```

---

# 47. Half-transaction retry interdit

Interdit :

```text
entry saved
audit failed
retry audit only
```

si cela rompt la frontière transactionnelle attendue.

---

# 48. External-effect retry

Pour un effet externalisé via outbox :

```text
business transaction
    commits intent
        ↓
dispatcher executes effect
        ↓
effect attempt state updated
```

La transaction métier n'est pas rejouée pour republier l'effet.

---

# 49. Transactional Outbox role

La transactional outbox résout :

```text
DB state committed
but event intent lost
```

Elle ne résout pas à elle seule :

```text
did the remote consumer execute the effect?
```

---

# 50. Outbox guarantee

La cible réaliste est :

```text
at-least-once delivery
```

avec :

```text
deduplication / idempotent consumer
```

---

# 51. Pas de distributed exactly-once claim

PyAccountingKit ne doit pas promettre :

```text
exactly once across DB + Kafka + ERP + bank
```

sans mécanisme démontrable.

---

# 52. Outbox lifecycle target

États proposés :

```text
PENDING
CLAIMED
PUBLISHED
FAILED_RETRYABLE
UNCERTAIN
DEAD_LETTER
```

---

# 53. `PENDING`

Message durable, jamais tenté.

---

# 54. `CLAIMED`

Un dispatcher détient temporairement le message.

Nécessite :

```text
lease / claim timeout
```

pour reprise après crash.

---

# 55. `PUBLISHED`

Le transport a confirmé selon sa sémantique contractuelle.

Cela ne signifie pas forcément :

```text
business side effect executed downstream
```

---

# 56. `FAILED_RETRYABLE`

La publication n'a pas réussi et peut être retentée.

---

# 57. `UNCERTAIN`

La publication a peut-être réussi mais l'ack est ambigu.

---

# 58. `DEAD_LETTER`

Le budget de retry est épuisé ou l'erreur est finale.

---

# 59. Outbox record target

```text
OutboxMessage
|
+-- message_id
+-- event_id
+-- event_type
+-- entity_id
+-- aggregate_ref?
+-- correlation_id?
+-- causation_id?
+-- payload
+-- payload_checksum
+-- idempotency_key
+-- status
+-- retry_count
+-- next_attempt_at?
+-- claimed_by?
+-- claim_expires_at?
+-- last_error_code?
+-- last_attempt_at?
+-- published_at?
```

---

# 60. Current implementation delta

Le runtime actuel ne stocke encore que :

```text
event_type
entity_id
payload
idempotency_key
```

Le lifecycle ci-dessus est donc une évolution cible.

---

# 61. `ExternalEffectRecord`
Pour les effets plus riches qu'un message :

```text
ExternalEffectRecord
|
+-- effect_id
+-- effect_type
+-- entity_id
+-- correlation_id
+-- state
+-- idempotency_strength
+-- external_idempotency_key?
+-- external_reference?
+-- request_checksum
+-- result_checksum?
+-- created_at
+-- updated_at
+-- last_attempt_id?
```

---

# 62. `EffectAttempt`

```text
EffectAttempt
|
+-- attempt_id
+-- effect_id
+-- attempt_number
+-- started_at
+-- ended_at?
+-- outcome
+-- error_code?
+-- remote_status?
+-- external_reference?
+-- evidence_checksum?
```

---

# 63. Request checksum

Chaque effet pinne :

```text
request_checksum
```

pour éviter :

```text
same idempotency key
+
different payload
```

---

# 64. Payload conflict

Le cas :

```text
same EffectId
different request checksum
```

doit échouer :

```text
EffectPayloadConflictError
```

---

# 65. Relation avec `IdempotencyKey`

Le `IdempotencyKey` actuel reste utile.

Il doit être distingué de :

```text
EffectId
```

---

# 66. IdempotencyKey

Répond :

> cette command ou mutation a-t-elle déjà été exécutée ?

---

# 67. EffectId

Répond :

> quel effet externe logique essayons-nous d'obtenir ?

---

# 68. EventId

Répond :

> quel fait métier immutable a été émis ?

---

# 69. CorrelationId

Répond :

> à quel parcours métier global cela appartient-il ?

---

# 70. Identity chain

```text
CorrelationId
    ↓
DomainEvent EventId
    ↓
Outbox MessageId
    ↓
External EffectId
    ↓
AttemptId(s)
```

---

# 71. Unknown DB commit outcome

Un cas particulier critique est :

```text
COMMIT envoyé
connexion perdue
ack non reçu
```

---

# 72. Pourquoi rollback ne suffit pas

Après une perte de connexion au moment du commit, le client peut ne pas savoir si PostgreSQL a :

```text
committed
```

ou :

```text
rolled back
```

Le code appelant ne doit pas conclure automatiquement :

```text
transaction failed
```

---

# 73. `CommitOutcome`

Concept cible :

```text
COMMITTED
ROLLED_BACK
UNCERTAIN
```

---

# 74. Normal local UoW

Dans la plupart des exécutions synchrones :

```text
commit success
→ COMMITTED

exception known before commit
→ ROLLED_BACK
```

---

# 75. Commit uncertainty

Si l'adapter/runtime détecte une exception dont le contrat ne permet pas de savoir si le commit a été appliqué :

```text
CommitOutcome = UNCERTAIN
```

---

# 76. Recovery from uncertain commit

La command doit être réconciliée via une identité durable.

Exemple Posting :

```text
idempotency key
entry ID
outbox key
```

---

# 77. Posting uncertain commit recovery

Pseudo-flow :

```text
POST entry E
    ↓
commit connection lost
    ↓
UNCERTAIN
    ↓
re-open transaction
    ↓
lookup:
    Entry E?
    Idempotency K?
    Audit?
    Outbox?
```

---

# 78. Recovery result A

Si :

```text
Entry POSTED
Idempotency COMPLETED
Outbox exists
```

alors :

```text
operation = SUCCEEDED
```

Ne pas reposter.

---

# 79. Recovery result B

Si aucune trace n'existe :

```text
operation = FAILED_RETRYABLE
```

Le command handler peut réessayer selon policy.

---

# 80. Recovery result C

Si l'état est partiel/incohérent :

```text
MANUAL_REVIEW
```

ou :

```text
ConsistencyViolationError
```

car l'atomicité attendue a été violée.

---

# 81. Atomicity evidence

Une UoW critique doit pouvoir réconcilier :

```text
business state
audit
idempotency
outbox
```

comme un ensemble.

---

# 82. Local recovery probe

Concept :

```text
OperationRecoveryProbe
```

---

# 83. Protocol possible

```python
class OperationRecoveryProbeProtocol(Protocol):
    def inspect(self, operation_ref: str) -> RecoveryObservation:
        ...
```

---

# 84. `RecoveryObservation`

```text
RecoveryObservation
|
+-- business_state
+-- idempotency_state
+-- audit_state
+-- outbox_state
+-- evidence
```

---

# 85. Reconciliation first

Le principe de recovery est :

> **observe before mutate**

---

# 86. Interdit

```text
uncertain
→ immediately run same mutation again
```

si l'effet original n'est pas prouvé idempotent.

---

# 87. External reconciliation

Pour un provider externe, le port de recovery peut être :

```text
ExternalEffectReconcilerProtocol
```

---

# 88. Protocol possible

```python
class ExternalEffectReconcilerProtocol(Protocol):
    def reconcile(
        self,
        effect: ExternalEffectRecord,
    ) -> ExternalEffectObservation:
        ...
```

---

# 89. Observation statuses

```text
APPLIED
NOT_APPLIED
PENDING_REMOTE
AMBIGUOUS
NOT_QUERYABLE
```

---

# 90. `APPLIED`

Le provider confirme que l'effet a été exécuté.

→ `SUCCEEDED`.

---

# 91. `NOT_APPLIED`

Le provider confirme l'absence d'effet.

→ `FAILED_RETRYABLE` ou `FAILED_FINAL` selon la cause.

---

# 92. `PENDING_REMOTE`

Le provider connaît l'opération mais ne l'a pas finalisée.

→ pas de retry duplicatif.

Continuer monitoring/reconciliation.

---

# 93. `AMBIGUOUS`

Plusieurs résultats possibles ou données insuffisantes.

→ manual review ou policy spécialisée.

---

# 94. `NOT_QUERYABLE`

Le provider ne permet aucune interrogation.

Le retry dépend alors du niveau d'idempotence documenté.

---

# 95. Recovery policy

Concept :

```text
RecoveryPolicy
```

---

# 96. Fields

```text
max_attempts
initial_backoff
max_backoff
backoff_strategy
jitter?
uncertain_reconcile_delay
manual_review_after
```

---

# 97. Jitter

Le jitter est acceptable pour la planification technique.

Il ne doit pas affecter :

```text
business result
manifest checksum
```

---

# 98. Retry budget

Tout retry automatique est borné.

Interdit :

```text
while True:
    retry()
```

---

# 99. Exponential backoff

Possible :

```text
1s
2s
4s
8s
...
```

avec plafond.

---

# 100. Business urgency

Certaines opérations peuvent exiger une policy différente :

```text
webhook
vs
regulatory submission
vs
payment
```

---

# 101. External effect classification

Catégories utiles :

```text
NOTIFICATION
PUBLICATION
REMOTE_MUTATION
PAYMENT
ARTIFACT_WRITE
REGULATORY_SUBMISSION
```

---

# 102. Notification

Exemple :

```text
email/webhook
```

Double envoi peut être désagréable mais parfois tolérable.

---

# 103. Remote mutation

Exemple :

```text
ERP state update
```

Double exécution peut être problématique.

---

# 104. Payment

Double exécution peut être critique.

La policy doit être fail-safe :

```text
reconcile before retry
```

---

# 105. Artifact write

Si l'artifact possède :

```text
content-addressed key
```

l'effet peut être naturellement idempotent.

---

# 106. Regulatory submission

Peut exiger :

```text
submission ID
provider receipt
manual review
```

avant nouvelle tentative.

---

# 107. Risk classes

```text
LOW
MEDIUM
HIGH
CRITICAL
```

---

# 108. Retry rule by risk

| Risk | Blind retry after UNCERTAIN |
|---|---|
| LOW | only if explicit policy permits |
| MEDIUM | normally reconcile first |
| HIGH | reconcile first |
| CRITICAL | reconcile first, manual review if unresolved |

---

# 109. Payment-like operations

Principe :

```text
UNKNOWN ≠ RETRY
```

---

# 110. Outbox dispatcher

Composant cible :

```text
OutboxDispatcher
```

---

# 111. Responsibilities

```text
claim pending messages
publish
classify outcome
persist attempt
schedule retry
mark published
route uncertain to reconciliation
dead-letter when needed
```

---

# 112. Dispatcher ownership

Le dispatcher appartient à :

```text
runtime/infrastructure
```

pas au domaine comptable.

---

# 113. Dispatcher concurrency

Plusieurs workers peuvent fonctionner.

Nécessite :

```text
claim/lease
locking
skip locked or equivalent
```

selon adapter.

---

# 114. Claim lease

Fields :

```text
claimed_by
claim_expires_at
```

---

# 115. Worker crash

Si un worker meurt avec un message `CLAIMED` :

```text
lease expires
→ another worker may resume
```

---

# 116. Fencing

Pour les effets critiques, un fencing token peut être utile si un effect executor peut rester actif après perte de lease.

Ce besoin doit être évalué avant implémentation.

---

# 117. Outbox ordering

L'ordre global n'est pas garanti.

Si nécessaire :

```text
aggregate sequence
```

ou :

```text
partition key
```

doit être explicite.

---

# 118. Same aggregate ordering

Pour un même aggregate :

```text
posted
then reversed
```

le transport ne doit pas publier :

```text
reversed
before posted
```

si le consumer exige l'ordre.

---

# 119. Ordering strategy

Options :

```text
aggregate_sequence
ordered partition
consumer buffering
```

---

# 120. Duplicate delivery

Le transport peut livrer :

```text
same EventId multiple times
```

---

# 121. Consumer rule

Un consumer critique doit dédupliquer par :

```text
EventId
```

ou une business effect key appropriée.

---

# 122. Consumer Inbox

Pattern possible :

```text
Inbox
```

pour les consumers qui ont besoin d'une déduplication durable.

---

# 123. Inbox model

```text
ConsumedEvent
|
+-- consumer_id
+-- event_id
+-- consumed_at
+-- result_ref?
```

Unique :

```text
(consumer_id, event_id)
```

---

# 124. Inbox != Outbox

```text
Outbox
    protects sending intent

Inbox
    protects consumer duplicate processing
```

---

# 125. Recovery coordinator

Composant cible possible :

```text
RecoveryCoordinator
```

---

# 126. Responsibilities

```text
find UNCERTAIN effects
invoke reconciler
apply RecoveryPolicy
transition state
emit audit/evidence
escalate manual review
```

---

# 127. Recovery jobs

Les jobs doivent être idempotents.

---

# 128. Recovery lock

Deux recovery workers ne doivent pas réconcilier le même effet de manière concurrente sans contrôle.

---

# 129. Recovery evidence

Chaque décision de recovery produit :

```text
RecoveryEvidence
```

---

# 130. Structure

```text
RecoveryEvidence
|
+-- recovery_id
+-- effect_id
+-- previous_state
+-- observation
+-- decision
+-- evidence_refs
+-- actor/system
+-- occurred_at
+-- checksum
```

---

# 131. Decision values

```text
CONFIRM_SUCCEEDED
CONFIRM_NOT_APPLIED
RETRY_SCHEDULED
MARK_FAILED_FINAL
ESCALATE_MANUAL
```

---

# 132. Auditability

Toute transition depuis :

```text
UNCERTAIN
```

doit être auditable.

---

# 133. Recovery and manifests

Un effect/recovery flow peut être référencé dans :

```text
ComputationManifest
EvidenceBundle
```

si l'effet est lié à une publication financière.

---

# 134. Domain events

Exemples d'événements possibles :

```text
external_effect.planned
external_effect.succeeded
external_effect.uncertain
external_effect.reconciled
external_effect.failed
```

Ces événements sont des faits techniques/métier selon leur portée.

---

# 135. Ne pas polluer le domaine

Tous les timeouts techniques ne nécessitent pas un DomainEvent public.

La visibilité peut être :

```text
INTERNAL
AUDIT
INTEGRATION
```

---

# 136. Error taxonomy cible

```text
ExternalEffectError
|
+-- ExternalEffectRejectedError
+-- ExternalEffectUnavailableError
+-- ExternalEffectTimeoutError
+-- ExternalEffectUncertainError
+-- ExternalEffectPayloadConflictError
+-- ExternalEffectReconciliationError
+-- ExternalEffectNotQueryableError
+-- ExternalEffectRetryExhaustedError
```

---

# 137. Persistence errors

Compléter la taxonomie locale avec :

```text
CommitOutcomeUncertainError
RecoveryConsistencyError
```

---

# 138. Public error semantics

L'API publique ne doit pas exposer :

```text
OperationalError
psycopg exception
SQLAlchemy exception
```

---

# 139. Retryable public error

Exemple :
```text
PERSISTENCE_TEMPORARILY_UNAVAILABLE
retryable = true
```

si l'échec est connu comme non-committed et sûr à retenter.

---

# 140. Uncertain public error

Une erreur :

```text
OPERATION_OUTCOME_UNCERTAIN
```

ne doit pas être exposée simplement comme :

```text
retryable = true
```

---

# 141. Public hint

Proposition :

```text
retryable = false
recovery_required = true
operation_ref = ...
```

ou un équivalent structuré.

---

# 142. Pourquoi `retryable: bool` seul est insuffisant

Trois états existent :

```text
retry safely
do not retry
reconcile first
```

Un booléen n'exprime que deux états.

---

# 143. Public disposition

Concept recommandé :

```text
RecoveryDisposition
```

---

# 144. Values

```text
RETRY
DO_NOT_RETRY
RECONCILE
MANUAL_REVIEW
```

---

# 145. Backward compatibility

Le champ :

```text
retryable
```

peut être conservé.

Ajouter :

```text
disposition
```

dans une évolution versionnée de l'API publique.

---

# 146. Public error example

```json
{
  "code": "OPERATION_OUTCOME_UNCERTAIN",
  "message": "The remote outcome could not be confirmed.",
  "retryable": false,
  "disposition": "RECONCILE",
  "details": {
    "operation_ref": "effect:..."
  }
}
```

---

# 147. Local DB error classification

Exemples :

```text
deadlock before commit known aborted
    → RETRY

lock timeout
    → RETRY

validation violation
    → DO_NOT_RETRY

unique business conflict
    → DO_NOT_RETRY / reload

commit connection loss
    → RECONCILE
```

---

# 148. External HTTP classification

L'adapter doit classifier selon le provider contract.

Ne pas coder génériquement :

```text
all 5xx = retry
all timeout = retry
```

---

# 149. Example HTTP 503

Si la documentation du provider garantit :

```text
request not processed
```

alors :

```text
FAILED_RETRYABLE
```

Sinon le status seul peut être insuffisant.

---

# 150. HTTP timeout

Un timeout après envoi complet du body est généralement :

```text
UNCERTAIN
```

sauf garantie contraire.

---

# 151. Connection refused

Avant établissement de connexion :

```text
FAILED_RETRYABLE
```

car l'effet n'a pas atteint le provider.

---

# 152. DNS failure

Généralement :

```text
FAILED_RETRYABLE
```

si aucune requête n'a pu atteindre le provider.

---

# 153. Client validation error

```text
FAILED_FINAL
```

---

# 154. Provider business rejection

```text
FAILED_FINAL
```

sauf si le provider marque explicitement la cause comme transitoire.

---

# 155. HTTP adapter contract

Le contract doit retourner un résultat métier structuré :

```text
ExternalCallOutcome
```

plutôt que seulement propager une exception réseau brute.

---

# 156. `ExternalCallOutcome`

```text
status
provider_code?
external_reference?
retry_after?
evidence?
```

---

# 157. Object storage effects

Upload cible :

```text
checksum-addressed object
```

permet de réduire l'ambiguïté.

---

# 158. Upload uncertain

Si timeout après upload :

```text
HEAD object
compare checksum
```

avant retry.

---

# 159. `ArtifactStore` recovery

Le port peut supporter :

```text
exists(ref)
checksum(ref)
```

pour réconciliation.

---

# 160. Regulatory submission

Chaque submission devrait posséder :

```text
submission_id
payload_checksum
provider receipt
```

---

# 161. Retry regulatory submission

En cas de timeout :

```text
query by submission_id
```

avant nouvel envoi.

---

# 162. Imports

Les imports sont principalement locaux aujourd'hui.

Leur reprise doit utiliser :

```text
checkpoint
source fingerprint
batch idempotency
entry idempotency
```

déjà prévus dans la spécification Import.

---

# 163. Import failure known before commit

```text
rollback
→ retry batch/chunk according to checkpoint policy
```

---

# 164. Import commit uncertainty

Réconcilier :

```text
batch fingerprint
imported source entry identities
ledger entries
```

avant reprise.

---

# 165. Import post-commit undo

Ne jamais :

```text
DELETE imported posted entries
```

Le domaine utilise :

```text
reversal
```

---

# 166. Posting

Posting est localement transactionnel.

En cas d'erreur connue avant commit :

```text
rollback
```

---

# 167. Posting commit uncertainty

Réconciliation :

```text
EntryId
IdempotencyKey
AuditEvent
OutboxRecord
```

---

# 168. Reversal

Même logique.

Une reversal incertaine ne doit jamais être répétée aveuglément car :

```text
double reversal
```

est une violation métier.

---

# 169. Closing

Clôture incertaine :

```text
reload period
inspect closing run
inspect generated entries
inspect audit/outbox
```

---

# 170. Closing retry

Si :

```text
period already CLOSED
with expected close revision
```

retourner l'état existant plutôt que recréer une clôture.

---

# 171. Settlement

Les settlements sont particulièrement sensibles.

En cas d'UNCERTAIN autour d'un provider de paiement externe :

```text
query payment reference first
```

---

# 172. Reconciliation

Le bounded context Reconciliation peut aider à résoudre certains effets externes.

Mais :

```text
recovery reconciliation
```

et :

```text
accounting reconciliation
```

doivent rester conceptuellement distincts.

---

# 173. `RecoveryReconciliation`

Termes recommandés :

```text
EffectReconciliation
OperationReconciliation
```

pour éviter la confusion avec le rapprochement bancaire/comptable.

---

# 174. Semantic/reports exports

Un export local déterministe peut être reconstruit.

Un envoi distant de l'export ne l'est pas nécessairement.

Séparer :

```text
artifact generation
```

de :

```text
artifact submission
```

---

# 175. Generate then submit

Pipeline recommandé :

```text
ReportSnapshot
    ↓
ExportArtifact
    ↓
checksum
    ↓
ExternalSubmission Effect
```

---

# 176. Rebuild artifact

Le rebuild est sûr si :

```text
same semantic source
same renderer version
```

---

# 177. Resubmit artifact

La resoumission nécessite :

```text
submission idempotency/reconciliation policy
```

---

# 178. Effect outbox

Option architecturale :

```text
OutboxMessage
```

peut représenter l'intention d'un `ExternalEffect`.

Le dispatcher transforme :

```text
message
→ effect attempt
```

---

# 179. Separate effect store?

Pour des effets complexes, un store spécialisé est préférable à surcharger l'outbox.

---

# 180. Rule

```text
simple reliable event publication
    → Outbox lifecycle

rich remote business effect with reconciliation
    → ExternalEffectRecord + attempts
```

---

# 181. Ports cibles

```text
OutboxRepositoryProtocol
OutboxDispatcherProtocol
ExternalEffectStoreProtocol
ExternalEffectExecutorProtocol
ExternalEffectReconcilerProtocol
RecoveryEvidenceRepositoryProtocol
```

---

# 182. Domain ownership

Ces ports appartiennent principalement à :

```text
application/runtime boundary
```

pas au core accounting domain.

---

# 183. Domain-first placement

Après `29`, cible possible :

```text
shared/
    recovery primitives

infrastructure/
    outbox/
    recovery/

<context>/
    external-effect policies specific to that context
```

---

# 184. Minimal shared recovery primitives

Seuls les concepts réellement génériques :

```text
EffectId
AttemptId
Outcome
RecoveryDisposition
```

peuvent être shared.

---

# 185. No shared provider knowledge

Interdit dans shared :

```text
Stripe timeout rules
ERP-specific codes
bank-specific statuses
```

---

# 186. Provider adapter owns classification

L'adapter du provider traduit :

```text
provider response
→ canonical outcome
```

---

# 187. Recovery strategy ownership

Une capability métier peut décider :

```text
whether a duplicated effect is tolerable
whether manual review is mandatory
```

---

# 188. Observability

Métriques recommandées :

```text
external_effect_started_total
external_effect_succeeded_total
external_effect_uncertain_total
external_effect_failed_total
external_effect_retry_total
external_effect_reconciled_total
external_effect_manual_review_total
outbox_pending
outbox_claimed
outbox_uncertain
outbox_dead_letter
```

---

# 189. Latency metrics

```text
effect_attempt_duration
time_in_uncertain
reconciliation_duration
outbox_oldest_pending_age
```

---

# 190. Alerts

Alertes recommandées :

```text
UNCERTAIN older than threshold
dead-letter > 0 critical effect
outbox backlog increasing
manual review queue too old
```

---

# 191. Logging

Logs structurés :

```text
effect_id
attempt_id
correlation_id
event_id
provider
outcome
```

---

# 192. No sensitive payload logging

Ne pas loguer par défaut :

```text
bank credentials
API tokens
personal data
full financial payload
```

---

# 193. Tracing

OpenTelemetry peut propager :

```text
correlation_id
effect_id
attempt_id
```

sans devenir la source de vérité métier.

---

# 194. Recovery evidence persistence

Les preuves doivent rester plus durables que les traces observability.

---

# 195. Security

Un retry ne doit jamais contourner :

```text
authorization
tenant scope
business validation
```

---

# 196. Reconciliation credentials

Les credentials de query externe restent dans l'adapter sécurisé.

Jamais dans :

```text
ExternalEffectRecord
```

---

# 197. Tenant isolation

Effect lookup et recovery sont scoped par :

```text
tenant/accounting entity
```

---

# 198. Manual review

Un opérateur peut :

```text
confirm success
confirm non-execution
authorize retry
mark failed final
```

selon permissions.

---

# 199. No arbitrary state editing

L'UI d'ops ne doit pas permettre :

```text
set status = SUCCEEDED
```

sans :

```text
reason
actor
evidence
timestamp
```

---

# 200. Manual decision record

```text
RecoveryDecision
|
+-- decision_id
+-- effect_id
+-- decision
+-- actor_id
+-- rationale
+-- evidence_refs
+-- occurred_at
```

---

# 201. SoD

Pour effets critiques, certaines décisions peuvent nécessiter :

```text
four-eyes approval
```

selon application.

PyAccountingKit peut fournir le contract sans imposer une UI.

---

# 202. Dead-letter

`DEAD_LETTER` ne veut pas dire :

```text
safe to forget
```

Il signifie :

```text
automatic processing stopped
operator/recovery process required
```

---

# 203. Dead-letter evidence

Conserver :

```text
last error
attempt count
payload checksum
effect identity
```

---

# 204. Retry exhaust

Lorsque `max_attempts` est atteint :

```text
FAILED_FINAL
```

ou :

```text
MANUAL_REVIEW
```

selon policy.

---

# 205. Timeout budget

Chaque tentative doit être bornée.

---

# 206. Request timeout vs operation timeout

Distinguer :

```text
network request timeout
```

de :

```text
business operation SLA
```

---

# 207. Circuit breaker

Option runtime possible pour un provider instable.

Il protège :

```text
system capacity
```

mais ne détermine pas le résultat d'un effet déjà commencé.

---

# 208. Circuit open

Nouveau call non commencé :

```text
FAILED_RETRYABLE / deferred
```

pas :

```text
UNCERTAIN
```

---

# 209. Bulkhead

Une integration lente ne doit pas épuiser tous les workers.

Sujet runtime, non domain.

---

# 210. Rate limit

HTTP `429` peut être :

```text
FAILED_RETRYABLE
```

avec :

```text
retry_after
```

si le provider garantit qu'il n'a pas appliqué l'opération.

---

# 211. Saga?

PyAccountingKit n'a pas besoin d'un framework Saga généraliste en première intention.

---

# 212. Compensation

Une compensation n'est pas un rollback distribué.

Exemple :

```text
payment sent
then business process fails
```

peut nécessiter :

```text
refund / reversal
```

comme nouvel effet explicite.

---

# 213. Accounting principle
Une écriture POSTED n'est pas supprimée parce qu'un downstream externe a échoué.

La correction comptable reste :

```text
reversal / replacement
```

selon règle métier.

---

# 214. Compensation state

Si des workflows multi-effets apparaissent :

```text
COMPENSATION_REQUIRED
```

peut être introduit.

Pas nécessaire au MVP de cette spécification.

---

# 215. Testing strategy

Le document `27` définit déjà les races.

`30` ajoute les tests d'ambiguïté et recovery.

---

# 216. Test category — known failure

Simuler :

```text
connection refused before send
```

Expected :

```text
FAILED_RETRYABLE
```

---

# 217. Test category — uncertain timeout

Simuler :

```text
provider processes request
response lost
```

Expected :

```text
UNCERTAIN
no blind duplicate effect
```

---

# 218. Test category — reconciliation confirms success

```text
Attempt timeout
remote lookup finds operation
```

Expected :

```text
SUCCEEDED
no retry
```

---

# 219. Test category — reconciliation confirms absence

```text
Attempt uncertain
lookup = NOT_APPLIED
```

Expected :

```text
FAILED_RETRYABLE
```

---

# 220. Test category — unresolved

```text
provider not queryable
no strong idempotency
```

Expected :

```text
MANUAL_REVIEW
```

---

# 221. Test category — duplicate retry

Retry with same:

```text
EffectId
idempotency key
request checksum
```

Expected :

```text
one remote effect
```

if provider fake models strong idempotency.

---

# 222. Test category — payload conflict

Same key, changed payload.

Expected :

```text
EffectPayloadConflictError
```

---

# 223. Test category — uncertain DB commit

Simulate adapter fault:

```text
commit may have succeeded
client receives connection error
```

Expected :

```text
recovery probe
no immediate repost
```

---

# 224. Test category — outbox crash

Crash:

```text
after remote publish
before local mark PUBLISHED
```

Expected :

```text
UNCERTAIN
reconciliation/dedup path
```

---

# 225. Test category — dispatcher crash before publish

Expected :

```text
lease expiry
reclaim
publish once logically
```

---

# 226. Test category — dead letter

Repeated known retryable failures exceed budget.

Expected :

```text
DEAD_LETTER / MANUAL_REVIEW
```

---

# 227. Testing toolkit integration

Le document `28` peut fournir :

```text
FakeExternalEffectProvider
EffectOutcomeScript
RecoveryHarness
assert_no_duplicate_external_effect
```

---

# 228. `EffectOutcomeScript`

Exemple :

```text
attempt 1 → TIMEOUT_AFTER_APPLY
reconcile → APPLIED
```

---

# 229. Golden recovery scenarios

Créer des scenarios :

```text
GOLD-RECOVERY-001
GOLD-RECOVERY-002
...
```

---

# 230. Golden 1 — Timeout but applied

```text
send
→ timeout
→ reconcile APPLIED
→ SUCCEEDED
```

---

# 231. Golden 2 — Timeout not applied

```text
send
→ timeout
→ reconcile NOT_APPLIED
→ retry
→ SUCCEEDED
```

---

# 232. Golden 3 — Not queryable

```text
send
→ timeout
→ provider has no query API
→ MANUAL_REVIEW
```

---

# 233. Golden 4 — Outbox duplicate delivery

```text
same EventId delivered twice
→ one consumer business effect
```

---

# 234. Concurrency — two recovery workers

```text
Worker A reconcile effect X
Worker B reconcile effect X
```

Expected :

```text
one state transition
no double retry
```

---

# 235. Concurrency — retry vs reconcile

Interdit :

```text
reconcile confirms APPLIED
while another worker launches retry
```

Nécessite lock/revision/lease.

---

# 236. Concurrency — manual decision vs worker retry

Manual intervention doit prendre une revision/lock explicite.

---

# 237. Property tests

Invariants :

```text
SUCCEEDED is terminal unless explicit compensation model
FAILED_FINAL is terminal
attempt_number monotonically increases
same EffectId never changes request checksum
UNCERTAIN never auto-transitions to retry without policy/reconciliation
```

---

# 238. State machine property

Toutes les transitions non autorisées doivent échouer.

---

# 239. Recovery evidence property

Chaque transition hors `UNCERTAIN` possède une preuve.

---

# 240. Architecture Fitness Functions

Règles proposées :

```text
AFF-REC-001
domain MUST NOT implement network retry loops

AFF-REC-002
external effects MUST have stable logical identity

AFF-REC-003
UNCERTAIN outcomes MUST NOT be treated as retryable failures by default

AFF-REC-004
outbox publication MUST occur outside the business DB transaction

AFF-REC-005
published business state and outbox intent MUST remain atomic

AFF-REC-006
critical retries MUST be bounded

AFF-REC-007
recovery decisions MUST be auditable
```

---

# 241. More fitness rules

```text
AFF-REC-008
production external adapters MUST classify ambiguous outcomes explicitly

AFF-REC-009
no provider secret may be persisted in recovery records

AFF-REC-010
effect payload conflict MUST fail closed

AFF-REC-011
production adapters MUST expose recovery capability metadata

AFF-REC-012
consumer duplicate processing MUST be tested where at-least-once delivery applies
```

---

# 242. Capability model

Adapters peuvent déclarer :

```text
supports_idempotency_key
supports_operation_lookup
supports_status_query
supports_cancellation
supports_receipt
idempotency_window
```

---

# 243. `ExternalEffectCapabilities`

```text
ExternalEffectCapabilities
|
+-- idempotency_strength
+-- queryable
+-- cancellable
+-- returns_stable_reference
+-- supports_receipt
```

---

# 244. Fail closed

Si une operation HIGH/CRITICAL exige :

```text
queryable or strong idempotency
```

mais l'adapter ne fournit ni l'un ni l'autre :

```text
configuration should fail
```

ou exiger :

```text
explicit manual recovery policy
```

---

# 245. No hidden downgrade

Ne pas passer silencieusement :

```text
PROVIDER_STRONG
→ LOCAL_ONLY
```

---

# 246. Provider contract versioning

Les garanties de provider doivent être versionnées/documentées.

---

# 247. Evidence manifest

Artifact possible :

```text
EXTERNAL_EFFECT_CAPABILITY_MANIFEST.json
```

---

# 248. Manifest fields

```text
adapter
provider
contract version
idempotency level
query capability
supported effect types
qualification status
```

---

# 249. Recovery qualification manifest

Artifact possible :

```text
RECOVERY_QUALIFICATION_MANIFEST.json
```

---

# 250. Qualification contents

```text
uncertain timeout scenario
reconciliation applied
reconciliation absent
payload conflict
duplicate retry
dispatcher crash
manual escalation
```

---

# 251. Release gates

Un adapter external effect déclaré Production doit passer :

```text
contract tests
uncertainty tests
recovery tests
duplicate tests
fault injection
```

---

# 252. No fake live proof

Ne pas déclarer :

```text
provider recovery qualified
```

sur la seule base d'un mock si les garanties dépendent du comportement réel du provider.

---

# 253. Sandbox qualification

Si disponible :

```text
provider sandbox
```

peut compléter la suite.

---

# 254. Documentation requirements

Chaque external adapter doit documenter :

```text
when request is considered sent
when outcome becomes uncertain
which errors are safely retryable
how reconciliation works
idempotency window
manual recovery procedure
```

---

# 255. Runbook

Pour chaque effet critique :

```text
What does UNCERTAIN mean?
How do I lookup remote status?
When can I retry?
When must I escalate?
How do I prove the final result?
```

---

# 256. Operational command set

Future CLI possible :

```text
pyak effects list --state uncertain
pyak effects inspect <id>
pyak effects reconcile <id>
pyak effects retry <id>
```

Uniquement si un vrai besoin CLI est confirmé.

---

# 257. Public API

Surface future possible :

```text
accounting.operations
```

ou :

```text
accounting.recovery
```

---

# 258. API examples

```python
status = accounting.recovery.inspect(operation_ref)
```

```python
result = accounting.recovery.reconcile(operation_ref)
```

---

# 259. Retry API

Le retry manuel doit vérifier :

```text
current state
policy
revision
request checksum
```

---

# 260. No direct force

Éviter :

```python
retry(force=True)
```

sans policy/evidence.

---

# 261. OperationRef

Un public opaque reference peut être :

```text
OperationRef
```

pour éviter d'exposer les internals.

---

# 262. Observed baseline mapping

| Capability | Baseline actuelle | Cible `30` |
|---|---|---|
| Local UoW | ✅ | conserver |
| Audit + Outbox atomicity | ✅ | conserver |
| Idempotency key | ✅ | enrichir |
| claimed/completed status | ✅ minimal | state machine richer |
| Retry classification | spec only / partial API shape | executable |
| Outbox dispatch lifecycle | non observé | ajouter |
| UNCERTAIN state | non observé | ajouter |
| Recovery reconciler | non observé | ajouter |
| Effect attempts | non observé | ajouter |
| Manual recovery evidence | non observé | ajouter |

---

# 263. Implementation roadmap

## REC-00 — Outcome vocabulary

```text
ExternalEffectOutcome
RecoveryDisposition
EffectId
AttemptId
```

---

# 264. REC-01 — Rich idempotency record

Évoluer de :

```text
claimed/completed
```

vers un modèle versionné capable de représenter :

```text
RESERVED
COMPLETED
FAILED_RETRYABLE
FAILED_FINAL
UNCERTAIN
```

si cette responsabilité reste dans le même store.

---

# 265. REC-02 — Outbox lifecycle

Ajouter :

```text
message_id
status
retry_count
claim/lease
last error
timestamps
```

---

# 266. REC-03 — Dispatcher

Implémenter :

```text
claim
publish
classify
mark
retry schedule
```

---

# 267. REC-04 — External effect model

Pour les remote business mutations riches :

```text
ExternalEffectRecord
EffectAttempt
```

---

# 268. REC-05 — Reconciliation ports

```text
ExternalEffectReconcilerProtocol
RecoveryObservation
```

---

# 269. REC-06 — Commit uncertainty recovery

Introduire :

```text
CommitOutcome
OperationRecoveryProbe
```

là où les adapters peuvent détecter un outcome ambigu.

---

# 270. REC-07 — Public error disposition

Évoluer :

```text
retryable bool
```

vers :

```text
retryable
+
RecoveryDisposition
```

de façon compatible.

---

# 271. REC-08 — Testing toolkit

Ajouter au `28` :

```text
FakeExternalEffectProvider
RecoveryHarness
uncertain outcome scripts
```

---

# 272. REC-09 — Production qualification

Ajouter :

```text
fault injection
sandbox/live contract evidence where possible
runbooks
```

---

# 273. Priorités

| Lot | Priorité |
|---|---:|
| REC-00 | P0 |
| REC-01 | P0 |
| REC-02 | P0 |
| REC-03 | P0 |
| REC-04 | P1 |
| REC-05 | P1 |
| REC-06 | P1 |
| REC-07 | P1 |
| REC-08 | P1 |
| REC-09 | P2 |

---

# 274. ADR proposées

| ADR | Décision |
|---|---|
| ADR-REC-001 | `UNCERTAIN` est distinct de `FAILED` |
| ADR-REC-002 | Un outcome ambigu n'est jamais retryable par défaut |
| ADR-REC-003 | Toute external effect possède une identité logique stable |
| ADR-REC-004 | `EffectId` et `AttemptId` sont distincts |
| ADR-REC-005 | Toutes les tentatives d'un effet conservent le même request checksum |
| ADR-REC-006 | Un payload conflict avec la même effect/idempotency identity échoue fail-closed |
| ADR-REC-007 | Les retries automatiques sont bornés |
| ADR-REC-008 | Le domaine comptable n'implémente pas les retry loops réseau |
| ADR-REC-009 | Les retries de transaction locale rejouent la transaction entière |
| ADR-REC-010 | Une demi-transaction ne se retry pas isolément |
| ADR-REC-011 | Transactional Outbox protège l'intention de publication, pas l'exécution downstream |
| ADR-REC-012 | La livraison Outbox est considérée at-least-once |
| ADR-REC-013 | PyAccountingKit ne promet pas distributed exactly-once |
| ADR-REC-014 | Les consumers critiques dédupliquent par EventId/effect identity |
| ADR-REC-015 | Un commit outcome ambigu déclenche reconciliation, pas repost aveugle |
| ADR-REC-016 | Recovery observe avant de muter |
| ADR-REC-017 | Les remote lookups utilisent des références/idempotency keys stables |
| ADR-REC-018 | Les ExternalEffect adapters déclarent leurs capacités d'idempotence et reconciliation |
| ADR-REC-019 | Les garanties provider ne sont pas inventées par l'adapter |
| ADR-REC-020 | Les effets critiques sans idempotence ni reconciliation exigent manual recovery |
| ADR-REC-021 | Payment-like operations suivent reconcile-before-retry |
| ADR-REC-022 | Artifact generation et external submission sont deux opérations distinctes |
| ADR-REC-023 | Un effet externe déjà appliqué n'est jamais compensé par suppression silencieuse d'écriture comptable |
| ADR-REC-024 | Les corrections comptables post-commit utilisent reversal/replacement |
| ADR-REC-025 | La dead-letter queue représente un arrêt automatique, pas une disparition de l'obligation |
| ADR-REC-026 | Toute transition depuis UNCERTAIN est auditable |
| ADR-REC-027 | Les décisions manuelles conservent actor, rationale et evidence |
| ADR-REC-028 | Les credentials externes ne sont jamais stockés dans EffectRecord |
| ADR-REC-029 | Les records de recovery sont tenant/entity-scoped |
| ADR-REC-030 | Les logs ne constituent pas la preuve durable de recovery |
| ADR-REC-031 | La public API doit distinguer RETRY de RECONCILE |
| ADR-REC-032 | Le booléen `retryable` seul n'est pas suffisant pour les outcomes ambigus |
| ADR-REC-033 | Les provider-specific retry rules restent dans leurs adapters |
| ADR-REC-034 | Le runtime peut utiliser circuit breaker/backoff sans contaminer le domain |
| ADR-REC-035 | L'Outbox lifecycle doit supporter claim/lease pour worker crash recovery |
| ADR-REC-036 | Un retry Outbox ne crée pas un nouvel EventId |
| ADR-REC-037 | La recovery concurrency est protégée par revision/lock/lease |
| ADR-REC-038 | Les external effect contract tests incluent ambiguous outcomes |
| ADR-REC-039 | Les Production adapters doivent documenter leur recovery contract |
| ADR-REC-040 | La qualification live/sandbox ne doit pas être remplacée par une fausse preuve mock |
| ADR-REC-041 | Import recovery conserve source fingerprint et lineage |
| ADR-REC-042 | Closing recovery inspecte le close revision avant toute nouvelle clôture |
| ADR-REC-043 | Reversal recovery protège l'unicité de la reversal |
| ADR-REC-044 | Published snapshots ne sont jamais réécrits par recovery |
| ADR-REC-045 | RecoveryEvidence est immutable |
| ADR-REC-046 | Effect reconciliation et accounting reconciliation sont des concepts distincts |
| ADR-REC-047 | Les effects peuvent être référencés depuis manifests/evidence bundles |
| ADR-REC-048 | Les external effect statuses sont machine-readable |
| ADR-REC-049 | Les retry budgets sont explicitement versionnés/configurés |
| ADR-REC-050 | L'incertitude devient une capacité de première classe de PyAccountingKit |

---

# 275. Architecture Fitness Functions associées

```text
AFF-REC-001
domain MUST NOT implement external retry loops

AFF-REC-002
UNCERTAIN MUST NOT map to retryable=true by default

AFF-REC-003
critical external effects MUST have stable EffectId

AFF-REC-004
same EffectId MUST preserve request checksum

AFF-REC-005
business transaction MUST NOT synchronously depend on remote publication when Outbox applies

AFF-REC-006
recovery decisions MUST create durable evidence

AFF-REC-007
production adapters MUST declare external-effect capabilities

AFF-REC-008
secrets MUST NOT be persisted in effect/recovery records
```

---

# 276. Definition of Done — P0 vocabulary

```text
[ ] EffectId défini
[ ] AttemptId défini
[ ] ExternalEffectOutcome défini
[ ] RecoveryDisposition défini
[ ] UNCERTAIN explicite
[ ] request checksum explicite
[ ] retryable vs reconcile distinction documentée
```

---

# 277. Definition of Done — Outbox

```text
[ ] message_id
[ ] status
[ ] retry_count
[ ] next_attempt_at
[ ] claim/lease
[ ] published_at
[ ] last_error
[ ] duplicate delivery tests
[ ] crash recovery tests
```

---

# 278. Definition of Done — Recovery

```text
[ ] ExternalEffectReconcilerProtocol
[ ] RecoveryObservation
[ ] RecoveryEvidence
[ ] APPLIED path
[ ] NOT_APPLIED path
[ ] AMBIGUOUS path
[ ] MANUAL_REVIEW path
[ ] no blind retry after uncertain path
```

---

# 279. Definition of Done — Commit uncertainty

```text
[ ] CommitOutcome vocabulary
[ ] uncertain commit fault test
[ ] local recovery probe
[ ] posting reconciliation
[ ] reversal reconciliation
[ ] closing reconciliation
```

---

# 280. Definition of Done — Public API

```text
[ ] retryable errors mapped
[ ] uncertain outcome public code
[ ] recovery disposition exposed
[ ] operation reference exposed where needed
[ ] provider exceptions hidden
```

---

# 281. Definition of Done — Production adapter

```text
[ ] idempotency guarantees documented
[ ] query/reconciliation capability documented
[ ] timeout semantics documented
[ ] bounded retry policy documented
[ ] ambiguous response test exists[ ] duplicate effect test exists
[ ] runbook exists
```

---

# 282. Risk matrix

| Risque | Impact | Protection |
|---|---:|---|
| Blind retry after applied timeout | Critique | UNCERTAIN + reconciliation |
| Double payment-like effect | Critique | EffectId + provider idempotency + query |
| Duplicate event consumer effect | Critique | EventId + inbox/dedup |
| Lost publication after DB commit | Critique | Transactional Outbox |
| Duplicate publication | Élevé | at-least-once + dedup |
| Commit ack lost | Critique | CommitOutcome + recovery probe |
| Endless retries | Élevé | bounded retry budget |
| Retry changed payload | Critique | request checksum |
| Recovery race | Élevé | revision/lease |
| Manual undocumented override | Élevé | RecoveryDecision evidence |
| Secrets in recovery DB | Critique | security rule |
| False "exactly-once" assumption | Critique | explicit delivery semantics |

---

# 283. Canonical flow — local mutation + external event

```text
Command
   ↓
Application
   ↓
UnitOfWork
   ├── Domain mutation
   ├── Audit
   ├── Idempotency
   └── Outbox PENDING
   ↓
COMMIT
   ↓
Outbox Dispatcher
   ↓
External Transport
   ├── success → PUBLISHED
   ├── known failure → FAILED_RETRYABLE/FINAL
   └── ambiguous → UNCERTAIN
                       ↓
                  Reconciler
```

---

# 284. Canonical flow — remote business effect

```text
Business intent
    ↓
ExternalEffectRecord PLANNED
    ↓
Attempt IN_PROGRESS
    ↓
Provider
  /    |      \
 /     |       \
OK   FAIL     TIMEOUT/RESET
|      |           |
v      v           v
SUCCESS FAILED   UNCERTAIN
                    |
                    v
               RECONCILE
              /    |     \
         APPLIED NOT_APPLIED AMBIGUOUS
            |        |         |
            v        v         v
        SUCCESS    RETRY     MANUAL
```

---

# 285. Canonical rule

```text
KNOWN FAILURE
    may retry

UNKNOWN OUTCOME
    must first become known
    or use a provider guarantee strong enough
    to make retry safe
```

---

# 286. Relation avec les documents précédents

`24` :

```text
architecture rules become executable
```

`25` :

```text
EventId / correlation / causality
```

`26` :

```text
reproducibility manifests and evidence
```

`27` :

```text
golden + concurrency scenarios
```

`28` :

```text
testing toolkit and fault/recovery harness
```

`29` :

```text
domain-first ownership and package placement
```

`30` complète cette série par :

```text
external-effect safety
+
uncertain outcomes
+
recovery
```

---

# 287. Positionnement final

PyAccountingKit doit distinguer quatre niveaux de garantie :

```text
1. LOCAL ATOMICITY
   UnitOfWork

2. DUPLICATE PREVENTION
   Idempotency

3. RELIABLE INTENT DELIVERY
   Outbox

4. UNKNOWN OUTCOME RECOVERY
   Effect state + reconciliation
```

Aucun des trois premiers ne remplace le quatrième.

---

# 288. Conclusion

PyAccountingKit possède déjà des fondations importantes :

```text
UnitOfWork
idempotency key
audit
transactional outbox persistence
retryability concepts in specs
```

Le gap restant est la modélisation explicite des cas où :

```text
the system cannot know whether the effect happened
```

La cible devient donc :

```text
DO
 ↓
OBSERVE OUTCOME
 ├── KNOWN SUCCESS
 ├── KNOWN FAILURE
 └── UNCERTAIN
          ↓
      RECONCILE
          ↓
   RECOVER SAFELY
```

Le principe final est :

> **PyAccountingKit ne doit jamais transformer une absence de réponse en certitude d'échec. Lorsqu'un effet peut avoir été appliqué, l'étape suivante est d'établir la vérité avant de répéter l'action.**