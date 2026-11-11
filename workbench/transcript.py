"""Write the student's Claude conversations into TRANSCRIPT.md, for grading.

    uv run python -m workbench.transcript      # by hand; the page also does it before each commit

Claude Code saves every conversation under ~/.claude/projects/ (or $CLAUDE_CONFIG_DIR/projects/).
The page keeps each step's session id in .workbench/state.json, so each step's conversation goes
under a heading naming the step, in step order, however many times the student came back to it.
A conversation that went on to other steps (the student pasted a step's "Start step 0c. ..."
prompt into it) is written once, under the step it was started for; each other step it served
gets a line under its own heading saying so, and its stretch starts at that message.
Conversations started in this folder some other way (plain `claude`) follow, under their own
heading.

Each conversation is written in the format of HW2's dump_transcript.py, which the grading tools
read: a `<!-- transcript-session: ID | START -->` line, a `## Session` heading, a line counting
the student's turns, then `**User:**` and `**Claude:**` turns, each tool call as one line
starting "- 🔧", and `<!-- end-session: ID -->`. Unlike HW2's, each tool call is followed by the
start of what it returned, in a fenced block. Anything that looks like an API key becomes
[key removed]. A conversation that is in the file but no longer on this laptop (one from another
computer, say) is kept as it was.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from .steps import Assignment

NAME = "TRANSCRIPT.md"
HEADER = """\
# Claude conversations (written by the homework page)

The homework page writes this file before each commit it makes: each step's Claude session under
the step, then any other Claude session started in this folder. Tool output is shortened and
Claude's reasoning is left out. Don't edit it by hand; the page writes it again.
"""

KEY = re.compile(r"sk-ant-[^\s\"'`<>]*")
SECTION = re.compile(r"<!-- transcript-session: (?P<id>[\w-]+) \| (?P<ts>\S+) -->\n(?P<body>.*?)"
                     r"<!-- end-session: (?P=id) -->\n", re.S)
STEP_HEAD = re.compile(r"^# (?P<label>\d+[a-z])\. ", re.M)
OTHERS = "# Other Claude sessions in this folder"
REMINDER = re.compile(r"<system-reminder>.*?</system-reminder>", re.S)
COMMAND = re.compile(r"<command-name>(.*?)</command-name>", re.S)
RESULT_LINES, RESULT_CHARS = 12, 1200


def redact(text: str) -> str:
    return KEY.sub("[key removed]", text)


def projects() -> Path:
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude") / "projects"


def files_for(session_id: str) -> list[Path]:
    """Every saved copy of one session: one, unless the folder was moved or renamed."""
    return sorted(projects().glob(f"*/{session_id}.jsonl")) if projects().is_dir() else []


def started_here(f: Path, repo: Path) -> bool:
    """Whether a saved session's recorded working folder is this repository."""
    try:
        with open(f, encoding="utf-8", errors="replace") as fh:
            for raw in fh:
                try:
                    cwd = json.loads(raw).get("cwd")
                except (ValueError, AttributeError):
                    continue
                if cwd:
                    return os.path.normcase(str(Path(cwd).resolve())) == os.path.normcase(str(repo.resolve()))
    except OSError:
        pass
    return False


def entries(paths: list[Path]) -> list[dict]:
    """The lines of a session's saved copies, each once, in time order."""
    seen, out = set(), []
    for p in paths:
        try:
            raws = p.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for raw in raws:
            try:
                e = json.loads(raw)
            except ValueError:
                continue
            if not isinstance(e, dict):
                continue
            k = e.get("uuid") or raw
            if k not in seen:
                seen.add(k)
                out.append(e)
    return sorted(out, key=lambda e: e.get("timestamp") or "")


def fence(text: str) -> str:
    longest = max((len(m) for m in re.findall(r"`+", text)), default=0)
    return "`" * max(3, longest + 1)


