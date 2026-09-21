"""JSON Schema export of the SimulationRecord.

The one machine-readable statement of the record shape, so a consumer that
does not run Python (the MCG worker, in TypeScript) validates the same record
this library writes. The schema is derived from what
:func:`omai.lineages.record_lineage`, :func:`omai.lineages.record_simulation`
and the gates in :mod:`omai.gates` already accept; it is a SHAPE gate only.
Identity (that ``id`` equals ``lineage_id(lineage)``), node resolution against
the live map, and the contribution gates stay in their own modules: a schema
cannot hash, and pretending otherwise would let an id-mismatched record pass.

Objects are CLOSED (``additionalProperties: false``) at every level the record
contract names, so a key nobody agreed on is refused rather than carried
silently into storage. The two open maps are the ones whose keys are data:
``lineage.conditions`` / ``lineage.params`` (the dials of an experiment) and
``mirrors`` (artifact path -> location).

SCOPE: a CURRENT record, the one that carries its lineage under ``lineage``.
A legacy record carrying the pre-rename ``recipe`` key is OUT OF SCOPE and is
refused here, although :func:`omai.lineages.record_lineage` still reads it.
That is deliberate: the schema states the shape new records are written in, and
widening it to ``recipe`` would keep the legacy spelling alive in every
consumer that validates. A caller holding a possibly-legacy record normalizes
it first, which is one line::

    record = {**record, "lineage": record_lineage(record)}
    record.pop("recipe", None)
    errors = validate_record(record)

Legacy links stay readable forever through ``record_lineage``; they are simply
not what this schema describes.
"""

from __future__ import annotations

# A sha256 hex digest, the shape lineages.py's _SHA256_RE enforces.
_SHA256 = r"^[0-9a-f]{64}$"

# A configuration pin: the bare uid, or the "sha256:<uid>" spelling that
# lineages.py _validate_configuration also accepts.
_CONFIGURATION_UID = r"^(sha256:)?[0-9a-f]{64}$"

_NON_EMPTY = {"type": "string", "minLength": 1}


def simulation_record_schema() -> dict:
    """The JSON Schema (draft 2020-12) of a SimulationRecord.

    A fresh dict per call: a caller that mutates the returned schema (pinning a
    ``$id``, tightening a field) must not mutate every other caller's copy.
    """
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://openmaterials.ai/schema/simulation-record-1.json",
        "title": "SimulationRecord",
        "description": (
            "One recorded computation: the lineage that identifies it, what "
            "ran, the artifacts produced, where their bytes are mirrored, and "
            "the result instances claimed. Identity is the lineage alone; "
            "execution, artifacts, mirrors and results sit outside the hash."
        ),
        "type": "object",
        "required": ["id", "lineage"],
        "additionalProperties": False,
        "properties": {
            "id": {
                "description": "sha256 of the canonical lineage (lineage_id).",
                "type": "string",
                "pattern": _SHA256,
            },
            "lineage": _lineage_schema(),
            "execution": _execution_schema(),
            "artifacts": {
                "description": "Artifact pointers; never part of identity.",
                "type": "array",
                "items": _artifact_schema(),
            },
            "mirrors": _mirrors_schema(),
            "results": {
                "description": (
                    "Result instances: a backref slug (string) or an inline "
                    "instance stub (object)."
                ),
                "type": "array",
                # if/then on the type rather than anyOf: a bad stub must report
                # the FIELD that is wrong ("results[0].value is not of type
                # number"), not collapse to "no branch matched" and leave the
                # reader hunting.
                "items": {
                    "type": ["string", "object"],
                    "if": {"type": "object"},
                    "then": _result_schema(),
                    "else": _NON_EMPTY,
                },
            },
            "kind": {
                "description": "Record family, when the writer states one.",
                "type": "string",
            },
            "source": {
                "description": (
                    "Legacy top-level provenance, outside identity. Current "
                    "records carry a 'scheme:ref' string on the lineage."
                ),
                "type": "object",
            },
        },
    }


