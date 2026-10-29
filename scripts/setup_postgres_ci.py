"""CI-only PostgreSQL test role setup. NEVER use on a real environment."""

import os

import psycopg

admin_dsn = os.environ["CC_PG_ADMIN_DSN"]
with psycopg.connect(admin_dsn, autocommit=True) as conn:
    conn.execute("CREATE ROLE cc_runtime LOGIN PASSWORD 'cc_testing'")
    conn.execute("GRANT USAGE ON SCHEMA company_configuration TO cc_runtime")
    conn.execute(
        "GRANT SELECT, INSERT, UPDATE ON company_configuration.legal_entities "
        "TO cc_runtime"
    )
    conn.execute(
        "GRANT SELECT, INSERT ON company_configuration.idempotency_requests, "
        "company_configuration.audit_records, company_configuration.outbox_events "
        "TO cc_runtime"
    )

# Disposable, intentionally separate roles for integration proofs.
with psycopg.connect(admin_dsn, autocommit=True) as conn:
    conn.execute("CREATE ROLE cc_dispatcher LOGIN PASSWORD 'cc_dispatch_testing'")
    conn.execute("GRANT USAGE ON SCHEMA company_configuration TO cc_dispatcher")
    conn.execute("GRANT SELECT ON company_configuration.outbox_events TO cc_dispatcher")
    conn.execute(
        "GRANT SELECT, INSERT, UPDATE ON company_configuration.outbox_delivery "
        "TO cc_dispatcher"
    )
    conn.execute(
        "GRANT INSERT, SELECT ON company_configuration.authorization_denials "
        "TO cc_runtime"
    )
    conn.execute("CREATE ROLE cc_inbox LOGIN PASSWORD 'cc_inbox_testing'")
    conn.execute("GRANT USAGE ON SCHEMA company_configuration TO cc_inbox")
    conn.execute(
        "GRANT SELECT, INSERT ON company_configuration.inbox_receipts TO cc_inbox"
    )
    conn.execute(
        "GRANT SELECT, INSERT, UPDATE ON company_configuration.inbox_projection_counts "
        "TO cc_inbox"
    )
