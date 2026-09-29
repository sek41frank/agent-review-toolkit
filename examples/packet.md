# Synthetic review packet: retry-safe import

This entire example is fictional. It contains no production data or credentials.

## Requirements

Import each item ID at most once, including after a process crash or a retry. Duplicate IDs in one batch must not create duplicate records. The store and state represent separately persisted data structures; there is no transaction between them.

## Code: importer.py

```python
def import_batch(items, store, state):
    for item in items:
        if item["id"] not in state["done"]:
            store.append(item)
    state["done"].update(item["id"] for item in items)
```

## Existing synthetic test: test_importer.py

```python
def test_repeat_after_success():
    store = []
    state = {"done": set()}
    items = [{"id": "item-001", "value": "example"}]
    import_batch(items, store, state)
    import_batch(items, store, state)
    assert len(store) == 1
```

This happy-path test is supplied as context. It does not simulate a crash. The example store is a list used to illustrate a persistence boundary, not a real database implementation.

## Questions to assess

Explain whether the requirements follow from this code and test. Identify a concrete failing sequence, and suggest a minimal verification or correction. Distinguish confirmed issues from assumptions about storage behavior.
