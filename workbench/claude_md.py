"""Write the repository's CLAUDE.md from steps.toml, for a student who starts plain `claude` here.

    uv run python -m workbench.claude_md

A session the page starts leaves this file out (its command has `--setting-sources user`), so it
reaches only a Claude started in this folder some other way. It sends the student to the homework
page, helps if the page won't start, and gives the homework's tutor rules from steps.toml for a
student who keeps working there anyway. tests/test_workbench.py fails when this file and
steps.toml are out of step: run this again after changing the tutor text.
"""

from __future__ import annotations

from pathlib import Path

from .steps import Assignment, load

REPO = Path(__file__).resolve().parent.parent


def text(a: Assignment) -> str:
    return f"""# {a.title}

<!-- Written by `uv run python -m workbench.claude_md` from steps.toml. Change steps.toml, then
run that command again. Don't edit this file by hand. -->

This homework is done on the homework page, not in a Claude session started here. Before anything
else, tell the student so in two sentences: run this in a terminal in this folder, and leave that
terminal open while they work:

    uv run python -m workbench

It opens the homework page in the browser. The page starts each Claude session for the homework:
the command a step shows, pasted into another terminal in this folder, starts a new one, and the
prompt a step shows, pasted into that session's chat, moves it on to that step.

If the page won't start, help them get it running, and nothing else until it does:
- It must be started in this folder, the one with steps.toml.
- It needs uv. If `uv` isn't found, point them to https://docs.astral.sh/uv/ to install it. uv
  fetches the right Python (3.12) by itself the first time.
- If it says the homework page is already running, it gives the address: open that.
- It picks a free port by itself, from 8450. If every port it tries is in use, it says so; then
  start it with `--port 9000`.
- For any other error, read it with them and fix what it names. If it still won't start, they
  post the error in #comp440-f26 on Slack.

If they keep working in this session anyway, these rules apply:

{a.tutor.strip()}
"""


def main() -> None:
    out = REPO / "CLAUDE.md"
    out.write_text(text(load(REPO / "steps.toml")), encoding="utf-8")
    print(f"Wrote {out.name} from steps.toml.")


if __name__ == "__main__":
    main()
