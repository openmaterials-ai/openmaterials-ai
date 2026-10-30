# Stable external-solve snapshots

`omai.external_solve` owns the neutral external-frontier envelope. Envelope
version 1, request/lineage hashing, ordered node identities, and execution
metadata's exclusion from identity are unchanged.

This API ships from openmaterials-ai 0.5.0, on PyPI as 0.5.1 (the same code). The 0.4.0 wheel does not include it.

`build_request` and `parse_request` still return mutable dictionaries;
`validate_request` still returns its report. Builders now detach caller-owned
lineage and execution values, so later caller edits cannot silently invalidate
the returned dictionary's hashes.

For a handoff that must remain stable after validation:

```python
from omai.external_solve import snapshot_request, validate_request_snapshot

# Shape/hash validation only; no map required.
received = snapshot_request(request)

# Separate live-map authorization; stale/dead bindings fail on every call.
validated = validate_request_snapshot(received, store_root=map_directory)
assert validated.request_id == received.request_id

wire_copy = validated.to_dict()
```

The shape/hash check also works from an installed 0.5.0 or later wheel; it
does not require a source map.

`ExternalSolveRequestSnapshot` stores only immutable JSON. Each `to_dict()`
returns independent nested data, including execution metadata. Its constructor
also performs the shape/hash check; constructing it does not bypass validation.
Supported values are finite JSON values with string object keys. Tuples,
non-string keys and nonfinite values are refused without coercion. Stored
values preserve integer/float distinctions and full input precision; identity
canonicalization still uses the existing lineage rules.

A snapshot is not permanent dispatch authorization. `snapshot_request` does not
inspect a map or grant an adapter capability. `validate_request_snapshot`
checks the current store on every call, reads exactly the head it checked, and
refuses a map that changes during validation. Consumers must also apply their
own reviewed capability binding and repeat freshness checks at later handoffs.

Keep the same accepted snapshot through capability selection and planning.
Pass a separate `to_dict()["lineage"]` to callbacks that accept mutable data;
never reread the original request after callbacks. OMAI adds no dispatcher,
engine dependency or execution behavior. The executor's existing
`ExternalSolveRequired` behavior is unchanged.
