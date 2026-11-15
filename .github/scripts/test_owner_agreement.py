"""Tests for owner_agreement.py: the table, the owners of a path, when a line holds, the
pure-revert rule, the deploy step and the table lint.

    python3 -m unittest discover -s .github/scripts -p 'test_owner_agreement.py'
"""

from __future__ import annotations

import contextlib
import io
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import owner_agreement as oa  # noqa: E402

SIGNER = "seat-account"
TABLE = f"""# Path owners

## Seats

Chief of staff, Platform, Engines, Revenue and legal.

## Signers

{SIGNER}

## Table

| Paths | Seats | What |
| --- | --- | --- |
| `OWNERS.md` | Chief of staff | The table |
| `app/` | Platform | The app |
| `app/billing.ts`, `app/**/*.price.json` | Revenue and legal | Money |
| `engine/` | Engines | Engines |
| `docs/*.md` | Platform | Docs, one level |
| (the Signers list) | Chief of staff, Engines | Who may sign |
| (any other path) | Platform | Default owner |
"""


def signed(*texts):
    return [(SIGNER, t) for t in texts]


class TableTest(unittest.TestCase):
    def setUp(self):
        self.t = oa.parse_table(TABLE)

    def test_overlapping_rows_add_up(self):
        self.assertEqual(self.t.owners("app/billing.ts"), {"Platform", "Revenue and legal"})
        self.assertEqual(self.t.owners("app/x/y/rate.price.json"), {"Platform", "Revenue and legal"})
        self.assertEqual(self.t.owners("app/main.ts"), {"Platform"})

    def test_default_only_when_no_row_matches(self):
        self.assertEqual(self.t.owners("README.md"), {"Platform"})
        self.assertEqual(self.t.owners("engine/a.py"), {"Engines"})

    def test_single_star_stays_in_one_segment(self):
        self.assertFalse(oa.pattern_regex("docs/*.md").fullmatch("docs/sub/a.md"))
        self.assertTrue(oa.pattern_regex("app/**/*.price.json").fullmatch("app/a/b/c.price.json"))

    def test_double_star_matches_no_directory_too(self):
        self.assertTrue(oa.pattern_regex("app/**/*.price.json").fullmatch("app/rate.price.json"))
        self.assertTrue(oa.pattern_regex("a/**/b").fullmatch("a/b"))

    def test_directory_pattern_does_not_match_a_sibling_prefix(self):
        self.assertFalse(oa.pattern_regex("app/").fullmatch("application.ts"))
        self.assertFalse(oa.pattern_regex("app/").fullmatch("app"))

    def test_unknown_seat_is_refused(self):
        with self.assertRaises(oa.TableError):
            oa.parse_table(TABLE.replace("| Engines | Engines |", "| Engine | Engines |"))

    def test_missing_default_seats_or_signers_is_refused(self):
        for broken in (
            TABLE.replace("| (any other path) | Platform | Default owner |\n", ""),
            TABLE.replace("## Seats", "## People"),
            TABLE.replace("## Signers", "## Writers"),
            TABLE.replace("| (the Signers list) | Chief of staff, Engines | Who may sign |\n", ""),
            TABLE + "| (the Signers list) | Chief of staff | A second Signers row |\n",
            TABLE + "| (any other path) | Engines | A second default |\n",
            TABLE + "\n## Signers\n\nsomeone-else\n",
            TABLE.replace("## Seats", "## Seats\n\nPlatform.\n\n## Seats"),
        ):
            with self.assertRaises(oa.TableError):
                oa.parse_table(broken)

    def test_a_marker_inside_a_path_cell_is_a_path_row(self):
        t = oa.parse_table(TABLE.replace("| `docs/*.md` | Platform |", "| `docs/*.md` (any other path) | Platform |"))
        self.assertEqual(t.default, ["Platform"])
        self.assertIn("docs/*.md", [p for p, _ in t.patterns()])

    def test_only_whole_lines_count(self):
        texts = [
            "Platform agreed at abc1234",
            "  Engines agreed at 0123456789abcdef.",
            "- Map agreed at 1111111",  # a to-do item
            "Platform agreed at 2222222? Not yet",  # a question
            "> Revenue and legal agreed at 3333333",  # a quote
            "Revenue and legal agreed at 4444444: the money change",  # trailing words
            "<!-- Chief of staff agreed at 5555555 -->",
            "```\nChief of staff agreed at 6666666\n```",
            "Nobody agreed at 7777777",  # not a seat
            "Chief of staff agreed at ZZZZZZZ",  # not a commit
            "    Map agreed at 8888888",  # an indented code block
            "<pre>\nMap agreed at 9999999\n</pre>",
            "<!-- an unclosed comment\nMap agreed at 1212121",
        ]
        lines = oa.agreement_lines(texts, self.t.seats + ["Map"])
        self.assertEqual(lines, {"Platform": ["abc1234"], "Engines": ["0123456789abcdef"]})
        mention = oa.agreement_lines(["Lines in `<pre>` do not count.\nPlatform agreed at abc1234"], self.t.seats)
        self.assertEqual(mention, {"Platform": ["abc1234"]})

    def test_seats_in_changed_rows(self):
        diff = "-| `app/` | Platform | The app |\n+| `app/` | Platform, Engines | The app |\n | `engine/` | Engines | x |\n"
        self.assertEqual(oa.seats_in_changed_rows(diff, self.t.seats), {"Platform", "Engines"})


