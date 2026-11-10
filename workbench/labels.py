"""Plain-language labels for what a session is doing, for the visualization.

Each tool call becomes a short label ("Ran agent.py", "Read README.md") and a kind, which the
page colors: read, run, write, search, ask (a permission question for the student), other.
Labels are worked out from the call itself, with no extra model call, so they cost nothing and
can't be wrong about what was run; they can only be vague.
"""

from __future__ import annotations

import re
import shlex
from pathlib import Path

SCRIPT = re.compile(r"\b(?:uv run )?python3?\s+(?:-m\s+)?([\w./-]+\.py|[\w.]+)")
PAGE_CALL = re.compile(r"^(?:uv run )?python3?\s+\S*page\.py\b")   # the `page` skill's own script


def pieces(cmd: str) -> list[str]:
    """The commands in a chained one, split at &&, || and ; and at line breaks, but never inside
    quotes. A pipe stays inside its piece."""
    out, buf, quote, i = [], [], None, 0
    while i < len(cmd):
        c = cmd[i]
        if c == "\\" and i + 1 < len(cmd) and quote != "'":
            buf.append(cmd[i:i + 2])
            i += 2
            continue
        if quote:
            quote = None if c == quote else quote
            buf.append(c)
        elif c in "'\"":
            quote = c
            buf.append(c)
        elif cmd.startswith(("&&", "||"), i):
            out.append("".join(buf))
            buf = []
            i += 1
        elif c in ";\n":
            out.append("".join(buf))
            buf = []
        else:
            buf.append(c)
        i += 1
    out.append("".join(buf))
    return [x.strip() for x in out if x.strip()]


def without_page_calls(cmd: str) -> str:
    """A shell command with its calls to the page's own script taken out; "" if that was all.
    Claude often chains a status update with a real run (`python3 .workbench/page.py 0b expected
    "supported" && uv run python check.py ...`), and the run must stay in the student's record."""
    return " && ".join(x for x in pieces(cmd) if not PAGE_CALL.match(x))


def short(path: str, repo: Path) -> str:
    try:
        return str(Path(path).resolve().relative_to(repo.resolve()))
    except (ValueError, OSError):
        return Path(path).name or path


def describe(tool: str, inp: dict, repo: Path) -> tuple[str, str]:
    """(kind, label) for one tool call."""
    if tool == "Read":
        return "read", f"Read {short(inp.get('file_path', ''), repo)}"
    if tool in ("Glob", "Grep"):
        what = inp.get("pattern", "")
        return "search", f"Searched for {what!r}" if tool == "Grep" else f"Listed files matching {what}"
    if tool in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        return "write", f"Edited {short(inp.get('file_path', inp.get('notebook_path', '')), repo)}"
    if tool == "WebFetch":
        return "search", f"Fetched {inp.get('url', '')[:60]}"
    if tool == "WebSearch":
        return "search", f"Searched the web for {inp.get('query', '')!r}"
    if tool == "TodoWrite":
        return "other", "Updated its to-do list"
    if tool == "Bash":
        return "run", bash_label(inp.get("command", ""), inp.get("description"))
    if tool.startswith("mcp__"):
        return "other", f"Used {tool.split('__')[-1]}"
    return "other", tool


def bash_label(cmd: str, description: str | None) -> str:
    c = cmd.strip()
    m = SCRIPT.search(c)
    if m:
        name = m.group(1)
        rest = re.sub(r"\s--out\s+\S+", "", c[m.end():]).strip()   # where it saves says little
        try:
            args = " ".join(a for a in shlex.split(rest)[:3] if len(a) <= 40)   # not the whole claim
        except ValueError:
            args = rest[:40]
        return f"Ran {name}" + (f" {args}" if args else "")
    if c.startswith("git "):
        verb = c.split()[1] if len(c.split()) > 1 else ""
        return {"commit": "Committed to git", "push": "Pushed to GitHub", "log": "Read the git log",
                "status": "Checked git status", "diff": "Looked at a git diff"}.get(verb, f"Ran git {verb}")
    if c.startswith(("uv sync", "uv add", "pip ")):
        return "Installed packages"
    if c.startswith(("ls", "find ", "tree")):
        return "Listed files"
    if c.startswith(("cat ", "head ", "tail ", "sed -n", "wc ")):
        try:
            words = shlex.split(c.split("|")[0])
        except ValueError:
            words = c.split()
        files = [w for w in words[1:] if not w.startswith("-") and not re.fullmatch(r"[\d,]+p?", w)]
        return f"Looked at {files[-1]}" if files else "Looked at a file"
    if description:
        return description[:70]
    return "Ran " + c.split()[0] if c else "Ran a command"
