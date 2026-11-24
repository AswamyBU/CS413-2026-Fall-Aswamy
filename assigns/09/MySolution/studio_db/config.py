"""Service limits (documented in API.md section 7)."""

from dataclasses import dataclass

API_VERSION = "1.0"


@dataclass(frozen=True)
class Limits:
    max_body_bytes: int = 256 * 1024       # whole HTTP request body -> 413
    max_name_chars: int = 100              # after trimming
    max_source_bytes: int = 64 * 1024      # UTF-8 bytes
    max_description_chars: int = 2000
    max_expected_value_chars: int = 10_000
    default_page_size: int = 50
    max_page_size: int = 100
    max_programs: int = 1000
    max_collections: int = 200
    max_cases_per_collection: int = 200
    max_snapshots: int = 256               # live list snapshots (LRU beyond this)
    snapshot_idle_seconds: float = 600.0   # snapshot lifetime after last use
