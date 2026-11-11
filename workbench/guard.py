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
import os
import re
import shlex
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


# A search must name the files it reads. A search of a folder, a wildcard or a recursive search
# could print the key in .env into the conversation, which is saved in TRANSCRIPT.md.
SEARCHES = {"grep", "egrep", "fgrep", "rg"}
AFTER = {"xargs", "-exec", "-execdir", "env", "command", "builtin", "nice", "nohup", "time", "sudo"}
TAKES_VALUE = {"grep": set("efmABCdD"), "rg": set("efgtTmABCMjEr")}   # short options with a value
LONG_VALUE = {"--regexp", "--file", "--max-count", "--after-context", "--before-context", "--context",
              "--directories", "--devices", "--label", "--include", "--exclude", "--exclude-dir",
              "--exclude-from", "--binary-files", "--glob", "--iglob", "--type", "--type-not",
              "--max-depth", "--replace", "--encoding", "--max-filesize", "--threads", "--sort",
              "--sortr", "--pre", "--pre-glob", "--max-columns", "--type-add", "--ignore-file"}
SEARCH_REASON = ('Search one named file at a time, for example: grep -n -o "a few words" '
                 "runs/part2/agent.jsonl. A search with no file, of a folder, with a wildcard or "
                 "with -r is refused, because it could print the key in .env into this "
                 "conversation, which is saved.")


def loose_search(cmd, conf):
    """Why a grep, egrep, fgrep or rg in this shell command could read more than the plain files
    it names; None if it names plain files only, or runs no search. The word in quotes or after
    echo is only a word."""
    if not re.search(r"\b[ef]?grep\b|\brg\b", cmd):
        return None
    try:
        lex = shlex.shlex(cmd, posix=True, punctuation_chars=True)
        lex.whitespace_split = True
        words = list(lex)
    except ValueError:
        return "the command could not be read"
    commands, current = [], []
    for w in words:
        if w and set(w) <= set(";|&()"):     # a separator: the next simple command starts
            commands.append(current)
            current = []
        else:
            current.append(w)
    commands.append(current)
    for ws in commands:
        first = next((j for j, x in enumerate(ws) if not re.match(r"^\w+=", x)), 0)
        for i, w in enumerate(ws):
            name = os.path.basename(w)
            if name not in SEARCHES:
                continue
            run = (i == first or (i and ws[i - 1] in AFTER) or (i >= 2 and ws[i - 2] == "timeout")
                   or (i >= 2 and ws[i - 2:i] == ["uv", "run"]))
            if run:
                why = search_args("rg" if name == "rg" else "grep", ws[i + 1:], conf)
                if why:
                    return why
    return None


def search_args(kind, args, conf):
    takes, given, positional, i = TAKES_VALUE[kind], False, [], 0
    while i < len(args):
        a = args[i]
        nxt = args[i + 1] if i + 1 < len(args) else ""
        if a in ("<", "<<", "<<<"):
            return "it reads its input, not a named file"
        if re.fullmatch(r"\d*(>>?|>&|&>)\d*", a):     # an output redirect and its target
            i += 1 if a.endswith(tuple("0123456789")) and "&" in a else 2
            continue
        if a == "--":
            positional += args[i + 1:]
            break
        if a.startswith("--"):
            opt, eq, val = a.partition("=")
            if opt in ("--recursive", "--dereference-recursive"):
                return "it searches folders"
            if opt == "--directories" and (val if eq else nxt) == "recurse":
                return "it searches folders"
            given = given or opt in ("--regexp", "--file")
            i += 2 if (not eq and opt in LONG_VALUE) else 1
            continue
        if a.startswith("-") and len(a) > 1:
            for j, c in enumerate(a[1:], 1):
                if kind == "grep" and c in "rR":
                    return "it searches folders"
                if c in takes:
                    val = a[j + 1:] or nxt
                    if not a[j + 1:]:
                        i += 1
                    given = given or c in "ef"
                    if kind == "grep" and c == "d" and val == "recurse":
                        return "it searches folders"
                    break
            i += 1
            continue
        positional.append(a)
        i += 1
    targets = positional if given else positional[1:]
    if not targets:
        return "it names no file"
    secrets = {Path(x).name for x in conf.get("never_read", [])}
    for t in targets:
        if t == "-" or any(ch in t for ch in "*?[]{}$`~"):
            return "it names files with a wildcard"
        p = Path(t) if Path(t).is_absolute() else Path(conf["repo"]) / t
        if p.is_dir():
            return "it names a folder"
        try:
            if p.resolve().name in secrets:
                return "it reads a file this session must not open"
        except OSError:
            pass
    return None


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
            records.append({**base, "kind": "refused", "text": "The page refused a git command, because the page makes the commits."})
        for secret in conf["never_read"]:
            if touches(secret, inp, tool):
                # Claude Code shows this to the step's Claude as the refused call's result.
                reason = (f"Never read, print or edit {secret}: it holds the student's own key. Ask "
                          "them to edit it themselves in their editor.") if secret == ".env" else \
                         (f"Never open {secret}: it holds a finished version of what the student writes "
                          "themselves in this homework. Do not look for its contents anywhere else either.")
                records.append({**base, "kind": "refused", "text": f"The page refused a command that touched {secret}."})
        if reason is None and tool == "Bash" and loose_search(inp.get("command", ""), conf):
            reason = SEARCH_REASON
            records.append({**base, "kind": "refused", "text": "The page refused a search that did not name its files."})
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
