#!/usr/bin/env python3
"""The owner-agreement check (part 9 of the working agreement between seats).

Every seat that owns a path a pull request changes must post one line on the pull
request, in its body or a comment:

    <Seat> agreed at <head commit>

The path table is OWNERS.md at the repository root, read from the base branch, so a
pull request cannot change the rules it is checked by. A line holds while the diff of
that seat's paths against the base is unchanged, so a later push that leaves the
seat's paths alone keeps the line, and one that touches them needs a new line.

All seats act as one GitHub user, so GitHub's own approvals cannot carry this. The
check stops a seat from forgetting. It cannot stop a forged line.

Standard library only. Needs git, and gh for the pull request's text.

    owner_agreement.py --pr 123                  # local merge gate
    owner_agreement.py --pr 123 --post-status    # CI: also posts the owner-agreement commit status

Exit 0 when every owning seat agreed, 3 when one is missing, 2 when OWNERS.md cannot be
read, and anything else when the check itself broke.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field

TABLE = "OWNERS.md"
CONTEXT = "owner-agreement"
EXIT_MISSING = 3
EXIT_TABLE = 2
DEFAULT_MARK = "(any other path)"
# Only text written by people with write access counts. In a public repository anyone can
# open a pull request or comment, and their "<Seat> agreed at" line must not count.
TRUSTED = {"OWNER", "MEMBER", "COLLABORATOR"}
LINE = re.compile(r"^[\s\-*\"`]*(?P<seat>[A-Za-z][A-Za-z\- ]*?) agreed at (?P<sha>[0-9a-f]{7,40})\b")


class TableError(Exception):
    """OWNERS.md cannot be read as a table: the check refuses rather than guess."""


@dataclass
class Row:
    patterns: list[str]
    seats: list[str]
    regexes: list[re.Pattern] = field(default_factory=list)


@dataclass
class Table:
    seats: list[str]
    rows: list[Row]
    default: list[str]

    def owners(self, path: str) -> set[str]:
        """Every seat of every row that matches, or the default owner when none does."""
        found: set[str] = set()
        for row in self.rows:
            if any(rx.fullmatch(path) for rx in row.regexes):
                found.update(row.seats)
        return found or set(self.default)


def pattern_regex(pattern: str) -> re.Pattern:
    """`dir/` matches everything under dir, `*` one path segment, `**` any depth."""
    out, i = [], 0
    while i < len(pattern):
        if pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    if pattern.endswith("/"):
        out.append(".*")
    return re.compile("".join(out))


def split_seats(cell: str) -> list[str]:
    return [s.strip().rstrip(".") for s in cell.split(",") if s.strip()]


def parse_table(text: str) -> Table:
    seats: list[str] = []
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.strip() == "## Seats":
            for nxt in lines[i + 1 :]:
                if nxt.strip():
                    seats = split_seats(nxt)
                    break
            break
    if not seats:
        raise TableError("OWNERS.md has no '## Seats' list")
    rows: list[Row] = []
    default: list[str] = []
    for line in lines:
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2 or set(cells[0]) <= {"-", " ", ":"} or cells[0] == "Paths":
            continue
        row_seats = split_seats(cells[1])
        unknown = [s for s in row_seats if s not in seats]
        if unknown or not row_seats:
            raise TableError(f"row {cells[0]!r} names unknown seats {unknown or 'none'}")
        if DEFAULT_MARK in cells[0]:
            default = row_seats
            continue
        patterns = re.findall(r"`([^`]+)`", cells[0])
        if not patterns:
            raise TableError(f"row {cells[0]!r} has no `path` pattern")
        rows.append(Row(patterns, row_seats, [pattern_regex(p) for p in patterns]))
    if not default:
        raise TableError(f"OWNERS.md has no '{DEFAULT_MARK}' row")
    return Table(seats, rows, default)


def unmatched_patterns(table: Table, files: list[str]) -> list[str]:
    """Patterns that match no tracked file. A moved or misspelled path would stop
    guarding anything without a word, so CI refuses the table instead."""
    return [p for row in table.rows for p, rx in zip(row.patterns, row.regexes) if not any(rx.fullmatch(f) for f in files)]


def lint(path: str = TABLE) -> int:
    """CI's check of the table in the working tree: it parses, and every pattern matches a file."""
    try:
        table = parse_table(open(path).read())
    except (OSError, TableError) as e:
        print(f"{path}: {e}")
        return EXIT_TABLE
    bad = unmatched_patterns(table, git("ls-files").splitlines())
    for p in bad:
        print(f"{path}: `{p}` matches no tracked file")
    if bad:
        return EXIT_TABLE
    print(f"{path}: {len(table.rows)} rows, {sum(len(r.patterns) for r in table.rows)} patterns, every one matches a file")
    return 0