def tool_line(block: dict) -> str:
    """One tool call on one line, as HW2's: the command for a shell call, else the file or name."""
    name, inp = block.get("name", "tool"), block.get("input") or {}
    if name == "Bash":
        brief, cap = inp.get("command") or inp.get("description") or "", 200
    elif name in ("Read", "Edit", "Write", "MultiEdit", "NotebookEdit"):
        brief, cap = inp.get("file_path") or inp.get("notebook_path") or "", 100
    elif name in ("Agent", "Task"):
        brief, cap = inp.get("description", ""), 100
    elif name == "Skill":
        brief, cap = inp.get("skill", ""), 100
    else:
        brief, cap = json.dumps(inp, ensure_ascii=False), 100
    brief = " ".join(str(brief).split())
    if len(brief) > cap:
        brief = brief[:cap - 3] + "..."
    return f"- 🔧 `{name}` — {brief}" if brief else f"- 🔧 `{name}`"


def result_text(block: dict) -> str:
    """The start of what a tool call returned: its first lines, each cut short."""
    c = block.get("content")
    if isinstance(c, list):
        c = "\n".join(b.get("text", "") if b.get("type") == "text" else "[an image]"
                      for b in c if isinstance(b, dict))
    lines = str(c or "").strip("\n").splitlines()
    kept = [x if len(x) <= 200 else x[:197] + "..." for x in lines[:RESULT_LINES]]
    text = "\n".join(kept)
    if len(text) > RESULT_CHARS:
        text = text[:RESULT_CHARS - 3] + "..."
    more = len(lines) - len(kept)
    if more:
        text += f"\n... ({more} more line{'s' if more != 1 else ''})"
    if block.get("is_error"):
        text = "(error) " + text
    return text or "(no output)"


def user_text(text: str) -> str:
    text = REMINDER.sub("", text)
    m = COMMAND.search(text)
    if m:
        return f"*(ran `{m.group(1).strip()}`)*"
    if text.lstrip().startswith(("<local-command", "<bash-")):
        return ""   # what Claude Code adds around a command's output, not the student's words
    return text.strip()


def render(session_id: str, lines: list[dict]) -> tuple[str, str] | None:
    """One session as (start time, Markdown between its two markers), or None if it is empty."""
    results = {}
    for e in lines:
        c = (e.get("message") or {}).get("content") if e.get("type") == "user" else None
        for b in c if isinstance(c, list) else []:
            if isinstance(b, dict) and b.get("type") == "tool_result":
                results[b.get("tool_use_id")] = b
    chunks, start = [], None
    for e in lines:
        if e.get("type") not in ("user", "assistant") or e.get("isSidechain") or e.get("isMeta") \
                or e.get("isApiErrorMessage") or not isinstance(e.get("message"), dict):
            continue
        start = start or e.get("timestamp")
        content, parts = e["message"].get("content"), []
        if e["type"] == "user":
            if isinstance(content, str):
                parts.append(user_text(content))
            else:
                parts += [user_text(b.get("text", "")) for b in content or []
                          if isinstance(b, dict) and b.get("type") == "text"]
            speaker = "User"
        else:
            for b in content if isinstance(content, list) else []:
                if b.get("type") == "text" and b.get("text", "").strip():
                    parts.append(b["text"].strip())
                elif b.get("type") == "tool_use":
                    line = tool_line(b)
                    if b.get("id") in results:
                        out = result_text(results[b["id"]])
                        f = fence(out)
                        line += f"\n\n  {f}\n" + "\n".join("  " + x for x in out.splitlines()) + f"\n  {f}"
                    parts.append(line)
            speaker = "Claude"
        text = "\n\n".join(p for p in parts if p)
        if text:
            chunks.append((speaker, text))
    if not chunks:
        return None
    body, prev = [], None
    for speaker, text in chunks:
        if speaker != prev:
            body.append(f"\n**{speaker}:**\n")
            prev = speaker
        else:
            body.append("\n")    # HW2's has none; a blank line keeps text apart from a tool's output
        body.append(text + "\n")
    start = start or "unknown"
    turns = sum(s == "User" for s, _ in chunks)
    head = (f"## Session `{session_id[:8]}` — {start[:19].replace('T', ' ')}\n\n"
            f"*{turns} user turns. Tool output shortened; reasoning omitted.*\n")
    return start, head + "".join(body) + "\n"


