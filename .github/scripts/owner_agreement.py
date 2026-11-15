#!/usr/bin/env python3
"""The owner-agreement check (part 9 of the working agreement between seats).

Every seat that owns a path a change touches must agree to it with a line of its own,
posted by a signer named in OWNERS.md:

    <Seat> agreed at <head commit>

For a pull request the line goes in its body or a comment. For a commit that reached the
main branch without a pull request it goes in a comment on that commit.

The path table is OWNERS.md at the repository root, read from the base, so a change
cannot alter the rules it is checked by. A line holds while the diff of that seat's
paths against the base is byte for byte the same, apart from line numbers.

All seats act as one GitHub user, so GitHub's own approvals cannot carry this. The check
stops a seat from forgetting. It cannot stop a forged line: anyone with write access can
edit a signer's pull request body or comment, and the API does not say who did.

Standard library only. Needs git, and gh for the text on GitHub.

    owner_agreement.py --pr 123                   # local merge gate
    owner_agreement.py --pr 123 --post-status     # CI: also posts the owner-agreement status
    owner_agreement.py --deployed HEAD --workflow deploy-app.yml   # the deploy step
    owner_agreement.py --lint --base HEAD^1       # CI: the table parses, its new patterns match files

Exit 0 when every owning seat agreed, 3 when one is missing, 2 when OWNERS.md cannot be
read, and anything else when the check itself broke.
"""

from __future__ import annotations

import argparse
import functools
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field

TABLE = "OWNERS.md"
SCRIPT = ".github/scripts/owner_agreement.py"
CONTEXT = "owner-agreement"
EXIT_MISSING = 3
EXIT_TABLE = 2
DEFAULT_MARK = "(any other path)"
# The row naming the seats that must agree to any change of the Signers list.
SIGNERS_MARK = "(the Signers list)"
# A line is the whole line: a seat name, "agreed at", a commit, and at most a full stop.
# Four spaces of indent or more make a markdown code block, so at most three are allowed.
LINE = re.compile(r"^ {0,3}(?P<seat>[A-Za-z][A-Za-z\- ]*?) agreed at (?P<sha>[0-9a-f]{7,40})\.?\s*$")
# Paths no pure revert may touch without lines: the table, and the workflows and scripts
# that run the check.
GUARDED = re.compile(r"^(OWNERS\.md$|\.github/)")
REVERT_DEPTH = 100
# The same diff text on every machine: no user configuration can change it.
GIT = ["git", "-c", "core.quotePath=false", "-c", "diff.noprefix=false", "-c", "diff.mnemonicPrefix=false", "-c", "diff.relative=false", "--literal-pathspecs"]
DIFF = ["diff", "--no-renames", "--full-index", "--binary", "--no-color", "--no-ext-diff", "--no-textconv", "--diff-algorithm=myers", "--indent-heuristic", "-U3", "--inter-hunk-context=0", "-O/dev/null", "--src-prefix=a/", "--dst-prefix=b/"]


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
    signers: list[str]
    rows: list[Row]
    default: list[str]
    signer_owners: list[str]

    def owners(self, path: str) -> set[str]:
        """Every seat of every row that matches, or the default owner when none does."""
        found: set[str] = set()
        for row in self.rows:
            if any(rx.fullmatch(path) for rx in row.regexes):
                found.update(row.seats)
        return found or set(self.default)

    def patterns(self) -> list[tuple[str, re.Pattern]]:
        return [(p, rx) for row in self.rows for p, rx in zip(row.patterns, row.regexes)]


def pattern_regex(pattern: str) -> re.Pattern:
    """`dir/` matches everything under dir, `*` one path segment, `**` any depth."""
    out, i = [], 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
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


def split_list(cell: str) -> list[str]:
    return [s.strip().strip("`").rstrip(".") for s in cell.split(",") if s.strip()]


def section_list(lines: list[str], heading: str) -> list[str]:
    if sum(1 for line in lines if line.strip() == heading) > 1:
        raise TableError(f"OWNERS.md has more than one '{heading}' section")
    for i, line in enumerate(lines):
        if line.strip() == heading:
            for nxt in lines[i + 1 :]:
                if nxt.strip():
                    return split_list(nxt)
    return []


