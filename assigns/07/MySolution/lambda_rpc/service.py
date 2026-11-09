"""RPC methods: validate params, call LAMBDA3, shape results.

This layer knows nothing about HTTP or JSON-RPC envelopes. Each method takes
the `params` object and returns a JSON-ready result or raises RpcError.
Unexpected exceptions are left to the dispatcher, which logs them and
returns -32603.
"""

from collections.abc import Callable

from . import backend
from .config import API_VERSION, Limits
from .errors import (INVALID_PARAMS, LAMBDA_SYNTAX_ERROR, LAMBDA_TYPE_ERROR,
                     RESOURCE_LIMIT, RpcError)
from .sandbox import ProcessInterpreter

COMPILE_TARGETS = ("python", "javascript")


def _invalid(message: str, **data) -> RpcError:
    return RpcError(INVALID_PARAMS, f"Invalid params: {message}", data or None)


def _check_keys(params: dict, allowed: tuple[str, ...]) -> None:
    unexpected = sorted(str(key) for key in params if key not in allowed)
    if unexpected:
        raise _invalid("unexpected parameter(s)", unexpected=unexpected[:10],
                       allowed=list(allowed))


class LambdaService:
    """The four RPC methods, wrapping the LAMBDA3 backend.

    `build` (parse + type-check) and `interpreter` can be replaced with test
    doubles to simulate backend failures and timeouts.
    """

    def __init__(self, limits: Limits | None = None, *,
                 build: Callable | None = None,
                 interpreter: Callable[[str, tuple[str, ...]], str] | None = None):
        self.limits = limits or Limits()
        self.L = backend.L
        self.build = build or backend.build
        self.interpreter = interpreter or ProcessInterpreter(
            self.limits.interpret_timeout,
            startup_timeout=self.limits.worker_startup_timeout,
            max_value_chars=self.limits.max_value_chars,
            recursion_limit=self.limits.recursion_limit,
        )

    def methods(self) -> dict[str, Callable[[dict], object]]:
        return {
            "service.health": self.health,
            "lambda.typecheck": self.typecheck,
            "lambda.interpret": self.interpret,
            "lambda.compile": self.compile,
        }

    # ---- methods ---------------------------------------------------------

    def health(self, params: dict) -> dict:
        _check_keys(params, ())
        return {"status": "ok", "version": API_VERSION}

    def typecheck(self, params: dict) -> dict:
        source, libraries = self._source_params(params, ())
        _, typ = self._parse_and_typecheck(source, libraries)
        return {"type": self.L.format_type(typ)}

    def interpret(self, params: dict) -> dict:
        source, libraries = self._source_params(params, ())
        _, typ = self._parse_and_typecheck(source, libraries)  # fail fast, in-process
        value = self.interpreter(source, libraries)             # worker re-checks, evaluates
        return {"type": self.L.format_type(typ), "value": value}

    def compile(self, params: dict) -> dict:
        source, libraries = self._source_params(params, ("target",))
        if "target" not in params:
            raise _invalid("'target' is required", allowed=list(COMPILE_TARGETS))
        target = params["target"]
        if target not in COMPILE_TARGETS:
            raise _invalid("'target' must be \"python\" or \"javascript\"",
                           allowed=list(COMPILE_TARGETS))
        expression, _ = self._parse_and_typecheck(source, libraries)
        compiler = self.L.d0exp_compile if target == "python" else self.L.d0exp_compile_js
        try:
            code = compiler(expression)
        except RecursionError:
            raise RpcError(RESOURCE_LIMIT, "Source is nested too deeply to compile",
                           {"limit": "recursionDepth"}) from None
        return {"target": target, "code": code}  # returned as text, never run

    # ---- helpers ---------------------------------------------------------

    def _source_params(self, params: dict, extra: tuple[str, ...]):
        _check_keys(params, ("source", "libraries") + extra)
        if "source" not in params:
            raise _invalid("'source' is required")
        source = params["source"]
        if not isinstance(source, str):
            raise _invalid("'source' must be a string")
        if not source.strip():
            raise _invalid("'source' must not be blank")
        size = len(source.encode("utf-8", errors="surrogatepass"))
        if size > self.limits.max_source_bytes:
            raise _invalid("'source' is too large", limit="maxSourceBytes",
                           maxSourceBytes=self.limits.max_source_bytes, actualBytes=size)
        libraries = params.get("libraries", [])
        if (not isinstance(libraries, list)
                or not all(isinstance(name, str) for name in libraries)
                or len(set(libraries)) != len(libraries)
                or any(name not in backend.LIBRARY_NAMES for name in libraries)):
            raise _invalid("'libraries' must be a list of distinct library names",
                           allowed=list(backend.LIBRARY_NAMES))
        return source, tuple(libraries)

    def _parse_and_typecheck(self, source: str, libraries: tuple[str, ...]):
        try:
            return self.build(source, libraries)
        except self.L.LambdaSyntaxError as error:
            line, column = error.lineno, error.offset
            raise RpcError(
                LAMBDA_SYNTAX_ERROR,
                f"LAMBDA syntax error at line {line}, column {column}: {error.msg}",
                {"stage": "parse", "message": error.msg, "line": line,
                 "column": column, "sourceLine": error.text},
            ) from None
        except self.L.TypeCheckError as error:
            raise RpcError(LAMBDA_TYPE_ERROR, f"LAMBDA type error: {error}",
                           {"stage": "typecheck", "message": str(error)}) from None
        except RecursionError:
            raise RpcError(RESOURCE_LIMIT, "Source is nested too deeply to parse or type-check",
                           {"limit": "recursionDepth"}) from None