def _lineage_schema() -> dict:
    """The asked computation: the object the identity hash reads."""
    return {
        "description": (
            "The asked computation. Canonicalized and hashed to the record id."
        ),
        "type": "object",
        "required": ["node"],
        "additionalProperties": False,
        "properties": {
            "node": {
                "description": "The map node id this computation targets.",
                **_NON_EMPTY,
            },
            "node_uid": {
                "description": "The content uid of that node, when pinned.",
                "type": "string",
                "pattern": _SHA256,
            },
            # A bare name ("Si") and the structured form ({name, configuration})
            # both appear in committed lineages, so both are accepted.
            "material": {
                "anyOf": [
                    {"type": "string"},
                    {
                        "type": "object",
                        "required": ["name"],
                        "additionalProperties": False,
                        "properties": {
                            "name": _NON_EMPTY,
                            "configuration": {
                                # lineages.py _validate_configuration accepts
                                # the uid bare or as "sha256:<uid>"; the schema
                                # must not refuse a form the gate admits.
                                "description": "A committed configuration uid, "
                                               "bare or 'sha256:'-prefixed.",
                                "type": "string",
                                "pattern": _CONFIGURATION_UID,
                            },
                        },
                    },
                ]
            },
            # Open maps: the KEYS are the experiment's dials, not a fixed
            # vocabulary. Closing these would refuse every new condition.
            "conditions": {"type": "object"},
            "params": {"type": "object"},
            "hyperparameters": {"type": "object"},
            "values": {"type": "object"},
            "template": {"description": "The code family, for bundle-derived "
                                        "lineages.", "type": "string"},
            "spec": {"description": "The host's verbatim input, for "
                                    "bundle-derived lineages.", "type": "object"},
            "source": {
                "description": "Namespaced 'scheme:ref' provenance, inside "
                               "identity.",
                "type": "string",
                "pattern": r"^[a-z][a-z0-9+.-]*:.+$",
            },
        },
    }


def _execution_schema() -> dict:
    """What ran. Only ``code`` is required, as _validate_execution enforces."""
    return {
        "description": "What ran. Stored, never hashed.",
        "type": "object",
        "required": ["code"],
        "additionalProperties": False,
        "properties": {
            "code": {"description": "The code that ran.", **_NON_EMPTY},
            "code_version": {"type": "string"},
            "image_digest": {
                "description": "The per-run image digest (worker vocabulary).",
                "type": "string",
            },
            "container_digest": {
                "description": "The per-run image digest (commons vocabulary).",
                "type": "string",
            },
            "registry": {
                "description": "Registries the image was resolved from.",
                "type": "array",
                "items": {"type": "string"},
            },
            "runner": {"type": "string"},
            "wall_time_s": {"type": "number"},
            "seeds": {"type": "array", "items": {"type": "integer"}},
            "started_at": {"type": "string"},
            "finished_at": {"type": "string"},
            "current_stage": {"type": "string"},
            "kind": {"type": "string"},
        },
    }


def _artifact_schema() -> dict:
    """A pointer: path and role required, byte claim and location optional.

    This is the LIGHT contract (_validate_pointers). The strict writer
    additionally requires bytes and sha256 on every entry; a schema that
    demanded them would refuse every valid light record, so the extra strictness
    stays in record_simulation where it belongs.
    """
    return {
        "type": "object",
        "required": ["path", "role"],
        "additionalProperties": False,
        "properties": {
            "path": _NON_EMPTY,
            "role": _NON_EMPTY,
            "sha256": {"type": "string", "pattern": _SHA256},
            "bytes": {"type": "integer", "minimum": 0},
            "url": {"type": "string"},
        },
    }


def _mirrors_schema() -> dict:
    """artifact path -> location, either a bare url or an object."""
    return {
        "description": "Where the artifact bytes live. Outside identity.",
        "type": "object",
        "additionalProperties": {
            "anyOf": [
                {"type": "string"},
                {"type": "null"},
                {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string"},
                        "provider": {"type": "string"},
                    },
                },
            ]
        },
    }


def _result_schema() -> dict:
    """An inline instance stub, the keys _validate_results requires."""
    return {
        "type": "object",
        "required": ["variable", "material", "conditions", "value", "units",
                     "source"],
        "additionalProperties": False,
        "properties": {
            "variable": _NON_EMPTY,
            "material": _NON_EMPTY,
            "conditions": {"type": "object"},
            # null is a real value for a node with no single scalar (a DOS, a
            # force-constant file); a string here is a category error.
            "value": {"type": ["number", "null"]},
            "units": {"type": "string"},
            "uncertainty": {"type": ["number", "null"]},
            "artifact": {"type": ["string", "null"]},
            "simulation": {
                "description": "Backref to the record that produced it.",
                "type": "string",
                "pattern": _SHA256,
            },
            "source": {
                "type": "object",
                "required": ["kind", "ref"],
                "additionalProperties": False,
                "properties": {
                    "kind": {"enum": ["simulation", "measurement"]},
                    "ref": _NON_EMPTY,
                    "detail": {"type": "string"},
                },
            },
        },
    }


def validate_record(record: dict) -> list[str]:
    """Every way ``record`` violates the schema, as readable messages.

    An empty list means it validates. Errors are sorted by their location in
    the document so two runs over the same record report them in the same
    order (a caller diffing messages sees a real change, never a reshuffle).
    """
    import jsonschema

    validator = jsonschema.Draft202012Validator(simulation_record_schema())
    return [
        f"{_where(error)}: {error.message}"
        for error in sorted(validator.iter_errors(record),
                            key=jsonschema.exceptions.relevance)
    ]


def _where(error) -> str:
    """The JSON path of an error, as ``<record>`` or ``<record>.a.b[0]``."""
    out = "<record>"
    for part in error.absolute_path:
        out += f"[{part}]" if isinstance(part, int) else f".{part}"
    return out
