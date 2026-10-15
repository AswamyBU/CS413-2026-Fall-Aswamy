"""Application state, independent of HTTP and the browser."""
from dataclasses import dataclass, field
from backend import LIMIT

@dataclass
class Model:
    source: str = ''
    name: str = 'Untitled'
    revision: int = 0
    results: list = field(default_factory=list)
    artifact: object = None
    busy: bool = False

    def apply(self, source, name):
        if self.busy:
            raise ValueError('An operation is in progress.')
        if not isinstance(source, str) or not source.strip():
            raise ValueError('Source cannot be empty. Enter a constructor expression.')
        if len(source.encode('utf-8')) > LIMIT:
            raise ValueError('Source exceeds the 65,536-byte limit.')
        self.source, self.name = source, str(name)[:200]
        self.revision += 1
        self.results.clear()
        self.artifact = None

    def begin(self, operation):
        if self.busy:
            raise ValueError('An operation is already in progress.')
        if operation == 'execute':
            raise ValueError('Execute requires a generated artifact. Compilation is not yet implemented.')
        if operation not in ('lint', 'interpret', 'typecheck', 'compile'):
            raise ValueError('Unknown operation.')
        if not self.revision:
            raise ValueError('Apply source before running tools.')
        if operation == 'compile':
            self.artifact = None
        self.busy = True

    def finish(self, operation, result):
        self.results.append(dict(result, operation=operation, revision=self.revision))
        self.busy = False
