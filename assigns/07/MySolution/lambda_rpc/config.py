"""Service limits. Defaults are documented in RPC.md; env vars override them."""

import os
from dataclasses import dataclass

API_VERSION = "1.0"


def _env_number(name: str, default, kind):
    raw = os.environ.get(name)
    return default if raw in (None, "") else kind(raw)


@dataclass(frozen=True)
class Limits:
    max_source_bytes: int = 64 * 1024          # UTF-8 bytes of `source`
    max_body_bytes: int = 1024 * 1024          # whole HTTP request body (413 above)
    max_batch_items: int = 50                  # larger batches are Invalid Request
    interpret_timeout: float = 5.0             # seconds of evaluation per call
    worker_startup_timeout: float = 20.0       # seconds to start a worker process
    max_value_chars: int = 1024 * 1024         # formatted interpreter result
    recursion_limit: int = 100_000             # Python frames in the worker

    @classmethod
    def from_env(cls) -> "Limits":
        base = cls()
        return cls(
            max_source_bytes=_env_number("LAMBDA_RPC_MAX_SOURCE_BYTES", base.max_source_bytes, int),
            max_body_bytes=_env_number("LAMBDA_RPC_MAX_BODY_BYTES", base.max_body_bytes, int),
            max_batch_items=_env_number("LAMBDA_RPC_MAX_BATCH", base.max_batch_items, int),
            interpret_timeout=_env_number("LAMBDA_RPC_TIMEOUT", base.interpret_timeout, float),
        )
