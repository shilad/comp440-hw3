"""The homework page: a homework's steps in the browser, with one Claude Code session per step.

    uv run python -m workbench              run it in the homework's folder; it opens the browser
    uv run python -m workbench --no-open    without opening the browser
    uv run python -m workbench --port 8460  look for a free port from 8460 instead of 8450

It serves the repository it sits in, with that repository's steps.toml. Only Python's standard
library is used. The student runs each step's Claude Code session in their own terminal, with the
command the page gives, and the page reads what the session did from the conversation Claude Code
saves. What the page does by itself (README.md beside this file says more):

- commits a part as "Part N done" once its last step is complete, with TRANSCRIPT.md (the
  conversations) and record/ (what the page showed for each step), and pushes it to origin when
  steps.toml says `push = true`;
- commits a later change to a committed part's answers or files as "Part N updated";
- lists the class repository's updates, from the remote `upstream`, with a button that merges them.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import shutil
import sys
import threading
import time
import traceback
import urllib.request
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import steps as stepmod
from . import transcript
from .sessions import Hub
from .updates import FETCH_EVERY, GENERATED, Updates, git, normal

HERE = Path(__file__).resolve().parent
REPO = HERE.parent              # the homework's repository, which this folder is part of
STATIC = HERE / "static"
PORT = 8450                     # other course tools use 8440
PORTS = 20                      # how many ports to try from there
SETTLE = 30                     # seconds a committed part's changes sit still before they're committed
CONVO_SETTLE = 120              # and seconds its conversations sit still, so a commit never cuts one off
RETRY_PUSH = 5 * 60
HELP = "post in #comp440-f26 on Slack"
NOT_A_CLONE = ("This folder is not a git clone of your fork, so the page cannot save your work to GitHub or "
               "bring you updates. Get the homework the way the README says: fork the repository on GitHub, "
               "then run git clone on your fork, and start the page in that folder.")
CODE = {".py", ".js", ".css", ".html", ".md", ".json"}   # a change to one of these asks for a restart
NO_VIEWER = ("<!doctype html><meta charset='utf-8'><title>Results</title>"
             "<p style='font: 16px/1.5 system-ui, sans-serif; margin: 40px'>The results viewer is not "
             "installed in this copy of the homework. <a href='/'>Back to the homework page</a></p>")
NO_FINDER = ("<!doctype html><meta charset='utf-8'><title>Find claims</title>"
             "<p style='font: 16px/1.5 system-ui, sans-serif; margin: 40px'>The claim finder is not "
             "installed in this copy of the homework. <a href='/'>Back to the homework page</a></p>")


def say(text: str) -> None:
    print(time.strftime("%H:%M ") + text, flush=True)


class App:
    def __init__(self, repo: Path, upstream: str | None = None):
        self.repo = repo
        self.steps_file = repo / "steps.toml"
        self.a = stepmod.load(self.steps_file)
        self.hub = Hub(self.a, repo)
        self.hub.locked = self.locked
        self.notices: dict[str, dict] = {}   # what the top of the page tells the student, by kind
        self.commit_lock = threading.RLock()
        self.reload_lock = threading.Lock()
        self.push_lock = threading.Lock()
        self.push_due = 0.0                  # when to try a push again; 0 for never
        self.pushed: bool | None = None      # True only when every commit is on origin
        self.commits = 0                     # commits the page has made, so a push knows if one came since
        self.push_state = threading.Lock()   # guards `pushed` and `commits` together
        self.retry_at = 0.0                  # after a commit that failed, when to try again
        self.idle = None                     # what `git status` showed after the last commit
        self.stamp = self.file_stamp()
        self.version = 1
        self.code = self.code_stamp()
        self.updates = Updates(repo, upstream or os.environ.get("WORKBENCH_UPSTREAM") or self.a.upstream)
        self.own, self.own_checked = False, 0.0

    def own_repo(self) -> bool:
        """Whether the homework folder is the top of its own git repository. Every git command that
        writes (remotes, fetch, add, commit, push, merge) runs only when it is, so a folder unpacked
        from a ZIP inside some other repository never touches that repository. Checked at start and
        kept once true; while false, checked again at most every 5 seconds, so a student who then
        clones properly isn't stuck. Any failure to check counts as false."""
        if self.own or time.time() - self.own_checked < 5:
            return self.own
        self.own_checked = time.time()
        try:
            top = git(self.repo, "rev-parse", "--show-toplevel")
            self.own = top.returncode == 0 and os.path.samefile(top.stdout.strip(), self.repo)
        except (OSError, ValueError):
            self.own = False
        return self.own

    def start(self) -> None:
        """The two loops that run beside the web server: saving work, and checking for updates."""
        if self.own_repo() and self.a.push and git(self.repo, "rev-list", "--count", "HEAD", "--not",
                                                   "--remotes=origin").stdout.strip() not in ("", "0"):
            self.push_due = time.time()      # commits from before a restart that never reached GitHub
        threading.Thread(target=self.watch, daemon=True).start()
        threading.Thread(target=self.watch_updates, daemon=True).start()

    def locked(self, step_id: str) -> bool:
        return next(x for x in stepmod.status(self.a, self.repo, self.hub.marked()) if x["id"] == step_id)["locked"]

    def notice(self, kind: str, text: str | None, **more) -> None:
        if text is None:
            self.notices.pop(kind, None)
        else:
            if self.notices.get(kind, {}).get("text") != text:
                say(text)
            self.notices[kind] = {"kind": kind, "text": text, **more}

    # -- re-reading the steps file and the brief's pages when they change -----------------------
    def file_stamp(self) -> tuple:
        files = [self.steps_file] + [self.repo / s.page for s in self.a.steps if s.page]
        if self.a.overview:
            files.append(self.repo / self.a.overview)
        return tuple(f.stat().st_mtime_ns if f.exists() else 0 for f in dict.fromkeys(files))

    def code_stamp(self) -> tuple:
        """The page's own code, the viewer's and the claim finder's: when one changes, the page must restart."""
        files = [f for d in (self.repo / "workbench", self.repo / "viewer", self.repo / "finder") if d.is_dir()
                 for f in sorted(d.rglob("*")) if f.suffix in CODE and "__pycache__" not in f.parts]
        return tuple((str(f), f.stat().st_mtime_ns) for f in files)

    def fresh(self) -> None:
        """Take a changed steps.toml or page (after an update, say) without a restart."""
        with self.reload_lock:
            stamp = self.file_stamp()
            if stamp == self.stamp:
                return
            self.stamp = stamp
            try:
                a = stepmod.load(self.steps_file)
            except Exception as err:  # noqa: BLE001
                self.notice("steps", f"steps.toml has a mistake, so the page still shows the steps from "
                            f"before ({err}). If you didn't change it, {HELP}.")
                return
            self.notice("steps", None)
            self.a = a
            self.hub.retarget(a)
            self.stamp = self.file_stamp()
            self.version += 1

    # -- what the page polls ---------------------------------------------------------------
    def assignment(self) -> dict:
        self.fresh()
        a = self.a
        overview = stepmod.page(a, self.repo, a.overview) if a.overview else None
        lede = re.sub(r"\s*[^.]*:$", "", stepmod.intro(overview))   # drop a closing "You will:"
        parts = []
        for n, p in sorted(a.parts.items()):
            first = next((s for s in a.steps if s.part == n and s.page), None)
            desc = p.get("desc") or (stepmod.intro(stepmod.page(a, self.repo, first.page)) if first else "")
            parts.append({"number": n, **p, "desc": desc})
        return {
            "title": a.title,
            "lede": lede,
            "sample_claim": a.sample_claim,
            "parts": parts,
            "steps": [{"id": s.id, "label": a.label(s), "part": s.part, "title": s.title, "summary": s.summary,
                       "goal": s.goal, "setup": s.setup, "claim": s.claim, "minutes": s.minutes, "files": s.files,
                       "run_yourself": stepmod.run_yourself(s),
                       "body": stepmod.body(s, a, self.repo)} for s in a.steps],
            "repo": str(self.repo),
            "version": self.version,
        }

    def state(self) -> dict:
        self.fresh()
        status = stepmod.status(self.a, self.repo, self.hub.marked())
        sessions = {}
        for sid, s in list(self.hub.sessions.items()):
            s.refresh()
            last = next((e for e in reversed(s.events) if e["kind"] in ("tool", "slot", "claude", "permission")), None)
            sessions[sid] = {"state": s.state, "now": s.now, "busy": s.busy, "totals": s.totals,
                             "status": (s.status or {}).get("text"),
                             "events": len(s.events),
                             "pending": s.state == "asking",
                             "last": (last or {}).get("label") or ((last or {}).get("text") or "")[:80]}
        now = next((x["id"] for x in status if not x["complete"] and not x["locked"]), None)
        committed = sorted(stepmod.part_done_commits(self.repo)) if self.own_repo() else []
        return {"steps": status, "sessions": sessions, "committed": committed,
                "now": now, "notices": self.current_notices(), "version": self.version,
                "push": {"on": self.a.push, "ok": self.pushed}}

    def current_notices(self) -> list[dict]:
        u, out = self.updates, []
        if not self.own_repo():
            out.append({"kind": "not-a-clone", "text": NOT_A_CLONE})
        elif u.url and u.copy_of_class:
            out.append({"kind": "fork", "text": (
                "This folder was cloned from the class repository, not from your own fork, so the page "
                f"can't save your work to GitHub. Fork {web(u.url)} on GitHub, then run this in a "
                "terminal in this folder, with your GitHub username:"),
                "code": "git remote set-url origin https://github.com/YOUR-USERNAME/" + Path(normal(u.url)).name})
        failed = self.notices.get("update-failed")
        if failed and failed["missing"] != u.missing:   # newer commits since: let them try again
            self.notice("update-failed", None)
        if u.missing:
            self.notice("updated", None)
        if u.missing and "update-failed" not in self.notices and self.own_repo():
            out.append({"kind": "update", "text": "There is an update to the homework. It brings:",
                        "items": u.missing[:8] + ([f"and {len(u.missing) - 8} more"] if len(u.missing) > 8 else []),
                        "button": "Update"})
        if self.code != self.code_stamp() and "restart" not in self.notices:
            self.notice("restart", "The homework page itself has changed. Restart it: press Ctrl-C in the "
                        "terminal where it runs, then run uv run python -m workbench again.")
        return out + list(self.notices.values())

    def file(self, rel: str) -> tuple[dict, int]:
        """A file in the student's repository, for the page's links: read-only, never a secret."""
        try:
            f = (self.repo / rel).resolve()
            f.relative_to(self.repo.resolve())
        except (ValueError, OSError):
            return {"error": "That file isn't in this repository."}, 404
        if any(part in (".git", ".workbench") for part in f.relative_to(self.repo.resolve()).parts) or \
                any(f.name == x or f.match(x) for x in self.a.never_read):
            return {"error": "The page doesn't show that file."}, 403
        if not f.is_file():
            return {"error": f"There's no {rel} yet."}, 404
        data = f.read_bytes()[:200_000]
        return {"path": rel, "text": data.decode("utf-8", errors="replace"),
                "cut": f.stat().st_size > len(data)}, 200

    # -- saving the student's work ---------------------------------------------------------------
    def watch(self) -> None:
        """Commit a part as soon as its steps are complete, however they got that way, and commit
        later changes to a committed part."""
        while True:
            try:
                self.tick()
            except Exception as err:  # noqa: BLE001
                traceback.print_exc()
                self.notice("save", f"Something went wrong while saving your work ({err}). Your files are "
                            f"untouched. If this stays, {HELP}.")
            time.sleep(3)

    def tick(self) -> None:
        self.fresh()
        if not self.own_repo():      # not a clone of the student's fork: nothing to commit into
            return
        self.commit_finished_parts()
        self.commit_changes()
        if self.push_due and time.time() >= self.push_due:
            self.push_soon()

    def git(self, *args: str, timeout: float = 60, env: dict | None = None):
        return git(self.repo, *args, timeout=timeout, env=env)

    def part_files(self, parts) -> list[str]:
        return [str(f.relative_to(self.repo)) for s in self.a.steps if s.part in parts
                for pat in s.files for f in stepmod.present(self.repo, pat)]

    def save(self, message: str, empty: bool = False) -> bool:
        """Commit the student's work as `message`: everything in the repository that isn't
        git-ignored, with TRANSCRIPT.md and record/ written first, but never uv.lock and never a
        file holding something like a key. True if committed (or nothing to commit)."""
        if not self.own_repo():
            return False
        with self.commit_lock:
            ids = {s.id: self.hub.session_id(s.id) for s in self.a.steps}
            try:
                transcript.write(self.repo, self.a, ids)
            except Exception as err:  # noqa: BLE001  never let the record stop the commit
                traceback.print_exc()
                say(f"Couldn't write {transcript.NAME}: {err}")
            try:
                self.hub.save_records(self.repo / "record")
            except Exception as err:  # noqa: BLE001
                traceback.print_exc()
                say(f"Couldn't write record/: {err}")
            self.git("add", "-A", timeout=300)          # everything that isn't git-ignored
            self.git("reset", "-q", "--", *GENERATED)   # uv.lock is uv's, not the student's work
            # Never commit a key: the student's fork is public.
            keyed = [f for f in self.git("diff", "--cached", "--name-only", "-G", "sk-ant-").stdout.split("\n") if f]
            # A never_read file that would be newly added (.env, if .gitignore ever lost it) is left
            # out. One the repository already tracks (a course file such as reference_loop.py) is
            # committed like any other; the sk-ant- check above still covers what is in it.
            keyed += [x for x in self.a.never_read
                      if self.git("diff", "--cached", "--name-only", "--diff-filter=A", "--", x).stdout.strip()]
            if keyed:
                self.git("reset", "-q", "--", *keyed)
                names = ", ".join(dict.fromkeys(keyed))
                self.notice("key", f"The page didn't commit {names}, because it holds what looks like an API "
                            "key and your repository on GitHub is public. Remove the key from it; the key "
                            "belongs only in .env.")
            else:
                self.notice("key", None)
            if not empty and self.git("diff", "--cached", "--quiet").returncode == 0:
                self.after_commit()
                return True
            r = self.git("commit", "-q", "--allow-empty", "-m", message, timeout=300)
            if r.returncode:
                self.retry_at = time.time() + 60    # don't write the transcript again every few seconds
                self.notice("save", f"The page couldn't commit “{message}”: "
                            f"{(r.stderr or r.stdout).strip()[-200:]}. Your files are untouched. If this stays, {HELP}.")
                return False
            self.notice("save", None)
            self.after_commit()
            with self.push_state:
                self.commits += 1
                self.pushed = None if self.a.push else self.pushed   # a commit is waiting for its push
            say(f"Committed “{message}”.")
            self.push_soon()
            return True

    def commit_finished_parts(self) -> None:
        if not self.a.commit_parts or not self.own_repo() or time.time() < self.retry_at:
            return
        with self.commit_lock:
            status = stepmod.status(self.a, self.repo, self.hub.marked())
            done = stepmod.part_done_commits(self.repo)
            for n in sorted(self.a.parts):
                mine = [s for s in status if s["part"] == n]
                if mine and n not in done and all(s["complete"] for s in mine):
                    self.save(f"Part {n} done", empty=True)

    def after_commit(self) -> None:
        self.hub.remember_convos()
        self.idle = self.loose()

    def loose(self) -> tuple:
        """What git sees changed, with each file's modification time; uv.lock left out."""
        out = self.git("status", "--porcelain", "--untracked-files=all", "--", ".",
                       *[f":(exclude){g}" for g in GENERATED]).stdout
        names = [line[3:].strip().strip('"') for line in out.splitlines() if line.strip()]
        return tuple((n, (self.repo / n).stat().st_mtime if (self.repo / n).exists() else 0) for n in names)

    def changed_parts(self) -> list[int]:
        """Committed parts whose answers, files or conversations have changed since the last commit.
        After the last part is committed, any other change (extra credit, code) counts as its own."""
        done = stepmod.part_done_commits(self.repo)
        if not done:
            return []
        saved = self.hub.state.get("saved_convos", {})
        head = self.git("show", f"HEAD:{self.a.writeup}")
        old, new = stepmod.read_slots(head.stdout if head.returncode == 0 else ""), self.hub.slots()
        out = []
        for n in sorted(done):
            mine = [s for s in self.a.steps if s.part == n]
            keys = {k for s in mine for k in stepmod.step_keys(s, old) + stepmod.step_keys(s, new)}
            patterns = [pat for s in mine for pat in s.files]
            grown = any(self.hub.convo_size(s.id) > saved.get(s.id, 0) for s in mine)
            if grown or any(old.get(k) != new.get(k) for k in keys) or (patterns and self.git(
                    "status", "--porcelain", "--untracked-files=all", "--", *patterns).stdout.strip()):
                out.append(n)
        last = max(self.a.parts, default=None)
        if last in done and last not in out:
            loose = self.loose()
            if loose and loose != self.idle:
                out.append(last)
        return out

    def commit_changes(self) -> None:
        """A change to a committed part's answers or files is committed as "Part N updated", once
        it has sat still for SETTLE seconds, so a student who is still typing gets one commit."""
        if not self.a.commit_parts or not self.own_repo() or time.time() < self.retry_at:
            return
        with self.commit_lock:
            changed = self.changed_parts()
            if not changed:
                return
            files = [self.repo / self.a.writeup] + [self.repo / p for p in self.part_files(changed)]
            newest = max([f.stat().st_mtime for f in files if f.exists()] + [t for _, t in self.loose()], default=0)
            talk = [self.hub.sessions[s.id].transcript() for s in self.a.steps if s.part in changed]
            talked = max((f.stat().st_mtime for f in talk if f), default=0)
            if time.time() - newest >= SETTLE and time.time() - talked >= CONVO_SETTLE:
                names = " and ".join(str(n) for n in changed)
                self.save(f"Part{'s' if len(changed) > 1 else ''} {names} updated")

    def push_soon(self) -> None:
        if self.a.push and not self.updates.copy_of_class and self.own_repo():
            threading.Thread(target=self.push, daemon=True).start()

    def push(self) -> None:
        """Push to origin. A failure never blocks anything: the work is committed, the page says
        so in one sentence, and tries again every few minutes."""
        if not self.own_repo():
            return
        if not self.push_lock.acquire(blocking=False):   # a push is running: push again after it
            self.push_due = time.time() + 10
            return
        try:
            started, commits = time.time(), self.commits
            env = {}
            if not os.environ.get("GIT_SSH_COMMAND") and self.git("config", "core.sshCommand").returncode:
                env["GIT_SSH_COMMAND"] = "ssh -o BatchMode=yes"   # never wait for a passphrase
            r = self.git("push", "-q", "origin", "HEAD", timeout=600, env=env)
            if r.returncode == 0:
                # A commit made while this push ran may not be in it: push again until none waits.
                waiting = self.git("rev-list", "--count", "HEAD", "--not", "--remotes=origin").stdout.strip()
                with self.push_state:
                    done = waiting == "0" and self.commits == commits
                    if done:
                        self.pushed = True
                        if self.push_due <= started:    # never clear a retry set while this push ran
                            self.push_due = 0.0
                    else:
                        self.pushed = None
                        self.push_due = time.time() + 3
                self.notice("push", None)
                say("Pushed to GitHub." if done else "Pushed to GitHub; a newer commit goes next.")
            else:
                self.pushed, self.push_due = False, time.time() + RETRY_PUSH
                say(f"The push didn't go through: {(r.stderr or r.stdout).strip()[-300:]}")
                self.notice("push", "Your work is committed on this laptop but not pushed to GitHub. The page "
                            "tries again every few minutes. To push it yourself, run git push in a terminal "
                            "in this folder.")
        finally:
            self.push_lock.release()

    # -- updates from the class repository ------------------------------------------------------
    def watch_updates(self) -> None:
        while True:
            try:
                self.check_updates()
            except Exception:  # noqa: BLE001  checking for updates is never worth a message
                traceback.print_exc()
            time.sleep(60)

    def check_updates(self) -> None:
        if not self.own_repo():      # never add a remote to, or fetch into, someone else's repository
            self.updates.missing = []
            return
        self.updates.setup()
        if time.time() - self.updates.fetched >= FETCH_EVERY:
            self.updates.fetch()
        else:
            self.updates.check()

    def update(self) -> dict:
        """The Update button: save the student's work, then merge the class repository's commits."""
        if not self.own_repo():
            return {"ok": False, "why": NOT_A_CLONE}
        with self.commit_lock:
            result = self.updates.apply(lambda: self.save("Save work before update"))
        if not result["ok"]:
            say(f"The update didn't go through: {result.get('why', '')}")
            self.notice("update-failed", "The update could not be applied automatically, and nothing in your "
                        f"files was changed. Please {HELP}.", missing=list(self.updates.missing))
            return {"ok": False}
        self.notice("update-failed", None)
        self.fresh()
        self.push_soon()
        if self.code != self.code_stamp():
            self.notice("restart", "The update changed the homework page itself. Restart it: press Ctrl-C in "
                        "the terminal where it runs, then run uv run python -m workbench again.")
        else:
            self.notice("updated", "The homework is up to date.")
        return {"ok": True}

    # -- the results viewer, under /results -----------------------------------------------------
    def results(self, method: str, path: str, query: dict) -> tuple[int, str, bytes, dict]:
        if str(self.repo) not in sys.path:
            sys.path.insert(0, str(self.repo))
        try:
            from viewer import app as viewer   # noqa: PLC0415  imported when first asked for
        except ModuleNotFoundError as err:
            if err.name in ("viewer", "viewer.app"):
                return 200, "text/html; charset=utf-8", NO_VIEWER.encode(), {}
            raise
        respond = getattr(viewer, "respond", None)    # its answer with headers, as a real redirect
        if respond:
            return respond(method, path, query, self.repo)
        return (*viewer.handle(method, path, query, self.repo), {})

    # -- the claim finder, under /claims --------------------------------------------------------
    def claims(self, method: str, path: str, query: dict, body: bytes) -> tuple[int, str, bytes]:
        if str(self.repo) not in sys.path:
            sys.path.insert(0, str(self.repo))
        try:
            from finder import web as finder   # noqa: PLC0415  imported when first asked for
        except ModuleNotFoundError as err:
            if err.name in ("finder", "finder.web"):
                return 200, "text/html; charset=utf-8", NO_FINDER.encode()
            raise
        return finder.handle(method, path, query, body, self.repo)


