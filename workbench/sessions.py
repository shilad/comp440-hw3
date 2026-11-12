"""One Claude Code session per step, which the student runs in their own terminal.

The page never talks to Claude. For each step it writes two files into .workbench/:

  - <step>.md, the step's prompt: the tutor rules every step shares, plus this step's text, brief
    and write-up slots. The command appends it to Claude Code's own system prompt;
  - <step>.json, the step's settings: the calls it may make without asking, and the hook
    (guard.py) that refuses commits, pushes and anything touching the student's key.

It shows the student the `claude` command that starts a new conversation for the step with those
files. The command names no session id, so it works however many times it is run, and the page
finds each conversation itself: every transcript Claude Code recorded for this folder whose first
message is "Start step <label>." (the session ids that older copies kept in .workbench/state.json
still count). Once the step has been worked on, the page also shows the `claude --resume` command
that goes back to its latest conversation. Every step after the first also shows a
one-line prompt, "Start step 0c. Read .workbench/0c.md and follow it ...", which the student pastes
into the Claude session they already have open: that session then serves the new step. So one
conversation can hold several steps, each from its own "Start step <label>." message to the next
one, and the page reads each step's record from those stretches, wherever they are. Every step's
settings allow the shell commands that any step allows, so a continued session asks no more often
than a new one would. `--setting-sources user` keeps the repository's own CLAUDE.md and
.claude/ settings out, so the step's prompt is the whole brief; the student's own Claude Code
settings still apply. `--plugin-dir .workbench/plugin` loads the `page` skill, with which Claude
tells the page what it is doing (a status line), what the student expects a run to show, and which
of the step's checkpoints that leave no file or answer behind the student has reached; it runs
.workbench/page.py, which posts to the server, and the server keeps what it was told in
.workbench/page.jsonl. Files and commands use the step's label, as 0b, which is what the page
calls it.

The page shows each step's checkpoints (what counts, from the steps file), ticked by their files or
answers, by Claude, or by a later checkpoint, and the student's record of working on the step:
what they expected, what they asked Claude to do, what Claude ran and what came back, in order,
with each checkpoint marked where it was reached, ending on the step's open question. The record
shows what happened, never the next move.

What the page shows of a session it reads from the transcript Claude Code writes anyway,
~/.claude/projects/<folder>/<session id>.jsonl: the student's messages, Claude's replies, and each
tool call, which labels.py turns into a plain label and a kind. Three things a transcript doesn't
hold come from the hook's log, .workbench/hooks.jsonl: a refused call, Claude Code asking the
student's OK in the terminal, and the write-up's text before and after each edit of it, from
which the page works out which answers that edit wrote.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from . import labels
from .steps import (Assignment, Step, body, checkpoints, filled, layout, present, read_slots, run_yourself,
                    status, step_keys)

REFUSED = ("git commit", "git push", "git reset", "git checkout", "git restore", "git stash", "git clean")
GUARD = Path(__file__).parent / "guard.py"
PAGE = Path(__file__).parent / "page.py"
PLUGIN = Path(__file__).parent / "plugin"
PAGE_CALL = "Bash(python3 .workbench/page.py:*)"
QUIET = 15 * 60   # a turn with no transcript activity this long probably ended with the terminal
SAVED = re.compile(r"Saved to (\S+)")
VERDICT = re.compile(r"^Verdict: (.+)$", re.M)
EXPLANATION = re.compile(r"^Explanation: (.+)$", re.M)
LOOKUPS = re.compile(r"^Lookups: (\d+)", re.M)


KEY = re.compile(r"sk-ant-[^\s\"'`<>]*")
# The message that starts a step, in a new session ("Start step 0b.") or in one that was on another
# step (the page's prompt to continue). A conversation's stretch for a step runs from it to the next.
START = re.compile(r"^Start step (\d+[a-z])\.")


def continue_prompt(label: str) -> str:
    """What the student pastes into an open Claude session to go on with step `label` in it."""
    return (f"Start step {label}. Read .workbench/{label}.md and follow it from now on, in place of "
            "your instructions for any other step.")


def said_by_student(d: dict) -> str | None:
    """The student's own words in one transcript line, or None: Claude's lines, tool results, and
    text Claude Code adds itself (a command's output, a meta line) are not the student's."""
    if d.get("type") != "user" or d.get("isMeta") or d.get("isSidechain"):
        return None
    content = (d.get("message") or {}).get("content")
    if isinstance(content, list) and any(isinstance(b, dict) and b.get("type") == "tool_result" for b in content):
        return None
    said = text_of(content).strip()
    return said if said and not said.startswith("<") else None


def when(t: float) -> str:
    return datetime.fromtimestamp(t).astimezone().isoformat(timespec="seconds")


def claude_home() -> Path:
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")


def stamp(ts: str | None) -> float:
    try:
        return datetime.fromisoformat((ts or "").replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def dq(text: str) -> str:
    """A double-quoted shell word."""
    return '"' + "".join("\\" + c if c in '"$`\\' else c for c in text) + '"'


def text_of(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        out = []
        for b in content:
            if isinstance(b, dict) and b.get("type") == "text":
                out.append(b.get("text", ""))
            elif isinstance(b, dict) and b.get("type") == "image":
                out.append("[an image]")
        return "\n".join(out)
    return ""


DENIED = "The user doesn't want to proceed with this tool use"
INTERRUPTED = "[Request interrupted by user"


class StepSession:
    def __init__(self, hub: "Hub", step: Step):
        self.hub, self.step = hub, step
        self.lock = threading.Lock()
        self.events: list[dict] = []
        self.state, self.now, self.busy = "not started", "", False
        self.totals = {"turns": 0, "tools": 0, "input_tokens": 0, "output_tokens": 0, "seconds": 0.0}
        self.seen: tuple | None = None   # (transcript, hook log, page log) sizes when last read
        self.status: dict | None = None   # the last status line Claude posted
        self.path: Path | None = None

    # -- the command --------------------------------------------------------------------------
    @property
    def session_id(self) -> str | None:
        """The session id .workbench/state.json gave this step, from before the new-session
        command stopped naming one; None for a step that never had one."""
        return self.hub.known_id(self.step.id)

    def stretches(self) -> list[dict]:
        """This step's stretches of the homework's conversations, oldest first."""
        return [x for x in self.hub.stretches() if x["step"] == self.step.id]

    def latest_session(self) -> str | None:
        """The conversation that served this step last."""
        mine = self.stretches()
        return mine[-1]["session"] if mine else None

    def transcript(self) -> Path | None:
        """The file of the conversation this step was last worked in; before that, of the step's
        own session from state.json, if it exists."""
        mine = self.stretches()
        if mine:
            return mine[-1]["path"]
        return self.hub.find(self.session_id) if self.session_id else None

    def prepare(self) -> None:
        """Write this step's prompt and settings into .workbench/, if they have changed. The
        settings allow every shell command that any step allows, because a session started for one
        step may go on to the next with the page's prompt, and keeps the settings it started with.
        Other rules (an edit of instructions.md in 3b) stay with their own step's new session."""
        d, s = self.hub.dir, self.step
        shared = [r for x in self.hub.assignment.steps for r in x.allow if r.startswith("Bash(")]
        settings = {
            "permissions": {"allow": list(dict.fromkeys(self.hub.assignment.allow + shared + s.allow + [PAGE_CALL]))},
            "hooks": {
                "PreToolUse": [{"matcher": "*", "hooks": [{"type": "command", "command": self.hub.hook("pre")}]}],
                "PostToolUse": [{"matcher": "Edit|Write|MultiEdit",
                                 "hooks": [{"type": "command", "command": self.hub.hook("post")}]}],
                "Notification": [{"matcher": "", "hooks": [{"type": "command", "command": self.hub.hook("notify")}]}],
            },
        }
        label = self.hub.assignment.label(s)
        for name, text in ((f"{label}.md", self.hub.prompt(s)), (f"{label}.json", json.dumps(settings, indent=2))):
            f = d / name
            if not f.exists() or f.read_text(encoding="utf-8") != text:
                f.write_text(text, encoding="utf-8")

    def flags(self) -> str:
        a, label = self.hub.assignment, self.hub.assignment.label(self.step)
        model = (f" --model {a.model}" if a.model else "") + (f" --effort {a.effort}" if a.effort else "")
        return (f"{model} --setting-sources user --settings .workbench/{label}.json "
                f"--append-system-prompt-file .workbench/{label}.md --plugin-dir .workbench/plugin")

    def command(self) -> str:
        """The terminal command that starts a new conversation for this step. It names no session
        id, so it works however many times it is run: Claude Code gives each run its own, and the
        page finds the conversation by its first message, "Start step <label>."."""
        a, s = self.hub.assignment, self.step
        label = a.label(s)
        return f"claude -n {dq(f'{label} {s.title}')}{self.flags()} {dq(f'Start step {label}.')}"

    def back_command(self) -> str | None:
        """The terminal command that opens this step's latest conversation again, once there is
        one. If that conversation has gone on to another step since, it also moves it back onto
        this one."""
        label = self.hub.assignment.label(self.step)
        mine = self.stretches()
        if mine:
            back = "" if mine[-1]["last"] else f" {dq(continue_prompt(label))}"
            return f"claude --resume {mine[-1]['session']}{self.flags()}{back}"
        if self.session_id and self.hub.find(self.session_id):
            return f"claude --resume {self.session_id}{self.flags()} {dq(continue_prompt(label))}"
        return None

    def continue_prompt(self) -> str | None:
        """The prompt that moves an open session onto this step; none for the first step, which
        has no earlier session to go on from."""
        steps = self.hub.assignment.steps
        return continue_prompt(self.hub.assignment.label(self.step)) if steps and steps[0].id != self.step.id else None

    # -- reading what the session did -----------------------------------------------------------
    def refresh(self) -> None:
        """Rebuild the events from the conversations and the hook log, if any of them has grown."""
        with self.lock:
            key = (self.hub.conversations_key(), self.hub.hooks_size(), self.hub.page_size())
            if key == self.seen and self.state not in ("thinking", "working"):
                return
            self.seen = key
            self.build(self.stretches())

    def build(self, stretches: list[dict]) -> None:
        events: list[dict] = []
        tools: dict[str, dict] = {}
        usage: dict[str, dict] = {}
        turns: list[list[float]] = []      # [start, last activity] per student message
        last_t, last_kind = 0.0, None

        where: dict[str, str | None] = {"session": None}   # the conversation the line being read is in

        def emit(t: float, kind: str, **data: Any) -> dict:
            e = {"t": t, "kind": kind, "session": where["session"], **data}
            events.append(e)
            return e

        # Each stretch of a conversation that served this step, oldest first; how the latest one
        # ends says whether Claude is working or waiting. When more than one conversation served
        # it, a line marks where each begins, so the panel shows them all, in order.
        many = len({st["session"] for st in stretches}) > 1
        lines, began = [], set()
        for st in stretches:
            if many and st["session"] not in began and st["lines"]:
                lines.append({"_begins": st["session"], "timestamp": st["lines"][0].get("timestamp")})
            began.add(st["session"])
            lines += [{**d, "_session": st["session"]} for d in st["lines"]]
        for d in lines:
            if "_begins" in d:
                where["session"] = d["_begins"]
                emit(stamp(d["timestamp"]) - 0.001, "note", text=f"Claude session {d['_begins'][:8]} begins here.")
                continue
            where["session"] = d["_session"]
            kind = d.get("type")
            if kind not in ("user", "assistant") or d.get("isSidechain"):
                continue
            t, m = stamp(d.get("timestamp")), d.get("message") or {}
            content = m.get("content")
            if kind == "assistant":
                if m.get("id") and m.get("usage"):
                    usage[m["id"]] = m["usage"]
                for b in content if isinstance(content, list) else []:
                    if b.get("type") == "text" and b.get("text", "").strip():
                        emit(t, "claude", text=b["text"])
                    elif b.get("type") == "tool_use":
                        inp = b.get("input") or {}
                        if b.get("name") == "Bash":   # leave out the page skill's own calls, keep the rest
                            real = labels.without_page_calls(inp.get("command", ""))
                            if real != inp.get("command", "").strip():   # its description was of the whole
                                inp = {k: v for k, v in inp.items() if k != "description"}
                            inp = {**inp, "command": real}
                        if b.get("name") == "Bash" and not inp["command"]:
                            cat, label = "page", "Updated the homework page"
                        else:
                            cat, label = labels.describe(b.get("name", ""), inp, self.hub.repo)
                            if cat in ("read", "write") and self.hub.secret(str(inp.get("file_path") or "")):
                                cat = "secret"      # never a link on the page, never in the record
                        detail = inp.get("command") or inp.get("file_path") or inp.get("pattern") or ""
                        tools[b.get("id")] = emit(t, "tool", id=b.get("id"), tool=b.get("name"), category=cat,
                                                  label=label, detail=str(detail)[:400], status="running", ended=None)
                last_kind = "end" if m.get("stop_reason") == "end_turn" else "assistant"
            else:
                if d.get("isMeta"):
                    continue
                results = [b for b in content if isinstance(b, dict) and b.get("type") == "tool_result"] \
                    if isinstance(content, list) else []
                for b in results:
                    e = tools.get(b.get("tool_use_id"))
                    if not e:
                        continue
                    out = text_of(b.get("content")) or json.dumps(b.get("content"))[:2000]
                    denied = DENIED in out
                    e.update(status="denied" if denied else "error" if b.get("is_error") else "ok",
                             ended=t, output=out[-1500:])
                    if denied:
                        e["label"] += " (you said no)"
                if results:
                    last_kind = "user"
                else:
                    said = text_of(content).strip()
                    if not said:
                        continue
                    if said.startswith(INTERRUPTED):
                        emit(t, "note", text="You stopped Claude.")
                        last_kind = "end"
                    elif said.startswith("<command-name>"):
                        name = said.split("<command-name>", 1)[1].split("</command-name>", 1)[0]
                        emit(t, "note", text=f"You typed {name}.")
                    elif said.startswith("<"):
                        continue   # a command's output or other text Claude Code adds, not the student's
                    else:
                        emit(t, "student", text=said, opening=not turns or bool(START.match(said)))
                        turns.append([t, t])
                        last_kind = "user"
            if turns:
                turns[-1][1] = max(turns[-1][1], t)
            last_t = max(last_t, t)

        # What only the hook saw: refusals, permission questions, and the write-up around each edit,
        # from each conversation while it served this step.
        before: dict[str, str] = {}
        asked_at = 0.0
        hooked = sorted(((r, st["session"]) for st in stretches for r in self.hub.hook_records(st["session"])
                         if st["start"] <= r["t"] < st["end"]), key=lambda x: x[0]["t"])
        for r, sid in hooked:
            where["session"] = sid
            if r["kind"] == "refused":
                emit(r["t"], "note", text=r["text"])
            elif r["kind"] == "asking":
                emit(r["t"], "permission", label=r.get("text") or "Claude asked your permission", detail="", answer="asked")
                asked_at = max(asked_at, r["t"])
            elif r["kind"] == "before":
                before[r.get("tool_use_id") or ""] = r["text"]
            elif r["kind"] == "after":
                old = read_slots(before.pop(r.get("tool_use_id") or "", ""))
                new = read_slots(r["text"])
                mine = set(step_keys(self.step, new))
                for k, answer in new.items():
                    if answer != old.get(k) and (k in old or filled(answer)):
                        emit(r["t"] + 0.001, "slot", key=k, filled=filled(answer), outside=k not in mine,
                             answer=answer, label=("Wrote into" if filled(answer) else "Cleared") + f" “{k.split(' / ')[-1]}”")
        # What Claude told the page with the `page` skill, by step label, from any conversation.
        said = None
        where["session"] = None
        for r in self.hub.page_records(self.step.id):
            if r["kind"] == "status":
                said = emit(r["t"], "status", text=r["text"])
            elif r["kind"] == "done":
                emit(r["t"], "note", text="Claude marked this step done.")
            elif r["kind"] in ("checkpoint", "milestone"):
                emit(r["t"], "note", text=f"Claude ticked “{r.get('text', '')}”.")
            elif r["kind"] == "expected":
                emit(r["t"], "note", text=f"Claude noted that you expect “{r.get('text', '')}”.")
        self.status = said and {"text": said["text"], "t": said["t"]}
        events.sort(key=lambda e: e["t"])
        for n, e in enumerate(events):
            e["n"] = n

        tins = touts = 0
        for u in usage.values():
            tins += u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0) + u.get("cache_creation_input_tokens", 0)
            touts += u.get("output_tokens", 0)
        self.events = events
        self.totals = {"turns": len(turns), "tools": sum(e["kind"] == "tool" for e in events),
                       "input_tokens": tins, "output_tokens": touts,
                       "seconds": round(sum(b - a for a, b in turns), 1)}

        running = [e for e in events if e["kind"] == "tool" and e["status"] == "running"]
        latest = stretches[-1] if stretches else None
        if not latest:
            self.state, self.now = "not started", ""
        elif not latest["last"]:
            # The conversation went on to another step: it is that step's now.
            self.state, self.now = "moved on", f"The Claude session went on to step {latest['next']}."
            for e in running:
                e["status"] = "unknown"
        elif asked_at > last_t:
            self.state, self.now = "asking", "Waiting for your permission in the terminal"
        elif last_kind in ("end", None):
            self.state, self.now = "your turn", "Your turn, in the terminal"
        elif time.time() - last_t > QUIET:
            self.state, self.now = "stopped", "Nothing has happened for 15 minutes. The terminal may be closed."
            for e in running:
                e["status"] = "unknown"
        elif running:
            self.state, self.now = "working", running[-1]["label"]
        else:
            self.state, self.now = "thinking", "Thinking"
        self.busy = self.state in ("thinking", "working", "asking")

    def record(self, last: int | None = 14) -> dict:
        """What counts in the step (its checkpoints, each ticked or not) and the student's record of
        working on it: what they expected, what they asked, what Claude ran and what came back, in
        order, with each checkpoint marked where it was reached, and the question still open. The
        page shows the `last` entries; the copy saved for grading keeps them all (last=None)."""
        a, s, repo = self.hub.assignment, self.step, self.hub.repo
        label = a.label(s)
        st = next(x for x in status(a, repo, self.hub.marked()) if x["id"] == s.id)
        slots, pages = self.hub.slots(), self.hub.page_records(s.id)
        marks = {r.get("n"): r["t"] for r in pages if r["kind"] in ("checkpoint", "milestone")}
        cps, done_at, covered = [], [], set()
        for i, c in enumerate(checkpoints(s), 1):
            item = {"n": i, "text": c.text, "task": c.task or c.text, "auto": bool(c.files or c.slots), "files": [], "slots": [],
                    "tick": c.tick or bool(c.files or c.slots)}
            t = None
            if c.files or c.slots:
                found = [str(f.relative_to(repo)) for pat in c.files for f in present(repo, pat)]
                keys = step_keys(Step(id=s.id, part=s.part, title="", slots=c.slots), slots) if c.slots else []
                covered.update(keys)
                ok = all(present(repo, pat) for pat in c.files) and all(filled(slots.get(k)) for k in keys)
                item["files"] = [f for f in found if not self.hub.secret(f)            # never a link to .env
                                 and not (s.hide_results and f.startswith("runs/"))][-2:]
                item["slots"] = [self.slot(k, slots) for k in keys]
                wp = repo / a.writeup
                when = max([(repo / f).stat().st_mtime for f in found]
                           + ([wp.stat().st_mtime] if keys and wp.exists() else []), default=None)
                t = self.hub.seen(f"{s.id}/{i}", ok, when)
            elif c.tick and i in marks:          # one with tick = false is never ticked
                t = marks[i]
            cps.append(item)
            done_at.append(t)
        reached = list(done_at)                  # when each was reached, as far as anything shows
        # A checkpoint with a file or answers of its own is ticked only by them, so a student can
        # see what is missing. One without (a prediction, say) is ticked by Claude, or by any later
        # checkpoint being reached. One with `tick = false` is never ticked. The step being complete
        # ticks nothing by itself.
        for i in range(len(cps) - 2, -1, -1):
            if done_at[i] is None and not cps[i]["auto"] and cps[i]["tick"]:
                done_at[i] = next((t for t in done_at[i + 1:] if t is not None), None)
        for i, item in enumerate(cps):
            item["done"] = done_at[i] is not None
        extra = [k for k in step_keys(s, slots) if k not in covered]   # answers no checkpoint names
        if extra:
            cps.append({"n": None, "text": "Your answers in " + a.writeup, "auto": True, "files": [], "tick": True,
                        "done": all(filled(slots.get(k)) for k in extra),
                        "slots": [self.slot(k, slots) for k in extra]})

        # The record is the latest conversation's: when a step was started again in a new session,
        # the earlier conversation stays in the step's conversation panel ("The conversation"), in
        # TRANSCRIPT.md, and one `claude --resume` away.
        latest = self.latest_session()
        entries = []
        for e in self.events:
            if e.get("session") not in (latest, None):
                continue
            if e["kind"] == "student" and not e.get("opening"):
                entries.append({"kind": "asked", "t": e["t"], "text": e["text"][:400]})
            elif e["kind"] == "tool" and e["category"] in ("run", "write"):
                out = e.get("output") or ""
                saved = SAVED.search(out)
                entries.append({"kind": "ran", "t": e["t"], "text": e["label"], "status": e["status"],
                                "file": saved.group(1) if saved else None})
                verdict = VERDICT.search(out)
                if verdict:
                    why, n = EXPLANATION.search(out), LOOKUPS.search(out)
                    entries.append({"kind": "said", "t": (e.get("ended") or e["t"]) + 0.001,
                                    "verdict": verdict.group(1).strip(), "reason": why.group(1).strip() if why else "",
                                    "lookups": int(n.group(1)) if n else None, "what": e["label"],
                                    "file": saved.group(1) if saved else None})
        # What the student expected, as Claude noted it, turns their message into a prediction.
        for r in (r for r in pages if r["kind"] == "expected"):
            said = [x for x in entries if x["kind"] == "asked" and x["t"] <= r["t"]]
            if said:
                said[-1].update(kind="expected", verdict=r.get("text", ""))
            else:
                entries.append({"kind": "expected", "t": r["t"], "text": "", "verdict": r.get("text", "")})
        entries.sort(key=lambda x: x["t"])
        guess = None
        for x in entries:
            if x["kind"] == "expected":
                guess = x["verdict"]
            elif x["kind"] == "said":
                x["expected"], guess = guess, None
        summary = self.summary(cps, reached, entries)
        # Each checkpoint is marked where it was reached: on the last entry before that moment.
        for i, item in enumerate(cps[:len(reached)]):
            if reached[i] is None:
                continue
            text = item["text"]
            before = [x for x in entries if x["t"] <= reached[i] + 2]
            if before:
                target = max(before, key=lambda x: x["t"])
            else:
                target = {"kind": "mark", "t": reached[i]}
                entries.append(target)
            target.setdefault("reached", []).append(text)
        entries.sort(key=lambda x: x["t"])
        open_q = next((x for c in cps for x in c["slots"] if not x["filled"]), None)
        todo = next((c["text"] for c in cps if c["tick"] and not c["done"]), None)
        if open_q and open_q["plain"]:     # the name at the top, not a question under the step
            now = {"plain": f"type your {open_q['question'].lower()} after {open_q['question']}: at the top "
                            f"of {a.writeup}, in your editor."}
        elif open_q:
            now = {"question": open_q["question"], "how": f"Write your answer in {a.writeup}, under {label}, in your editor."}
        else:
            now = {"todo": todo} if todo and not st["complete"] else {"done": True}
        shown = entries if last is None else entries[-last:]
        return {"checkpoints": cps, "summary": summary, "entries": shown,
                "earlier": len(entries) - len(shown), "now": now,
                "counts": {"messages": sum(x["kind"] in ("asked", "expected") for x in entries),
                           "commands": sum(x["kind"] == "ran" for x in entries)}}

    def slot(self, k: str, slots: dict[str, str]) -> dict:
        """One answer slot as the page shows it: its question, the answer, and where to type it."""
        plain = " / " not in k                  # Name: at the top of the write-up
        where = (f"Not written yet. Type it after {k}: at the top of {self.hub.assignment.writeup}." if plain else
                 f"Not written yet. Type it in {self.hub.assignment.writeup}, under {self.hub.assignment.label(self.step)}.")
        return {"question": k.split(" / ")[-1], "answer": slots.get(k, ""), "filled": filled(slots.get(k)),
                "plain": plain, "todo": where}

    def summary(self, cps: list[dict], reached: list, entries: list[dict]) -> list[dict]:
        """The record at the level the page shows by default: the checkpoints reached, what the
        student predicted, and what came back beside it. Every message and command is one click
        further down, and the whole conversation one more."""
        out = [{"kind": "predicted", "t": x["t"], "text": x["verdict"]} for x in entries if x["kind"] == "expected"]
        out += [{"kind": "result", "t": x["t"], "verdict": x["verdict"], "expected": x.get("expected"),
                 "lookups": x["lookups"], "what": x["what"], "file": x["file"]} for x in entries if x["kind"] == "said"]
        results = [x for x in out if x["kind"] == "result"]
        for i, item in enumerate(cps[:len(reached)]):
            if reached[i] is None:
                continue
            text = item["text"]
            near = [x for x in results if abs(reached[i] - x["t"]) <= 5]   # reached by that result
            if near:
                near[-1].setdefault("reached", []).append(text)
            else:
                out.append({"kind": "reached", "t": reached[i], "text": text,
                            "file": item["files"][-1] if item["files"] else None})
        return sorted(out, key=lambda x: x["t"])

    def results(self) -> str | None:
        """The newest file under runs/ of the first `files` entry that has one, for the results
        viewer, which opens nothing outside runs/ (so never .env, never the student's claims). None
        for a step with hide_results, which asks the student not to look at results yet."""
        if self.step.hide_results:
            return None
        for pattern in self.step.files:
            found = [f for f in present(self.hub.repo, pattern)
                     if f.relative_to(self.hub.repo).parts[:1] == ("runs",)]
            if found:
                return str(max(found, key=lambda f: f.stat().st_mtime).relative_to(self.hub.repo))
        return None

    def snapshot(self) -> dict:
        self.refresh()
        locked = self.hub.locked(self.step.id)
        if not locked:
            self.prepare()
        a = self.hub.assignment
        return {"id": self.step.id, "label": a.label(self.step), "state": self.state,
                "now": self.now, "busy": self.busy, "totals": self.totals, "events": list(self.events),
                "started": self.state != "not started", "status": self.status, "record": self.record(),
                "command": None if locked else self.command(),
                "back_command": None if locked else self.back_command(),
                "session_id": self.latest_session() or self.session_id,
                "continue_prompt": None if locked else self.continue_prompt(),
                "model_flags": " ".join(x for x in (f"--model {a.model}" if a.model else "",
                                                    f"--effort {a.effort}" if a.effort else "") if x),
                "results": self.results()}