class RepoCase(unittest.TestCase):
    """A real repository: main with the table, and a branch."""

    def setUp(self):
        oa.diff_hash.cache_clear()
        self.dir = tempfile.TemporaryDirectory()
        self.cwd = os.getcwd()
        os.chdir(self.dir.name)
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "t@example.com")
        self.git("config", "user.name", "t")
        self.write("OWNERS.md", TABLE)
        self.write("app/main.ts", "a\n")
        self.write("app/billing.ts", "b\n")
        self.write("engine/run.py", "def run(items):\n    for item in items:\n        save(item)\n    return items\n")
        self.commit("base")
        self.git("checkout", "-q", "-b", "pr")

    def tearDown(self):
        os.chdir(self.cwd)
        self.dir.cleanup()

    def git(self, *args):
        return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout.strip()

    def write(self, path, text):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w") as f:
            f.write(text)

    def commit(self, msg):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", msg)
        return self.git("rev-parse", "HEAD")

    def verdict(self, items, base="main"):
        head = self.git("rev-parse", "HEAD")
        text, diff = oa.table_at(base, head)
        return oa.check(base, head, items, text, diff)


class RepoTest(RepoCase):
    """Lines at different commits."""

    def test_every_owner_of_a_shared_file_must_agree(self):
        self.write("app/billing.ts", "b2\n")
        head = self.commit("price")
        v = self.verdict(signed(f"Platform agreed at {head[:8]}"))
        self.assertEqual(sorted(v.required), ["Platform", "Revenue and legal"])
        self.assertEqual(v.missing, ["Revenue and legal"])
        v = self.verdict(signed(f"Platform agreed at {head[:8]}", f"Revenue and legal agreed at {head}"))
        self.assertEqual(v.missing, [])

    def test_lines_by_someone_not_a_signer_do_not_count(self):
        self.write("app/main.ts", "a2\n")
        head = self.commit("app")
        self.assertEqual(self.verdict([("someone-else", f"Platform agreed at {head[:8]}")]).missing, ["Platform"])

    def test_a_line_holds_when_the_seat_paths_are_unchanged(self):
        self.write("app/billing.ts", "b2\n")
        first = self.commit("price")
        self.write("engine/run.py", "c2\n")
        self.commit("engine change after the money line")
        v = self.verdict(signed(f"Revenue and legal agreed at {first[:8]}"))
        self.assertIn("Revenue and legal", v.agreed)
        self.assertEqual(v.missing, ["Engines", "Platform"])

    def test_a_line_goes_stale_when_the_seat_paths_change(self):
        self.write("app/billing.ts", "b2\n")
        first = self.commit("price")
        self.write("app/billing.ts", "b3\n")
        self.commit("price again")
        v = self.verdict(signed(f"Revenue and legal agreed at {first[:8]}"))
        self.assertNotIn("Revenue and legal", v.agreed)
        self.assertEqual(v.stale["Revenue and legal"], [first[:8]])

    def test_a_whitespace_change_makes_a_line_stale(self):
        self.write("engine/clean.sh", "rm -rf /tmp/build\n")
        first = self.commit("clean")
        self.write("engine/clean.sh", "rm -rf / tmp/build\n")
        self.commit("one space")
        self.assertEqual(self.verdict(signed(f"Engines agreed at {first[:8]}")).missing, ["Engines"])

    def test_a_line_holds_across_a_merge_of_main(self):
        self.write("app/billing.ts", "b2\n")
        first = self.commit("price")
        self.git("checkout", "-q", "main")
        self.write("engine/run.py", "main moved\n")
        self.commit("main moves")
        self.git("checkout", "-q", "pr")
        self.git("merge", "-q", "--no-edit", "main")
        v = self.verdict(signed(f"Revenue and legal agreed at {first[:8]}", f"Platform agreed at {first[:8]}"))
        self.assertEqual(v.missing, [])
        self.assertNotIn("Engines", v.required)

    def test_an_unknown_commit_is_stale(self):
        self.write("engine/run.py", "c2\n")
        self.commit("engine")
        v = self.verdict(signed("Engines agreed at deadbeef"))
        self.assertEqual(v.missing, ["Engines"])
        self.assertEqual(v.stale["Engines"], ["deadbeef"])

    def test_changing_the_table_needs_every_seat_in_a_changed_row(self):
        new = TABLE.replace("| `engine/` | Engines | Engines |", "| `engine/` | Engines, Revenue and legal | Engines |")
        self.write("OWNERS.md", new)
        head = self.commit("table")
        v = self.verdict([])
        self.assertEqual(sorted(v.required), ["Chief of staff", "Engines", "Revenue and legal"])
        items = signed(*(f"{s} agreed at {head[:8]}" for s in ("Chief of staff", "Engines", "Revenue and legal")))
        self.assertEqual(self.verdict(items).missing, [])

    def test_a_new_signer_needs_the_signers_row(self):
        self.write("OWNERS.md", TABLE.replace(f"\n{SIGNER}\n", f"\n{SIGNER}, newcomer\n"))
        head = self.commit("signer")
        self.assertEqual(sorted(self.verdict([]).required), ["Chief of staff", "Engines"])
        self.assertEqual(self.verdict(signed(f"Chief of staff agreed at {head[:8]}")).missing, ["Engines"])

    def test_a_new_signer_does_not_count_in_its_own_change(self):
        self.write("OWNERS.md", TABLE.replace(f"\n{SIGNER}\n", f"\n{SIGNER}, newcomer\n"))
        head = self.commit("signer")
        items = [("newcomer", f"Chief of staff agreed at {head[:8]}\nEngines agreed at {head[:8]}")]
        self.assertEqual(self.verdict(items).missing, ["Chief of staff", "Engines"])

    def test_a_table_edit_outside_the_signers_needs_only_the_chief_of_staff(self):
        self.write("OWNERS.md", TABLE + "\nA note.\n")
        self.commit("note")
        self.assertEqual(sorted(self.verdict([]).required), ["Chief of staff"])

    def test_no_owned_change_needs_nothing(self):
        self.git("commit", "-q", "--allow-empty", "-m", "empty")
        v = self.verdict([])
        self.assertEqual(v.required, {})
        self.assertEqual(v.missing, [])

    def test_a_non_ascii_path_has_its_owner(self):
        self.write("engine/stagé.py", "x\n")
        head = self.commit("accent")
        v = self.verdict([])
        self.assertEqual(v.required, {"Engines": ["engine/stagé.py"]})
        self.write("engine/stagé.py", "y\n")
        self.commit("accent again")
        self.assertEqual(self.verdict(signed(f"Engines agreed at {head[:8]}")).missing, ["Engines"])

    def test_a_file_named_like_a_pathspec_is_only_a_file(self):
        self.write(":!app", "x\n")
        self.write("app/main.ts", "a2\n")
        first = self.commit("odd name")
        self.write("app/main.ts", "a3\n")
        self.commit("app again")
        self.assertIn("Platform", self.verdict(signed(f"Platform agreed at {first[:8]}")).missing)


