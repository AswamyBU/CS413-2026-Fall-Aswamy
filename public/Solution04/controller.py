"""Coordinates state and a replaceable backend."""
from dataclasses import asdict
from threading import Lock
from model import Model
from backend import Backend

class Controller:
    def __init__(self, backend=None):
        self.model = Model()
        self.backend = backend or Backend()
        self.lock = Lock()

    def state(self):
        with self.lock:
            return asdict(self.model)

    def apply(self, source, name):
        with self.lock:
            self.model.apply(source, name)
            return asdict(self.model)

    def run(self, operation):
        with self.lock:
            self.model.begin(operation)
            source = self.model.source
        try:
            result = self.backend.run(operation, source)
        except Exception:
            result = {'outcome': 'backend_error', 'text': 'Backend unavailable. Your source is preserved; retry the operation.'}
        with self.lock:
            self.model.finish(operation, result)
            return asdict(self.model)
