"""FND-C04: real PostgreSQL upgrade, recovery and fail-closed history proofs.

Every test owns disposable databases on the ephemeral PostgreSQL CI service.
NEVER point the administrator DSN at a shared or production cluster.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from importlib import resources
from pathlib import Path
from uuid import uuid4

import pytest

psycopg = pytest.importorskip("psycopg")
from psycopg import sql  # noqa: E402
from psycopg.conninfo import conninfo_to_dict, make_conninfo  # noqa: E402

from pyaccountingkit.company_configuration.infrastructure.postgres import migrate  # noqa: E402

ADMIN = os.getenv("CC_PG_ADMIN_DSN")
pytestmark = pytest.mark.skipif(not ADMIN, reason="Isolated PostgreSQL CI required")

PACKAGE = migrate.MIGRATION_PACKAGE
MIGRATION_TABLE = "company_configuration.schema_migrations"


@pytest.fixture
def isolated_database():
    """Provision distinct, throwaway databases; clean up even on test failure."""
    names: list[str] = []

    def create() -> str:
        database = f"cc_fnd_c04_{uuid4().hex[:20]}"
        with psycopg.connect(ADMIN, autocommit=True) as conn:
            conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database)))
        names.append(database)
        return make_conninfo(ADMIN, dbname=database)

    yield create

    with psycopg.connect(ADMIN, autocommit=True) as conn:
        for name in reversed(names):
            conn.execute(
                sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name))
            )


def _migration_entries():
    directory = resources.files(PACKAGE)
    return sorted(
        (entry.name, entry.read_text(encoding="utf-8"))
        for entry in directory.iterdir()
        if entry.name.endswith(".sql") and entry.name[:4].isdigit()
    )


def _bootstrap_at_0013(dsn: str) -> list[str]:
    """Simulate a pre-0014 deployment from its immutable historical SQL bytes."""
    entries = _migration_entries()
    assert [name[:4] for name, _ in entries] == [
        f"{ordinal:04}" for ordinal in range(1, 27)
    ]
    with psycopg.connect(dsn) as conn:
        with conn.transaction():
            conn.execute("CREATE SCHEMA company_configuration")
            conn.execute(
                "CREATE TABLE company_configuration.schema_migrations ("
                "filename text PRIMARY KEY, sha256 char(64) NOT NULL, "
                "applied_at timestamptz NOT NULL DEFAULT now())"
            )
            for filename, source in entries[:13]:
                conn.execute(source)
                conn.execute(
                    "INSERT INTO company_configuration.schema_migrations "
                    "(filename, sha256) VALUES (%s, %s)",
                    (filename, hashlib.sha256(source.encode()).hexdigest()),
                )
    return [name for name, _ in entries]


def _seed_legacy_evidence(dsn: str):
    """Commit genuine 0013-era business, IAM receipt and DEAD queue records."""
    company, entity, event, request_id = (uuid4() for _ in range(4))
    with psycopg.connect(dsn) as conn:
        conn.execute(
            "INSERT INTO company_configuration.legal_entities "
            "(tenant_id,company_id,entity_id,legal_name,jurisdiction,"
            "functional_currency,revision) VALUES "
            "(%s,%s,%s,%s,%s,%s,%s)",
            ("tenant-a", company, entity, "Existing SARL", "FR", "EUR", 1),
        )
        conn.execute(
            "INSERT INTO company_configuration.privileged_iam_revocation_receipts "
            "(request_id,event_id,tenant_id,login_role,operation,issuer,"
            "signer_kid,revoker_id,signed_digest,disposition) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (request_id, event, "tenant-a", "cc_runtime_a", "rotate",
             "test-issuer", "test-key", "reviewer", "a" * 64, "TOMBSTONED"),
        )
        conn.execute(
            "UPDATE company_configuration.privileged_iam_ack_outbox "
            "SET state='DEAD',attempts=5,error_code='HTTP_REJECTED' "
            "WHERE event_id=%s", (event,),
        )
    return company, entity, event, request_id


def _assert_preserved_evidence(dsn: str, ids) -> None:
    company, entity, event, request_id = ids
    with psycopg.connect(dsn) as conn:
        legal = conn.execute(
            "SELECT company_id, legal_name, revision "
            "FROM company_configuration.legal_entities WHERE entity_id=%s",
            (entity,),
        ).fetchone()
        assert legal == (company, "Existing SARL", 1)
        ack = conn.execute(
            "SELECT request_id,state,attempts,error_code,redrive_count "
            "FROM company_configuration.privileged_iam_ack_outbox "
            "WHERE event_id=%s", (event,),
        ).fetchone()
        assert ack == (request_id, "DEAD", 5, "HTTP_REJECTED", 0)
        assert conn.execute(
            "SELECT count(*) FROM company_configuration.privileged_iam_ack_redrive_decisions "
            "WHERE event_id=%s", (event,),
        ).fetchone()[0] == 0


def _recorded_versions(dsn: str):
    with psycopg.connect(dsn) as conn:
        return conn.execute(
            "SELECT filename,trim(sha256) FROM company_configuration.schema_migrations "
            "ORDER BY filename"
        ).fetchall()


def test_upgrade_0013_to_0026_is_atomic_preserves_records_and_is_idempotent(
    isolated_database,
):
    dsn = isolated_database()
    names = _bootstrap_at_0013(dsn)
    ids = _seed_legacy_evidence(dsn)
    with psycopg.connect(dsn) as conn:
        assert conn.execute(
            "SELECT to_regclass('company_configuration.privileged_iam_ack_recovery_grants')"
        ).fetchone()[0] is None
    before = _recorded_versions(dsn)
    assert len(before) == 13
    assert migrate.apply_migrations(dsn) == names[13:]
    assert len(_recorded_versions(dsn)) == 26
    assert _recorded_versions(dsn)[:13] == before
    _assert_preserved_evidence(dsn, ids)
    with psycopg.connect(dsn) as conn:
        assert conn.execute(
            "SELECT count(*) FROM pg_catalog.pg_proc p "
            "JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace "
            "WHERE n.nspname='company_configuration' "
            "AND p.proname='cp_grant_iam_ack_redrive' AND p.prosecdef"
        ).fetchone()[0] == 1
    assert migrate.apply_migrations(dsn) == []
    assert _recorded_versions(dsn)[:13] == before


def test_failed_migration_is_fully_rolled_back_and_rerun_works(
    isolated_database, monkeypatch, tmp_path,
):
    dsn = isolated_database()
    assert len(migrate.apply_migrations(dsn)) == 26
    prior = _recorded_versions(dsn)
    for filename, source in _migration_entries():
        (tmp_path / filename).write_text(source, encoding="utf-8")
    bad_file = tmp_path / "0027_injected_failure.sql"
    bad_file.write_text(
        "CREATE TABLE company_configuration.uncommitted_test_table (id integer);"
        "DO $$ BEGIN RAISE EXCEPTION 'fnd-c04 injected failure'; END $$;",
        encoding="utf-8",
    )
    with monkeypatch.context() as patch:
        patch.setattr(migrate.resources, "files", lambda _: tmp_path)
        with pytest.raises(psycopg.errors.RaiseException, match="fnd-c04 injected"):
            migrate.apply_migrations(dsn)
    with psycopg.connect(dsn) as conn:
        assert conn.execute(
            "SELECT to_regclass('company_configuration.uncommitted_test_table')"
        ).fetchone()[0] is None
    assert _recorded_versions(dsn) == prior
    assert migrate.apply_migrations(dsn) == []


def test_unrecognized_future_and_noncontiguous_applied_history_fail_closed(
    isolated_database,
):
    dsn = isolated_database()
    assert len(migrate.apply_migrations(dsn)) == 26
    expected = _recorded_versions(dsn)
    with psycopg.connect(dsn) as conn:
        conn.execute(
            "INSERT INTO company_configuration.schema_migrations "
            "(filename,sha256) VALUES (%s,%s)",
            ("0027_future.sql", "0" * 64),
        )
    with pytest.raises(RuntimeError, match="Unknown already-applied"):
        migrate.apply_migrations(dsn)
    with psycopg.connect(dsn) as conn:
        conn.execute(
            "DELETE FROM company_configuration.schema_migrations "
            "WHERE filename='0027_future.sql'"
        )
    assert _recorded_versions(dsn) == expected
    with psycopg.connect(dsn) as conn:
        conn.execute(
            "DELETE FROM company_configuration.schema_migrations "
            "WHERE filename=%s", (expected[6][0],),
        )
    with pytest.raises(RuntimeError, match="contiguous prefix"):
        migrate.apply_migrations(dsn)


def test_checksum_drift_rejected_without_touching_schema(
    isolated_database, monkeypatch, tmp_path,
):
    dsn = isolated_database()
    assert len(migrate.apply_migrations(dsn)) == 26
    original = _recorded_versions(dsn)
    for filename, source in _migration_entries():
        (tmp_path / filename).write_text(source, encoding="utf-8")
    with (tmp_path / "0013_iam_ack_operations_and_redrive.sql").open(
        "a", encoding="utf-8"
    ) as output:
        output.write("\n-- simulated historic checksum drift\n")
    with monkeypatch.context() as patch:
        patch.setattr(migrate.resources, "files", lambda _: tmp_path)
        with pytest.raises(RuntimeError, match="Migration checksum changed: 0013"):
            migrate.apply_migrations(dsn)
    assert _recorded_versions(dsn) == original


def test_concurrent_fresh_migration_applies_each_script_exactly_once(
    isolated_database,
):
    dsn = isolated_database()
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(migrate.apply_migrations, (dsn, dsn)))
    assert sorted(len(result) for result in results) == [0, 26]
    assert len(_recorded_versions(dsn)) == 26


def _run_pg_tool(binary: str, dsn: str, args: list[str]) -> None:
    executable = shutil.which(binary)
    if executable is None:
        pytest.fail(f"{binary} required; backup/restore may not be silently skipped")
    credentials = conninfo_to_dict(dsn)
    env = os.environ.copy()
    env["PGPASSWORD"] = credentials.get("password", "")
    command = [
        executable, "-h", credentials.get("host", "localhost"),
        "-p", credentials.get("port", "5432"),
        "-U", credentials.get("user", "postgres"),
        "-d", credentials["dbname"], *args,
    ]
    subprocess.run(command, env=env, check=True, capture_output=True, text=True, timeout=90)


def test_real_custom_dump_restores_all_migration_history_and_evidence(
    isolated_database, tmp_path: Path,
):
    source = isolated_database()
    restored = isolated_database()
    assert len(migrate.apply_migrations(source)) == 26
    ids = _seed_legacy_evidence(source)
    expected_history = _recorded_versions(source)
    archive = tmp_path / "company_configuration.dump"
    _run_pg_tool(
        "pg_dump", source,
        ["--format=custom", "--no-owner", "--no-acl",
         "--schema=company_configuration", "--file", str(archive)],
    )
    assert archive.is_file() and archive.stat().st_size > 0
    _run_pg_tool(
        "pg_restore", restored,
        ["--exit-on-error", "--no-owner", "--no-acl", str(archive)],
    )
    assert _recorded_versions(restored) == expected_history
    _assert_preserved_evidence(restored, ids)
    assert migrate.apply_migrations(restored) == []
    with psycopg.connect(restored) as conn:
        assert conn.execute(
            "SELECT count(*) FROM pg_catalog.pg_trigger WHERE tgname="
            "'forbid_privileged_recovery_grant_change' AND NOT tgisinternal"
        ).fetchone()[0] == 1