def parse_table(text: str) -> Table:
    lines = text.splitlines()
    seats = section_list(lines, "## Seats")
    if not seats:
        raise TableError("OWNERS.md has no '## Seats' list")
    signers = section_list(lines, "## Signers")
    if not signers:
        raise TableError("OWNERS.md has no '## Signers' list")
    rows: list[Row] = []
    default: list[str] = []
    signer_owners: list[str] = []
    for line in lines:
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2 or set(cells[0]) <= {"-", " ", ":"} or cells[0] == "Paths":
            continue
        row_seats = split_list(cells[1])
        unknown = [s for s in row_seats if s not in seats]
        if unknown or not row_seats:
            raise TableError(f"row {cells[0]!r} names unknown seats {unknown or 'none'}")
        if cells[0] in (DEFAULT_MARK, SIGNERS_MARK):
            if (default if cells[0] == DEFAULT_MARK else signer_owners):
                raise TableError(f"OWNERS.md has more than one '{cells[0]}' row")
            if cells[0] == DEFAULT_MARK:
                default = row_seats
            else:
                signer_owners = row_seats
            continue
        patterns = re.findall(r"`([^`]+)`", cells[0])
        if not patterns:
            raise TableError(f"row {cells[0]!r} has no `path` pattern")
        rows.append(Row(patterns, row_seats, [pattern_regex(p) for p in patterns]))
    if not default:
        raise TableError(f"OWNERS.md has no '{DEFAULT_MARK}' row")
    if not signer_owners:
        raise TableError(f"OWNERS.md has no '{SIGNERS_MARK}' row")
    return Table(seats, signers, rows, default, signer_owners)


def seats_in_changed_rows(diff_text: str, seats: list[str]) -> set[str]:
    """Seats named in table rows a diff of OWNERS.md adds or removes: each must agree."""
    named: set[str] = set()
    for line in diff_text.splitlines():
        if line[:2] in ("+|", "-|"):
            cells = [c.strip() for c in line[1:].strip().strip("|").split("|")]
            if len(cells) >= 2:
                named.update(s for s in split_list(cells[1]) if s in seats)
    return named


# --- git -------------------------------------------------------------------------


def git(*args: str, check: bool = True) -> str:
    res = subprocess.run([*GIT, *args], capture_output=True, text=True)
    if check and res.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {res.stderr.strip()}")
    return res.stdout


def git_z(*args: str) -> list[str]:
    """A NUL-separated list of paths, exactly as stored."""
    out = subprocess.run([*GIT, *args, "-z"], capture_output=True, check=True).stdout
    return [p.decode("utf-8", "surrogateescape") for p in out.split(b"\0") if p]


