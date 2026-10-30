"""docs/assets/submap.js draws the same SVG as omai/submap.py, byte for byte."""

import json

from node_runner import run_module

from omai import submap
from omai.snapshots import DATA, build_snapshot

JS = (DATA.parent / "assets" / "submap.js").resolve()


def test_js_submap_matches_python():
    snap = build_snapshot()
    graph = json.loads((DATA / "graph.json").read_text())
    cases = {k: c["nodes"] for k, c in snap["codes"].items()}
    cases["one source"] = ["Temperature"]
    cases["one sink"] = ["ThermalConductivity[bte_solver=rta]"]
    cases["everything"] = [n["id"] for n in snap["nodes"]]
    script = (f"import {{ svg }} from {json.dumps(JS.as_uri())};"
              "let s='';process.stdin.on('data',d=>s+=d).on('end',()=>{const {snap,cases}=JSON.parse(s);"
              "const out={};for(const k in cases) out[k]=svg(snap,cases[k],{mapHref:'/map/',fitUnder:760});"
              "process.stdout.write(JSON.stringify(out));});")
    got = json.loads(run_module(script, json.dumps({"snap": snap, "cases": cases})))
    for k, ids in cases.items():
        assert got[k] == submap.svg(graph, set(ids), map_href="/map/", fit_under=760), k


def test_every_edge_stays_inside_the_view_box():
    # a cubic reaches 0.75 of the way to its control points; a loop in the last column must not be clipped
    import re
    snap = build_snapshot()
    graph = json.loads((DATA / "graph.json").read_text())
    for k, c in snap["codes"].items():
        out = submap.svg(graph, set(c["nodes"]))
        width = int(re.search(r'viewBox="0 0 (\d+)', out)[1])
        for d in re.findall(r'class="sm-edge" d="([^"]+)"', out):
            x = [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", d)[0::2]]
            assert x[0] + 0.75 * (max(x[1], x[2]) - x[0]) <= width, (k, d)
