# Stable external-solve receive values

`omai.external_solve` owns the neutral external-frontier envelope. Envelope
version 1, request/lineage hashing, ordered node identities, and execution
metadata's exclusion from identity are unchanged.

Existing `build_request` and `parse_request` still return mutable dictionaries;
`validate_request` still returns its small report. Builders now detach caller
lineage/execution values, so later caller edits cannot silently invalidate the
new dictionary's hashes.

For a handoff that must remain stable after validation:

```python
from omai.external_solve import snapshot_request, validate_request_snapshot

# Shape/hash validation only; usable from an installed wheel without a map.
received = snapshot_request(request)

# Separate live-map authorization; stale/dead bindings fail on every call.
validated = validate_request_snapshot(received, store_root=map_directory)
assert validated.request_id == received.request_id

wire_copy = validated.to_dict()
```

`ExternalSolveRequestSnapshot` stores only immutable JSON. Each `to_dict()`
returns independent nested data, including execution metadata. Its constructor
also performs the shape/hash check; constructing it is not a validation bypass.
Supported values are finite JSON values with string object keys. Tuples,
non-string keys and nonfinite values are refused, not silently coerced. Stored
values preserve integer/float distinctions and full input precision; identity
canonicalization still uses the existing lineage rules.

A snapshot is **not a permanent dispatch permit**. `snapshot_request` does not
inspect a map or grant an adapter capability. `validate_request_snapshot`
checks the current store on every call, reads exactly the head it checked, and
refuses a map that changes during validation. Consumers must also apply their
own reviewed capability binding and repeat freshness checks at later handoffs.

Keep the same accepted snapshot through capability selection and planning.
Pass a separate `to_dict()["lineage"]` to callbacks that accept mutable data;
never reread the original request after callbacks. OMAI adds no dispatcher,
engine dependency or execution behavior. The executor's existing
`ExternalSolveRequired` behavior is unchanged.