def web(url: str) -> str:
    """The class repository's address as a student would type it in a browser."""
    n = normal(url)
    return "https://" + n if n.startswith("github.com/") else url


def handler(app: App):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *args):  # quiet
            pass

        def send(self, code: int, ctype: str, body: bytes, extra: dict | None = None) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def send_json(self, data, code=200):
            self.send(code, "application/json", json.dumps(data).encode())

        def read_json(self) -> dict:
            n = int(self.headers.get("Content-Length") or 0)
            try:
                return json.loads(self.rfile.read(n) or b"{}")
            except ValueError:
                return {}

        def results(self, method: str) -> bool:
            u = urlparse(self.path)
            if u.path == "/results":    # so the viewer's relative links stay under /results/
                self.send(301, "text/plain", b"", {"Location": "/results/" + (f"?{u.query}" if u.query else "")})
                return True
            if not u.path.startswith("/results/"):
                return False
            try:
                code, ctype, body, headers = app.results(method, u.path[len("/results"):], parse_qs(u.query))
            except Exception as err:  # noqa: BLE001
                traceback.print_exc()
                code, ctype, body, headers = (500, "text/plain; charset=utf-8",
                                              f"The results viewer ran into a problem: {err}".encode(), {})
            self.send(code, ctype, body, headers)
            return True

        def claims(self, method: str) -> bool:
            u = urlparse(self.path)
            if u.path == "/claims":     # so the screen's relative links stay under /claims/
                self.send(301, "text/plain", b"", {"Location": "/claims/"})
                return True
            if not u.path.startswith("/claims/"):
                return False
            body = self.rfile.read(int(self.headers.get("Content-Length") or 0)) if method == "POST" else b""
            try:
                code, ctype, data = app.claims(method, u.path[len("/claims"):], parse_qs(u.query), body)
            except Exception as err:  # noqa: BLE001
                traceback.print_exc()
                code, ctype, data = (500, "text/plain; charset=utf-8",
                                     f"The claim finder ran into a problem: {err}".encode())
            self.send(code, ctype, data)
            return True

        def do_GET(self):
            if self.results("GET") or self.claims("GET"):
                return
            path = urlparse(self.path).path
            if path == "/api/ping":
                return self.send_json({"repo": str(app.repo)})
            if path == "/api/assignment":
                return self.send_json(app.assignment())
            if path == "/api/state":
                return self.send_json(app.state())
            if path == "/api/file":
                return self.send_json(*app.file(parse_qs(urlparse(self.path).query).get("path", [""])[0]))
            if path.startswith("/api/session/"):
                sid = path.split("/")[3]
                if sid in app.hub.sessions:
                    return self.send_json(app.hub.sessions[sid].snapshot())
                return self.send_json({"error": "no such step"}, 404)
            name = "index.html" if path in ("/", "") else path.lstrip("/").removeprefix("static/")
            f = (STATIC / name).resolve()
            if not f.is_file() or STATIC.resolve() not in f.parents:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            self.send(200, mimetypes.guess_type(f.name)[0] or "application/octet-stream", f.read_bytes())

        def do_POST(self):
            origin = self.headers.get("Origin")
            if origin and urlparse(origin).hostname not in ("localhost", "127.0.0.1"):
                return self.send_json({"error": "Only the homework page itself can do that."}, 403)
            if self.results("POST") or self.claims("POST"):
                return
            parts = urlparse(self.path).path.strip("/").split("/")
            body = self.read_json()
            if parts == ["api", "update"]:
                return self.send_json(app.update())
            if parts[:2] != ["api", "step"] or len(parts) != 4:
                return self.send_json({"error": "not found"}, 404)
            try:
                step = app.a.step(parts[2])
            except KeyError:
                return self.send_json({"error": f"There is no step {parts[2]}. Use the label your instructions give."}, 404)
            sid, label, action = step.id, app.a.label(step), parts[3]
            st = next(x for x in stepmod.status(app.a, app.repo, app.hub.marked()) if x["id"] == sid)
            if action == "mark" and body.get("checkpoint") is not None:
                cps = stepmod.checkpoints(step)
                try:
                    n = int(body["checkpoint"])
                except (TypeError, ValueError):
                    n = 0
                if not 1 <= n <= len(cps):
                    return self.send_json({"error": f"Step {label} has {len(cps)} checkpoints; there is no {body['checkpoint']}."}, 400)
                c = cps[n - 1]
                if c.files or c.slots:
                    what = " and ".join(([", ".join(c.files) + " exists"] if c.files else [])
                                        + (["the student's answers are in " + app.a.writeup] if c.slots else []))
                    return self.send_json({"error": f"“{c.text}” ticks itself when {what}. Nothing was changed."}, 409)
                app.hub.record(sid, "checkpoint", n=n, text=c.text)
                return self.send_json({"ok": True, "said": f"The page now shows “{c.text}” as reached."})
            if action == "expected":
                text = " ".join(str(body.get("text") or "").split())[:80]
                if not text:
                    return self.send_json({"error": "Say what they expect, in a few words. Nothing was changed."}, 400)
                app.hub.record(sid, "expected", text=text)
                return self.send_json({"ok": True, "said": f"The page will set “{text}” beside the result."})
            if action == "mark":
                if body.get("by") == "claude":
                    if not st["manual"]:
                        return self.send_json({"error": f"Step {label} is complete when its answers are in "
                                               f"{app.a.writeup}; the page ticks it by itself. Nothing was changed."}, 409)
                    if st["locked"]:
                        return self.send_json({"error": f"Step {label} is still locked: finish "
                                               + ", ".join(st["waiting_on"]) + " first."}, 409)
                    app.hub.record(sid, "done")
                app.hub.mark(sid, bool(body.get("done", True)))   # the page commits within a few seconds
                return self.send_json({"ok": True, "said": f"The page now shows step {label} as done."})
            if action == "status":
                text = " ".join(str(body.get("text") or "").split())
                if not text:
                    return self.send_json({"error": "The status was empty. Nothing was changed."}, 400)
                text = text[:120]
                app.hub.record(sid, "status", text=text)
                return self.send_json({"ok": True, "said": f"The page now says: {text}"})
            return self.send_json({"error": "not found"}, 404)

    return H


