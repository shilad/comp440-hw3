"""Updates to the homework after it went out: new commits on the class repository's main branch.

A student's fork doesn't get them by itself. At start the page makes sure a remote named
`upstream` points at the class repository (the steps file's `upstream`; the environment variable
WORKBENCH_UPSTREAM overrides it, so trying the page out never touches GitHub). It never changes
`origin`. It fetches `upstream` quietly at start and about every 30 minutes; any failure is
silent. When the class repository's main branch has commits the student's branch lacks, the page
lists their subjects with an Update button, which merges them.

An update must never lose the student's work or leave a merge half done. Before merging, the page
commits the student's changes ("Save work before update"), so git never has to refuse because a
file has uncommitted edits, and those edits are in a commit whatever happens next. (uv.lock, which
uv writes, is put back as it was committed instead.) If the merge
still fails (a real conflict, or an untracked file in the way), `git merge --abort` puts every file
back as it was, and the student is told to ask for help.
"""

from __future__ import annotations

import os
import re
import subprocess
import threading
import time
from pathlib import Path
from typing import Callable

FETCH_EVERY = 30 * 60
FETCH_TIMEOUT = 20
BUSY = ("MERGE_HEAD", "rebase-merge", "rebase-apply", "CHERRY_PICK_HEAD", "REVERT_HEAD")
# Files a program writes, not the student. A student's own uv may rewrite uv.lock; the page never
# commits that, and puts the file back before an update so it can't stand in the update's way.
GENERATED = ("uv.lock",)


def git(repo: Path, *args: str, timeout: float = 60, env: dict | None = None) -> subprocess.CompletedProcess:
    """Run git in the repository. Never asks for a login or an editor, and never raises."""
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_MERGE_AUTOEDIT": "no", "GIT_EDITOR": "true", **(env or {})}
    try:
        return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True,
                              timeout=timeout, env=env, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired) as err:
        return subprocess.CompletedProcess(["git", *args], 1, "", str(err))


def normal(url: str) -> str:
    """A repository address in one form, so https, ssh and a trailing .git compare equal."""
    u = url.strip()
    scp = re.match(r"^[\w.-]+@([\w.-]+):(.*)$", u)          # git@github.com:owner/repo.git
    if scp:
        u = f"{scp.group(1)}/{scp.group(2)}"
    elif "://" in u:
        u = re.sub(r"^[a-z+]+://([^@/]+@)?", "", u, flags=re.I)
    else:                                                  # a folder on this computer
        u = os.path.realpath(os.path.expanduser(u))
    return u.lower().rstrip("/").removesuffix(".git").removeprefix("www.")


def same(a: str, b: str) -> bool:
    return normal(a) == normal(b)


class Updates:
    def __init__(self, repo: Path, url: str | None, branch: str = "main"):
        self.repo, self.url, self.branch = repo, url, branch
        self.ref = f"refs/remotes/upstream/{branch}"
        self.copy_of_class = False      # origin is the class repository itself: no fork to push to
        self.missing: list[str] = []    # subjects of the class repository's commits this branch lacks
        self.fetched = 0.0
        self.lock = threading.Lock()

    def git(self, *args: str, timeout: float = 60) -> subprocess.CompletedProcess:
        return git(self.repo, *args, timeout=timeout)

    def setup(self) -> None:
        """Point the remote `upstream` at the class repository; see whether origin is it too."""
        if not self.url:
            return
        origin = self.git("remote", "get-url", "origin")
        self.copy_of_class = origin.returncode == 0 and same(origin.stdout.strip(), self.url)
        up = self.git("remote", "get-url", "upstream")
        if up.returncode:
            self.git("remote", "add", "upstream", self.url)
        elif not same(up.stdout.strip(), self.url):
            self.git("remote", "set-url", "upstream", self.url)

    def fetch(self) -> None:
        if self.url:
            self.git("fetch", "--quiet", "--no-tags", "upstream",
                     f"+refs/heads/{self.branch}:{self.ref}", timeout=FETCH_TIMEOUT)
            self.fetched = time.time()
        self.check()

    def check(self) -> None:
        r = self.git("log", "--format=%s", f"HEAD..{self.ref}") if self.url else None
        self.missing = r.stdout.splitlines() if r is not None and r.returncode == 0 else []

    def git_dir(self) -> Path:
        d = Path(self.git("rev-parse", "--git-dir").stdout.strip() or ".git")
        return d if d.is_absolute() else self.repo / d

    def apply(self, save: Callable[[], bool]) -> dict:
        """Merge the class repository's new commits. `save` commits the student's changes first
        and says whether that worked. Returns {"ok": bool, "changed": [paths]}."""
        with self.lock:
            self.check()
            if not self.missing:
                return {"ok": True, "changed": []}
            if any((self.git_dir() / x).exists() for x in BUSY) or not save():
                return {"ok": False, "changed": []}
            for f in GENERATED:
                if self.git("diff", "--quiet", "--", f).returncode == 1:
                    self.git("checkout", "--", f)
            before = self.git("rev-parse", "HEAD").stdout.strip()
            merged = self.git("merge", "--no-edit", "-m", "Take the class repository's updates", self.ref, timeout=120)
            if merged.returncode:
                if (self.git_dir() / "MERGE_HEAD").exists():
                    self.git("merge", "--abort")
                self.check()
                return {"ok": False, "changed": [], "why": (merged.stdout + merged.stderr).strip()[-300:]}
            changed = self.git("diff", "--name-only", before, "HEAD").stdout.split("\n")
            self.check()
            return {"ok": True, "changed": [c for c in changed if c]}