def resolve(ref: str) -> str | None:
    res = subprocess.run([*GIT, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"], capture_output=True, text=True)
    return res.stdout.strip() or None


def is_ancestor(a: str, b: str) -> bool:
    return subprocess.run([*GIT, "merge-base", "--is-ancestor", a, b], capture_output=True).returncode == 0


def merge_base(a: str, b: str) -> str:
    return git("merge-base", a, b).strip()


def changed_files(a: str, b: str) -> list[str]:
    return git_z("diff", "--name-only", "--no-renames", a, b)


INDEX_LINE = re.compile(rb"^index [0-9a-f]+\.\.[0-9a-f]+(?: [0-7]+)?\n", re.M)
# The whole hunk header: its line numbers and the function name git copies from above the hunk.
HUNK_HEADER = re.compile(rb"^@@ [^\n]*", re.M)


@functools.lru_cache(maxsize=4096)
def diff_hash(a: str, b: str, files: tuple[str, ...] | None = None, exact: bool = False) -> str:
    """A hash of the diff a..b (over these files, or all), byte for byte apart from blob
    ids and hunk headers, so the same change on a moved base keeps its hash while
    any change to its text, whitespace included, does not. With exact, the hunk headers
    stay, so the same lines at another place in the file differ. "" when nothing changed."""
    if files == ():
        return ""
    args = [*GIT, *DIFF, a, b] + (["--", *files] if files else [])
    out = subprocess.run(args, capture_output=True, check=True).stdout
    if not out:
        return ""
    out = INDEX_LINE.sub(b"", out)
    if not exact:
        out = HUNK_HEADER.sub(b"@@", out)
    return hashlib.sha256(out).hexdigest()


def seat_hash(base: str, commit: str, files: list[str]) -> str:
    """The seat's diff from the merge base of base and commit."""
    return diff_hash(merge_base(base, commit), commit, tuple(sorted(files)))


def revert_of(base: str, a: str, b: str) -> str | None:
    """The commit among the last REVERT_DEPTH on the base's first-parent line whose exact
    inverse is the diff a..b. Part 5 of the working agreement lets any seat merge a pure
    revert of a change that broke production and tell the owners after, so it needs no
    line. Not for a change to OWNERS.md or .github/, which guard the check itself. A
    partial revert, one with any other change, and the revert of a revert (which lands
    the first change again) are ordinary changes."""
    if any(GUARDED.match(f) for f in changed_files(a, b)):
        return None
    want = diff_hash(a, b, exact=True)
    if not want:
        return None
    for r in git("rev-list", "--first-parent", f"--max-count={REVERT_DEPTH}", base).split():
        parent = resolve(f"{r}^1")
        if parent and diff_hash(r, parent, exact=True) == want:
            return None if revert_of(parent, parent, r) else r
    return None


# --- the check -------------------------------------------------------------------


@dataclass
class Verdict:
    required: dict[str, list[str]]  # seat -> its changed files
    agreed: dict[str, str]  # seat -> the commit of its line that holds
    stale: dict[str, list[str]]  # seat -> commits of lines that no longer hold
    revert_of: str = ""  # the commit this change exactly undoes (part 5): no line needed

    @property
    def missing(self) -> list[str]:
        return [] if self.revert_of else sorted(s for s in self.required if s not in self.agreed)


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
    """Lines on their own, outside HTML comments, <pre> blocks, fenced and indented code."""
    lines: dict[str, list[str]] = {}
    for text in texts:
        fenced = False
        text = re.sub(r"<!--.*?(?:-->|\Z)|^[ \t]*<pre\b.*?(?:</pre>|\Z)", "", text or "", flags=re.S | re.I | re.M)
        for line in text.splitlines():
            if line.lstrip().startswith(("```", "~~~")):
                fenced = not fenced
                continue
            m = None if fenced else LINE.match(line)
            if m and m.group("seat").strip() in seats:
                lines.setdefault(m.group("seat").strip(), []).append(m.group("sha"))
    return lines


def signed_texts(table: Table, items: list[tuple[str, str]]) -> list[str]:
    """The bodies of (login, body) pairs written by a signer named in the table."""
    return [body for login, body in items if login in table.signers]


def check(base: str, head: str, items: list[tuple[str, str]], table_text: str, table_diff: str, extra: frozenset[str] = frozenset()) -> Verdict:
    """The verdict of base..head. Seats in `extra` must agree to the whole diff."""
    table = parse_table(table_text)
    table_seats = seats_in_changed_rows(table_diff, table.seats)
    if table_diff and signers_changed(base, head):
        table_seats |= set(table.signer_owners)

    def seat_files(files: list[str]) -> dict[str, list[str]]:
        by_seat = owners_map(table, files, table_seats)
        for seat in extra:
            if files:
                by_seat[seat] = list(files)
        return by_seat

    mb = merge_base(base, head)
    required = seat_files(changed_files(mb, head))
    lines = agreement_lines(signed_texts(table, items), table.seats)
    agreed: dict[str, str] = {}
    stale: dict[str, list[str]] = {}
    for seat, files in sorted(required.items()):
        want = seat_hash(base, head, files)
        for sha in lines.get(seat, []):
            commit = resolve(sha)
            if commit is None:
                stale.setdefault(seat, []).append(sha)
                continue
            theirs = seat_files(changed_files(merge_base(base, commit), commit)).get(seat, [])
            if seat_hash(base, commit, theirs) == want:
                agreed[seat] = sha
                break
            stale.setdefault(seat, []).append(sha)
    v = Verdict(required, agreed, stale)
    if v.missing:
        v.revert_of = revert_of(base, mb, head) or ""
    return v


def report(v: Verdict, head: str, where: str) -> str:
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
            out.append(f"  MISSING  {seat}: post \"{seat} agreed at {head[:8]}\" {where}{why} ({shown})")
    return "\n".join(out)


def table_at(base: str, head: str) -> tuple[str, str]:
    """The table to judge by (the base's, or the head's when the head first adds it) and
    the diff of OWNERS.md the change makes."""
    text = git("show", f"{base}:{TABLE}", check=False) or git("show", f"{head}:{TABLE}", check=False)
    return text, git(*DIFF, merge_base(base, head), head, "--", TABLE)


def signers_changed(base: str, head: str) -> bool:
    """Whether the change alters the Signers list, which then needs the seats of the
    Signers row too."""
    def signers(ref: str) -> list[str]:
        return section_list(git("show", f"{ref}:{TABLE}", check=False).splitlines(), "## Signers")
    return signers(merge_base(base, head)) != signers(head)


RECOVERY_DEPTH = 200


def last_readable_table(base: str) -> tuple[str, str] | None:
    """The newest commit on the base's first-parent line whose OWNERS.md parses, and its text."""
    for c in git("rev-list", "--first-parent", f"--max-count={RECOVERY_DEPTH}", base).split():
        text = git("show", f"{c}:{TABLE}", check=False)
        if not text:
            return None
        try:
            parse_table(text)
            return c, text
        except TableError:
            continue
    return None


def judge(base: str, head: str, items: list[tuple[str, str]], label: str, where: str, strict: bool = True) -> tuple[int, str, Verdict | None]:
    """The exit code, the report and the verdict of the change base..head.

    A pull request that leaves OWNERS.md unreadable is refused (strict), so a broken table
    cannot pass its own check. If one reaches main anyway, the deploy (not strict) asks
    the seats of the `OWNERS.md` row and the Signers row to agree to that commit, and
    judges later changes by the last table that parses with the same seats agreeing to
    each, so a fix can ship."""
    table_text, table_diff = table_at(base, head)
    if not table_text:
        return 0, f"{label}: {TABLE} is on neither the base nor the head, nothing to check.", None
    head_broken = ""
    if table_diff:
        head_text = git("show", f"{head}:{TABLE}", check=False)
        if head_text:
            try:
                parse_table(head_text)
            except TableError as e:
                head_broken = str(e)
    if head_broken and strict:
        return EXIT_TABLE, f"{label}: this change leaves {TABLE} unreadable: {head_broken}", None
    notes = []
    try:
        table = parse_table(table_text)
    except TableError as e:
        good = last_readable_table(base)
        if good is None:
            return EXIT_TABLE, f"{label}: {TABLE} cannot be read: {e}", None
        table_text = good[1]
        table = parse_table(table_text)
        notes.append(f"{TABLE} on the base cannot be read ({e}). Judged by the table at {good[0][:8]}.")
    extra: frozenset[str] = frozenset()
    if notes or head_broken:
        extra = frozenset(table.owners(TABLE) | set(table.signer_owners))
        if head_broken:
            notes.append(f"This change left {TABLE} unreadable ({head_broken}).")
        notes.append(f"{', '.join(sorted(extra))} must agree to the whole change.")
    note = "".join(f"\n  {n}" for n in notes)
    try:
        v = check(base, head, items, table_text, table_diff, extra)
    except TableError as e:
        return EXIT_TABLE, f"{label}: {TABLE} cannot be read: {e}", None
    return (EXIT_MISSING if v.missing else 0), f"{label} " + report(v, head, where) + note, v


# --- GitHub ----------------------------------------------------------------------


def gh_json(path: str):
    res = subprocess.run(["gh", "api", path], capture_output=True, text=True, check=True)
    return json.loads(res.stdout)


def gh_list(path: str) -> list:
    """Every item of a list endpoint, one page of 100 at a time."""
    items: list = []
    page = 1
    sep = "&" if "?" in path else "?"
    while True:
        batch = gh_json(f"{path}{sep}per_page=100&page={page}")
        if isinstance(batch, dict):  # endpoints that wrap their list, such as workflow runs
            batch = next(v for v in batch.values() if isinstance(v, list))
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


def fetch(remote: str, *refs: str) -> None:
    git("fetch", "--quiet", remote, *refs)


def pr_items(repo: str, pr: dict) -> list[tuple[str, str]]:
    items = [(pr["user"]["login"], pr.get("body") or "")]
    items += [(c["user"]["login"], c.get("body") or "") for c in gh_list(f"repos/{repo}/issues/{pr['number']}/comments")]
    return items


def commit_items(repo: str, sha: str) -> list[tuple[str, str]]:
    return [(c["user"]["login"], c.get("body") or "") for c in gh_list(f"repos/{repo}/commits/{sha}/comments")]


# --- the deploy step ---------------------------------------------------------------


def last_checked(repo: str, target: str, workflow: str) -> str | None:
    """The newest commit, an ancestor of the target, whose deploy run passed this step.

    Every run is read, newest first. A run that skipped the step (main had moved on, or
    an earlier step failed) does not count, so the commits after the last one checked
    are all checked now."""
    for run in gh_list(f"repos/{repo}/actions/workflows/{workflow}/runs"):
        commit = resolve(run["head_sha"])
        if commit is None or commit == target or not is_ancestor(commit, target):
            continue
        for job in gh_json(f"repos/{repo}/actions/runs/{run['id']}/jobs")["jobs"]:
            if any(st.get("name") == CONTEXT and st.get("conclusion") == "success" for st in job.get("steps", [])):
                return commit
    return None


def table_added(target: str) -> str | None:
    """The commit on the target's first-parent line that added OWNERS.md."""
    found = git("log", "--first-parent", "--diff-filter=A", "--format=%H", target, "--", TABLE).split()
    return found[-1] if found else None


def deploy_range(repo: str, target: str, workflow: str | None) -> tuple[str | None, list[str]]:
    """The last checked commit (or the one that added the table) and the commits to judge,
    oldest first. When no run ever passed the step, every commit since the table is judged."""
    since = last_checked(repo, target, workflow) if workflow else None
    if since:
        return since, git("rev-list", "--reverse", "--first-parent", f"{since}..{target}").split()
    added = table_added(target)
    if not added:
        return None, []
    start = resolve(f"{added}^1")
    rng = f"{start}..{target}" if start else target
    return added, git("rev-list", "--reverse", "--first-parent", rng).split()


class Untrusted(Exception):
    """The commits being judged changed .github/ and the trusted commit has no check at
    this script's path, so no trusted copy can judge them."""


def trusted_script(trusted: str, target: str) -> str | None:
    """The check as of the last trusted commit, when the commits being judged changed
    anything under .github/, so a weakened check does not judge itself. A check moved to
    a new path has no trusted copy, and the deploy refuses: move it in two steps, a copy
    that deploys first, then the switch. A deliberate change can still edit the workflow,
    which the `.github/` row guards."""
    if not trusted or not any(f.startswith(".github/") for f in changed_files(trusted, target)):
        return None
    text = git("show", f"{trusted}:{SCRIPT}", check=False)
    if not text:
        raise Untrusted(f"{trusted[:8]} has no {SCRIPT}")
    return text


def deployed(repo: str, target_ref: str, workflow: str | None, remote: str, argv: list[str]) -> int:
    """The deploy step: every main commit this deploy ships, since the last one checked,
    came from a pull request whose owning seats agreed, is a pure revert, or carries the
    owners' lines as comments on the commit itself."""
    target = resolve(target_ref)
    if target is None:
        raise RuntimeError(f"{target_ref} is not a commit")
    trusted, commits = deploy_range(repo, target, workflow)
    if not commits:
        print(f"owner-agreement for the deploy of {target[:8]}: {TABLE} is not on main, nothing to check.")
        return 0
    if not os.environ.get("OWNER_AGREEMENT_TRUSTED"):
        try:
            older = trusted_script(trusted, target)
        except Untrusted as e:
            print(f"Refused. The commits being shipped change .github/, and {e}, so no trusted copy of the check can judge them.")
            return EXIT_MISSING
        if older and older != open(__file__, encoding="utf-8").read():
            print(f"The commits being judged change the check, so it runs as of {trusted[:8]}.")
            with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
                f.write(older)
            try:
                env = dict(os.environ, OWNER_AGREEMENT_TRUSTED="1")
                return subprocess.run([sys.executable, "-I", f.name, *argv], env=env).returncode
            finally:
                os.unlink(f.name)
    print(f"owner-agreement for the deploy of {target[:8]}: {len(commits)} commit(s) since {trusted[:8]}")
    worst = 0
    for c in commits:
        parent = resolve(f"{c}^1")
        if parent is None:
            continue
        prs = [p for p in gh_json(f"repos/{repo}/commits/{c}/pulls") if p.get("merge_commit_sha") == c]
        code, text = EXIT_MISSING, ""
        if prs:
            pr = gh_json(f"repos/{repo}/pulls/{prs[0]['number']}")
            fetch(remote, f"+refs/pull/{pr['number']}/head:refs/remotes/{remote}/pr-{pr['number']}")
            code, text, _ = judge(parent, pr["head"]["sha"], pr_items(repo, pr), f"#{pr['number']}", "on the pull request", strict=False)
        if code:
            # No pull request, or its lines do not hold: the commit's own comments, or a pure revert.
            code2, text2, _ = judge(parent, c, commit_items(repo, c), f"commit {c[:8]}", f"as a comment on commit {c[:8]}", strict=False)
            if code2 == 0 or not prs:
                code, text = code2, (text + "\n" if text else "") + text2
        print(f"{c[:8]}: {text}")
        worst = worst or code
    if worst:
        print("Refused. Post the missing lines where named above, then run the deploy again.")
    return worst


# --- the table lint ----------------------------------------------------------------


def lint(base: str | None) -> int:
    """The table in the working tree parses, and every pattern it adds or changes against
    the base matches a tracked file. A pattern the base already had that no longer matches
    (its file moved or was deleted) is a warning, so a deletion cannot stop the deploys."""
    try:
        with open(TABLE, encoding="utf-8") as f:
            table = parse_table(f.read())
    except (OSError, TableError) as e:
        print(f"{TABLE}: {e}")
        return EXIT_TABLE
    old: set[str] = set()
    if base and resolve(base):
        try:
            old = {p for p, _ in parse_table(git("show", f"{base}:{TABLE}", check=False)).patterns()}
        except TableError:
            old = set()
    files = git_z("ls-files")
    bad = 0
    for p, rx in table.patterns():
        if any(rx.fullmatch(f) for f in files):
            continue
        if p in old:
            print(f"::warning::{TABLE}: `{p}` no longer matches a tracked file. Update its row.")
        else:
            print(f"{TABLE}: `{p}` matches no tracked file")
            bad += 1
    if bad:
        return EXIT_TABLE
    print(f"{TABLE}: {len(table.rows)} rows, {len(table.patterns())} patterns, signers {', '.join(table.signers)}")
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pr", type=int)
    ap.add_argument("--deployed", metavar="COMMIT", help="judge every main commit a deploy of COMMIT ships (the deploy step)")
    ap.add_argument("--workflow", help="with --deployed: the deploy workflow file, to find the last commit it checked")
    ap.add_argument("--lint", action="store_true", help="check the table in the working tree and exit (CI)")
    ap.add_argument("--base", help="with --lint: the commit whose table the working tree's is compared with")
    ap.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY"))
    ap.add_argument("--remote", default="origin")
    ap.add_argument("--post-status", action="store_true", help="post the owner-agreement commit status on the head")
    a = ap.parse_args(argv)
    if a.lint:
        return lint(a.base)
    if not a.repo:
        a.repo = subprocess.run(["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"], capture_output=True, text=True, check=True).stdout.strip()
    if a.deployed:
        return deployed(a.repo, a.deployed, a.workflow, a.remote, argv)
    if a.pr is None:
        ap.error("--pr, --deployed or --lint is required")
    pr = gh_json(f"repos/{a.repo}/pulls/{a.pr}")
    base_ref, head = pr["base"]["ref"], pr["head"]["sha"]
    fetch(a.remote, f"+refs/heads/{base_ref}:refs/remotes/{a.remote}/{base_ref}", f"+refs/pull/{a.pr}/head:refs/remotes/{a.remote}/pr-{a.pr}")
    if resolve(head) is None:
        raise RuntimeError(f"head {head} is not in the fetched pull request ref")
    code, text, v = judge(f"refs/remotes/{a.remote}/{base_ref}", head, pr_items(a.repo, pr), f"#{a.pr}", "on the pull request")
    print(text)
    if a.post_status:
        if code == EXIT_TABLE:
            post_status(a.repo, head, "error", text.split(": ", 1)[-1])
        elif v is None:
            post_status(a.repo, head, "success", f"No {TABLE} yet")
        elif v.revert_of:
            post_status(a.repo, head, "success", f"Pure revert of {v.revert_of[:8]}: tell the owners")
        elif v.missing:
            post_status(a.repo, head, "failure", "Waiting for: " + ", ".join(v.missing))
        else:
            post_status(a.repo, head, "success", "Every owning seat agreed" if v.required else "No owned path changed")
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
