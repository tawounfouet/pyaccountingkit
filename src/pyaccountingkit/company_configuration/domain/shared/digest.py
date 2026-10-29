"""Basic content fingerprint primitives; not yet a publication snapshot contract."""

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

from .errors import InvalidDigest


@dataclass(frozen=True, slots=True)
class ContentDigest:
    hex_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.hex_sha256, str) or not re.fullmatch(
            r"[0-9a-f]{64}", self.hex_sha256
        ):
            raise InvalidDigest("Expected a lowercase hexadecimal SHA-256 digest")

    @classmethod
    def from_canonical_json(cls, payload: Any) -> "ContentDigest":
        """Hash a restricted JSON payload using stable key ordering and encoding.

        This is a local primitive. A cross-language canonicalization protocol
        (including schema versions) remains subject to ADR-CC-06.
        """
        try:
            canonical = json.dumps(
                payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        except (TypeError, ValueError, OverflowError) as exc:
            raise InvalidDigest("Payload is not valid JSON content") from exc
        return cls(hashlib.sha256(canonical).hexdigest())