class Hub:
    """All the step sessions for one repository."""

    def __init__(self, assignment: Assignment, repo: Path):
        self.assignment, self.repo = assignment, repo
        self.dir = repo / ".workbench"
        self.dir.mkdir(exist_ok=True)
        ignore = self.dir / ".gitignore"
        if not ignore.exists():
            ignore.write_text("*\n")
        shutil.copyfile(GUARD, self.dir / "guard.py")
        shutil.copyfile(PAGE, self.dir / "page.py")
        shutil.copytree(PLUGIN, self.dir / "plugin", dirs_exist_ok=True)
        self.write_guard()
        self.state_file = self.dir / "state.json"
        self.state = json.loads(self.state_file.read_text()) if self.state_file.exists() else {}
        self.state_lock = threading.Lock()
        self.locked = lambda step_id: False   # the server sets this
        self.hooks_log = self.dir / "hooks.jsonl"
        self.hooks_seen: tuple | None = None
        self.hooks: dict[str, list[dict]] = {}
        self.page_log = self.dir / "page.jsonl"
        self.page_seen: int | None = None
        self.page: dict[str, list[dict]] = {}
        self.paths: dict[str, Path] = {}                      # session id -> its transcript
        self.convos: dict[str, tuple[tuple, list[dict]]] = {}  # session id -> ((path, size), lines)
        self.cut: tuple[tuple, list[dict]] = ((), [])          # (conversations' key, stretches)
        self.missed: dict[str, float] = {}                     # session id -> when a search last found nothing
        self.found: dict[Path, dict] = {}                      # transcript -> what its first lines say
        self.scanned_at = 0.0                                  # when the folders were last listed
        self.read_lock = threading.Lock()
        self.sessions = {s.id: StepSession(self, s) for s in assignment.steps}

    def retarget(self, assignment: Assignment) -> None:
        """Take a changed steps file without a restart: keep each step's session and its id."""
        self.assignment = assignment
        old, self.sessions = self.sessions, {}
        for s in assignment.steps:
            self.sessions[s.id] = old.get(s.id) or StepSession(self, s)
            self.sessions[s.id].step, self.sessions[s.id].seen = s, None
        self.cut = ((), [])
        self.write_guard()

    # -- the conversations, and which step each stretch of them served --------------------------
    def find(self, session_id: str) -> Path | None:
        """A session's transcript. Claude Code keeps it under a folder named after the repository's
        path; the session id is unique, so any folder will do. A session not found is searched for
        again after two seconds, not on every step's refresh."""
        known = self.paths.get(session_id)
        if known and known.exists():
            return known
        if time.time() - self.missed.get(session_id, 0) < 2.0:
            return None
        found = list((claude_home() / "projects").glob(f"*/{session_id}.jsonl"))
        if not found:
            self.missed[session_id] = time.time()
            return None
        self.missed.pop(session_id, None)
        self.paths[session_id] = max(found, key=lambda p: p.stat().st_mtime)
        return self.paths[session_id]

    def known_id(self, step_id: str) -> str | None:
        """The session id .workbench/state.json kept for a step, if any (from before the command
        stopped naming one)."""
        with self.state_lock:
            return self.state.get("sessions", {}).get(step_id)

    def peek(self, path: Path, size: int) -> dict:
        """What a transcript says about itself, from its first lines: the folder it was recorded in
        (`cwd`) and the student's first message. Settled once both are known."""
        info = {"size": size, "cwd": None, "first": None, "settled": False}
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                for n, raw in enumerate(f):
                    if n > 400:
                        break
                    try:
                        d = json.loads(raw)
                    except ValueError:
                        continue
                    if not isinstance(d, dict):
                        continue
                    info["cwd"] = info["cwd"] or d.get("cwd")
                    if info["cwd"] and not self.here(info["cwd"]):
                        info["settled"] = True          # another folder's: never this homework's
                        break
                    said = said_by_student(d)
                    if said:
                        info["first"], info["settled"] = said, bool(info["cwd"])
                        break
        except OSError:
            pass
        info["here"] = bool(info["cwd"]) and self.here(info["cwd"])
        return info

    def here(self, cwd: str) -> bool:
        try:
            return os.path.normcase(str(Path(cwd).resolve())) == os.path.normcase(str(self.repo.resolve()))
        except OSError:
            return False

    def discovered(self) -> dict[str, Path]:
        """The homework's conversations that the page did not name in advance: every transcript
        Claude Code recorded for this folder (under projects/, in the folder named after this
        repository's path, and in any folder where a state.json session was found) whose first
        student message starts "Start step <label>." for one of the steps. The folders are listed
        at most every two seconds; a file is read again only when its size changes, and then only
        its first lines."""
        now = time.time()
        if now - self.scanned_at >= 2.0:
            self.scanned_at = now
            projects = claude_home() / "projects"
            folders = {projects / re.sub(r"[^A-Za-z0-9]", "-", str(p)) for p in (self.repo, self.repo.resolve())}
            folders |= {p.parent for p in self.paths.values()}
            for folder in folders:
                try:
                    found = [e for e in os.scandir(folder) if e.name.endswith(".jsonl") and e.is_file()]
                except OSError:
                    continue
                for e in found:
                    path, size = Path(e.path), e.stat().st_size
                    info = self.found.get(path)
                    if info and (info["settled"] or info["size"] == size):
                        info["size"] = size
                        continue
                    self.found[path] = self.peek(path, size)
        labels = {self.assignment.label(s) for s in self.assignment.steps}
        with self.state_lock:
            # Conversations from before the steps were renumbered open with the old labels, so a
            # port lists them here and the page reads them for no step (TRANSCRIPT.md still writes
            # them, under "Other Claude sessions in this folder").
            retired = set(self.state.get("retired_sessions", []))
        out = {}
        for path, info in self.found.items():
            m = START.match(info["first"] or "")
            if info["here"] and m and m.group(1) in labels and path.stem not in retired:
                out[path.stem] = path
        return out

    def conversations(self) -> dict[str, tuple[Path, list[dict]]]:
        """Every conversation of the homework: the sessions .workbench/state.json names, and the
        ones found by their first message (see discovered()): session id -> (its transcript, its
        lines). A transcript is read again only when it has grown."""
        with self.state_lock:
            ids = list(dict.fromkeys(self.state.get("sessions", {}).values()))
        out = {}
        with self.read_lock:
            found = self.discovered()
            for sid in ids + [x for x in found if x not in ids]:
                path = found.get(sid) or self.find(sid)
                if not path:
                    continue
                size = path.stat().st_size
                got = self.convos.get(sid)
                if not got or got[0] != (path, size):
                    lines = []
                    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
                        try:
                            d = json.loads(raw)
                        except ValueError:
                            continue
                        if isinstance(d, dict):
                            lines.append(d)
                    got = ((path, size), lines)
                    self.convos[sid] = got
                out[sid] = (path, got[1])
        return out

    def conversations_key(self) -> tuple:
        return tuple(sorted((sid, len(lines)) for sid, (_, lines) in self.conversations().items()))

    def stretches(self) -> list[dict]:
        """Every conversation cut at each message that starts a step ("Start step 0c."), each
        stretch with the step it served, its session, its transcript, its lines, when it began and
        ended (the next stretch's start), whether it is its conversation's last, and the label of
        the step that came next. What comes before the first such message serves the step the
        session was started for."""
        convos = self.conversations()
        key = tuple(sorted((sid, len(lines)) for sid, (_, lines) in convos.items()))
        with self.read_lock:
            if self.cut[0] == key:
                return self.cut[1]
            with self.state_lock:
                owner = {sid: step for step, sid in self.state.get("sessions", {}).items()}
            labels = {self.assignment.label(s): s.id for s in self.assignment.steps}
            out = []
            for sid, (path, lines) in convos.items():
                mine = []
                for d in lines:
                    said = said_by_student(d)
                    m = START.match(said) if said else None
                    step = labels.get(m.group(1)) if m else None
                    if step:
                        mine.append({"session": sid, "path": path, "step": step, "start": stamp(d.get("timestamp")),
                                     "lines": []})
                    elif not mine:
                        mine.append({"session": sid, "path": path, "step": owner.get(sid),
                                     "start": float("-inf"), "lines": []})
                    mine[-1]["lines"].append(d)
                for i, st in enumerate(mine):
                    nxt = mine[i + 1] if i + 1 < len(mine) else None
                    st["end"] = nxt["start"] if nxt else float("inf")
                    st["last"] = nxt is None
                    st["next"] = self.label_of(nxt["step"]) if nxt else None
                out += [st for st in mine if st["step"] in self.sessions]
            out.sort(key=lambda st: stamp((st["lines"][0] if st["lines"] else {}).get("timestamp")))
            self.cut = (key, out)
            return out

    def label_of(self, step_id: str | None) -> str | None:
        try:
            return self.assignment.label(self.assignment.step(step_id)) if step_id else None
        except KeyError:
            return None

    def worked_in(self) -> dict[str, list[str]]:
        """Each step's conversations, oldest first: step id -> session ids."""
        out: dict[str, list[str]] = {}
        for st in self.stretches():
            ids = out.setdefault(st["step"], [])
            if st["session"] not in ids:
                ids.append(st["session"])
        return out

    def homes(self) -> dict[str, str]:
        """The step each conversation is written under in TRANSCRIPT.md: the one state.json gave
        it, else the one its first message started."""
        with self.state_lock:
            out = {sid: step for step, sid in self.state.get("sessions", {}).items()}
        for st in self.stretches():
            out.setdefault(st["session"], st["step"])
        return out

    def convo_size(self, step_id: str) -> int:
        """How much of the homework's conversations served this step, in transcript lines."""
        return sum(len(st["lines"]) for st in self.stretches() if st["step"] == step_id)

    def remember_convos(self) -> None:
        """How long each step's conversation was when the page last committed, so it can tell
        when a committed part's conversation has grown since."""
        sizes = {sid: self.convo_size(sid) for sid in self.sessions}
        with self.state_lock:
            self.state["saved_convos"] = sizes
            self.save_state()

    def secret(self, rel: str) -> bool:
        """A file the page never shows or links to, such as .env."""
        return any(Path(rel).name == x or Path(rel).match(x) for x in self.assignment.never_read)

    def write_guard(self) -> None:
        (self.dir / "guard.json").write_text(json.dumps({
            "repo": str(self.repo), "writeup": self.assignment.writeup,
            "never_read": self.assignment.never_read, "refused": list(REFUSED)}, indent=2))

    def hook(self, mode: str) -> str:
        # The page's own Python runs the hook: it is there for certain, which a student's `python3`
        # may not be, and a hook that can't start lets the call through.
        return f"{dq(sys.executable)} {dq(str(self.dir / 'guard.py'))} {mode}"

    def session_id(self, step_id: str) -> str:
        """Give a step a session id in state.json, as older copies did for every step. The page no
        longer does; the tests use it to make a conversation that state.json names."""
        with self.state_lock:
            sessions = self.state.setdefault("sessions", {})
            if step_id not in sessions:
                sessions[step_id] = str(uuid.uuid4())
                self.save_state()
            return sessions[step_id]

    def hooks_size(self) -> int:
        return self.hooks_log.stat().st_size if self.hooks_log.exists() else -1

    def hook_records(self, session_id: str) -> list[dict]:
        with self.state_lock:
            size = self.hooks_size()
            if size != self.hooks_seen:
                self.hooks_seen, self.hooks = size, {}
                if size > 0:
                    for raw in self.hooks_log.read_text(encoding="utf-8", errors="replace").splitlines():
                        try:
                            r = json.loads(raw)
                        except ValueError:
                            continue
                        self.hooks.setdefault(r.get("session_id") or "", []).append(r)
            return list(self.hooks.get(session_id, []))

    def page_size(self) -> int:
        return self.page_log.stat().st_size if self.page_log.exists() else -1

    def record(self, step_id: str, kind: str, **data: Any) -> None:
        """Keep something Claude told the page, so it survives a restart of the server."""
        with self.state_lock, self.page_log.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"t": time.time(), "step": step_id, "kind": kind, **data}) + "\n")

    def page_records(self, step_id: str) -> list[dict]:
        with self.state_lock:
            size = self.page_size()
            if size != self.page_seen:
                self.page_seen, self.page = size, {}
                if size > 0:
                    for raw in self.page_log.read_text(encoding="utf-8", errors="replace").splitlines():
                        try:
                            r = json.loads(raw)
                        except ValueError:
                            continue
                        self.page.setdefault(r.get("step") or "", []).append(r)
            return list(self.page.get(step_id, []))

    def seen(self, key: str, ok: bool, when: float | None = None) -> float | None:
        """When a checkpoint's files or answers were first seen in place (their own modification
        time if known), kept across restarts; None once they are gone again."""
        with self.state_lock:
            seen = self.state.setdefault("seen", {})
            if ok and key not in seen:
                seen[key] = min(when or time.time(), time.time())
                self.save_state()
            elif not ok and key in seen:
                del seen[key]
                self.save_state()
            return seen.get(key)

    def save_state(self) -> None:
        self.state_file.write_text(json.dumps(self.state, indent=2))

    def marked(self) -> set[str]:
        return set(self.state.get("marked", []))

    def mark(self, step_id: str, done: bool) -> None:
        with self.state_lock:
            m = self.marked()
            (m.add if done else m.discard)(step_id)
            self.state["marked"] = sorted(m)
            self.save_state()

    def slots(self) -> dict[str, str]:
        wp = self.repo / self.assignment.writeup
        return read_slots(wp.read_text(encoding="utf-8")) if wp.exists() else {}

    def save_records(self, folder: Path) -> None:
        """What the page shows for each started step, kept in the repository for grading, one
        JSON file per step: which checkpoints were reached, what the student predicted, asked and
        ran, what came back, what Claude told the page, and who last wrote each answer."""
        a, slots = self.assignment, self.slots()
        edits: dict[str, dict] = {}       # each answer's last edit by Claude, from any step's session
        for s in self.sessions.values():
            s.refresh()
            for e in s.events:
                if e["kind"] == "slot" and e["t"] >= edits.get(e["key"], {}).get("t", 0):
                    edits[e["key"]] = {**e, "step": a.label(s.step)}
        for s in self.sessions.values():
            pages = self.page_records(s.step.id)
            if s.state == "not started" and not pages:
                continue
            rec, label = s.record(last=None), a.label(s.step)
            answers = []
            for k in step_keys(s.step, slots):
                e, answer = edits.get(k), slots.get(k, "")
                by = None if not filled(answer) else "the student" if not e else \
                    f"Claude, in {e['step']}'s session" if e.get("answer") == answer else "the student, after Claude"
                answers.append({"question": k.split(" / ")[-1], "answer": answer, "written_by": by})
            out = {
                "step": label, "title": s.step.title, "session_id": s.session_id,
                "conversations": list(dict.fromkeys(st["session"] for st in s.stretches())),
                "complete": all(c["done"] for c in rec["checkpoints"] if c["tick"]),
                "checkpoints": [{"text": c["text"], "reached": c["done"]} for c in rec["checkpoints"] if c["tick"]],
                "answers": answers,
                "record": [{**{k: v for k, v in x.items() if k != "t"}, "time": when(x["t"])} for x in rec["entries"]],
                "told_the_page": [{"time": when(r["t"]), **{k: v for k, v in r.items() if k not in ("t", "step")}}
                                  for r in pages],
                "turns": s.totals["turns"],
            }
            text = KEY.sub("[key removed]", json.dumps(out, indent=2, ensure_ascii=False)) + "\n"
            f = folder / f"{label}.json"
            if not (f.exists() and f.read_text(encoding="utf-8") == text):
                folder.mkdir(exist_ok=True)
                f.write_text(text, encoding="utf-8")

    def body(self, s: Step) -> str:
        return body(s, self.assignment, self.repo)

    def prompt(self, s: Step) -> str:
        a = self.assignment
        label = a.label(s)
        part = a.parts.get(s.part, {})
        keys = step_keys(s, self.slots())
        wp = self.repo / a.writeup
        quote = wp.exists() and layout(wp.read_text(encoding="utf-8")) == "quote"
        lines = []
        for k in keys:
            if " / " not in k:
                lines.append(f'- the "{k}:" line' if quote else f'- "**{k}:**"')
            elif quote:
                where = k.split(" / ")[1:]
                ask = where.pop()
                lines.append(f'- under "{" / ".join(where)}" in Part {s.part}: "{ask}"')
            else:
                lines.append(f'- "### {k.split(" / ", 1)[1]}" under "## Part {s.part}"')
        slot_lines = "\n".join(lines) or "- (none: the step is complete from its files, or once the student has done it)"
        if quote and keys:
            slot_lines += ("\nWrite in these only where " + a.writeup + " itself says to ask Claude, and only when "
                           "the student asks: put the program's output where it says (rows of a table, a column it "
                           "names, or inside an empty ``` block). Write nowhere else in " + a.writeup + ". Never "
                           "change a question, a heading, a table's header row or the student's own words, and never "
                           "write on a \"> \" answer line.")
        files = ", ".join(s.files)
        others = "\n".join(f"- {a.label(o)}: Part {o.part}, {o.title}" for o in a.steps if o.id != s.id)
        counts = []
        for i, c in enumerate(checkpoints(s), 1):
            if c.files or c.slots:
                how = "ticks itself when " + " and ".join(
                    ([f"{', '.join(c.files)} exists"] if c.files else [])
                    + (["the student's answers are in " + a.writeup] if c.slots else []))
            elif not c.tick:
                how = ("the student does this where you cannot see it, and the page shows it with no tick: "
                       "never tick it, and never ask whether they have done it")
            else:
                how = f"you tick it once you have seen it happen in this session: python3 .workbench/page.py {label} done {i}"
            counts.append(f"{i}. {c.text} ({how})")
        counts_text = "\n".join(counts) or "(none listed)"
        manual = not (s.slots or s.files)
        return f"""
{a.tutor.strip()}

# This session: one step of the assignment

You help with one step, and only this one: {label}, "{s.title}", in Part {s.part} ({part.get('title', '')}).
What this step is, as the page says it under the step's title: {s.summary.strip()}
The student talks to you in a terminal. Beside it, a web page shows every step of the assignment,
each with its own Claude Code session, and this step's instructions, which say:

<step-instructions>
{self.body(s).strip()}
</step-instructions>

{f"""The claim this step checks, word for word:

