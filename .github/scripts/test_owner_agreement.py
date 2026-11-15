"""Tests for owner_agreement.py: the table, the owners of a path, and when a line holds.

    python3 -m unittest discover -s .github/scripts -p 'test_owner_agreement.py'
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import owner_agreement as oa  # noqa: E402

TABLE = """# Path owners

## Seats

Chief of staff, Platform, Engines, Revenue and legal.

## Table

| Paths | Seats | What |
| --- | --- | --- |
| `OWNERS.md` | Chief of staff | The table |
| `app/` | Platform | The app |
| `app/billing.ts`, `app/**/*.price.json` | Revenue and legal | Money |
| `engine/` | Engines | Engines |
| `docs/*.md` | Platform | Docs, one level |
| (any other path) | Platform | Default owner |
"""


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
        self.assertEqual(self.t.owners("docs/a.md"), {"Platform"})
        self.assertEqual(self.t.owners("docs/sub/a.md"), {"Platform"})  # default, same seat
        self.assertFalse(oa.pattern_regex("docs/*.md").fullmatch("docs/sub/a.md"))
        self.assertTrue(oa.pattern_regex("app/**/*.price.json").fullmatch("app/a/b/c.price.json"))

    def test_directory_pattern_does_not_match_a_sibling_prefix(self):
        self.assertFalse(oa.pattern_regex("app/").fullmatch("application.ts"))
        self.assertFalse(oa.pattern_regex("app/").fullmatch("app"))

    def test_unknown_seat_is_refused(self):
        with self.assertRaises(oa.TableError):
            oa.parse_table(TABLE.replace("| Engines | Engines |", "| Engine | Engines |"))

    def test_missing_default_or_seats_is_refused(self):
        with self.assertRaises(oa.TableError):
            oa.parse_table(TABLE.replace("| (any other path) | Platform | Default owner |\n", ""))
        with self.assertRaises(oa.TableError):
            oa.parse_table(TABLE.replace("## Seats", "## People"))

    def test_lines(self):
        texts = [
            "Platform agreed at abc1234",
            "- Engines agreed at 0123456789abcdef: read the provisioning change",
            "> Revenue and legal agreed at 1111111",  # a quote is not a line
            "Nobody agreed at 2222222",  # not a seat
            "Chief of staff agreed at ZZZZZZZ",  # not a commit
        ]
        lines = oa.agreement_lines(texts, self.t.seats)
        self.assertEqual(lines, {"Platform": ["abc1234"], "Engines": ["0123456789abcdef"]})

    def test_a_pattern_that_matches_no_file_is_reported(self):
        files = ["app/main.ts", "app/billing.ts", "engine/run.py", "docs/a.md", "OWNERS.md"]
        self.assertEqual(oa.unmatched_patterns(self.t, files), ["app/**/*.price.json"])
        self.assertEqual(oa.unmatched_patterns(self.t, files + ["app/x/rate.price.json"]), [])

    def test_seats_in_changed_rows(self):
        diff = "-| `app/` | Platform | The app |\n+| `app/` | Platform, Engines | The app |\n | `engine/` | Engines | x |\n"
        self.assertEqual(oa.seats_in_changed_rows(diff, self.t.seats), {"Platform", "Engines"})


class RepoCase(unittest.TestCase):
    """A real repository: main with the table, and a branch."""

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.cwd = os.getcwd()
        os.chdir(self.dir.name)
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "t@example.com")
        self.git("config", "user.name", "t")
        self.write("OWNERS.md", TABLE)
        self.write("app/main.ts", "a\n")
        self.write("app/billing.ts", "b\n")
        self.write("engine/run.py", "c\n")
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



class RepoTest(RepoCase):
    """Lines at different commits."""

    def verdict(self, texts, table_text=TABLE):
        head = self.git("rev-parse", "HEAD")
        mb = self.git("merge-base", "main", head)
        diff = self.git("diff", mb, head, "--", "OWNERS.md")
        return oa.check("main", head, texts, table_text, diff)

    def test_every_owner_of_a_shared_file_must_agree(self):
        self.write("app/billing.ts", "b2\n")
        head = self.commit("price")
        v = self.verdict([f"Platform agreed at {head[:8]}"])
        self.assertEqual(sorted(v.required), ["Platform", "Revenue and legal"])
        self.assertEqual(v.missing, ["Revenue and legal"])
        v = self.verdict([f"Platform agreed at {head[:8]}", f"Revenue and legal agreed at {head}"])
        self.assertEqual(v.missing, [])

    def test_a_line_holds_when_the_seat_paths_are_unchanged(self):
        self.write("app/billing.ts", "b2\n")
        first = self.commit("price")
        self.write("engine/run.py", "c2\n")
        self.commit("engine change after the money line")
        v = self.verdict([f"Revenue and legal agreed at {first[:8]}"])
        self.assertIn("Revenue and legal", v.agreed)
        self.assertEqual(v.missing, ["Engines", "Platform"])

    def test_a_line_goes_stale_when_the_seat_paths_change(self):
        self.write("app/billing.ts", "b2\n")
        first = self.commit("price")
        self.write("app/billing.ts", "b3\n")
        self.commit("price again")
        v = self.verdict([f"Revenue and legal agreed at {first[:8]}"])
        self.assertNotIn("Revenue and legal", v.agreed)
        self.assertEqual(v.stale["Revenue and legal"], [first[:8]])

    def test_a_line_holds_across_a_merge_of_main(self):
        self.write("app/billing.ts", "b2\n")
        first = self.commit("price")
        self.git("checkout", "-q", "main")
        self.write("engine/run.py", "main moved\n")
        self.commit("main moves")
        self.git("checkout", "-q", "pr")
        self.git("merge", "-q", "--no-edit", "main")
        v = self.verdict([f"Revenue and legal agreed at {first[:8]}", f"Platform agreed at {first[:8]}"])
        self.assertEqual(v.missing, [])
        self.assertNotIn("Engines", v.required)  # main's own change needs no line here

    def test_an_unknown_commit_is_stale(self):
        self.write("engine/run.py", "c2\n")
        self.commit("engine")
        v = self.verdict(["Engines agreed at deadbeef"])
        self.assertEqual(v.missing, ["Engines"])
        self.assertEqual(v.stale["Engines"], ["deadbeef"])

    def test_changing_the_table_needs_every_seat_in_a_changed_row(self):
        new = TABLE.replace("| `engine/` | Engines | Engines |", "| `engine/` | Engines, Revenue and legal | Engines |")
        self.write("OWNERS.md", new)
        head = self.commit("table")
        v = self.verdict([])
        self.assertEqual(sorted(v.required), ["Chief of staff", "Engines", "Revenue and legal"])
        texts = [f"{s} agreed at {head[:8]}" for s in ("Chief of staff", "Engines", "Revenue and legal")]
        self.assertEqual(self.verdict(texts).missing, [])

    def test_no_owned_change_needs_nothing(self):
        self.git("commit", "-q", "--allow-empty", "-m", "empty")
        v = self.verdict([])
        self.assertEqual(v.required, {})
        self.assertEqual(v.missing, [])


class DeployTest(RepoCase):
    """The deploy step: commits on main, each judged by the pull request merged as it."""

    def setUp(self):
        super().setUp()
        self.api, self.saved = {}, (oa.gh_json, oa.gh_list, oa.fetch_pr)
        oa.gh_json = lambda path: self.api[path]
        oa.gh_list = lambda path: []
        oa.fetch_pr = lambda *a, **k: None
        self.api["repos/r/actions/workflows/deploy.yml/runs?per_page=30"] = {"workflow_runs": []}

    def tearDown(self):
        oa.gh_json, oa.gh_list, oa.fetch_pr = self.saved
        super().tearDown()

    def squash(self, number, body, association="MEMBER"):
        """A pull request changing engine/run.py, squash-merged onto main."""
        self.git("checkout", "-q", "-B", f"pr{number}", "main")
        self.write("engine/run.py", f"change {number}\n")
        head = self.commit(f"pr {number}")
        self.git("checkout", "-q", "main")
        self.write("engine/run.py", f"change {number}\n")
        merged = self.commit(f"squash {number}")
        self.api[f"repos/r/commits/{merged}/pulls"] = [{"number": number, "merge_commit_sha": merged}]
        self.api[f"repos/r/pulls/{number}"] = {"number": number, "head": {"sha": head}, "body": body.format(head=head[:8]), "author_association": association}
        return merged

    def test_a_merged_pull_request_with_its_lines_deploys(self):
        self.squash(1, "Engines agreed at {head}")
        self.assertEqual(oa.deployed("r", "HEAD", "deploy.yml", "origin"), 0)

    def test_lines_from_outside_the_repository_do_not_count(self):
        self.squash(1, "Engines agreed at {head}", association="CONTRIBUTOR")
        self.assertEqual(oa.deployed("r", "HEAD", "deploy.yml", "origin"), oa.EXIT_MISSING)
        merged = self.git("rev-parse", "HEAD")
        head = self.api["repos/r/pulls/1"]["head"]["sha"]
        oa.gh_list = lambda path: [{"body": f"Engines agreed at {head[:8]}", "author_association": "NONE"}]
        self.assertEqual(oa.deployed("r", merged, "deploy.yml", "origin"), oa.EXIT_MISSING)
        oa.gh_list = lambda path: [{"body": f"Engines agreed at {head[:8]}", "author_association": "MEMBER"}]
        self.assertEqual(oa.deployed("r", merged, "deploy.yml", "origin"), 0)

    def test_a_missing_line_refuses_the_deploy(self):
        self.squash(1, "Platform agreed at {head}")
        self.assertEqual(oa.deployed("r", "HEAD", "deploy.yml", "origin"), oa.EXIT_MISSING)

    def test_a_direct_push_refuses_the_deploy(self):
        self.git("checkout", "-q", "main")
        self.write("app/main.ts", "pushed\n")
        pushed = self.commit("direct")
        self.api[f"repos/r/commits/{pushed}/pulls"] = []
        self.assertEqual(oa.deployed("r", "HEAD", "deploy.yml", "origin"), oa.EXIT_MISSING)

    def test_every_commit_since_the_last_checked_deploy_is_judged(self):
        checked = self.squash(1, "Engines agreed at {head}")
        self.api["repos/r/actions/workflows/deploy.yml/runs?per_page=30"] = {"workflow_runs": [{"id": 7, "head_sha": checked}]}
        self.api["repos/r/actions/runs/7/jobs"] = {"jobs": [{"steps": [{"name": oa.CONTEXT, "conclusion": "success"}]}]}
        self.squash(2, "Platform agreed at {head}")  # never deployed alone, and Engines did not agree
        self.squash(3, "Engines agreed at {head}")
        self.assertEqual(oa.deployed("r", "HEAD", "deploy.yml", "origin"), oa.EXIT_MISSING)

    def test_a_run_that_skipped_the_step_does_not_count(self):
        self.squash(1, "Engines agreed at {head}")
        skipped = self.squash(2, "Platform agreed at {head}")
        self.api["repos/r/actions/workflows/deploy.yml/runs?per_page=30"] = {"workflow_runs": [{"id": 8, "head_sha": skipped}]}
        self.api["repos/r/actions/runs/8/jobs"] = {"jobs": [{"steps": [{"name": oa.CONTEXT, "conclusion": "skipped"}]}]}
        self.squash(3, "Engines agreed at {head}")
        # No checked deploy is found, so only the tip is judged, and it passes.
        self.assertEqual(oa.deployed("r", "HEAD", "deploy.yml", "origin"), 0)

    def test_a_pure_revert_ships_without_lines(self):
        self.squash(1, "Engines agreed at {head}")
        self.git("revert", "--no-edit", "HEAD")
        pushed = self.git("rev-parse", "HEAD")
        self.api[f"repos/r/commits/{pushed}/pulls"] = []
        self.assertEqual(oa.deployed("r", "HEAD", "deploy.yml", "origin"), 0)

    def test_a_revert_with_anything_else_in_it_needs_lines(self):
        self.squash(1, "Engines agreed at {head}")
        self.git("revert", "--no-commit", "HEAD")
        self.write("app/main.ts", "and one more thing\n")
        pushed = self.commit("revert plus a change")
        self.api[f"repos/r/commits/{pushed}/pulls"] = []
        self.assertEqual(oa.deployed("r", "HEAD", "deploy.yml", "origin"), oa.EXIT_MISSING)

    def test_reverting_a_revert_needs_lines(self):
        self.git("checkout", "-q", "main")
        self.write("engine/run.py", "pushed without a line\n")
        self.commit("direct")
        self.git("revert", "--no-edit", "HEAD")
        self.git("revert", "--no-edit", "HEAD")
        pushed = self.git("rev-parse", "HEAD")
        self.api[f"repos/r/commits/{pushed}/pulls"] = []
        self.assertEqual(oa.deployed("r", "HEAD", None, "origin"), oa.EXIT_MISSING)

    def test_a_partial_revert_needs_lines(self):
        self.git("checkout", "-q", "main")
        self.write("engine/run.py", "c2\n")
        self.write("app/main.ts", "a2\n")
        self.commit("two files")
        self.write("engine/run.py", "c\n")
        pushed = self.commit("undo one of them")
        self.api[f"repos/r/commits/{pushed}/pulls"] = []
        self.assertEqual(oa.deployed("r", "HEAD", None, "origin"), oa.EXIT_MISSING)

    def test_commits_before_the_table_need_nothing(self):
        self.git("checkout", "-q", "--orphan", "fresh")
        self.git("rm", "-q", "-rf", ".")
        self.write("x.txt", "x\n")
        self.commit("root")
        self.write("x.txt", "y\n")
        self.commit("second")
        self.assertEqual(oa.deployed("r", "HEAD", None, "origin"), 0)


if __name__ == "__main__":
    unittest.main()