def section(session_id: str, start: str, body: str) -> str:
    return f"<!-- transcript-session: {session_id} | {start} -->\n{body}<!-- end-session: {session_id} -->\n"


def build(repo: Path, a: Assignment, session_ids: dict[str, str],
          worked: dict[str, list[str]] | None = None) -> str:
    """The whole file. `session_ids` maps each step's id to its own session id; `worked`, each
    step's id to the sessions whose conversation served it, as the page reads them."""
    old: dict[str, tuple[str | None, str, str]] = {}   # session id -> (step label, start, body)
    path = repo / NAME
    if path.exists():
        text = path.read_text(encoding="utf-8", errors="replace")
        for m in SECTION.finditer(text):
            heads = list(STEP_HEAD.finditer(text, 0, m.start()))
            others = text.rfind(OTHERS, 0, m.start())
            label = heads[-1].group("label") if heads and heads[-1].start() > others else None
            old[m.group("id")] = (label, m.group("ts"), m.group("body"))

    def one(sid: str) -> str:
        got = render(sid, entries(files_for(sid)))
        if got:
            return section(sid, *got)
        return section(sid, old[sid][1], old[sid][2]) if sid in old else ""

    out, mine = [HEADER], set(session_ids.values())
    home = {sid: step for step, sid in session_ids.items()}     # where each conversation is written
    for s in a.steps:
        label = a.label(s)
        ids = [session_ids[s.id]] if s.id in session_ids else []
        ids += [k for k, v in old.items() if v[0] == label and k not in ids and k not in mine]
        done = [x for x in (one(sid) for sid in ids) if x]
        # A conversation written under another step that also served this one.
        elsewhere = [sid for sid in (worked or {}).get(s.id, []) if home.get(sid, s.id) != s.id]
        done += [f"This step was done in the conversation under {a.label(a.step(home[sid]))}, session "
                 f"`{sid[:8]}`, from the message “Start step {label}.”\n" for sid in elsewhere]
        if done:
            out.append(f"\n# {label}. {s.title}\n\n" + "\n".join(done))
    found = {f.stem for f in projects().glob("*/*.jsonl") if f.stem not in mine and started_here(f, repo)} \
        if projects().is_dir() else set()
    found |= {k for k, v in old.items() if v[0] is None and k not in mine}
    rest = sorted((x for x in (one(sid) for sid in found) if x),
                  key=lambda x: x.split(" | ", 1)[1])   # by start time
    if rest:
        out.append(f"\n{OTHERS}\n\n" + "\n".join(rest))
    return redact("".join(out))


def write(repo: Path, a: Assignment, session_ids: dict[str, str],
          worked: dict[str, list[str]] | None = None) -> bool:
    """Write TRANSCRIPT.md if it changed. True if the file now holds at least one conversation."""
    text = build(repo, a, session_ids, worked)
    path = repo / NAME
    if not (path.exists() and path.read_text(encoding="utf-8", errors="replace") == text):
        path.write_text(text, encoding="utf-8", newline="\n")
    return "<!-- transcript-session:" in text


def main() -> None:
    from .steps import load
    repo = Path(__file__).resolve().parent.parent
    state = repo / ".workbench" / "state.json"
    ids = json.loads(state.read_text()).get("sessions", {}) if state.exists() else {}
    a = load(repo / "steps.toml")
    print(f"Wrote {NAME}." if write(repo, a, ids) else f"Wrote {NAME}, but no conversation was found yet.")


if __name__ == "__main__":
    main()
