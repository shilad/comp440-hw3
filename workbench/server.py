"""The workbench: a homework write-up in the browser, with one Claude Code session per step.

    uv run workbench <student repo> --steps hw3          # serve http://localhost:8440
    uv run workbench demo hw3 ~/hw3-try                  # make a scratch repo to try it in

Only Python's standard library is used. The student runs each step's Claude Code session in their
own terminal, with the command the page gives; the page reads what the session did from its
transcript.
"""

from __future__ import annotations

import argparse
import io
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import tomllib
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import steps as stepmod
from .sessions import Hub

STATIC = stepmod.PACKAGE / "static"


class App:
    def __init__(self, repo: Path, assignment: stepmod.Assignment):
        self.repo, self.a = repo, assignment
        self.hub = Hub(assignment, repo)
        self.hub.locked = self.locked
        self.log: list[dict] = []
        self.commit_lock = threading.Lock()
        threading.Thread(target=self.watch, daemon=True).start()

    def locked(self, step_id: str) -> bool:
        return next(x for x in stepmod.status(self.a, self.repo, self.hub.marked()) if x["id"] == step_id)["locked"]

    def note(self, text: str) -> None:
        self.log.append({"t": time.time(), "text": text})

    # -- what the page polls ---------------------------------------------------------------
    def assignment(self) -> dict:
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
                       "body": stepmod.body(s, a, self.repo)} for s in a.steps],
            "repo": str(self.repo),
        }

    def state(self) -> dict:
        status = stepmod.status(self.a, self.repo, self.hub.marked())
        sessions = {}
        for sid, s in self.hub.sessions.items():
            s.refresh()
            last = next((e for e in reversed(s.events) if e["kind"] in ("tool", "slot", "claude", "permission")), None)
            sessions[sid] = {"state": s.state, "now": s.now, "busy": s.busy, "totals": s.totals,
                             "status": (s.status or {}).get("text"),
                             "events": len(s.events),
                             "pending": s.state == "asking",
                             "last": (last or {}).get("label") or ((last or {}).get("text") or "")[:80]}
        now = next((x["id"] for x in status if not x["complete"] and not x["locked"]), None)
        return {"steps": status, "sessions": sessions, "committed": sorted(stepmod.part_done_commits(self.repo)),
                "now": now, "log": self.log[-20:]}

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

    # -- commits -----------------------------------------------------------------------
    def watch(self) -> None:
        """Commit a part as soon as its steps are complete, however they got that way."""
        while True:
            time.sleep(3)
            try:
                self.commit_finished_parts()
            except Exception as err:  # noqa: BLE001
                self.note(f"Couldn't check for finished parts: {err}")

    def git(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(["git", *args], cwd=self.repo, capture_output=True, text=True, timeout=60)

    def commit_finished_parts(self) -> None:
        if not self.a.commit_parts or not (self.repo / ".git").exists():
            return
        with self.commit_lock:
            status = stepmod.status(self.a, self.repo, self.hub.marked())
            done = stepmod.part_done_commits(self.repo)
            for n in sorted(self.a.parts):
                mine = [s for s in status if s["part"] == n]
                if not mine or n in done or not all(s["complete"] for s in mine):
                    continue
                if self.a.before_commit:
                    script = self.a.before_commit.split()[-1]
                    if (self.repo / script).exists():
                        subprocess.run(self.a.before_commit, shell=True, cwd=self.repo,
                                       capture_output=True, timeout=120)
                paths = [self.a.writeup, "TRANSCRIPT.md"]
                for s in self.a.steps:
                    if s.part == n:
                        paths += [str(f.relative_to(self.repo)) for pat in s.files
                                  for f in stepmod.present(self.repo, pat)]
                paths = [p for p in dict.fromkeys(paths) if (self.repo / p).exists()]
                if paths:  # git refuses the whole add if one path is git-ignored
                    ignored = set(self.git("check-ignore", "--", *paths).stdout.split())
                    paths = [p for p in paths if p not in ignored]
                if paths:
                    self.git("add", "--", *paths)
                r = self.git("commit", "--allow-empty", "-m", f"Part {n} done")
                if r.returncode:
                    self.note(f"Couldn't commit Part {n}: {(r.stderr or r.stdout).strip()[-200:]}")
                    continue
                self.note(f"Every step of Part {n} is complete, so I committed it as “Part {n} done”.")
                if self.a.push:
                    p = self.git("push")
                    self.note("Pushed to GitHub." if p.returncode == 0
                              else f"The push didn't go through ({p.stderr.strip()[-120:]}). The commit is safe on this laptop.")


def handler(app: App):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *args):  # quiet
            pass

        def send_json(self, data, code=200):
            body = json.dumps(data).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def read_json(self) -> dict:
            n = int(self.headers.get("Content-Length") or 0)
            return json.loads(self.rfile.read(n) or b"{}")

        def do_GET(self):
            path = urlparse(self.path).path
            if path == "/api/assignment":
                return self.send_json(app.assignment())
            if path == "/api/state":
                return self.send_json(app.state())
            if path == "/api/sessions":
                return self.send_json({k: s.snapshot() for k, s in app.hub.sessions.items()})
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
            data = f.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", mimetypes.guess_type(f.name)[0] or "application/octet-stream")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):
            parts = urlparse(self.path).path.strip("/").split("/")
            body = self.read_json()
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
                n = int(body["checkpoint"])
                if not 1 <= n <= len(cps):
                    return self.send_json({"error": f"Step {label} has {len(cps)} checkpoints; there is no {n}."}, 400)
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
                app.hub.mark(sid, bool(body.get("done", True)))
                app.commit_finished_parts()
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