class BrokenTableTest(RepoCase):
    BROKEN = TABLE + "| (the Signers list) | Chief of staff | A second Signers row |\n"

    def judge(self, base="main", items=()):
        head = self.git("rev-parse", "HEAD")
        return oa.judge(base, head, list(items), "#1", "on the pull request")

    def test_a_change_that_breaks_the_table_is_refused(self):
        self.write("OWNERS.md", self.BROKEN)
        head = self.commit("second signers row")
        code, text, _ = self.judge(items=signed(f"Chief of staff agreed at {head[:8]}"))
        self.assertEqual(code, oa.EXIT_TABLE)
        self.assertIn("leaves OWNERS.md unreadable", text)

    def test_after_a_broken_table_reaches_main_a_fix_can_ship(self):
        self.git("checkout", "-q", "main")
        self.write("OWNERS.md", self.BROKEN)
        self.commit("broken table lands")
        self.git("checkout", "-q", "-B", "fix", "main")
        self.write("OWNERS.md", TABLE)
        head = self.commit("fix the table")
        code, text, v = self.judge()
        self.assertEqual(code, oa.EXIT_MISSING)
        self.assertIn("Judged by the table at", text)
        self.assertEqual(v.missing, ["Chief of staff", "Engines"])
        items = signed(f"Chief of staff agreed at {head[:8]}", f"Engines agreed at {head[:8]}")
        self.assertEqual(self.judge(items=items)[0], 0)

    def test_a_duplicate_signers_section_on_main_can_be_fixed(self):
        self.git("checkout", "-q", "main")
        self.write("OWNERS.md", TABLE + f"\n## Signers\n\n{SIGNER}\n")
        self.commit("duplicate signers section lands")
        self.git("checkout", "-q", "-B", "fix", "main")
        self.write("OWNERS.md", TABLE)
        head = self.commit("fix the table")
        code, _, v = self.judge()
        self.assertEqual(code, oa.EXIT_MISSING)
        self.assertEqual(v.missing, ["Chief of staff", "Engines"])
        items = signed(f"Chief of staff agreed at {head[:8]}", f"Engines agreed at {head[:8]}")
        self.assertEqual(self.judge(items=items)[0], 0)

    def test_after_a_broken_table_any_change_needs_the_table_seats(self):
        self.git("checkout", "-q", "main")
        self.write("OWNERS.md", self.BROKEN)
        self.commit("broken table lands")
        self.git("checkout", "-q", "-B", "other", "main")
        self.write("app/main.ts", "a2\n")
        head = self.commit("app change")
        _, _, v = self.judge(items=signed(f"Platform agreed at {head[:8]}"))
        self.assertEqual(v.missing, ["Chief of staff", "Engines"])


