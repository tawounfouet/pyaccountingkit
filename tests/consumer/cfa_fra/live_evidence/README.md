# CFA FRA live cutover evidence artifacts

This directory is the canonical materialization root for external CFA FRA cutover proofs.

A `PASS` record in `../RETIREMENT_EVIDENCE.json` must reference a file beneath this
directory using a safe relative path. Canonical CI resolves the path, reads the actual bytes
and verifies the declared lowercase SHA-256 before exposing any MIG-13 retirement boolean.

Do not place fabricated evidence here. Until a real live-consumer proof exists, keep the
corresponding manifest record `BLOCKED` with an explicit reason.
