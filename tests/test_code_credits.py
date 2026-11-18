"""Enforcement: every code representation on the map is cited and licensed.

Giuseppe's rule: every code we represent must carry a citation (paper / DOI)
and its license. This test is the "remember" mechanism. It discovers every
representation actually present on the map (every representation_name that build_codes
emits) and fails if any representation lacks a CODE_CREDITS entry, has an empty citation
or license, or carries license "UNKNOWN" without an explicit waiver below.
A future representation therefore cannot land uncredited: adding an adapter without a
credits entry breaks this test.
"""

import json
import re
from pathlib import Path

from omai.map_data import DOMAINS, build_codes
from omai.representation.credits import CODE_CREDITS, PER_NODE_CREDITS

# Representations permitted to carry an UNKNOWN license, each with a written reason.
# Empty today: UNKNOWN is allowed, but only with a recorded justification.
ALLOWED_UNKNOWN: dict[str, str] = {
    # "some-representation": "reason the license genuinely cannot be determined",
}


def _representations() -> set[str]:
    return set(build_codes(DOMAINS).keys())


def test_every_representation_has_a_credits_entry():
    missing = sorted(_representations() - set(CODE_CREDITS))
    assert not missing, (
        f"code representations on the map with no CODE_CREDITS entry: {missing}. "
        "Every code we represent must be cited and licensed "
        "(omai/representation/credits.py)."
    )


def test_citation_and_license_non_empty():
    problems = []
    for representation in sorted(_representations()):
        cr = CODE_CREDITS.get(representation)
        if cr is None:
            continue  # covered by test_every_representation_has_a_credits_entry
        if not (cr.get("citation") or "").strip():
            problems.append(f"{representation}: empty citation")
        if not (cr.get("license") or "").strip():
            problems.append(f"{representation}: empty license")
    assert not problems, "; ".join(problems)


def test_license_not_unknown_unless_waived():
    offenders = []
    for representation in sorted(_representations()):
        cr = CODE_CREDITS.get(representation)
        if cr is None:
            continue
        if cr.get("license") == "UNKNOWN" and representation not in ALLOWED_UNKNOWN:
            offenders.append(representation)
    assert not offenders, (
        f"representations with UNKNOWN license and no ALLOWED_UNKNOWN waiver: {offenders}"
    )


def test_credits_flow_into_codes_json():
    codes = build_codes(DOMAINS)
    for representation, spaces in codes.items():
        for space, entry in spaces.items():
            cr = PER_NODE_CREDITS.get((representation, space), CODE_CREDITS[representation])
            assert entry["license"] == cr["license"], (representation, space)
            assert entry["citation"] == cr["citation"], (representation, space)
            assert entry["license"] != "UNKNOWN", (representation, space)


def test_license_source_recorded():
    # The sourcing bar: every license must say where it was read.
    for representation, cr in CODE_CREDITS.items():
        assert (cr.get("license_source") or "").strip(), representation


def test_per_node_overrides_point_at_real_representations():
    """An override must name a (representation, node) pair actually on the map, and
    meet the same completeness bar as a code-level credit. A stale override
    (the representation moved or the node renamed) is a bug, not dead weight."""
    codes = build_codes(DOMAINS)
    problems = []
    for (representation, node), cr in PER_NODE_CREDITS.items():
        if representation not in codes:
            problems.append(f"({representation}, {node}): representation not on the map")
            continue
        if node not in codes[representation]:
            problems.append(f"({representation}, {node}): node not served by this representation")
        if not (cr.get("citation") or "").strip():
            problems.append(f"({representation}, {node}): empty citation")
        if not (cr.get("license") or "").strip():
            problems.append(f"({representation}, {node}): empty license")
        if not (cr.get("license_source") or "").strip():
            problems.append(f"({representation}, {node}): empty license_source")
    assert not problems, "; ".join(problems)


def test_overrides_reach_the_emitted_data():
    """build_codes must actually apply the per-node override: the emitted
    entry carries the override's citation, doi, license, and url, not the
    code-level ones."""
    codes = build_codes(DOMAINS)
    for (representation, node), cr in PER_NODE_CREDITS.items():
        entry = codes.get(representation, {}).get(node)
        assert entry is not None, (representation, node)
        for field in ("citation", "doi", "license", "url"):
            assert entry[field] == cr.get(field), (
                f"({representation}, {node}) field {field} does not carry the override")


def test_every_code_carries_its_display_name_on_every_entry():
    # The name rides on each node entry (a sibling key would read as a node).
    for code, spaces in build_codes(DOMAINS).items():
        name = (CODE_CREDITS[code].get("name") or "").strip()
        assert name, code
        assert {e["name"] for e in spaces.values()} == {name}, code


# GPL-2.0, GPL-3.0, LGPL-2.1 and LGPL-3.0 without a suffix, or with "+", are deprecated
# SPDX ids. The bare form does not say whether later versions of the license are allowed.
# A credits license names -only or -or-later, as the code's own grant reads.
_BARE_GNU = re.compile(r"\b(?:L?GPL|AGPL)-[0-9]\.[0-9](?!-only|-or-later)\b")


def test_no_deprecated_bare_gnu_license_id():
    bare = {code: c["license"] for code, c in CODE_CREDITS.items()
            if _BARE_GNU.search(c.get("license") or "")}
    assert not bare, (
        f"credits licenses with a deprecated bare GNU id: {bare}. Write the SPDX id "
        "with -only or -or-later, as the code's own license grant reads")


def test_license_agrees_with_the_release_read_at_its_tag():
    # The release registry reads each license at the tag (docs/data/releases/<code>.json,
    # field spdx). The code page shows both, so for a code with a registered release the
    # credits license must lead with the same first SPDX id as the newest release. Codes
    # without a release file are checked only by the bare-id test above.
    releases = Path(__file__).resolve().parents[1] / "docs" / "data" / "releases"
    first_id = re.compile(r"[A-Za-z0-9.+-]+")
    for path in sorted(releases.glob("*.json")):
        rows = json.loads(path.read_text()).get("releases") or []
        spdx = (rows[-1].get("spdx") or "") if rows else ""
        code = path.stem
        if not spdx or code not in CODE_CREDITS:
            continue
        lead = first_id.match(CODE_CREDITS[code]["license"]).group(0)
        assert lead == first_id.match(spdx).group(0), (code, CODE_CREDITS[code]["license"], spdx)
