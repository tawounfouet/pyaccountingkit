"""L02-07 candidate: physically segregated, versioned PostgreSQL tenant pools.

A trusted secret provider is queried at every checkout. A stale/missing secret
never authorizes reuse of a cached pool. This is not a vault, IAM, or general
production pool manager; credentials and privileged operations live elsewhere.
"""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from threading import RLock
from typing import Protocol


class TenantPoolDenied(PermissionError):
    """Tenant/role/credential provenance is missing or inconsistent."""


class PoolGenerationConflict(RuntimeError):
    """Credential epochs must advance and identify immutable snapshots."""


@dataclass(frozen=True, slots=True, repr=False)
class TenantCredential:
    """Secret lease provided by a trusted source; never serialize or log it.

    Generation must be strictly increasing for each tenant + role kind when
    the secret changes. A credential is held in process memory by its pool.
    """

    tenant_id: str
    role_kind: str
    login_role: str
    generation: int
    dsn: str = field(repr=False)

    def __post_init__(self) -> None:
        if any(
            not isinstance(value, str) or not value or value.strip() != value
            for value in (self.tenant_id, self.role_kind, self.login_role, self.dsn)
        ):
            raise TenantPoolDenied("Invalid tenant credential identity")
        if self.role_kind not in ("runtime", "dispatcher", "inbox"):
            raise TenantPoolDenied("Unknown tenant role kind")
        if type(self.generation) is not int or self.generation < 1:
            raise TenantPoolDenied("Credential generation must be positive")
        if not self.login_role.startswith(f"cc_{self.role_kind}_"):
            raise TenantPoolDenied("Login does not match role kind")

    def __repr__(self) -> str:
        return (
            "TenantCredential(tenant_id=<redacted>, role_kind="
            f"{self.role_kind!r}, login_role=<redacted>, generation={self.generation}, "
            "dsn=<redacted>)"
        )


class TenantSecretProvider(Protocol):
    """Trusted adapter for immutable, monotonically versioned secret snapshots."""

    def get(self, *, tenant_id: str, role_kind: str) -> TenantCredential: ...


class TenantPool(Protocol):
    def connection(self): ...

    def close(self) -> None: ...


@dataclass(slots=True)
class _Entry:
    credential: TenantCredential
    pool: TenantPool
    active: int = 0
    retired: bool = False


class TenantPoolRegistry:
    """One *physical* pool per tenant/role credential generation.

    A secret lookup happens before every checkout and must succeed. When the
    generation changes, previous connections are retired; a checked-out
    connection remains held until its context exits. The producer of a secret
    change must still terminate old DB sessions and revoke its login, as
    proven in L02-06; this registry is not a forced in-flight cancellation.
    """

    def __init__(
        self,
        secrets: TenantSecretProvider,
        *,
        max_size: int = 4,
        pool_factory: Callable[[str, int], TenantPool] | None = None,
        verifier: Callable[[object, str, str], None] | None = None,
    ) -> None:
        if type(max_size) is not int or not 1 <= max_size <= 100:
            raise ValueError("Pool max_size must be between 1 and 100")
        self._secrets = secrets
        self._max_size = max_size
        self._pool_factory = pool_factory or self._create_pool
        self._verifier = verifier or self._verify_database_identity
        self._entries: dict[tuple[str, str], _Entry] = {}
        self._highwater: dict[tuple[str, str], int] = {}
        self._lock = RLock()
        self._closed = False

    @staticmethod
    def _create_pool(dsn: str, max_size: int) -> TenantPool:
        # Only users opting into [postgres] need the separate psycopg_pool package.
        from psycopg_pool import ConnectionPool

        return ConnectionPool(conninfo=dsn, min_size=0, max_size=max_size, open=True)

    @staticmethod
    def _verify_database_identity(connection: object, tenant: str, login_role: str) -> None:
        from .tenant_boundary import require_tenant_connection

        require_tenant_connection(connection, tenant)
        row = connection.execute("SELECT session_user").fetchone()
        if row is None or row[0] != login_role:
            raise TenantPoolDenied("Authenticated database login does not match secret")

    @staticmethod
    def _valid_key(tenant_id: str, role_kind: str) -> tuple[str, str]:
        if (
            not isinstance(tenant_id, str)
            or not tenant_id
            or tenant_id.strip() != tenant_id
            or role_kind not in ("runtime", "dispatcher", "inbox")
        ):
            raise TenantPoolDenied("Tenant and approved role kind required")
        return (tenant_id, role_kind)

    def _retire(self, key: tuple[str, str]) -> None:
        old = self._entries.pop(key, None)
        if old is not None:
            old.retired = True
            if old.active == 0:
                old.pool.close()

    @contextmanager
    def connection(self, *, tenant_id: str, role_kind: str) -> Iterator[object]:
        key = self._valid_key(tenant_id, role_kind)
        with self._lock:
            if self._closed:
                raise TenantPoolDenied("Tenant pool registry is closed")
            try:
                credential = self._secrets.get(tenant_id=tenant_id, role_kind=role_kind)
                if (
                    not isinstance(credential, TenantCredential)
                    or (credential.tenant_id, credential.role_kind) != key
                ):
                    raise TenantPoolDenied("Trusted secret does not match requested scope")
            except Exception:
                # Always fail closed when the trusted provider is unavailable.
                self._retire(key)
                raise
            entry = self._entries.get(key)
            if credential.generation < self._highwater.get(key, 0):
                self._retire(key)
                raise PoolGenerationConflict("Credential generation regressed")
            if entry is not None:
                old = entry.credential
                if credential.generation < old.generation:
                    self._retire(key)
                    raise PoolGenerationConflict("Credential generation regressed")
                if credential.generation == old.generation and credential != old:
                    self._retire(key)
                    raise PoolGenerationConflict("Credential changed without epoch update")
            if entry is None or credential.generation > entry.credential.generation:
                self._retire(key)
                entry = _Entry(credential, self._pool_factory(credential.dsn, self._max_size))
                self._entries[key] = entry
            self._highwater[key] = credential.generation
            entry.active += 1
        try:
            with entry.pool.connection() as conn:
                self._verifier(conn, tenant_id, credential.login_role)
                yield conn
        finally:
            with self._lock:
                entry.active -= 1
                if entry.retired and entry.active == 0:
                    entry.pool.close()

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            for key in list(self._entries):
                self._retire(key)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