SKIP = {".git", ".venv", "__pycache__", ".cache", ".pytest_cache", "runs", ".env", ".workbench"}


def starter_code(src: Path, where: Path, folder: Path | None) -> str:
    """Copy the assignment's starter code into `where`; say where it came from.

    `folder` is a template checkout given on the command line. Otherwise the steps file's [demo]
    table says where: `repo` and `branch`, a repository cloned fresh each time (HW3's own, since
    Nov 9), or `path`, a folder at `git_ref` in the repository this package lives in. The brief's
    pages come from `git_ref`. Either way the demo takes the newest commit without merging it
    anywhere.
    """
    spec = tomllib.loads((src / "steps.toml").read_text(encoding="utf-8")).get("demo") or {}
    skip = set(spec.get("skip", []))
    if folder:
        if not folder.is_dir():
            sys.exit(f"{folder} isn't a folder")
        copy_folder(folder, where, skip)
        return f"the starter code from {folder}"
    ref, sub = spec.get("git_ref"), (spec.get("path") or "").strip("/")
    if spec.get("repo"):
        said = clone(spec["repo"], spec.get("branch") or "main", where, skip)
    elif ref and sub:
        said = f"the starter code in {sub}/"
    else:
        return ""
    if not ref:
        return said
    top = subprocess.run(["git", "-C", str(stepmod.PACKAGE), "rev-parse", "--show-toplevel"],
                         capture_output=True, text=True)
    root, why = top.stdout.strip(), ""
    if top.returncode:
        why = "this copy of the workbench isn't in a git repository"
    else:
        if ref.startswith("origin/"):  # take the branch's newest commit, if the network allows
            subprocess.run(["git", "-C", root, "fetch", "-q", "origin", ref.removeprefix("origin/")],
                           capture_output=True, timeout=120)
        commit = subprocess.run(["git", "-C", root, "rev-parse", "--short", ref], capture_output=True, text=True)
        if commit.returncode:
            why = f"{ref} isn't in {root}"
    if why:
        if spec.get("repo"):
            return f"{said}; the brief's pages are the copies shipped with the workbench, since {why}"
        return f"no starter code: {why} (use --template)"
    if not spec.get("repo") and not extract(root, ref, sub, where, skip):
        return f"no starter code: {ref} has no folder {sub} (use --template)"
    for path, dest in (spec.get("pages") or {}).items():   # the brief's pages, where a student's repo has them
        if not extract(root, ref, path.strip("/"), where / dest):
            print(f"Note: {ref} has no {path}; the page uses the copy shipped with the workbench.")
    return f"{said} and the brief's pages at {ref} ({commit.stdout.strip()})"


def copy_folder(folder: Path, where: Path, skip: set[str]) -> None:
    """Copy `folder` into `where`, leaving out SKIP at any depth and `skip` at the top."""
    shutil.copytree(folder, where, dirs_exist_ok=True,
                    ignore=lambda d, names: [n for n in names if n in SKIP
                                             or (Path(d) == folder and n in skip)])


def clone(url: str, branch: str, where: Path, skip: set[str]) -> str:
    """Copy the newest commit of `branch` at `url` into `where`, without its .git; say which.
    Stops with a plain message if it can't be cloned."""
    with tempfile.TemporaryDirectory(prefix="workbench-") as tmp:
        try:
            got = subprocess.run(["git", "clone", "-q", "--depth", "1", "--branch", branch, url, tmp],
                                 capture_output=True, text=True, timeout=300,
                                 env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})  # never ask for a login
            why = "" if got.returncode == 0 else \
                (got.stderr.strip().splitlines() or ["git gave no reason"])[-1].removeprefix("fatal: ")
        except (OSError, subprocess.TimeoutExpired) as err:
            why = str(err)
        if why:
            sys.exit(f"Stopped: couldn't copy the starter code from {url} ({branch}): {why}\n"
                     f"Check the network and try again, or use --template with a folder that has it.")
        commit = subprocess.run(["git", "-C", tmp, "rev-parse", "--short", "HEAD"],
                                capture_output=True, text=True).stdout.strip()
        copy_folder(Path(tmp), where, skip)
    return f"the starter code from {url} ({branch}, {commit})"