def seats_in_changed_rows(diff_text: str, seats: list[str]) -> set[str]:
    """Seats named in table rows a diff of OWNERS.md adds or removes: each must agree."""
    named: set[str] = set()
    for line in diff_text.splitlines():
        if line[:2] in ("+|", "-|"):
            cells = [c.strip() for c in line[1:].strip().strip("|").split("|")]
            if len(cells) >= 2:
                named.update(s for s in split_seats(cells[1]) if s in seats)
    return named


# --- git -------------------------------------------------------------------------


def git(*args: str, check: bool = True) -> str:
    res = subprocess.run(["git", *args], capture_output=True, text=True)
    if check and res.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {res.stderr.strip()}")
    return res.stdout


def resolve(ref: str) -> str | None:
    res = subprocess.run(["git", "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"], capture_output=True, text=True)
    return res.stdout.strip() or None


def changed_files(base: str, commit: str) -> list[str]:
    mb = git("merge-base", base, commit).strip()
    return [f for f in git("diff", "--name-only", "--no-renames", mb, commit).splitlines() if f]


def seat_patch_id(base: str, commit: str, files: list[str]) -> str:
    """The stable patch id of the commit's diff against its merge base, over these files."""
    if not files:
        return ""
    mb = git("merge-base", base, commit).strip()
    diff = git("diff", "--no-renames", "--full-index", "--binary", mb, commit, "--", *files)
    if not diff:
        return ""
    res = subprocess.run(["git", "patch-id", "--stable"], input=diff, capture_output=True, text=True, check=True)
    return "\n".join(sorted(line.split()[0] for line in res.stdout.splitlines() if line.strip()))


def diff_id(a: str, b: str) -> str:
    """The stable patch id of the whole diff a..b, or "" when nothing changed."""
    diff = git("diff", "--no-renames", "--full-index", "--binary", a, b)
    if not diff:
        return ""
    res = subprocess.run(["git", "patch-id", "--stable"], input=diff, capture_output=True, text=True, check=True)
    return res.stdout.split()[0] if res.stdout.strip() else ""


REVERT_DEPTH = 100


def revert_of(base: str, a: str, b: str) -> str | None:
    """The commit among the last REVERT_DEPTH on the base's first-parent line whose exact
    inverse is the diff a..b. Part 5 of the working agreement lets any seat merge a pure
    revert of a change that broke production and tell the owners after, so it needs no line.
    A partial revert, or one with any other change in it, is an ordinary change. So is
    the revert of a revert: it lands the first change again, which needs its lines."""
    want = diff_id(a, b)
    if not want:
        return None
    for r in git("rev-list", "--first-parent", f"--max-count={REVERT_DEPTH}", base).split():
        parent = resolve(f"{r}^1")
        if parent and diff_id(r, parent) == want:
            return None if revert_of(parent, parent, r) else r
    return None


# --- the check -------------------------------------------------------------------


@dataclass
class Verdict:
    required: dict[str, list[str]]  # seat -> its changed files at the head
    agreed: dict[str, str]  # seat -> the commit of its line that holds
    stale: dict[str, list[str]]  # seat -> commits of lines that no longer hold
    revert_of: str = ""  # the commit this change exactly undoes (part 5), which needs no line

    @property
    def missing(self) -> list[str]:
        return sorted(s for s in self.required if s not in self.agreed)


def owners_map(table: Table, files: list[str], table_seats: set[str]) -> dict[str, list[str]]:
    by_seat: dict[str, list[str]] = {}
    for f in files:
        owners = table.owners(f)
        if f == TABLE:
            owners = owners | table_seats
        for seat in owners:
            by_seat.setdefault(seat, []).append(f)
    return by_seat


def agreement_lines(texts: list[str], seats: list[str]) -> dict[str, list[str]]:
    lines: dict[str, list[str]] = {}
    for text in texts:
        for line in (text or "").splitlines():
            m = LINE.match(line)
            if m and m.group("seat").strip() in seats:
                lines.setdefault(m.group("seat").strip(), []).append(m.group("sha"))
    return lines


