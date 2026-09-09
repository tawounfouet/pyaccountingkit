"""Idempotency key handling to make operations safe to retry."""


class Idempotency:
    """Tracks request idempotency keys to prevent duplicate side effects."""