def extract(root: str, ref: str, path: str, dest: Path, skip: set[str] = frozenset()) -> bool:
    """Write the file or folder `path` at `ref` to `dest`. False if `ref` has no such path."""
    tar = subprocess.run(["git", "-C", root, "archive", "--format=tar", ref, path], capture_output=True)
    if tar.returncode:
        return False
    with tarfile.open(fileobj=io.BytesIO(tar.stdout)) as archive:
        for member in archive.getmembers():
            if not member.isfile():
                continue
            rel = Path(member.name).relative_to(path)
            if SKIP & set(rel.parts) or str(rel) in skip:
                continue
            out = dest / rel if rel.parts else dest
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(archive.extractfile(member).read())
    return True


def demo(name: str, where: Path, folder: Path | None = None) -> None:
    """A scratch git repository to try the page in: the starter code and a WRITEUP.md."""
    src = stepmod.BUILT_IN / name
    if not (src / "steps.toml").is_file():
        sys.exit(f"No built-in assignment called {name}")
    if where.exists() and any(where.iterdir()):
        sys.exit(f"{where} isn't empty")
    where.mkdir(parents=True, exist_ok=True)
    try:
        origin = starter_code(src, where, folder)
    except SystemExit:
        shutil.rmtree(where, ignore_errors=True)   # leave no half-made folder behind
        raise
    writeup = stepmod.load(src / "steps.toml").writeup
    if not (where / writeup).exists():
        shutil.rmtree(where)
        sys.exit(f"Stopped: {origin or 'no starter code'}, and it has no {writeup}, which every step "
                 f"is checked against. Use --template with a folder that has one.")
    ignore = where / ".gitignore"
    lines = ignore.read_text().splitlines() if ignore.exists() else []
    lines += [x for x in (".env", ".workbench/") if x not in lines]
    ignore.write_text("\n".join(lines) + "\n")
    for args in (["init", "-q"], ["add", "."], ["commit", "-q", "-m", "Start from the template"]):
        subprocess.run(["git", *args], cwd=where, check=True)
    print(f"Made {where}, with {origin}.")
    print(f"Now run:\n  uv run workbench {where} --steps {name}")


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        p = argparse.ArgumentParser(prog="workbench demo")
        p.add_argument("demo")
        p.add_argument("name")
        p.add_argument("where", type=Path)
        p.add_argument("--template", type=Path, help="copy the starter code from this folder instead")
        args = p.parse_args()
        return demo(args.name, args.where.expanduser().resolve(),
                    args.template.expanduser().resolve() if args.template else None)
    p = argparse.ArgumentParser(prog="workbench", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("repo", type=Path, nargs="?", default=Path("."), help="the student's repository (default: here)")
    p.add_argument("--steps", help="a steps.toml, or a built-in assignment's name (hw3, retrieval)")
    p.add_argument("--port", type=int, default=8440)
    p.add_argument("--no-open", action="store_true")
    p.add_argument("--model", help="put --model in every step's command (default: the assignment's, else Claude Code's own)")
    p.add_argument("--effort", choices=["low", "medium", "high", "xhigh", "max"],
                   help="put --effort in every step's command (default: the assignment's, else Claude Code's own)")
    args = p.parse_args()
    repo = args.repo.expanduser().resolve()
    if shutil.which("claude") is None:
        print("Note: the `claude` command isn't installed here. Each step's session needs Claude Code, signed in.")
    # `uv run workbench` sets VIRTUAL_ENV to the workbench's own environment. The script the page
    # runs before a part's commit would inherit it, and a `uv run` in the student's repository
    # would warn that it doesn't match.
    os.environ.pop("VIRTUAL_ENV", None)
    a = stepmod.load(stepmod.find(args.steps, repo))
    if args.model:
        a.model = args.model
    if args.effort:
        a.effort = args.effort
    app = App(repo, a)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler(app))
    # Where the `page` skill's script finds this server.
    (app.hub.dir / "server.json").write_text(json.dumps({"port": args.port}))
    url = f"http://localhost:{args.port}"
    print(f"{a.title}\nRepository: {repo}\nOpen {url}  (Ctrl-C to stop)")
    if not args.no_open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped. The step sessions are Claude Code's own; `claude --resume` goes back to any of them.")


if __name__ == "__main__":
    main()
