"""JSON-RPC 2.0 service for the LAMBDA3 language tools.

Layers (each module depends only on the ones below it):

    app.py       HTTP transport (Flask): POST /rpc, media type, status codes
    jsonrpc.py   JSON-RPC 2.0 envelopes, batches, notifications, error objects
    service.py   RPC methods: parameter validation + calls into LAMBDA3
    sandbox.py   runs interpretation in a worker process with a hard deadline
    backend.py   locates and imports LAMBDA3 and its mylib/ libraries

This package file stays import-light so the sandbox's worker processes start
quickly (they never import Flask).
"""