def check(base: str, head: str, texts: list[str], table_text: str, table_diff: str) -> Verdict:
    table = parse_table(table_text)
    table_seats = seats_in_changed_rows(table_diff, table.seats)
    required = owners_map(table, changed_files(base, head), table_seats)
    lines = agreement_lines(texts, table.seats)
    agreed: dict[str, str] = {}
    stale: dict[str, list[str]] = {}
    for seat, files in sorted(required.items()):
        want = seat_patch_id(base, head, files)
        for sha in lines.get(seat, []):
            commit = resolve(sha)
            if commit is None:
                stale.setdefault(seat, []).append(sha)
                continue
            theirs = owners_map(table, changed_files(base, commit), table_seats).get(seat, [])
            if seat_patch_id(base, commit, theirs) == want:
                agreed[seat] = sha
                break
            stale.setdefault(seat, []).append(sha)
    return Verdict(required, agreed, stale)


def report(v: Verdict, head: str) -> str:
    out = [f"owner-agreement at {head[:8]}"]
    if v.revert_of:
        out.append(f"A pure revert of {v.revert_of[:8]} (part 5 of the working agreement): no line needed. Tell the owners.")
        return "\n".join(out)
    if not v.required:
        out.append("No owned path changed.")
    for seat, files in sorted(v.required.items()):
        shown = ", ".join(files[:4]) + (f" and {len(files) - 4} more" if len(files) > 4 else "")
        if seat in v.agreed:
            out.append(f"  ok       {seat} agreed at {v.agreed[seat]} ({shown})")
        else:
            why = f"; lines at {', '.join(v.stale[seat])} no longer hold" if seat in v.stale else ""
            out.append(f"  MISSING  {seat}: post \"{seat} agreed at {head[:8]}\"{why} ({shown})")
    return "\n".join(out)


# --- GitHub ----------------------------------------------------------------------


def gh_json(path: str):
    res = subprocess.run(["gh", "api", path], capture_output=True, text=True, check=True)
    return json.loads(res.stdout)


def gh_list(path: str) -> list:
    """Every item of a list endpoint, one page of 100 at a time."""
    items: list = []
    page = 1
    while True:
        batch = gh_json(f"{path}?per_page=100&page={page}")
        items.extend(batch)
        if len(batch) < 100:
            return items
        page += 1


def post_status(repo: str, head: str, state: str, description: str) -> None:
    url = ""
    if os.environ.get("GITHUB_RUN_ID"):
        url = f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/{repo}/actions/runs/{os.environ['GITHUB_RUN_ID']}"
    args = ["gh", "api", "-X", "POST", f"repos/{repo}/statuses/{head}", "-f", f"state={state}", "-f", f"context={CONTEXT}", "-f", f"description={description[:140]}"]
    if url:
        args += ["-f", f"target_url={url}"]
    subprocess.run(args, capture_output=True, text=True, check=True)


def fetch_pr(remote: str, number: int, base_ref: str | None = None) -> None:
    refs = [f"+refs/pull/{number}/head:refs/remotes/{remote}/pr-{number}"]
    if base_ref:
        refs.append(f"+refs/heads/{base_ref}:refs/remotes/{remote}/{base_ref}")
    git("fetch", "--quiet", remote, *refs)


def judge(repo: str, pr: dict, base: str) -> tuple[int, str, Verdict | None]:
    """The exit code, the report and the verdict of one pull request against a base commit."""
    head_sha = pr["head"]["sha"]
    if resolve(head_sha) is None:
        raise RuntimeError(f"head {head_sha} of #{pr['number']} is not in the fetched pull request ref")
    texts = [pr.get("body") or ""] if pr.get("author_association") in TRUSTED else []
    texts += [c.get("body") or "" for c in gh_list(f"repos/{repo}/issues/{pr['number']}/comments") if c.get("author_association") in TRUSTED]
    # The table comes from the base. Only the pull request that first adds it is
    # checked against its own copy, and that one needs every seat it names.
    table_text = git("show", f"{base}:{TABLE}", check=False)
    mb = git("merge-base", base, head_sha).strip()
    table_diff = git("diff", "--no-renames", mb, head_sha, "--", TABLE)
    if not table_text:
        table_text = git("show", f"{head_sha}:{TABLE}", check=False)
    if not table_text:
        return 0, f"#{pr['number']}: {TABLE} is on neither the base nor the head, nothing to check.", None
    reverted = revert_of(base, mb, head_sha)
    if reverted:
        v = Verdict({}, {}, {}, reverted)
        return 0, f"#{pr['number']} " + report(v, head_sha), v
    try:
        v = check(base, head_sha, texts, table_text, table_diff)
    except TableError as e:
        return EXIT_TABLE, f"#{pr['number']}: {TABLE} cannot be read: {e}", None
    return (EXIT_MISSING if v.missing else 0), f"#{pr['number']} " + report(v, head_sha), v


