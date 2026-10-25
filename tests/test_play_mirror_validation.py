"""Browser mirror shape checks agree with the authoritative Python light gate."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from omai import lineages as lin

_PLAY = Path(__file__).resolve().parents[1] / "docs" / "play" / "index.html"


def _function(html: str, name: str) -> str:
    match = re.search(rf"function {re.escape(name)}\s*\([^)]*\)\s*\{{", html)
    assert match
    end, depth = match.end(), 1
    while depth:
        depth += (html[end] == "{") - (html[end] == "}")
        end += 1
    return html[match.start():end]


def _on_page(record: dict) -> dict:
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is needed for browser/Python agreement")
    html = _PLAY.read_text()
    source = "var nodeById = {}; var SHA256_RE = /^[0-9a-f]{64}$/;\n"
    source += "\n".join(_function(html, name) for name in (
        "normalizeLineageRecord", "validateLightJS", "heavyHost"))
    source += "\nvar rec = " + json.dumps(record) + ";\n"
    source += "console.log(JSON.stringify({check:validateLightJS(rec),host:heavyHost(rec)}));"
    result = subprocess.run([node, "-e", source], capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


@pytest.mark.parametrize("mirrors,valid", [
    (None, True), ({}, True),
    ({"model": None}, True), ({"model": "https://example.org/model"}, True),
    ({"model": {}}, True),
    ({"model": {"url": None, "provider": None}}, True),
    ({"model": {"provider": "private host"}}, True),
    ({"model": {"url": "https://example.org/model", "provider": "repository", "extra": 4}}, True),
    ([], False), (["https://example.org/model"], False), ("bad", False), (3, False), (False, False),
    ({"model": []}, False), ({"model": 3}, False), ({"model": False}, False),
    ({"model": {"url": []}}, False), ({"model": {"url": 42}}, False),
    ({"model": {"provider": {}}}, False),
    ({"model": {"url": "https://example.org/model", "provider": True}}, False),
])
def test_browser_mirrors_match_python_shape_gate(mirrors, valid):
    record = {"lineage": {"template": "test"}, "mirrors": mirrors}
    if valid:
        lin.validate_light(record, name_to_uid={})
    else:
        with pytest.raises(lin.LineageError, match="mirror"):
            lin.validate_light(record, name_to_uid={})
    page = _on_page(record)
    assert page["check"]["ok"] is valid
    if not valid:
        assert "mirror" in page["check"]["error"].lower()
        assert page["host"] is None


def test_absent_and_legacy_mirror_records_still_open_without_identity_changes():
    lineage = {"template": "test"}
    for key in ("lineage", "recipe"):
        record = {key: lineage, "id": lin.lineage_id(lineage)}
        result = _on_page(record)["check"]
        assert result["ok"]
        assert result["record"]["lineage"] == lineage
        assert result["record"]["id"] == record["id"]


def test_host_rendering_uses_only_well_shaped_locations():
    assert _on_page({"lineage": {}, "mirrors": {"x": {"provider": "private"}}})["host"] is None
    record = {"lineage": {}, "mirrors": {"x": None},
              "artifacts": [{"path": "model", "role": "output", "url": "https://example.org/model"}]}
    assert _on_page(record)["host"]["url"] == "https://example.org/model"
    record["artifacts"][0]["url"] = {"bad": "not a location"}
    assert _on_page(record)["host"] is None
