"""Checks an installed wheel, run outside the source tree (the CI job `wheel`;
pytest does not collect it): with no docs/data/ beside the package, the
registry the wheel ships resolves the committed Si configuration uid and its
former uid, and the binding model check refuses an unlisted private uid on
both writers, a SetVoltage calibration included."""
import json
import tempfile

import omai.evidence as ev
from omai.lineages import LineageError, record_light, record_simulation, unregistered_for

SI = "7b5e77b1062f0997037cb9fd490d9edb8fce8099c4f700db334aa8afb8af22be"
SI_FORMER = "55bf22ca81868867402ac4ce50a830f91da84c805990c37c3bdafe3b93a69143"
TERSOFF = "52a93e90596829c57d54eef091de6215f1fac7ca15d57eac7568ddfdda26adfb"
PRIVATE = "2" * 64

assert "site-packages" in ev.__file__, ev.__file__
assert ev.default_roots() == [ev.REGISTRY], ev.default_roots()
for pin in (SI, SI_FORMER, "sha256:" + SI):
    record_light(lineage={"template": "kaldo", "conditions": {"potential_sha256": TERSOFF},
                          "material": {"name": "Si", "configuration": pin}})
private = {"template": "kaldo", "conditions": {"potential_sha256": PRIVATE}}
try:
    record_light(lineage=private)
except LineageError:
    pass
else:
    raise SystemExit("an unlisted private model uid was accepted")
record = record_light(lineage=private, unregistered=[{"kind": "model", "uid": PRIVATE}])
assert ev.private_reasons(record) == [
    {"field": "unregistered", "kind": "model"},
    {"field": "conditions.potential_sha256", "kind": "model"}]
assert json.loads(ev.REGISTRY.read_text())["citation_keys"]["SetVoltage"] == ["calibration_sha256"]
print("installed wheel ok:", ev.REGISTRY)

# The strict writer, on the live map the wheel builds: a SetVoltage record
# citing a calibration no registry holds is refused unless it is listed.
calibration = {"node": "SetVoltage", "material": {"name": "fixture"},
               "conditions": {"calibration_sha256": PRIVATE}}
artifacts = [{"path": "r.json", "bytes": 1, "sha256": "a" * 64, "role": "result"}]
with tempfile.TemporaryDirectory() as sim_dir:
    try:
        record_simulation(lineage=calibration, execution={"code": "fixture"},
                          artifacts=artifacts, sim_dir=sim_dir)
    except LineageError as exc:
        assert "never registered" in str(exc), exc
    else:
        raise SystemExit("an unlisted calibration was accepted")
    declared = unregistered_for(calibration)
    assert declared == [{"kind": "model", "uid": PRIVATE}], declared
    path = record_simulation(lineage=calibration, execution={"code": "fixture"},
                             artifacts=artifacts, sim_dir=sim_dir, unregistered=declared)
    assert json.loads(open(path).read())["unregistered"] == declared
print("installed wheel ok: record_simulation")