{a.sample_claim}
""" if s.claim and a.sample_claim else ""}
Earlier steps' answers are in {a.writeup}. Read it when you need them, unless this step's
instructions below say not to open it yet.

What you do in this step:

{s.brief.strip()}

What counts in this step. The page lists these for the student under "Tasks", each worded as a task:
{counts_text}
{"This is a setup step: you may walk the student through its steps in order." if s.setup else
"The page shows the student these tasks. If they ask what to do next, you may name the next one that is not done."}
Beside them the page keeps the student's record: what they asked you to do, what you ran and what
came back. If the student says what they expect a run to show, you may note it in a few words, and
the page sets it beside the result:
python3 .workbench/page.py {label} expected "supported"

The slots this step fills in {a.writeup}. The student types their own answers into these, in their
editor:
{slot_lines}
{f"The step also needs these files to exist: {files}." if files else ""}
{f"""The page also shows the student this command, which they run themselves in a terminal tab of
their own, not in this session: {run_yourself(s)["command"]}
""" if run_yourself(s) else ""}
How the page works, so you don't duplicate it:
- It marks this step complete by itself, from {a.writeup}{" and the files" if files else ""}. Don't announce it.
- It commits "Part {s.part} done" when every step of Part {s.part} is complete. Never run git commit,
  git push or anything that rewrites history; those calls are refused.
- If the student asks about another step, name it, and say in one line that they start it from
  that step on the page: its prompt, pasted into this chat, moves this session onto it. The other
  steps are:
{others}

Keep the page up to date with the `page` skill, using `{label}` as the step: post a one-line status
when what you are doing changes, and tick each
checkpoint above that says you tick it, once you have seen it happen{", then mark the step done once the student says they have finished it, since it has nothing to fill in" if manual else ""}.

This step opens with the message "Start step {label}.": alone, in a new session, or followed by a
line asking you to read this file, in a session that was on another step. From that message on,
this step's instructions replace any other step's. In a session that was on another step, first
say in one line that you are now on step {label}. Then reply in two or three sentences: what this
step is, from the summary above, then the first task on the page that is not done yet and what to
type to get it done, for example: "When you are ready, ask me to run the agent on the claim." Do
not ask what they would like to do first. Then wait for the student. If the student comes back to
this session later, say in one or two sentences what they have reached so far, and what the next
task is and where they do it.
""".strip()