def is_ancestor(a: str, b: str) -> bool:
    return subprocess.run(["git", "merge-base", "--is-ancestor", a, b], capture_output=True).returncode == 0


def last_checked(repo: str, target: str, workflow: str) -> str | None:
    """The newest commit, an ancestor of the target, whose deploy run passed this step.

    A run that skipped its deploy (main had moved on) never ran the step, so its commit
    does not count: the commits after the last one checked are all checked now."""
    runs = gh_json(f"repos/{repo}/actions/workflows/{workflow}/runs?per_page=30")["workflow_runs"]
    for run in runs:
        commit = resolve(run["head_sha"])
        if commit is None or commit == target or not is_ancestor(commit, target):
            continue
        for job in gh_json(f"repos/{repo}/actions/runs/{run['id']}/jobs")["jobs"]:
            if any(st.get("name") == CONTEXT and st.get("conclusion") == "success" for st in job.get("steps", [])):
                return commit
    return None


def deployed(repo: str, target_ref: str, workflow: str | None, remote: str) -> int:
    """The deploy step: every main commit this deploy ships, since the last one checked,
    came from a pull request whose owning seats agreed. A direct push fails."""
    target = resolve(target_ref)
    if target is None:
        raise RuntimeError(f"{target_ref} is not a commit")
    since = last_checked(repo, target, workflow) if workflow else None
    commits = git("rev-list", "--first-parent", f"{since}..{target}").split() if since else [target]
    print(f"owner-agreement for the deploy of {target[:8]}: {len(commits)} commit(s) since " + (since[:8] if since else "no checked deploy (only this commit)"))
    worst = 0
    for c in commits:
        parent = resolve(f"{c}^1")
        if parent is None or not (git("show", f"{parent}:{TABLE}", check=False) or git("show", f"{c}:{TABLE}", check=False)):
            print(f"{c[:8]}: before {TABLE}, nothing to check.")
            continue
        reverted = revert_of(parent, parent, c)
        if reverted:
            print(f"{c[:8]}: a pure revert of {reverted[:8]} (part 5 of the working agreement), shipped without lines. Tell the owners.")
            continue
        prs = [p for p in gh_json(f"repos/{repo}/commits/{c}/pulls") if p.get("merge_commit_sha") == c]
        if not prs:
            print(f"{c[:8]}: no pull request was merged as this commit, so no seat could agree to it. Refused.")
            worst = worst or EXIT_MISSING
            continue
        pr = gh_json(f"repos/{repo}/pulls/{prs[0]['number']}")
        fetch_pr(remote, pr["number"])
        code, text, _ = judge(repo, pr, parent)
        print(f"{c[:8]}: {text}")
        worst = worst or code
    if worst:
        print("Refused. A missing line can still be posted on the merged pull request; then run the deploy again.")
    return worst


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pr", type=int)
    ap.add_argument("--deployed", metavar="COMMIT", help="check every main commit a deploy of COMMIT ships (the deploy step)")
    ap.add_argument("--workflow", help="with --deployed: the deploy workflow file, to find the last commit it checked")
    ap.add_argument("--lint", action="store_true", help="check the table in the working tree and exit (CI)")
    ap.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY"))
    ap.add_argument("--remote", default="origin")
    ap.add_argument("--post-status", action="store_true", help="post the owner-agreement commit status on the head")
    a = ap.parse_args(argv)
    if a.lint:
        return lint()
    if not a.repo:
        a.repo = subprocess.run(["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"], capture_output=True, text=True, check=True).stdout.strip()
    if a.deployed:
        return deployed(a.repo, a.deployed, a.workflow, a.remote)
    if a.pr is None:
        ap.error("--pr, --deployed or --lint is required")
    pr = gh_json(f"repos/{a.repo}/pulls/{a.pr}")
    base_ref = pr["base"]["ref"]
    fetch_pr(a.remote, a.pr, base_ref)
    code, text, v = judge(a.repo, pr, f"refs/remotes/{a.remote}/{base_ref}")
    print(text)
    if a.post_status:
        head = pr["head"]["sha"]
        if code == EXIT_TABLE:
            post_status(a.repo, head, "error", text.split(": ", 1)[-1])
        elif v is not None and v.missing:
            post_status(a.repo, head, "failure", "Waiting for: " + ", ".join(v.missing))
        elif v is None:
            post_status(a.repo, head, "success", f"No {TABLE} yet")
        elif v.revert_of:
            post_status(a.repo, head, "success", f"Pure revert of {v.revert_of[:8]}: tell the owners")
        else:
            post_status(a.repo, head, "success", "Every owning seat agreed" if v.required else "No owned path changed")
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