class Server(ThreadingHTTPServer):
    daemon_threads = True


def serve(app: App, start: int = PORT, tries: int = PORTS) -> Server:
    """A server on the first free port from `start`."""
    for port in range(start, start + tries):
        try:
            return Server(("127.0.0.1", port), handler(app))
        except OSError:
            continue
    sys.exit(f"Ports {start} to {start + tries - 1} are all in use. Close another program that uses "
             f"them, or start the page with --port and another number, as in --port 9000.")


def running_already(repo: Path) -> str | None:
    """The address of a homework page already running for this folder, if there is one."""
    try:
        port = json.loads((repo / ".workbench" / "server.json").read_text())["port"]
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(f"http://127.0.0.1:{port}/api/ping", timeout=2) as r:
            if json.loads(r.read()).get("repo") == str(repo):
                return f"http://localhost:{port}"
    except Exception:  # noqa: BLE001  nothing answers: start a new one
        pass
    return None


def main() -> None:
    p = argparse.ArgumentParser(prog="uv run python -m workbench",
                                description="Start the homework page for the homework in this folder.")
    p.add_argument("--port", type=int, default=PORT, help=f"look for a free port from this one (default {PORT})")
    p.add_argument("--no-open", action="store_true", help="don't open the page in the browser")
    args = p.parse_args()
    repo = REPO
    if not (repo / "steps.toml").is_file():
        sys.exit(f"There's no steps.toml in {repo}, so there is no homework to show.")
    url = running_already(repo)
    if url:
        print(f"The homework page is already running, at {url}")
        if not args.no_open:
            webbrowser.open(url)
        return
    if shutil.which("claude") is None:
        print("Note: the claude command isn't installed here. Each step's session needs Claude Code, signed in.")
    try:
        app = App(repo)
    except (OSError, ValueError, TypeError, KeyError) as err:
        sys.exit(f"The homework page couldn't read steps.toml: {err}")
    server = serve(app, args.port)
    port = server.server_address[1]
    (app.hub.dir / "server.json").write_text(json.dumps({"port": port}))   # where page.py finds it
    app.start()
    url = f"http://localhost:{port}"
    print(f"{app.a.title}\nThe homework page is at {url}\n"
          "Leave this terminal open while you work. To stop the page, press Ctrl-C here.", flush=True)
    if not args.no_open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped. Each step's Claude session is still saved; the page shows how to go back to it.")
