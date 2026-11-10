"""The hook every step's Claude Code session runs, copied into the student's .workbench/ folder.

Standard library only. The step's settings run it with the homework page's own Python (the
repository's .venv), given by its full path. Claude Code calls it with the event as JSON on
standard input:

    <python> .workbench/guard.py pre      before each tool call
    <python> .workbench/guard.py post     after an edit of the write-up
    <python> .workbench/guard.py notify   when Claude Code wants the student's attention

`pre` refuses commits, pushes and resets (the page makes the commits) and any call that reads,
prints or edits a secret file such as .env; checking that the file exists is allowed. Around an
edit of the write-up, `pre` and `post` save its text before and after, so the page can say which
answers that edit wrote. `notify` records Claude Code asking the student's OK in the terminal,
which the session's transcript doesn't hold. All three append to .workbench/hooks.jsonl, which
the page reads. The settings sit beside this file, in guard.json.
"""

import json
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXISTS = re.compile(r"(?:\btest\s+-[ef]\s+\S+|\[\s+-[ef]\s+\S+\s+\])")
SEPARATOR = re.compile(r"\s*(?:&&|\|\||;|\||\n)\s*")
EDITS = ("Edit", "Write", "MultiEdit")
WORDS_ONLY = re.compile(r"(echo|printf)\b|(uv run )?python3?\s+\S*page\.py\b")   # their words are only text


def pieces(cmd):
    """The simple commands in a compound one, or None if it redirects or substitutes a command."""
    cmd = re.sub(r"\s*2>&1", "", cmd.strip())
    if any(x in cmd for x in (">", "<", "`", "$(")):
        return None
    return [x for x in SEPARATOR.split(cmd) if x]


def touches(secret, inp, tool):
    """Whether a call could read or write the secret file. Checking that it exists is fine, and so
    is text that only mentions it (echo ".env missing", or a status line for the homework page);
    .env.example is another file."""
    if tool == "Bash":
        text = EXISTS.sub("", inp.get("command", ""))
        parts = pieces(text)
        if parts is not None:   # no redirect or substitution, so these words are only words
            text = "\n".join(x for x in parts if not WORDS_ONLY.match(x))
    else:
        text = json.dumps(inp)
    if not secret.endswith(".py"):
        return re.search(r"(?<![\w.])" + re.escape(secret) + r"(?![\w.])", text) is not None
    return any(re.search(r"(?<![\w.])" + re.escape(n) + r"(?![\w])", text) for n in names_of(secret))


def names_of(secret):
    """Every name a command can use for a .py file: tests/test_loop_check.py, its file name alone
    (after cd tests), and its module names (tests.test_loop_check, test_loop_check)."""
    stem, base = secret[:-3], secret.rsplit("/", 1)[-1]
    return {secret, stem, stem.replace("/", "."), base, base[:-3]}


def writeup_text(conf, inp):
    """The write-up's text, if this call edits it; else None."""
    target = inp.get("file_path") or ""
    if not target:
        return None
    path = Path(target) if Path(target).is_absolute() else Path(conf["repo"]) / target
    want = Path(conf["repo"]) / conf["writeup"]
    try:
        if path.resolve() != want.resolve():
            return None
        return want.read_text(encoding="utf-8") if want.exists() else ""
    except OSError:
        return None


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "pre"
    conf = json.loads((HERE / "guard.json").read_text(encoding="utf-8"))
    data = json.load(sys.stdin)
    tool, inp = data.get("tool_name", ""), data.get("tool_input") or {}
    base = {"t": time.time(), "session_id": data.get("session_id"), "tool_use_id": data.get("tool_use_id")}
    records, reason = [], None

    if mode == "notify":
        kind = data.get("notification_type") or ""
        message = data.get("message") or ""
        if kind == "permission_prompt" or (not kind and "permission" in message.lower()):
            records.append({**base, "kind": "asking", "text": message})
    elif mode == "pre":
        if tool == "Bash" and any(r in inp.get("command", "") for r in conf["refused"]):
            reason = ("Don't commit, push or reset: the page commits each part itself when its steps "
                      "are complete. Carry on.")
            records.append({**base, "kind": "refused", "text": "Refused a git command: the page makes the commits."})
        for secret in conf["never_read"]:
            if touches(secret, inp, tool):
                reason = (f"Never read, print or edit {secret}: it holds the student's own key. Ask "
                          "them to edit it themselves in their editor.")
                records.append({**base, "kind": "refused", "text": f"Refused a call that touched {secret}."})
        if reason is None and tool in EDITS:
            text = writeup_text(conf, inp)
            if text is not None:
                records.append({**base, "kind": "before", "text": text})
    elif mode == "post" and tool in EDITS:
        text = writeup_text(conf, inp)
        if text is not None:
            records.append({**base, "kind": "after", "text": text})

    if records:
        with open(HERE / "hooks.jsonl", "a", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")
    if reason:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                                 "permissionDecision": "deny",
                                                 "permissionDecisionReason": reason}}))


if __name__ == "__main__":
    main()