class RevertTest(RepoCase):
    def land(self, path, text, msg):
        self.git("checkout", "-q", "main")
        self.write(path, text)
        sha = self.commit(msg)
        self.git("checkout", "-q", "-B", "pr", "main")
        return sha

    def test_a_pure_revert_needs_no_line(self):
        bad = self.land("app/main.ts", "broken\n", "break")
        self.git("revert", "--no-edit", bad)
        v = self.verdict([])
        self.assertEqual(v.revert_of, bad)
        self.assertEqual(v.missing, [])

    def test_a_reindented_line_is_not_a_revert(self):
        removed = self.land("engine/run.py", "def run(items):\n    for item in items:\n        pass\n    return items\n", "drop save")
        self.write("engine/run.py", "def run(items):\n    for item in items:\n        pass\n    save(item)\n    return items\n")
        self.commit("save once, after the loop")
        self.assertEqual(self.verdict([]).revert_of, "")
        self.assertEqual(self.verdict([]).missing, ["Engines"])
        self.assertTrue(removed)

    def test_the_same_lines_at_another_place_are_not_a_revert(self):
        block = "a\nb\nc\n{x}d\ne\nf\n"
        filler = "".join(f"line {i}\n" for i in range(10))
        self.git("checkout", "-q", "main")
        self.write("engine/job.yml", block.format(x="check\n") + filler + block.format(x=""))
        self.commit("two jobs")
        self.land("engine/job.yml", block.format(x="") + filler + block.format(x=""), "drop the check from job a")
        self.write("engine/job.yml", block.format(x="") + filler + block.format(x="check\n"))
        self.commit("add the check to job b")
        self.assertEqual(self.verdict([]).revert_of, "")
        self.assertEqual(self.verdict([]).missing, ["Engines"])

    def test_a_revert_of_a_table_change_needs_its_lines(self):
        change = self.land("OWNERS.md", TABLE.replace("| Engines | Engines |", "| Engines, Revenue and legal | Engines |"), "row")
        self.git("revert", "--no-edit", change)
        v = self.verdict([])
        self.assertEqual(v.revert_of, "")
        self.assertIn("Chief of staff", v.missing)

    def test_reverting_a_revert_needs_lines(self):
        bad = self.land("engine/run.py", "x\n", "change")
        self.git("checkout", "-q", "main")
        self.git("revert", "--no-edit", bad)
        self.git("checkout", "-q", "-B", "pr", "main")
        self.git("revert", "--no-edit", "HEAD")
        self.assertEqual(self.verdict([]).missing, ["Engines"])


