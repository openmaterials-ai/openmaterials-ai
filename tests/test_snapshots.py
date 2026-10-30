"""Share-link snapshots: the data a /m/ link reads, frozen under its content hash."""

import hashlib
import json

from omai import snapshots, submap
from omai.snapshots import DATA, build_snapshot, decode, encode, snapshot_bytes, write_snapshot


def test_snapshot_is_deterministic_and_named_by_its_hash(tmp_path):
    b1, b2 = snapshot_bytes(build_snapshot()), snapshot_bytes(build_snapshot())
    assert b1 == b2
    h = write_snapshot(tmp_path)
    assert h == hashlib.sha256(b1).hexdigest()
    assert (tmp_path / f"{h}.json").read_bytes() == b1


def test_snapshot_holds_no_private_code():
    snap = build_snapshot()
    reg = json.loads((DATA / "registry.json").read_text()).get("code", {})
    private = {k for k, v in reg.items() if v.get("visibility") == "private"}
    assert not private & set(snap["codes"])
    raw = snapshot_bytes(snap).lower()
    assert b"meskal" not in raw and b"mescal" not in raw


def test_snapshot_names_match_the_submap():
    for n in build_snapshot()["nodes"]:
        assert n["name"] == submap.node_name(n["id"])
        runs = submap.symbol_runs(n["symbol"] or "")
        assert n["sym"] == ([list(r) for r in runs] if runs else None)


def test_snapshot_order_is_the_graph_order():
    graph = json.loads((DATA / "graph.json").read_text())
    assert [n["id"] for n in build_snapshot()["nodes"]] == [n["id"] for n in graph["nodes"]]


def test_committed_latest_is_the_generator_output():
    index = json.loads((DATA / "v" / "index.json").read_text())
    b = snapshot_bytes(build_snapshot())
    assert index["latest"] == hashlib.sha256(b).hexdigest(), "the share snapshot is stale: run python -m omai.snapshots"
    assert (DATA / "v" / f"{index['latest']}.json").read_bytes() == b
    assert index["latest"] in index["snapshots"]


def test_existing_snapshots_are_never_rewritten(tmp_path, monkeypatch):
    h1 = write_snapshot(tmp_path)
    f = tmp_path / f"{h1}.json"
    before = (f.read_bytes(), f.stat().st_mtime_ns)
    assert write_snapshot(tmp_path) == h1
    assert (f.read_bytes(), f.stat().st_mtime_ns) == before
    real = snapshots.build_snapshot
    monkeypatch.setattr(snapshots, "build_snapshot", lambda: {**real(), "map_version": "changed"})
    h2 = write_snapshot(tmp_path)
    assert h2 != h1 and f.read_bytes() == before[0]
    assert json.loads((tmp_path / "index.json").read_text()) == {"latest": h2, "snapshots": [h1, h2]}


def test_succession_lists_the_phonon_dos_supersede():
    succ = build_snapshot()["succession"]
    old = next(k for k in succ if k.startswith("9b0af04f9828"))
    assert any(u.startswith("e14b6cdd007c") for u in succ[old])


def test_selection_round_trip_and_rejections():
    snap = build_snapshot()
    n = len(snap["nodes"])
    for key, code in snap["codes"].items():
        hx = encode(snap, code["nodes"])
        assert hx == hx.lower() and len(hx) % 2 == 0 and not hx.endswith("00")
        assert decode(snap, hx) == sorted(code["nodes"], key=[m["id"] for m in snap["nodes"]].index)
    assert encode(snap, [snap["nodes"][0]["id"]]) == "80"
    over = format(1 << (8 * ((n + 8) // 8) - 1 - n), "0%dx" % (2 * ((n + 8) // 8)))
    for bad in ["", "0", "00", "ABC", "abc", over]:
        assert decode(snap, bad) is None, bad
