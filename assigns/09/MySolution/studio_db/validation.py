"""Pure request validation. No storage access, no HTTP objects.

Each function takes already-decoded JSON (or a header/query string) and
returns clean values or raises ApiError(400 invalid_request) with the
offending `field` or `parameter` named in the error body.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .config import Limits
from .errors import invalid
from .records import Expected

ID_PATTERNS = {
    "program": re.compile(r"prg_[0-9a-f]{16}"),
    "collection": re.compile(r"col_[0-9a-f]{16}"),
    "case": re.compile(r"case_[0-9a-f]{16}"),
}
_ETAG = re.compile(r'"([1-9][0-9]{0,17})"')
_DIGITS = re.compile(r"[0-9]{1,6}")


@dataclass(frozen=True)
class ProgramFields:
    name: str
    source: str
    description: str


@dataclass(frozen=True)
class CollectionFields:
    name: str
    description: str


@dataclass(frozen=True)
class CaseFields:
    name: str
    source: str
    expected: Expected
    description: str


def check_id(kind: str, value: str, parameter: str = "id") -> str:
    if not ID_PATTERNS[kind].fullmatch(value):
        raise invalid(f"{parameter} is not a valid {kind} ID", parameter=parameter)
    return value


def parse_if_match(header: str) -> int:
    """`"3"` -> 3. Anything else (weak tags, *, lists, bare numbers) is 400."""
    match = _ETAG.fullmatch(header.strip())
    if not match:
        raise invalid('If-Match must be one strong entity tag holding the revision, e.g. "3"',
                      parameter="If-Match")
    return int(match.group(1))


def _object(body, allowed: tuple[str, ...], required: tuple[str, ...]) -> dict:
    if not isinstance(body, dict):
        raise invalid("request body must be a JSON object")
    unknown = sorted(k for k in body if k not in allowed)
    if unknown:
        raise invalid(f"unknown field: {unknown[0][:60]}", field=unknown[0][:60])
    for key in required:
        if key not in body:
            raise invalid(f"{key} is required", field=key)
    return body


def _string(body: dict, key: str) -> str:
    value = body[key]
    if not isinstance(value, str):
        raise invalid(f"{key} must be a string", field=key)
    return value


def _name(body: dict, limits: Limits) -> str:
    name = _string(body, "name").strip()
    if not name:
        raise invalid("name must not be blank", field="name")
    if len(name) > limits.max_name_chars:
        raise invalid(f"name is longer than {limits.max_name_chars} characters",
                      field="name", limit=limits.max_name_chars, actual=len(name))
    return name


def _source(body: dict, limits: Limits) -> str:
    source = _string(body, "source")
    if not source.strip():
        raise invalid("source must not be blank", field="source")
    size = len(source.encode("utf-8", errors="surrogatepass"))
    if size > limits.max_source_bytes:
        raise invalid(f"source is larger than {limits.max_source_bytes} bytes",
                      field="source", limit=limits.max_source_bytes, actual=size)
    return source


def _description(body: dict, limits: Limits) -> str:
    if "description" not in body:
        return ""
    description = _string(body, "description")
    if len(description) > limits.max_description_chars:
        raise invalid(f"description is longer than {limits.max_description_chars} characters",
                      field="description", limit=limits.max_description_chars,
                      actual=len(description))
    return description


def _expected(body: dict, limits: Limits) -> Expected:
    raw = body["expected"]
    if not isinstance(raw, dict):
        raise invalid("expected must be an object", field="expected")
    kind = raw.get("kind")
    if kind == "value":
        allowed = ("kind", "value")
    elif kind == "error":
        allowed = ("kind", "category")
    else:
        raise invalid('expected.kind must be "value" or "error"', field="expected.kind")
    unknown = sorted(k for k in raw if k not in allowed)
    if unknown:
        raise invalid(f"unknown field: expected.{unknown[0][:50]}",
                      field=f"expected.{unknown[0][:50]}")
    if kind == "value":
        if "value" not in raw:
            raise invalid("expected.value is required", field="expected.value")
        value = raw["value"]
        if not isinstance(value, str) or not value:
            raise invalid("expected.value must be a nonempty string", field="expected.value")
        if len(value) > limits.max_expected_value_chars:
            raise invalid(f"expected.value is longer than {limits.max_expected_value_chars} characters",
                          field="expected.value", limit=limits.max_expected_value_chars,
                          actual=len(value))
        return Expected("value", value=value)
    if "category" not in raw:
        raise invalid("expected.category is required", field="expected.category")
    if raw["category"] not in ("syntax", "type"):
        raise invalid('expected.category must be "syntax" or "type"', field="expected.category")
    return Expected("error", category=raw["category"])


def program_fields(body, limits: Limits) -> ProgramFields:
    body = _object(body, ("name", "source", "description"), ("name", "source"))
    return ProgramFields(_name(body, limits), _source(body, limits), _description(body, limits))


def collection_fields(body, limits: Limits) -> CollectionFields:
    body = _object(body, ("name", "description"), ("name",))
    return CollectionFields(_name(body, limits), _description(body, limits))


def case_fields(body, limits: Limits) -> CaseFields:
    body = _object(body, ("name", "source", "expected", "description"),
                   ("name", "source", "expected"))
    return CaseFields(_name(body, limits), _source(body, limits),
                      _expected(body, limits), _description(body, limits))


def page_params(args: dict[str, list[str]], limits: Limits) -> tuple[int, str | None]:
    """Validate list query parameters; `args` maps each name to all its values."""
    unknown = sorted(k for k in args if k not in ("limit", "cursor"))
    if unknown:
        raise invalid(f"unknown query parameter: {unknown[0][:40]}", parameter=unknown[0][:40])
    for key, values in args.items():
        if len(values) != 1:
            raise invalid(f"{key} may appear only once", parameter=key)
    limit = limits.default_page_size
    if "limit" in args:
        raw = args["limit"][0]
        if not _DIGITS.fullmatch(raw) or not 1 <= int(raw) <= limits.max_page_size:
            raise invalid(f"limit must be an integer from 1 to {limits.max_page_size}",
                          parameter="limit")
        limit = int(raw)
    cursor = None
    if "cursor" in args:
        cursor = args["cursor"][0]
        if not cursor or len(cursor) > 100:
            raise invalid("cursor is invalid or expired", parameter="cursor")
    return limit, cursor
