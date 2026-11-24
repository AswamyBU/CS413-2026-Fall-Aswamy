"""In-memory database service for LAMBDA-studio (Assign09).

Layers (each module depends only on the ones listed after it):

    api.py         HTTP routes (Flask): status codes, headers, JSON bodies
    service.py     business rules: uniqueness, revisions, capacity, atomicity
    validation.py  request bodies, If-Match, query parameters, route IDs
    pagination.py  snapshot cursors for list routes
    store.py       storage interface + the in-memory backend
    records.py     immutable record values and their JSON representations
    errors.py      ApiError (HTTP status + stable code)
    config.py      limits

This package never imports or runs LAMBDA3: it only stores source text.
"""