class DeployTest(RepoCase):
    """The deploy step: commits on main, each judged by the pull request merged as it."""

    RUNS = "repos/r/actions/workflows/deploy.yml/runs"

    def setUp(self):
        super().setUp()
        self.api, self.lists = {}, {}
        self.saved = (oa.gh_json, oa.gh_list, oa.fetch)
        oa.gh_json = lambda path: self.api[path]
        oa.gh_list = lambda path: self.lists.get(path, [])
        oa.fetch = lambda *a, **k: None

    def tearDown(self):
        oa.gh_json, oa.gh_list, oa.fetch = self.saved
        super().tearDown()

    def squash(self, number, body, login=SIGNER, path="engine/run.py"):
        """A pull request changing one file, squash-merged onto main."""
        self.git("checkout", "-q", "-B", f"pr{number}", "main")
        self.write(path, f"change {number}\n")
        head = self.commit(f"pr {number}")
        self.git("checkout", "-q", "main")
        self.write(path, f"change {number}\n")
        merged = self.commit(f"squash {number}")
        self.api[f"repos/r/commits/{merged}/pulls"] = [{"number": number, "merge_commit_sha": merged}]
        self.api[f"repos/r/pulls/{number}"] = {"number": number, "head": {"sha": head}, "user": {"login": login}, "body": body.format(head=head[:8])}
        return merged

    def push(self, path, text):
        self.git("checkout", "-q", "main")
        self.write(path, text)
        sha = self.commit("direct")
        self.api[f"repos/r/commits/{sha}/pulls"] = []
        return sha

    def deployed(self, workflow="deploy.yml"):
        with contextlib.redirect_stdout(io.StringIO()):
            return oa.deployed("r", "HEAD", workflow, "origin", [])

    def checked(self, sha, run_id=7, conclusion="success"):
        self.lists[self.RUNS] = [{"id": run_id, "head_sha": sha}]
        self.api[f"repos/r/actions/runs/{run_id}/jobs"] = {"jobs": [{"steps": [{"name": oa.CONTEXT, "conclusion": conclusion}]}]}

    def test_a_merged_pull_request_with_its_lines_deploys(self):
        self.squash(1, "Engines agreed at {head}")
        self.assertEqual(self.deployed(), 0)

    def test_a_missing_line_refuses_the_deploy(self):
        self.squash(1, "Platform agreed at {head}")
        self.assertEqual(self.deployed(), oa.EXIT_MISSING)

    def test_lines_from_a_non_signer_do_not_count(self):
        self.squash(1, "Engines agreed at {head}", login="outsider")
        self.assertEqual(self.deployed(), oa.EXIT_MISSING)

    def test_a_direct_push_needs_lines_on_the_commit(self):
        sha = self.push("app/main.ts", "pushed\n")
        self.assertEqual(self.deployed(), oa.EXIT_MISSING)
        self.lists[f"repos/r/commits/{sha}/comments"] = [{"user": {"login": SIGNER}, "body": f"Platform agreed at {sha[:8]}"}]
        self.assertEqual(self.deployed(), 0)

    def test_every_commit_since_the_last_checked_deploy_is_judged(self):
        self.checked(self.squash(1, "Engines agreed at {head}"))
        self.squash(2, "Platform agreed at {head}")  # never deployed alone, and Engines did not agree
        self.squash(3, "Engines agreed at {head}")
        self.assertEqual(self.deployed(), oa.EXIT_MISSING)

    def test_with_no_checked_deploy_every_commit_since_the_table_is_judged(self):
        self.squash(1, "Engines agreed at {head}")
        skipped = self.squash(2, "Platform agreed at {head}")
        self.checked(skipped, conclusion="skipped")
        self.squash(3, "Engines agreed at {head}")
        self.assertEqual(self.deployed(), oa.EXIT_MISSING)
        self.assertEqual(self.deployed(workflow=None), oa.EXIT_MISSING)

    def test_commits_before_the_table_need_nothing(self):
        self.git("checkout", "-q", "--orphan", "fresh")
        self.git("rm", "-q", "-rf", ".")
        self.write("x.txt", "x\n")
        self.commit("root")
        self.write("x.txt", "y\n")
        self.commit("second")
        self.assertEqual(self.deployed(), 0)

    def test_a_pure_revert_ships_without_lines(self):
        self.checked(self.squash(1, "Engines agreed at {head}"))
        self.git("revert", "--no-edit", "HEAD")
        self.api[f"repos/r/commits/{self.git('rev-parse', 'HEAD')}/pulls"] = []
        self.assertEqual(self.deployed(), 0)

    def test_a_revert_with_anything_else_in_it_needs_lines(self):
        self.checked(self.squash(1, "Engines agreed at {head}"))
        self.git("revert", "--no-commit", "HEAD")
        self.write("app/main.ts", "and one more thing\n")
        pushed = self.commit("revert plus a change")
        self.api[f"repos/r/commits/{pushed}/pulls"] = []
        self.assertEqual(self.deployed(), oa.EXIT_MISSING)

    def test_a_partial_revert_needs_lines(self):
        self.git("checkout", "-q", "main")
        self.write("engine/run.py", "c2\n")
        self.write("app/main.ts", "a2\n")
        both = self.commit("two files")
        self.api[f"repos/r/commits/{both}/comments"] = []
        self.lists[f"repos/r/commits/{both}/comments"] = [{"user": {"login": SIGNER}, "body": f"Engines agreed at {both}\nPlatform agreed at {both}"}]
        self.api[f"repos/r/commits/{both}/pulls"] = []
        self.checked(both)
        self.push("engine/run.py", "def run(items):\n    for item in items:\n        save(item)\n    return items\n")
        self.assertEqual(self.deployed(), oa.EXIT_MISSING)

    def test_a_direct_push_that_reverts_the_table_is_refused(self):
        self.git("checkout", "-q", "main")
        self.write("OWNERS.md", TABLE.replace("| Engines | Engines |", "| Engines, Revenue and legal | Engines |"))
        row = self.commit("row")
        self.lists[f"repos/r/commits/{row}/comments"] = [{"user": {"login": SIGNER}, "body": "\n".join(f"{s} agreed at {row}" for s in ("Chief of staff", "Engines", "Revenue and legal"))}]
        self.api[f"repos/r/commits/{row}/pulls"] = []
        self.checked(row)
        self.git("revert", "--no-edit", "HEAD")
        self.api[f"repos/r/commits/{self.git('rev-parse', 'HEAD')}/pulls"] = []
        self.assertEqual(self.deployed(), oa.EXIT_MISSING)

    def test_a_broken_table_on_main_does_not_stop_the_deploys(self):
        self.checked(self.squash(1, "Engines agreed at {head}"))
        broken = self.push("OWNERS.md", BrokenTableTest.BROKEN)
        self.lists[f"repos/r/commits/{broken}/comments"] = [{"user": {"login": SIGNER}, "body": f"Chief of staff agreed at {broken[:8]}"}]
        self.assertEqual(self.deployed(), oa.EXIT_MISSING)  # Engines, of the Signers row, has not agreed
        self.lists[f"repos/r/commits/{broken}/comments"].append({"user": {"login": SIGNER}, "body": f"Engines agreed at {broken[:8]}"})
        fix = self.push("OWNERS.md", TABLE)
        self.lists[f"repos/r/commits/{fix}/comments"] = [{"user": {"login": SIGNER}, "body": f"Chief of staff agreed at {fix[:8]}\nEngines agreed at {fix[:8]}"}]
        self.assertEqual(self.deployed(), 0)

    def test_the_check_runs_as_of_the_last_trusted_commit(self):
        self.git("checkout", "-q", "main")
        self.write(oa.SCRIPT, "old check\n")
        trusted = self.commit("check v1")
        self.write(oa.SCRIPT, "weakened check\n")
        target = self.commit("check v2")
        self.assertEqual(oa.trusted_script(trusted, target), "old check\n")
        self.write("app/main.ts", "unrelated\n")
        later = self.commit("unrelated")
        self.assertIsNone(oa.trusted_script(target, later))

    def test_a_moved_check_has_no_trusted_copy(self):
        self.git("checkout", "-q", "main")
        self.write(oa.SCRIPT, "check v1\n")
        trusted = self.commit("check v1")
        self.write(".github/scripts/moved.py", "weakened\n")
        self.git("rm", "-q", oa.SCRIPT)
        target = self.commit("move the check")
        saved, oa.SCRIPT = oa.SCRIPT, ".github/scripts/moved.py"  # the moved copy's own constant
        try:
            with self.assertRaises(oa.Untrusted):
                oa.trusted_script(trusted, target)
        finally:
            oa.SCRIPT = saved

    def test_any_change_under_github_defers_to_the_trusted_check(self):
        self.git("checkout", "-q", "main")
        self.write(oa.SCRIPT, "check v1\n")
        trusted = self.commit("check v1")
        self.write(".github/workflows/deploy.yml", "steps: []\n")
        target = self.commit("workflow edit")
        self.assertEqual(oa.trusted_script(trusted, target), "check v1\n")


class LintTest(RepoCase):
    def lint(self, base=None):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = oa.lint(base)
        return code, out.getvalue()

    def test_a_new_pattern_that_matches_nothing_fails(self):
        self.write("OWNERS.md", TABLE.replace("| `engine/` |", "| `engine/`, `enigne/x.py` |"))
        code, out = self.lint("main")
        self.assertEqual(code, oa.EXIT_TABLE)
        self.assertIn("enigne/x.py", out)

    def test_an_old_pattern_whose_files_left_only_warns(self):
        self.write("OWNERS.md", TABLE.replace("| `engine/` |", "| `engine/`, `engine/gone.py` |"))
        self.write("engine/gone.py", "x\n")
        self.commit("named file")
        self.git("checkout", "-q", "-B", "main")
        os.remove("engine/gone.py")
        self.commit("delete it")
        code, out = self.lint("HEAD^1")
        self.assertEqual(code, 0)
        self.assertIn("::warning::", out)

    def test_an_unreadable_table_fails(self):
        self.write("OWNERS.md", TABLE.replace("## Signers", "## Writers"))
        self.assertEqual(self.lint("main")[0], oa.EXIT_TABLE)


if __name__ == "__main__":
    unittest.main()
