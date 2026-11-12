"""Offline tests of the homework page (workbench/): no network, no Claude, no GitHub.

Each test builds what it needs in a temporary folder: a small steps file, a WRITEUP.md in the
"## 0b. Title" heading style, git repositories that stand in for the class repository and the
student's fork, and saved Claude Code conversations under a temporary CLAUDE_CONFIG_DIR.
"""

import json
import socket
import time
import subprocess
import sys
import threading
import urllib.request
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from workbench import claude_md, labels, server, steps, transcript  # noqa: E402
from workbench.sessions import stamp  # noqa: E402

STEPS = '''
title = "COMP 440 HW9: A small homework"
writeup = "WRITEUP.md"
push = true
model = "claude-opus-5-5"
effort = "medium"
never_read = [".env"]
tutor = """
Be brief.
"""

[[part]]
number = 0
title = "Set up"

[[part]]
number = 1
title = "The loop"

[[step]]
id = "0a"
part = 0
title = "Get the repository"
slots = ["Name"]

[[step]]
id = "0b"
part = 0
title = "Ask the model on its own"
slots = ["0b.*"]
files = ["runs/part0/no-tools-*.json"]
allow = ["Bash(uv run python check.py:*)"]
checkpoints = [
  "You read the output with Claude",
  { text = "You've seen the model answer", files = ["runs/part0/no-tools-*.json"] },
  { text = "Your answers", slots = ["0b.*"] },
]

[[step]]
id = "1a"
part = 1
title = "Read the loop"
slots = ["1a.*"]
'''

WRITEUP = """# HW9 write-up

Name:

# Part 0: Set up

## 0a. Get the repository

Write your name at the top of this file.

## 0b. Ask the model on its own

What did it say?

>

How much would you trust it, and why?

>

# Part 1: The loop

## 1a. Read the loop

What does Claude get sent on each turn?

>
"""

FILLED = (WRITEUP.replace("Name:", "Name: Sam Student")
          .replace("What did it say?\n\n>", "What did it say?\n\n> It said supported.")
          .replace("and why?\n\n>", "and why?\n\n> Not much: it guessed."))


@pytest.fixture(autouse=True)
def quiet_world(tmp_path, monkeypatch):
    """No real git settings, Claude conversations or class repository reach a test."""
    (tmp_path / "gitconfig").write_text("")
    for k, v in {"GIT_CONFIG_GLOBAL": str(tmp_path / "gitconfig"), "GIT_CONFIG_NOSYSTEM": "1",
                 "GIT_AUTHOR_NAME": "Student", "GIT_AUTHOR_EMAIL": "student@example.edu",
                 "GIT_COMMITTER_NAME": "Student", "GIT_COMMITTER_EMAIL": "student@example.edu",
                 "CLAUDE_CONFIG_DIR": str(tmp_path / "claude")}.items():
        monkeypatch.setenv(k, v)
    monkeypatch.delenv("WORKBENCH_UPSTREAM", raising=False)
    # A commit pushes in a thread; here it pushes at once, so the test can look at the result.
    monkeypatch.setattr(server.App, "push_soon",
                        lambda self: self.push() if self.a.push and not self.updates.copy_of_class else None)


def git(where, *args):
    r = subprocess.run(["git", *args], cwd=where, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout


def homework(tmp_path, files=None):
    """The class repository (bare), the student's fork of it (bare) and the student's clone.
    `seed` is the instructor's working copy: commit there and push to `cls` to make an update."""
    seed = tmp_path / "seed"
    seed.mkdir()
    for name, text in {"steps.toml": STEPS, "WRITEUP.md": WRITEUP, "README.md": "# HW9\n\nA small homework.\n",
                       ".gitignore": ".env\n.workbench/\n", **(files or {})}.items():
        (seed / name).parent.mkdir(parents=True, exist_ok=True)
        (seed / name).write_text(text)
    git(seed, "init", "-q", "-b", "main")
    git(seed, "add", ".")
    git(seed, "commit", "-q", "-m", "Start")
    cls, fork, student = tmp_path / "class.git", tmp_path / "fork.git", tmp_path / "student"
    git(tmp_path, "clone", "-q", "--bare", str(seed), str(cls))
    git(tmp_path, "clone", "-q", "--bare", str(cls), str(fork))
    git(tmp_path, "clone", "-q", str(fork), str(student))
    return SimpleNamespace(seed=seed, cls=cls, fork=fork, student=student)


def upstream_commit(h, name, text, message):
    (h.seed / name).parent.mkdir(parents=True, exist_ok=True)
    (h.seed / name).write_text(text)
    git(h.seed, "add", ".")
    git(h.seed, "commit", "-q", "-m", message)
    git(h.seed, "push", "-q", str(h.cls), "main")


def subjects(where, ref="HEAD"):
    return git(where, "log", "--format=%s", ref).splitlines()


def save_session(repo, session_id, lines, folder="-tmp-student", hour=19):
    """A conversation as Claude Code saves it, under CLAUDE_CONFIG_DIR/projects/: one line a minute
    from `hour` o'clock on Nov 10."""
    d = Path(transcript.projects()) / folder
    d.mkdir(parents=True, exist_ok=True)
    out = []
    for n, (kind, content) in enumerate(lines):
        out.append(json.dumps({"type": kind, "uuid": f"{session_id}-{n}", "sessionId": session_id,
                               "cwd": str(repo), "timestamp": f"2026-11-10T{hour}:{n:02d}:00.000Z",
                               "message": {"role": kind, "content": content}}))
    (d / f"{session_id}.jsonl").write_text("\n".join(out) + "\n")


def tool_use(i, command):
    return {"type": "tool_use", "id": f"t{i}", "name": "Bash", "input": {"command": command}}


def tool_result(i, text):
    return {"type": "tool_result", "tool_use_id": f"t{i}", "content": text}


FAKE_KEY = "sk-" + "ant-" + "not-a-real-key"    # what a key looks like, in pieces

CHECK_OUTPUT = ("Claim: The director was born in Illinois.\nMethod: no-tools\n\nVerdict: supported\n"
                "Explanation: It remembers so.\nLookups: 0   tokens: 300 in, 40 out\n\n"
                "Saved to runs/part0/no-tools-1.json")
CHAINED = ('python3 .workbench/page.py 0b expected "supported" && uv run python check.py --method no-tools '
           '--out runs/part0 "The director was born in Illinois."')


def chained_session(repo, sid):
    save_session(repo, sid, [
        ("user", "Start step 0b."),
        ("assistant", [{"type": "text", "text": "What do you expect it to say?"}]),
        ("user", "I think supported. Run it."),
        ("assistant", [tool_use(1, CHAINED)]),
        ("user", [tool_result(1, "The page will set “supported” beside the result.\n" + CHECK_OUTPUT)]),
        ("assistant", [tool_use(2, 'python3 .workbench/page.py 0b status "Waiting for your answer"')]),
        ("user", [tool_result(2, "The page now says: Waiting for your answer")]),
        ("assistant", [{"type": "text", "text": "Here is the output. My key is " + FAKE_KEY + "."}]),
    ])


# -- the steps file and the write-up -------------------------------------------------------------

def test_the_repositorys_steps_file_loads():
    a = steps.load(ROOT / "steps.toml")
    assert a.title and a.tutor and a.parts and a.steps
    labels_ = [a.label(s) for s in a.steps]
    assert len(set(labels_)) == len(labels_)
    for s in a.steps:
        assert s.part in a.parts, s.id


def test_labels_follow_ids_like_0b_and_positions_otherwise(tmp_path):
    a = steps.load(_write(tmp_path / "s.toml", STEPS))
    assert [a.label(s) for s in a.steps] == ["0a", "0b", "1a"]
    old = STEPS.replace('id = "0a"', 'id = "0.1"').replace('id = "0b"', 'id = "0.2"')
    b = steps.load(_write(tmp_path / "t.toml", old))
    assert [b.label(s) for s in b.steps] == ["0a", "0b", "1a"]
    assert b.step("0b").id == "0.2"


def test_an_unknown_step_key_is_ignored(tmp_path, capsys):
    a = steps.load(_write(tmp_path / "s.toml", STEPS.replace('title = "Read the loop"', 'title = "Read the loop"\nnew_key = 3')))
    assert a.step("1a").title == "Read the loop"
    assert "ignoring new_key" in capsys.readouterr().out


def test_slots_and_completion_in_the_new_heading_style(tmp_path):
    a = steps.load(_write(tmp_path / "steps.toml", STEPS))
    slots = steps.read_slots(FILLED)
    assert slots["Name"] == "Sam Student"
    keys = steps.step_keys(a.step("0b"), slots)
    assert keys == ["Part 0 / 0b. Ask the model on its own / What did it say?",
                    "Part 0 / 0b. Ask the model on its own / How much would you trust it, and why?"]
    assert steps.step_keys(a.step("1a"), slots) == ["Part 1 / 1a. Read the loop / What does Claude get sent on each turn?"]

    (tmp_path / "WRITEUP.md").write_text(WRITEUP.replace("Name:", "Name: Sam Student"))
    st = {x["id"]: x for x in steps.status(a, tmp_path, set())}
    assert st["0a"]["complete"] and not st["0b"]["complete"] and not st["0b"]["locked"]
    assert st["1a"]["locked"] and st["1a"]["waiting_on"] == ["0b"]

    (tmp_path / "WRITEUP.md").write_text(FILLED)
    st = {x["id"]: x for x in steps.status(a, tmp_path, set())}
    assert not st["0b"]["complete"] and st["0b"]["missing_files"] == ["runs/part0/no-tools-*.json"]
    (tmp_path / "runs/part0").mkdir(parents=True)
    (tmp_path / "runs/part0/no-tools-1.json").write_text("{}")
    st = {x["id"]: x for x in steps.status(a, tmp_path, set())}
    assert st["0b"]["complete"] and not st["1a"]["locked"]


def test_a_second_paragraph_stays_with_its_answer_in_the_real_writeup():
    import re
    blank = (ROOT / "WRITEUP.md").read_text()
    n1, n2 = iter(range(1, 999)), iter(range(1, 999))
    filled = re.sub(r"(?m)^>[ \t]*$", lambda m: f"> Answer {next(n1)}.", blank)
    two = re.sub(r"(?m)^>[ \t]*$", lambda m: (lambda k: f"> Answer {k}.\n\nMore {k}, after a blank line.")(next(n2)), blank)
    empty, one, both = steps.read_slots(blank), steps.read_slots(filled), steps.read_slots(two)
    assert list(empty) == list(one) == list(both)           # the questions' labels never change
    assert all(v == "" for v in empty.values())             # no template text fills a blank answer
    kept = [k for k in both if both[k] != one[k]]
    assert kept and all(re.fullmatch(r"Answer (\d+)\.\n\nMore \1, after a blank line\.", both[k]) for k in kept)
    assert len(kept) == sum(v.startswith("Answer") for v in one.values())


def test_what_counts_as_more_of_an_answer():
    text = ("# Part 0: Set up\n\n## 0b. Ask\n\nFirst question?\n\n> Mine.\n\nMy second paragraph.\n\n"
            "Second question?\n\n>\n\nA note before the table:\n\n| # | Tool |\n|---|---|\n| | |\n\n"
            "Third question?\n\n> Three.\n\nThe end of answer three.\n\n## 0c. Next\n\nFourth?\n\n>\n")
    got = steps.read_slots(text)
    assert got["Part 0 / 0b. Ask / First question?"] == "Mine.\n\nMy second paragraph."
    assert got["Part 0 / 0b. Ask / Second question?"] == ""  # blank: the note never fills it
    assert "Part 0 / 0b. Ask / A note before the table:" in got   # the table's question stays its label
    assert got["Part 0 / 0b. Ask / Third question?"] == "Three.\n\nThe end of answer three."
    assert got["Part 0 / 0c. Next / Fourth?"] == ""


def _write(path, text):
    path.write_text(text)
    return path


# -- the student's record --------------------------------------------------------------------

def test_a_chained_page_call_keeps_the_real_run_in_the_record(tmp_path):
    h = homework(tmp_path)
    app = server.App(h.student)
    chained_session(h.student, app.hub.session_id("0b"))
    s = app.hub.sessions["0b"]
    s.refresh()
    rec = s.record()
    ran = [x for x in rec["entries"] if x["kind"] == "ran"]
    assert [x["text"] for x in ran] == ["Ran check.py --method no-tools The director was born in Illinois."]
    said = [x for x in rec["entries"] if x["kind"] == "said"]
    assert said and said[0]["verdict"] == "supported" and said[0]["file"] == "runs/part0/no-tools-1.json"
    tools = [e for e in s.events if e["kind"] == "tool"]
    assert tools[0]["detail"].startswith("uv run python check.py")      # the page.py part is gone
    assert tools[1]["category"] == "page"                              # a page-only call stays out


def test_the_command_splitter_respects_quotes():
    assert labels.pieces('a "x && y; z" && b; c || d\ne') == ['a "x && y; z"', "b", "c", "d", "e"]
    assert labels.without_page_calls('python3 .workbench/page.py 0b status "a; b"') == ""
    assert labels.without_page_calls("uv run python check.py x | tail -3") == "uv run python check.py x | tail -3"


def test_each_command_carries_the_model_and_troubleshooting_says_what_to_do_without_it(tmp_path):
    h = homework(tmp_path)
    snap = server.App(h.student).hub.sessions["0a"].snapshot()
    flags = "--model claude-opus-5-5 --effort medium"
    assert snap["model_flags"] == flags
    assert flags in snap["command"]
    # The page says nothing about it under the command (the instructor, Nov 11). Step 0a's
    # Troubleshooting and the README say what to do, with the same flags the command carries.
    js = (ROOT / "workbench/static/app.js").read_text()
    assert "model is not available" not in js
    first_step = (ROOT / "instructions/part0.md").read_text().split("\n## ")[1]
    trouble = " ".join(first_step.split("**Troubleshooting:**")[1].split())
    assert f"is not available. Delete `{flags}` from the command" in trouble
    assert f"is not available.** Delete `{flags}` from the command" in " ".join((ROOT / "README.md").read_text().split())


def test_a_chained_call_is_labelled_by_what_is_left(tmp_path):
    h = homework(tmp_path)
    app = server.App(h.student)
    save_session(h.student, app.hub.session_id("0a"), [
        ("user", "Start step 0a."),
        ("assistant", [{"type": "tool_use", "id": "t1", "name": "Bash", "input": {
            "command": 'python3 .workbench/page.py 0a done 4 && grep -n "^Name:" WRITEUP.md',
            "description": "Tick the checkpoint and confirm the name line"}}]),
        ("user", [tool_result(1, "The page now shows it as reached.\n3:Name: Sam")]),
    ])
    s = app.hub.sessions["0a"]
    s.refresh()
    assert [x["text"] for x in s.record()["entries"] if x["kind"] == "ran"] == ["Ran grep"]


def test_each_tick_sits_at_the_moment_it_was_reached(tmp_path):
    two = STEPS.replace('"You read the output with Claude",', '"You read the output with Claude", "You asked it to run",')
    h = homework(tmp_path, {"steps.toml": two})
    app = server.App(h.student)
    save_session(h.student, app.hub.session_id("0b"), [
        ("user", "Start step 0b."), ("assistant", [{"type": "text", "text": "What do you expect?"}]),
        ("user", "Supported."), ("assistant", [{"type": "text", "text": "Noted."}]),
        ("user", "Run it."), ("assistant", [{"type": "text", "text": "Done."}]),
    ])
    with open(app.hub.page_log, "a") as f:                       # what Claude told the page, and when
        for clock, n in (("18:59:00", 1), ("19:04:30", 2)):
            f.write(json.dumps({"t": stamp(f"2026-11-10T{clock}Z"), "step": "0b", "kind": "checkpoint", "n": n}) + "\n")
    s = app.hub.sessions["0b"]
    s.refresh()
    marked = {x.get("text"): x["reached"] for x in s.record()["entries"] if x.get("reached")}
    assert marked == {None: ["You read the output with Claude"], "Run it.": ["You asked it to run"]}


def test_the_guard_lets_a_search_through_only_when_it_names_its_files(tmp_path):
    h = homework(tmp_path)
    app = server.App(h.student)
    (h.student / "runs/part2").mkdir(parents=True)
    (h.student / "runs/part2/agent.jsonl").write_text("{}\n")
    (h.student / "data").mkdir()
    (h.student / "data/eval.jsonl").write_text("{}\n")
    guard = app.hub.dir / "guard.py"

    def reason(command):
        event = {"tool_name": "Bash", "tool_input": {"command": command}, "session_id": "s"}
        out = subprocess.run([sys.executable, str(guard), "pre"], input=json.dumps(event),
                             capture_output=True, text=True).stdout
        return json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"] if out.strip() else None

    for ok in ('grep -n -o "Mike Smith was born" runs/part2/agent.jsonl',      # the briefs' three commands
               """grep -n -o '"correct": false' runs/part2/agent.jsonl""",
               'grep -n "hover-1234" data/eval.jsonl',
               'grep -n -e "x" -e "y" data/eval.jsonl runs/part2/agent.jsonl',
               'grep -n -A2 "x" data/eval.jsonl 2>/dev/null',
               'echo "use grep -r x . to search everything"',                    # the word in quotes
               'echo grep is a tool',
               'python3 .workbench/page.py 0b status "Searching with grep -rn"',
               "uv run pytest -q"):
        assert reason(ok) is None, ok
    for bad in ('grep -n -r "x" .', 'grep -rn "x" .', 'grep -nr "x" .', 'grep -R "x" runs',
                'grep --recursive -n "x" runs', 'grep -d recurse -n "x" runs', 'grep --directories=recurse x runs',
                'grep -n "x" *.py', 'grep -n "x" tests/*', 'grep -n "x" .', 'grep -n "x" runs/part2',
                'grep -n "x"', 'cat data/eval.jsonl | grep -n "x"', 'grep -n "x" < data/eval.jsonl',
                'rg "x"', 'rg -n "x" .', 'egrep -r "x" runs', 'fgrep -n "x" *',
                'find . -type f -exec grep -n KEY {} \\;', 'ls | xargs grep -n KEY',
                'cd runs && grep -rn x .', 'timeout 5 grep -rn x runs'):
        assert "Search one named file at a time" in (reason(bad) or ""), bad
    assert reason('grep -n "KEY" .env').startswith("Never read, print or edit .env")   # as before
    (h.student / "keyfile").symlink_to(h.student / ".env")
    assert "Search one named file" in reason('grep -n "KEY" keyfile')                 # a link to it


def test_the_guard_lets_a_status_line_mention_the_key_file(tmp_path):
    h = homework(tmp_path)
    app = server.App(h.student)
    guard = app.hub.dir / "guard.py"

    def refused(command):
        event = {"tool_name": "Bash", "tool_input": {"command": command}, "session_id": "s"}
        out = subprocess.run([sys.executable, str(guard), "pre"], input=json.dumps(event),
                             capture_output=True, text=True).stdout
        return "deny" in out

    assert not refused('python3 .workbench/page.py 0a status "Waiting for you to make .env"')
    assert not refused("test -f .env && echo there")
    assert refused("cat .env")
    assert refused('python3 .workbench/page.py 0a status "x" && cat .env')
    assert refused('python3 .workbench/page.py 0a status "$(cat .env)"')
    assert refused("git commit -m x")


def test_every_step_of_the_real_homework_has_a_command_and_a_prompt(tmp_path):
    for name in ("steps.toml", "WRITEUP.md", "README.md"):
        (tmp_path / name).write_text((ROOT / name).read_text())
    (tmp_path / "instructions").mkdir()
    for f in (ROOT / "instructions").glob("*.md"):
        (tmp_path / "instructions" / f.name).write_text(f.read_text())
    git(tmp_path, "init", "-q", "-b", "main")
    app = server.App(tmp_path)
    for s in app.a.steps:
        sess = app.hub.sessions[s.id]
        sess.prepare()
        label = app.a.label(s)
        assert sess.command().startswith(f'claude -n "{label} ')
        prompt = (app.hub.dir / f"{label}.md").read_text()
        assert app.a.tutor.strip()[:60] in prompt and "(No section" not in prompt, label
        assert json.loads((app.hub.dir / f"{label}.json").read_text())["permissions"]["allow"]
    assert json.loads(json.dumps(app.assignment()))["steps"]


def test_a_checkpoint_with_a_file_or_answers_is_ticked_only_by_them(tmp_path):
    h = homework(tmp_path)
    app = server.App(h.student)
    (h.student / "WRITEUP.md").write_text(FILLED)           # 0b's answers typed, no run file yet
    rec = app.hub.sessions["0b"].record()
    # The prediction (no file or answer of its own) is implied by the later answers; the run's
    # file is not there, so its box stays empty and the student can see what is missing.
    assert [c["done"] for c in rec["checkpoints"]] == [True, False, True]
    assert rec["now"] == {"todo": "You've seen the model answer"}
    (h.student / "runs/part0").mkdir(parents=True)
    (h.student / "runs/part0/no-tools-1.json").write_text("{}")
    rec = app.hub.sessions["0b"].record()
    assert [c["done"] for c in rec["checkpoints"]] == [True, True, True]
    assert sorted(x["text"] for x in rec["summary"] if x["kind"] == "reached") == \
        ["You've seen the model answer", "Your answers"]     # each line says its checkpoint


# 0b's first checkpoint as a task only the student can see done (instructor, Nov 11: "Should I be
# talking with Claude? Should I be typing in the writeup? Clarify.").
NO_TICK_STEPS = STEPS.replace('  "You read the output with Claude",\n',
                              '  { text = "You read the output", task = "In the results viewer, read the output.", tick = false },\n')


def test_a_task_only_the_student_can_see_done_is_never_ticked_and_nothing_waits_on_it(tmp_path):
    assert NO_TICK_STEPS != STEPS
    h = homework(tmp_path, {"steps.toml": NO_TICK_STEPS})
    app = server.App(h.student)
    finish_part0(h.student)                                  # 0b's run and answers are in place
    rec = app.hub.sessions["0b"].record()
    # Not ticked by the later checkpoints either, and not named as still to do.
    assert [(c["tick"], c["done"]) for c in rec["checkpoints"]] == [(False, False), (True, True), (True, True)]
    assert rec["now"] == {"done": True}
    assert {x["id"]: x for x in steps.status(app.a, h.student, set())}["0b"]["complete"]
    srv, base = serving(app)
    try:
        code, _, body = fetch(base + "/api/step/0b/mark", json.dumps({"checkpoint": 1, "by": "claude"}).encode(),
                              {"Content-Type": "application/json"})
        assert code == 409 and "with no tick" in json.loads(body)["error"]
    finally:
        srv.shutdown()
        srv.server_close()
    assert not [r for r in app.hub.page_records("0b") if r["kind"] == "checkpoint"]
    app.hub.record("0b", "status", text="Waiting for your answers in WRITEUP.md")
    app.hub.save_records(h.student / "record")
    saved = json.loads((h.student / "record/0b.json").read_text())
    assert saved["complete"] and "You read the output" not in [c["text"] for c in saved["checkpoints"]]
    app.hub.sessions["0b"].prepare()
    prompt = " ".join((app.hub.dir / "0b.md").read_text().split())
    assert ("1. You read the output (the student does this where you cannot see it, and the page shows it with "
            "no tick: never tick it, and never ask whether they have done it)") in prompt


def test_a_step_whose_only_task_has_no_tick_is_still_done_when_claude_marks_it(tmp_path):
    only = STEPS.replace('title = "Read the loop"\nslots = ["1a.*"]',
                         'title = "Read the loop"\ncheckpoints = [{ text = "You read it", task = "In the results viewer, read it.", tick = false }]')
    assert only != STEPS
    h = homework(tmp_path, {"steps.toml": only})
    app = server.App(h.student)
    finish_part0(h.student)
    st = {x["id"]: x for x in steps.status(app.a, h.student, app.hub.marked())}["1a"]
    assert st["manual"] and not st["complete"] and not st["locked"]
    app.hub.sessions["1a"].prepare()
    assert "then mark the step done once the student says they have finished it" in \
        " ".join((app.hub.dir / "1a.md").read_text().split())
    srv, base = serving(app)
    try:
        code, _, _ = fetch(base + "/api/step/1a/mark", json.dumps({"done": True, "by": "claude"}).encode(),
                           {"Content-Type": "application/json"})
        assert code == 200
    finally:
        srv.shutdown()
        srv.server_close()
    assert {x["id"]: x for x in steps.status(app.a, h.student, app.hub.marked())}["1a"]["complete"]


# -- going on to another step in the same session (instructor, Nov 11: "i'd like to rework so that i
# always have the option of continuing an existing claude session (from a previous step) or
# starting a new one. Give both in the web ui.") ---------------------------------------------------

def go_on(label):
    from workbench.sessions import continue_prompt
    return continue_prompt(label)


def test_one_conversation_can_serve_several_steps_and_each_record_follows_its_step(tmp_path):
    h = homework(tmp_path)
    app = server.App(h.student)
    hub = app.hub
    sid = hub.session_id("0b")
    lines = [
        ("user", "Start step 0b."),                                                      # 19:00
        ("assistant", [{"type": "text", "text": "This step asks the model. Ask me to run it."}]),
        ("user", "Run it."),
        ("assistant", [tool_use(1, "uv run python check.py --method no-tools --out runs/part0 \"x\"")]),
        ("user", [tool_result(1, CHECK_OUTPUT)]),
        ("assistant", [{"type": "text", "text": "Next, type your answers in WRITEUP.md."}]),
        ("user", go_on("1a")),                                                           # 19:06
        ("assistant", [{"type": "text", "text": "I am now on step 1a. Read the loop first."}]),
        ("user", "What does Claude get sent?"),
        ("assistant", [{"type": "text", "text": "The whole conversation so far."}]),
    ]
    save_session(h.student, sid, lines)
    with (hub.dir / "hooks.jsonl").open("a") as f:      # one refusal while it served 1a
        f.write(json.dumps({"t": stamp("2026-11-10T19:08:30.000Z"), "session_id": sid, "kind": "refused",
                            "text": "The page refused a git command, because the page makes the commits."}) + "\n")
    b, a1 = hub.sessions["0b"], hub.sessions["1a"]
    for s in (b, a1):
        s.refresh()
    asked = lambda s: [x["text"] for x in s.record()["entries"] if x["kind"] == "asked"]   # noqa: E731
    ran = lambda s: [x["text"] for x in s.record()["entries"] if x["kind"] == "ran"]       # noqa: E731
    assert asked(b) == ["Run it."] and len(ran(b)) == 1
    assert asked(a1) == ["What does Claude get sent?"] and ran(a1) == []
    assert [e["text"] for e in a1.events if e["kind"] == "student" and e["opening"]] == [go_on("1a")]
    assert any("refused a git command" in e.get("text", "") for e in a1.events)
    assert not any("refused a git command" in e.get("text", "") for e in b.events)
    assert b.state == "moved on" and "went on to step 1a" in b.now and not b.busy
    assert a1.state != "moved on"                      # old test times: "stopped", not "moved on"
    assert hub.worked_in() == {"0b": [sid], "1a": [sid]}
    flags = f"--model claude-opus-5-5 --effort medium --setting-sources user"
    # Back to 1a: reopen the conversation as it is. Back to 0b: reopen it and move it back onto 0b.
    assert a1.back_command().startswith(f"claude --resume {sid} {flags} --settings .workbench/1a.json ")
    assert not a1.back_command().endswith('."')
    assert b.back_command().startswith(f"claude --resume {sid} {flags} --settings .workbench/0b.json ")
    assert b.back_command().endswith(f' "{go_on("0b")}"')
    # TRANSCRIPT.md: the conversation once, under 0b; 1a says where its part is.
    ids = {s.id: hub.session_id(s.id) for s in app.a.steps}
    text = transcript.build(h.student, app.a, ids, hub.worked_in())
    assert text.count(f"<!-- transcript-session: {sid} |") == 1
    assert text.index("# 0b.") < text.index(sid) < text.index("# 1a.")
    assert f"This step was done in the conversation under 0b, session `{sid[:8]}`, from the message “Start step 1a.”" in text

    # The student goes back to 0b in the same conversation.
    save_session(h.student, sid, lines + [("user", go_on("0b")),
                                          ("assistant", [{"type": "text", "text": "I am now on step 0b."}])])
    for s in (b, a1):
        s.refresh()
    assert a1.state == "moved on" and b.state != "moved on"
    assert not b.back_command().endswith('."') and a1.back_command().endswith(f' "{go_on("1a")}"')

    # 1a goes on later in a new session of its own: the record is the latest conversation's, and
    # the conversation panel (the events) holds both, each marked where it begins.
    own = hub.session_id("1a")
    save_session(h.student, own, [("user", "Start step 1a."), ("user", "And the tools?"),
                                  ("assistant", [{"type": "text", "text": "Four of them."}])], hour=20)
    assert own in hub.missed                         # looked for a moment ago: the page waits 2 seconds
    hub.missed.clear()                               # before it looks for a new session again
    a1.refresh()
    assert asked(a1) == ["And the tools?"]
    said = [e["text"] for e in a1.events if e["kind"] == "student"]
    assert "What does Claude get sent?" in said and "And the tools?" in said
    assert [e["text"] for e in a1.events if e["kind"] == "note" and "begins here" in e["text"]] == \
        [f"Claude session {sid[:8]} begins here.", f"Claude session {own[:8]} begins here."]
    assert hub.worked_in()["1a"] == [sid, own] and a1.state != "moved on"
    assert a1.back_command().startswith(f"claude --resume {own} ")


# -- a new-session command that can be run any number of times (instructor, Nov 11, 9:20pm:
# "Error: Session ID 45c672c2-... is already in use.") ------------------------------------------

def project_folder(repo):
    """The folder Claude Code keeps a working folder's conversations in, under projects/."""
    import re
    return re.sub(r"[^A-Za-z0-9]", "-", str(repo))


def test_no_new_session_command_names_a_session_id(tmp_path):
    import shutil as sh
    h = homework(tmp_path)
    for name in ("steps.toml", "WRITEUP.md", "README.md", "instructions"):
        src = ROOT / name
        (sh.copytree if src.is_dir() else sh.copyfile)(src, h.student / name)
    app = server.App(h.student)
    for s in app.a.steps:
        cmd = app.hub.sessions[s.id].command()
        assert "--session-id" not in cmd and cmd.startswith(f'claude -n "{app.a.label(s)} '), s.id
        assert cmd.endswith(f'"Start step {app.a.label(s)}."'), s.id
    assert "sessions" not in app.hub.state or not app.hub.state["sessions"]   # no id is made in advance


def test_a_steps_conversations_are_found_by_their_first_message_and_the_latest_is_its_record(tmp_path):
    h = homework(tmp_path)
    app = server.App(h.student)
    hub, b = app.hub, app.hub.sessions["0b"]
    here = project_folder(h.student)
    # Two runs of 0b's command: two conversations, neither in state.json.
    save_session(h.student, "first-run", [("user", "Start step 0b."), ("user", "Run it."),
                                          ("assistant", [{"type": "text", "text": "Ran it."}])], folder=here)
    save_session(h.student, "second-run", [("user", "Start step 0b."), ("user", "Run it again."),
                                           ("assistant", [{"type": "text", "text": "Ran it again."}])],
                 folder=here, hour=20)
    # Not the homework's: the same opening message recorded for another folder, in its own folder
    # and in this one; and a plain `claude` conversation in this folder.
    save_session(tmp_path / "elsewhere", "elsewhere-run", [("user", "Start step 0b.")], folder=project_folder(tmp_path / "elsewhere"))
    save_session(tmp_path / "elsewhere", "stray-run", [("user", "Start step 0b.")], folder=here)
    save_session(h.student, "plain-run", [("user", "hello")], folder=here)
    assert "sessions" not in hub.state or not hub.state["sessions"]
    b.refresh()
    assert sorted(hub.discovered()) == ["first-run", "second-run"]
    assert hub.worked_in() == {"0b": ["first-run", "second-run"]}
    asked = [x["text"] for x in b.record()["entries"] if x["kind"] == "asked"]
    assert asked == ["Run it again."]                                       # the latest conversation
    assert "Run it." in [e["text"] for e in b.events if e["kind"] == "student"]   # the earlier one, in the panel
    assert b.back_command().startswith("claude --resume second-run ")
    assert "--session-id" not in b.command()
    text = transcript.build(h.student, app.a, {}, hub.worked_in(), hub.homes())
    for sid in ("first-run", "second-run"):
        assert text.count(f"<!-- transcript-session: {sid} |") == 1
        assert text.index("# 0b.") < text.index(sid)
    assert text.index("plain-run") > text.index("# Other Claude sessions in this folder")
    assert "elsewhere-run" not in text and "stray-run" not in text


def test_a_session_id_already_in_state_json_is_still_read(tmp_path):
    """Records made before the command stopped naming an id: state.json's sessions still count, in
    whatever folder Claude Code put them, and their step's go-back command resumes them."""
    h = homework(tmp_path)
    app = server.App(h.student)
    hub = app.hub
    hub.state["sessions"] = {"0b": "old-0b"}
    save_session(h.student, "old-0b", [("user", "Start step 0b."), ("user", "Run it."),
                                       ("assistant", [{"type": "text", "text": "Ran it."}])], folder="-somewhere-else")
    b = hub.sessions["0b"]
    b.refresh()
    assert [x["text"] for x in b.record()["entries"] if x["kind"] == "asked"] == ["Run it."]
    assert b.back_command().startswith("claude --resume old-0b ")
    ids = {s.id: sid for s in app.a.steps if (sid := hub.known_id(s.id))}
    assert ids == {"0b": "old-0b"}
    text = transcript.build(h.student, app.a, ids, hub.worked_in(), hub.homes())
    assert text.count("<!-- transcript-session: old-0b |") == 1 and text.index("# 0b.") < text.index("old-0b")


def test_a_retired_conversation_is_read_for_no_step(tmp_path):
    """A conversation from before the steps were renumbered opens with an old label ("Start step
    0c." was the no-tools step): a port lists it in state.json's retired_sessions, and the page then
    reads it for no step. TRANSCRIPT.md still writes it, with the folder's other conversations."""
    h = homework(tmp_path)
    app = server.App(h.student)
    hub = app.hub
    save_session(h.student, "before-renumbering", [("user", "Start step 0b."), ("user", "Old step 0b.")],
                 folder=project_folder(h.student))
    hub.state["retired_sessions"] = ["before-renumbering"]
    assert hub.discovered() == {} and hub.worked_in() == {}
    text = transcript.build(h.student, app.a, {}, hub.worked_in(), hub.homes())
    assert text.index("before-renumbering") > text.index("# Other Claude sessions in this folder")


def test_a_start_message_for_a_step_that_does_not_exist_starts_nothing(tmp_path):
    h = homework(tmp_path)
    app = server.App(h.student)
    sid = app.hub.session_id("0b")
    save_session(h.student, sid, [("user", "Start step 0b."), ("user", "Start step 9z. Read .workbench/9z.md"),
                                  ("assistant", [{"type": "text", "text": "There is no such step."}])])
    assert [st["step"] for st in app.hub.stretches()] == ["0b"]


def test_every_steps_settings_allow_every_steps_shell_commands_and_share_the_hook(tmp_path):
    """A continued session keeps the settings it was started with, so no step's commands ask
    first in it. An Edit rule (3b's instructions.md, 1a's my_loop.py) stays with its own step."""
    import shutil as sh
    h = homework(tmp_path)
    for name in ("steps.toml", "WRITEUP.md", "README.md", "instructions"):
        src = ROOT / name
        (sh.copytree if src.is_dir() else sh.copyfile)(src, h.student / name)
    app = server.App(h.student)
    shells = {r for s in app.a.steps for r in s.allow if r.startswith("Bash(")}
    hooks = set()
    for s in app.a.steps:
        app.hub.sessions[s.id].prepare()
        settings = json.loads((app.hub.dir / f"{app.a.label(s)}.json").read_text())
        allow = settings["permissions"]["allow"]
        assert shells <= set(allow), s.id
        assert ("Edit(instructions.md)" in allow) == (s.id == "3b"), s.id
        assert ("Edit(my_loop.py)" in allow) == (s.id == "1a"), s.id
        hooks.add(json.dumps(settings["hooks"], sort_keys=True))
    assert len(hooks) == 1                                   # the same guard for every step


def test_the_page_offers_both_ways_and_only_the_command_for_the_first_step(tmp_path):
    h = homework(tmp_path)
    (h.student / "WRITEUP.md").write_text(WRITEUP.replace("Name:", "Name: Sam"))
    app = server.App(h.student)
    first, second = app.hub.sessions["0a"].snapshot(), app.hub.sessions["0b"].snapshot()
    assert first["continue_prompt"] is None and first["command"].startswith('claude -n "0a ')
    assert second["continue_prompt"] == ("Start step 0b. Read .workbench/0b.md and follow it from now on, in "
                                         "place of your instructions for any other step.")
    assert second["command"].startswith('claude -n "0b ')
    assert (app.hub.dir / "0b.md").exists()                  # the file the prompt names
    prompt = " ".join((app.hub.dir / "0b.md").read_text().split())
    assert "In a session that was on another step, first say in one line that you are now on step 0b." in prompt
    assert "its prompt, pasted into this chat, moves this session onto it" in prompt
    node = node_or_none()
    if not node:
        return
    js = (ROOT / "workbench/static/app.js").read_text()
    lines = js.splitlines()
    first_line = next(i for i, x in enumerate(lines) if x.startswith("const esc ="))
    last_line = next(i for i, x in enumerate(lines) if x.startswith("let A"))
    consts = [x for x in lines if x.startswith(("const IN_CHAT =", "const GO_BACK =", "const IN_TERMINAL ="))]
    run = "\n".join(lines[first_line:last_line] + consts + [page_function(js, "command"), page_function(js, "claudeBoxes")])
    cases = [{"command": "claude -n x", "continue_prompt": None, "back_command": None},
             {"command": "claude -n y", "continue_prompt": "Start step 0b. Read it.", "back_command": None},
             {"command": "claude -n z", "continue_prompt": "Start step 0b. Read it.", "back_command": "claude --resume z"},
             {"command": "claude -n w", "continue_prompt": None, "back_command": "claude --resume w"}]
    run += "\n" + "\n".join(f"console.log(JSON.stringify(claudeBoxes({json.dumps(c)})));" for c in cases)
    out = [json.loads(x) for x in subprocess.run([node, "-e", run], capture_output=True, text=True).stdout.splitlines()]
    labels_of = lambda html_text: __import__("re").findall(r'<span class="label">([^<]*)</span>', html_text)  # noqa: E731
    assert labels_of(out[0]) == ["Start a new Claude session"]
    assert labels_of(out[1]) == ["Continue in the Claude session you have open", "Or start a new Claude session"]
    # A started step: three choices, the easiest first, each with its Copy button and its sentence.
    assert labels_of(out[2]) == ["Continue in the Claude session you have open", "Or go back to this step's conversation",
                                 "Or start a new Claude session"]
    assert labels_of(out[3]) == ["Go back to this step's conversation", "Or start a new Claude session"]   # 0a, started
    assert out[2].count('class="copy"') == 3 and out[2].count('<span class="small">') == 3
    assert out[2].index("Start step 0b. Read it.") < out[2].index("claude --resume z") < out[2].index("claude -n z")
    assert "Paste this into the Claude session you already have open from this page, as a message." in out[2]
    assert "to open this step's last conversation again." in out[2]
    assert "It starts a new conversation for this step every time you run it." in out[2]
    assert "If another Claude session is open in that terminal, type /exit first." in out[1]


def test_the_name_has_its_own_plain_now_line(tmp_path):
    h = homework(tmp_path, {"steps.toml": STEPS.replace('slots = ["Name"]', 'slots = ["Name"]\ncheckpoints = [{ text = "Your name", slots = ["Name"] }]')})
    app = server.App(h.student)
    rec = app.hub.sessions["0a"].record()
    assert rec["now"] == {"plain": "type your name after Name: at the top of WRITEUP.md, in your editor."}
    slot = rec["checkpoints"][0]["slots"][0]
    assert slot["todo"] == "Not written yet. Type it after Name: at the top of WRITEUP.md."
    js = (ROOT / "workbench/static/app.js").read_text()
    assert "Paste this into a terminal in your homework folder, not into a Claude chat. It starts a new " \
           "conversation for this step every time you run it. If another Claude session is open in that " \
           "terminal, type /exit first." in js


def test_a_step_can_carry_a_command_the_student_runs_themselves(tmp_path):
    own = ("uv run python evaluate.py data/eval.jsonl --out \"runs/part 2\" --note 'the student\'s run'")
    literal = "'" * 3 + own + "'" * 3                     # a TOML literal string
    steps_ = STEPS.replace('title = "Read the loop"', 'title = "Read the loop"\nrun_yourself = { command = '
                           + literal + ', note = "About 20 minutes. Leave that tab open." }')
    h = homework(tmp_path, {"steps.toml": steps_})
    app = server.App(h.student)
    a = json.loads(json.dumps(app.assignment()))
    by = {s["label"]: s for s in a["steps"]}
    assert by["1a"]["run_yourself"] == {"command": own, "note": "About 20 minutes. Leave that tab open."}
    assert by["0b"]["run_yourself"] is None
    (h.student / "WRITEUP.md").write_text(FILLED)
    finish_part0(h.student)
    app.hub.sessions["1a"].prepare()
    assert own in (app.hub.dir / "1a.md").read_text()
    app.hub.sessions["0b"].prepare()
    assert "terminal tab of\ntheir own" not in (app.hub.dir / "0b.md").read_text()
    js = (ROOT / "workbench/static/app.js").read_text()
    assert "Run this yourself, in a terminal tab of your own" in js


def node_or_none():
    import glob
    import shutil
    return shutil.which("node") or next(iter(sorted(glob.glob(str(Path.home() / ".nvm/versions/node/*/bin/node")))), None)


def text_helpers(js):
    """The page's text helpers (esc, linkText, codeText): the lines from `const esc =` to `let A`."""
    lines = js.splitlines()
    first = next(i for i, x in enumerate(lines) if x.startswith("const esc ="))
    last = next(i for i, x in enumerate(lines) if x.startswith("let A"))
    return "\n".join(lines[first:last])


def test_a_code_span_or_a_link_in_a_task_or_question_shows_as_such_and_nothing_else_is_markup():
    js = (ROOT / "workbench/static/app.js").read_text()
    helpers = text_helpers(js)
    assert "linkText(emphasis(esc(part)))" in helpers and "esc(part.slice(1, -1))" in helpers   # escaped first
    for site in ('<span class="q">${codeText(text)}</span>', "codeText(now.question)", "codeText(now.todo)",
                 'line("tick", codeText(x.text) + ".")', "row(c.done, `${c.n}. ${c.task || c.text}`"):
        assert site in js, site
    node = node_or_none()
    if not node:                                            # a laptop without node: the checks above stand
        return
    cases = {
        "Give the line numbers in `my_loop.py`.": "Give the line numbers in <code>my_loop.py</code>.",
        "Is <b>this</b> bold? `<i>x</i>`": "Is &lt;b&gt;this&lt;/b&gt; bold? <code>&lt;i&gt;x&lt;/i&gt;</code>",
        "Write *supported* or `doesn't say`.": "Write <em>supported</em> or <code>doesn't say</code>.",
        "A **bold** word, a `*code*` span and 2 * 3 * 4.": "A <strong>bold</strong> word, a <code>*code*</code> span and 2 * 3 * 4.",
        "Select 112 claims in the [claim finder](/claims/) and save them.":
            'Select 112 claims in the <a href="/claims/" target="_blank" rel="noopener">claim finder</a> and save them.',
        "Read the [retrieval code](https://github.com/shilad/comp440-hw3/blob/main/finder/search.py#L1-L165) in `finder/search.py`.":
            'Read the <a href="https://github.com/shilad/comp440-hw3/blob/main/finder/search.py#L1-L165" '
            'target="_blank" rel="noopener">retrieval code</a> in <code>finder/search.py</code>.',
        "[a](javascript:void) [b](//elsewhere.example) [c](notes.md)": "a b c",   # only words
        'A [quoted](https://x.example/"onclick=1) link': 'A <a href="https://x.example/&quot;onclick=1" '
                                                          'target="_blank" rel="noopener">quoted</a> link',
        "`[not a link](/x)` stays code": "<code>[not a link](/x)</code> stays code",
    }
    run = helpers + "\n" + "\n".join(f"console.log(codeText({json.dumps(q)}));" for q in cases)
    out = subprocess.run([node, "-e", run], capture_output=True, text=True).stdout.splitlines()
    assert out == list(cases.values())


def test_a_steps_summary_shows_open_and_closed_and_only_setup_is_plain(tmp_path):
    h = homework(tmp_path, {"steps.toml": STEPS.replace('title = "Ask the model on its own"',
                                                        'title = "Ask the model on its own"\nsummary = "In this step you ask it."\n'
                                                        'goal = "An old goal, no longer shown."')})
    a = server.App(h.student).assignment()
    step = next(s for s in a["steps"] if s["label"] == "0b")
    assert step["summary"] == "In this step you ask it." and "goal" not in step
    js = (ROOT / "workbench/static/app.js").read_text()
    css = (ROOT / "workbench/static/style.css").read_text()
    assert ".step.open .step-sum" not in css                # shown when the step is open too
    assert "const plain" not in js and "s.goal" not in js     # one layout for every step, no goal


def test_a_part_marked_extra_credit_is_labelled_not_counted_and_still_committed(tmp_path):
    extra = STEPS.replace('number = 1\ntitle = "The loop"', 'number = 1\ntitle = "The loop"\nextra_credit = true')
    h = homework(tmp_path, {"steps.toml": extra})
    app = server.App(h.student)
    parts = {p["number"]: p for p in app.assignment()["parts"]}
    assert parts[1].get("extra_credit") is True and not parts[0].get("extra_credit")
    js = (ROOT / "workbench/static/app.js").read_text()
    assert '${p.extra_credit ? " (extra credit)" : ""}' in js
    assert "const required = S.steps.filter((x) => !extra.includes(x.part));" in js
    assert "extra credit." in js
    # Once the required steps are done, the next step is named as extra credit, and so is its due date.
    assert "`Every required step is done. The next step, ${jump}, is extra credit.`" in js and '"Every step is done."' in js
    assert '${part.extra_credit ? " (extra credit)" : ""} is due ${due(part)}' in js
    assert "What you ask Claude, and what comes back, will be recorded here." in js and "What you predict" not in js
    finish_part0(h.student)
    (h.student / "WRITEUP.md").write_text(FILLED.replace("each turn?\n\n>", "each turn?\n\n> The messages."))
    app.commit_finished_parts()
    assert subjects(h.student)[:2] == ["Part 1 done", "Part 0 done"]   # the extra-credit part commits too


def test_the_session_opens_on_the_summary_and_asks_for_no_prediction(tmp_path):
    h = homework(tmp_path, {"steps.toml": STEPS.replace('title = "Ask the model on its own"',
                                                        'title = "Ask the model on its own"\nsummary = "In this step you ask it."')})
    app = server.App(h.student)
    (h.student / "WRITEUP.md").write_text(WRITEUP.replace("Name:", "Name: Sam"))
    app.hub.sessions["0b"].prepare()
    prompt = (app.hub.dir / "0b.md").read_text()
    assert "as the page says it under the step's title: In this step you ask it." in prompt
    # The first reply names the first task not done and what to type for it, never "What would you
    # like to do first?" (instructor, Nov 11: "Should I be talking with Claude? ... Clarify.").
    flat_prompt = " ".join(prompt.split())
    assert "then the first task on the page that is not done yet and what to type to get it done" in flat_prompt
    assert "Do not ask what they would like to do first." in flat_prompt
    assert "ask what they would like to do first, and wait" not in flat_prompt
    assert "what they expect, or" not in prompt and "note what the student expects before a run" not in prompt
    assert "you may name the next one that is not done" in prompt
    skill = (ROOT / "workbench/plugin/skills/page/SKILL.md").read_text()
    assert "Waiting for your prediction" not in skill and "said their prediction" not in skill


def page_function(js, name):
    """The source of a top-level function in app.js."""
    start = js.index(f"function {name}(")
    return js[start:js.index("\n}\n", start) + 3]


def run_layout_js(calls, setup=""):
    """Each expression's value, from the page's own text helpers, sections(), leftCol(), counts()
    and trim, run in node; None without node. `setup` runs first (to set A, say)."""
    node = node_or_none()
    if not node:
        return None
    js = (ROOT / "workbench/static/app.js").read_text()
    lines = js.splitlines()
    first = next(i for i, x in enumerate(lines) if x.startswith("const esc ="))
    last = next(i for i, x in enumerate(lines) if x.startswith("// Replace an element's HTML"))
    trim_line = next(x for x in lines if x.startswith("const trim ="))
    run = "\n".join(lines[first:last] + [trim_line, page_function(js, "leftCol"), page_function(js, "counts"), setup]) \
        + "\n" + "\n".join(f"console.log(JSON.stringify({c}));" for c in calls)
    done = subprocess.run([node, "-e", run], capture_output=True, text=True)
    assert done.returncode == 0, done.stderr[-2000:]
    return [json.loads(x) for x in done.stdout.splitlines()]


def folds(html_text):
    """(summary, body) of each folded part, in order."""
    import re
    return re.findall(r'<details class="fold" data-key="[^"]*"><summary>([^<]*)</summary>'
                      r'<div class="fold-body">(.*?)</div></details>', html_text, re.S)


STEP = {"label": "0b", "summary": "In this step you ask it.", "claim": False, "body":
        "In this step you ask it.\n\nThe claim you check:\n\n> A short claim.\n\n"
        "**Words in this step:** A *word*.\n\n**Actions:**\n\n1. Do this.\n2. Then that.\n\n"
        "**The six rules:**\n\n1. Ask the model.\n\n**Interpreting output:** It prints a line.\n\n```\n**Hint:** in code\n```\n\n"
        "**Write-up:** Type it.\n\n**Completion:** Done.\n\n**Troubleshooting:**\n\n- One.\n\n"
        "**Hint:** Read it twice.\nAnd slowly.\n\n**Something new:** Folds too."}


def test_the_real_0b_question_shows_its_verdict_words_in_italics():
    import re
    slots = steps.read_slots((ROOT / "WRITEUP.md").read_text())
    question = next(k.split(" / ")[-1] for k in slots if " / 0b." in k)
    assert "*supported*" in question
    out = run_page_js([f"codeText({json.dumps(question)})"])
    if out is None:
        return
    assert "<em>supported</em>, <em>refuted</em> or <em>doesn't say</em>" in out[0] and "*" not in out[0]
    assert not re.search(r"<(?!/?em>)", out[0])               # no other markup


def test_one_due_date_is_said_once_at_the_top_and_different_ones_on_each_part():
    js = (ROOT / "workbench/static/app.js").read_text()
    assert "byId(\"due\").textContent = dues.top;" in js
    assert "(p.due && !saved && !dues.same ? ` · due ${shortDue(p)}` : \"\")" in js   # headers keep it only then
    node = node_or_none()
    if not node:
        return
    lines = js.splitlines()
    helpers = [x for x in lines if x.startswith(("const due =", "const shortDue ="))] + [page_function(js, "dueText")]
    same = [{"number": n, "due": "8:00am Tuesday, November 24"} for n in range(4)]
    same[3]["extra_credit"] = True
    differ = [{"number": 0, "due": "8:00am Thursday, November 12"}, {"number": 1, "due": "8:00am Tuesday, November 24"},
              {"number": 3, "due": "8:00am Tuesday, November 24", "extra_credit": True}]
    calls = [f"dueText({json.dumps(same)}, {json.dumps(same[1])})", f"dueText({json.dumps(same)}, null)",
             f"dueText({json.dumps(differ)}, {json.dumps(differ[0])})", f"dueText({json.dumps(differ)}, {json.dumps(differ[2])})",
             "dueText([], null)"]
    run = "\n".join(helpers) + "\n" + "\n".join(f"console.log(JSON.stringify({c}));" for c in calls)
    out = [json.loads(x) for x in subprocess.run([node, "-e", run], capture_output=True, text=True).stdout.splitlines()]
    assert out[0] == {"same": True, "top": "Everything is due 8:00am Tuesday, November 24."}
    assert out[1] == out[0]                                   # said even when every step is done
    assert out[2] == {"same": False, "top": "Part 0 is due 8:00am Thursday, November 12"}
    assert out[3] == {"same": False, "top": "Part 3 (extra credit) is due 8:00am Tuesday, November 24"}
    assert out[4] == {"same": False, "top": ""}


def test_every_step_opens_the_same_way_text_then_tasks_then_every_part_folded():
    js = (ROOT / "workbench/static/app.js").read_text()
    css = (ROOT / "workbench/static/style.css").read_text()
    for gone in ("If you're stuck", "Setup steps", '"label">Instructions<', "plainsteps", "details.stuck"):
        assert gone not in js and gone not in css, gone
    left = page_function(js, "leftCol")
    assert left.index("opening") < left.index('class="counts"') < left.index('class="doc folds"')
    assert "if (s.setup)" not in page_function(js, "recordCol")   # one record column for every step
    for setup in (False, True):                             # a set-up step and an ordinary one alike
        out = run_layout_js([f"leftCol({json.dumps({**STEP, 'setup': setup})})"])
        if out is None:
            return
        html_text = out[0]
        opening, rest = html_text.split('<div class="counts" id="dw-0b"></div>')
        assert "The claim you check:" in opening and "<blockquote>A short claim.</blockquote>" in opening
        assert "In this step you ask it." not in html_text     # the summary is under the title only
        assert "<details" not in opening and rest.startswith('<div class="doc folds">')
        got = folds(rest)
        assert [x[0] for x in got] == ["Words in this step", "Actions", "The six rules", "Interpreting output",
                                       "Write-up", "Completion", "Troubleshooting", "Hint", "Something new"]
        body = dict(got)
        assert "<li>Do this.</li>" in body["Actions"] and "<li>Ask the model.</li>" in body["The six rules"]
        assert "**Hint:** in code" in body["Interpreting output"]   # a label in a code block is only text
        assert "Read it twice. And slowly." in body["Hint"] and "Folds too." in body["Something new"]


def test_the_claim_box_shows_only_when_the_opening_does_not_quote_the_claim():
    with_quote = {**STEP, "claim": True}
    without = {**STEP, "claim": True, "body": "In this step you ask it.\n\n**Actions:**\n\n1. Do this."}
    out = run_layout_js([f"leftCol({json.dumps(with_quote)})", f"leftCol({json.dumps(without)})"],
                        setup='A = {sample_claim: "A short claim."};')
    if out is None:
        return
    assert 'class="claimbox"' not in out[0] and out[0].count("A short claim.") == 1
    assert '<div class="claimbox">A short claim.</div>' in out[1]


def test_a_set_up_steps_tasks_show_numbered_with_their_ticks():
    rec = {"checkpoints": [
        {"n": 1, "task": "Copy .env.example to .env.", "text": "", "done": True, "slots": [], "files": []},
        {"n": 2, "task": "Type your name after Name: at the top of WRITEUP.md.", "text": "", "done": True,
         "slots": [{"question": "Name", "answer": "Sam", "filled": True}], "files": []},
        {"n": 3, "task": "Start this step's Claude session.", "text": "", "done": False, "slots": [], "files": []},
        {"n": 4, "task": "Ask Claude to run the set-up check.", "text": "", "done": False, "slots": [], "files": []}]}
    out = run_layout_js([f"counts({json.dumps({'label': '0a', 'setup': True})}, {{manual: false, complete: false}}, {json.dumps(rec)})"])
    if out is None:
        return
    import re
    rows = re.findall(r'<div class="check ( ?ok)?"><span class="tick">(.)</span>\s*<div><span class="q">([^<]*)</span>', out[0])
    assert [(tick, text) for _, tick, text in rows] == [
        ("✓", "1. Copy .env.example to .env."), ("✓", "2. Type your name after Name: at the top of WRITEUP.md."),
        ("○", "3. Start this step's Claude session."), ("○", "4. Ask Claude to run the set-up check.")]
    assert out[0].startswith('<span class="label">Tasks</span>') and ">Sam<" in out[0]


def test_a_task_with_no_tick_and_the_sentence_above_the_questions_show_in_tasks():
    import re
    answers = "Type your answers to these questions in WRITEUP.md, in your editor. Claude does not write them."
    s = {"label": "0d", "setup": False, "answers_task": answers,
         "session_tasks": {"start": "First, start this step's Claude session.", "stop": "Last, type /exit."}}
    rec = {"checkpoints": [
        {"n": 1, "task": "Ask Claude to run the agent on the claim.", "text": "", "done": True, "tick": True,
         "slots": [], "files": ["runs/part0/agent-1.json"]},
        {"n": 2, "task": "In the results viewer, read the trace.", "text": "", "done": False, "tick": False,
         "slots": [], "files": []},
        {"n": 3, "task": "", "text": "Your answers", "done": False, "tick": True, "files": [], "slots": [
            {"question": "How did it get there?", "answer": "", "filled": False,
             "todo": "Not written yet. Type it in WRITEUP.md, under 0d."},
            {"question": "Which lookup?", "answer": "Entry 2.", "filled": True}]}]}
    setup = {"label": "0a", "setup": True, "answers_task": answers, "session_tasks": {}}
    setup_rec = {"checkpoints": [{"n": 1, "task": "Read it.", "text": "", "done": False, "tick": False,
                                  "slots": [], "files": []}]}
    out = run_layout_js([f"counts({json.dumps(s)}, {{manual: false, complete: false}}, {json.dumps(rec)}, true)",
                         f"counts({json.dumps({**s, 'answers_task': ''})}, {{manual: false, complete: false}}, {json.dumps(rec)}, true)",
                         f"counts({json.dumps(setup)}, {{manual: false, complete: false}}, {json.dumps(setup_rec)}, false)"])
    if out is None:
        return
    rows = re.findall(r'<div class="check ?(ok)?"><span class="tick">([^<]*)</span>\s*<div><span class="q">([^<]*)</span>', out[0])
    assert [(tick, text) for _, tick, text in rows] == [
        ("✓", "First, start this step's Claude session."), ("✓", "Ask Claude to run the agent on the claim."),
        ("", "In the results viewer, read the trace."),          # no tick, like the /exit task
        ("○", "How did it get there?"), ("✓", "Which lookup?"), ("", "Last, type /exit.")]
    note = f'<p class="answers-note">{answers}</p>'
    assert out[0].count(note) == 1                              # once, above the first question
    assert out[0].index("read the trace.") < out[0].index(note) < out[0].index("How did it get there?")
    assert ">Not written yet.<" in out[0] and "under 0d" not in out[0]
    assert "answers-note" not in out[1] and "Not written yet. Type it in WRITEUP.md, under 0d." in out[1]
    assert '<span class="tick"></span><div><span class="q">1. Read it.</span>' in out[2]


def test_one_sentence_near_the_top_says_what_happens_where(tmp_path):
    a = steps.load(ROOT / "steps.toml")
    readme = " ".join((ROOT / "README.md").read_text().split())
    how = readme.split("## How this homework works", 1)[1].split(" ## ", 1)[0]
    assert a.top_note and f"- {a.top_note}" in how              # the same sentence, as one bullet
    js = (ROOT / "workbench/static/app.js").read_text()
    assert 'paint(byId("how"), A.top_note ? inline(A.top_note) : "");' in js
    assert '<p class="lede how" id="how"></p>' in (ROOT / "workbench/static/index.html").read_text()
    h = homework(tmp_path)
    plain = server.App(h.student).assignment()
    assert plain["top_note"] == "" and all(s["answers_task"] == "" for s in plain["steps"])


def test_in_the_real_steps_every_labeled_part_folds_in_order_and_nothing_is_lost():
    import re
    a = steps.load(ROOT / "steps.toml")
    calls = []
    for st in a.steps:
        body = steps.body(st, a, ROOT)
        calls += [f"sections(withoutSummary({json.dumps(body)}, {json.dumps(st.summary)}))",
                  f"withoutSummary({json.dumps(body)}, {json.dumps(st.summary)})",
                  f"leftCol({json.dumps({'label': a.label(st), 'summary': st.summary, 'body': body, 'claim': st.claim, 'setup': st.setup})})"]
    out = run_layout_js(calls, setup=f"A = {{sample_claim: {json.dumps(a.sample_claim)}}};")
    if out is None:
        return
    flat = lambda t: " ".join(str(t).split())                 # noqa: E731
    for k, st in enumerate(a.steps):
        secs, shown, html_text = out[3 * k:3 * k + 3]
        body = steps.body(st, a, ROOT)
        want = re.findall(r"(?m)^\*\*([^*]+):\*\*", body)      # no label in these pages sits in a code block
        assert [x["label"] for x in secs if x["label"]] == want, st.id
        assert [x[0] for x in folds(html_text)] == want, st.id      # every labeled part folds, in order
        rebuilt = "\n\n".join((f"**{x['label']}:** " if x["label"] else "") + x["text"] for x in secs)
        assert flat(rebuilt) == flat(shown), st.id                 # nothing of the instructions is lost
        assert flat(st.summary) not in flat(re.sub(r"<[^>]+>", " ", html_text)) or not st.summary, st.id
        if st.setup:
            assert len([c for c in st.checkpoints]) == 4, st.id    # 0a's four tasks, shown by counts()


def run_page_js(calls):
    """Each JavaScript expression's value, from the page's own text helpers run in node; None
    without node."""
    node = node_or_none()
    if not node:
        return None
    lines = (ROOT / "workbench/static/app.js").read_text().splitlines()
    first = next(i for i, x in enumerate(lines) if x.startswith("const esc ="))
    last = next(i for i, x in enumerate(lines) if x.startswith("// Replace an element's HTML"))
    run = "\n".join(lines[first:last]) + "\n" + "\n".join(f"console.log(JSON.stringify({c}));" for c in calls)
    return [json.loads(x) for x in subprocess.run([node, "-e", run], capture_output=True, text=True).stdout.splitlines()]


def test_a_steps_summary_is_not_shown_a_second_time_in_its_instructions():
    js = (ROOT / "workbench/static/app.js").read_text()
    assert "const secs = sections(withoutSummary(s.body, s.summary));" in js
    body = "In this step you ask the\nmodel a question.\n\n**Actions:**\n\n1. Ask it."
    out = run_page_js([f"withoutSummary({json.dumps(body)}, {json.dumps('In this step you ask the model a question.')})",
                       f"withoutSummary({json.dumps(body)}, {json.dumps('In this step you ask the model one question.')})",
                       f"withoutSummary({json.dumps('In this step you ask it.')}, {json.dumps('In this step you ask it.')})",
                       f"withoutSummary({json.dumps(body)}, {json.dumps('')})"])
    if out is None:
        return
    assert out[0] == "**Actions:**\n\n1. Ask it."             # the same sentence, wrapped differently: dropped
    assert out[1] == body                                     # one word different: kept
    assert out[2] == ""                                       # nothing but the summary: nothing left
    assert out[3] == body                                     # no summary: nothing dropped


def test_no_real_step_shows_its_summary_twice():
    import re
    a = steps.load(ROOT / "steps.toml")
    calls = [f"withoutSummary({json.dumps(steps.body(s, a, ROOT))}, {json.dumps(s.summary)})" for s in a.steps]
    out = run_page_js(calls)
    if out is None:
        return
    flat = lambda t: " ".join(str(t).split())                 # noqa: E731
    for s, shown in zip(a.steps, out):
        firstpara = flat(re.split(r"\n\s*\n", shown.strip(), maxsplit=1)[0]) if shown.strip() else ""
        assert firstpara != flat(s.summary) and flat(s.summary) not in flat(shown), s.id
        assert shown.strip(), s.id                            # each step still has instructions to show


def test_an_open_part_stays_open_through_the_refresh():
    js = (ROOT / "workbench/static/app.js").read_text()
    update = js[js.index("function update() {"):js.index("\n}\n", js.index("function update() {"))]
    assert "leftCol(" not in update                         # the refresh never redraws the instructions
    assert "keep.has(d.dataset.key)" in js                  # and a rebuild reopens what was open


def test_the_learning_goals_come_from_readme_word_for_word():
    import re
    readme = (ROOT / "README.md").read_text()
    first, bullets = [p for p in readme.split("\n\n") if p.strip()][1:3]
    assert first.rstrip().endswith("You will:")
    want = [" ".join(x.split()) for x in re.split(r"(?m)^- ", bullets) if x.strip()]
    assert steps.goals(readme) == want and len(want) == 4
    assert want[0].startswith("Understand what makes a program an *agent*")
    assert steps.goals("# T\n\nOpening sentence.\n\n## The task\n\nMore.\n") == []
    assert steps.goals("# T\n\nOpening. You will:\n\nA paragraph, not a list.\n") == []
    assert steps.goals(None) == []
    js = (ROOT / "workbench/static/app.js").read_text()
    assert "`<p>You will:</p><ul>${A.goals.map((g) => `<li>${inline(g)}</li>`).join(\"\")}</ul>`" in js
    assert '<div class="lede goals" id="goals"></div>' in (ROOT / "workbench/static/index.html").read_text()


def test_the_page_serves_the_goals_and_none_without_them(tmp_path):
    h = homework(tmp_path, {"README.md": "# HW9\n\nA small homework. You will:\n\n- Learn *one* thing.\n- Learn\n  another.\n\nFor extra credit, more.\n",
                            "steps.toml": STEPS.replace('writeup = "WRITEUP.md"', 'writeup = "WRITEUP.md"\noverview = "README.md"')})
    a = server.App(h.student).assignment()
    assert a["goals"] == ["Learn *one* thing.", "Learn another."] and a["lede"] == "A small homework."
    (h.student / "README.md").write_text("# HW9\n\nA small homework.\n\n## The task\n")
    assert server.App(h.student).assignment()["goals"] == []


# -- saving the student's work -------------------------------------------------------------------

def finish_part0(repo):
    (repo / "WRITEUP.md").write_text(FILLED)
    (repo / "runs/part0").mkdir(parents=True, exist_ok=True)
    (repo / "runs/part0/no-tools-1.json").write_text("{}")


def test_a_finished_part_is_committed_with_its_conversations_and_pushed(tmp_path):
    h = homework(tmp_path)
    app = server.App(h.student)
    chained_session(h.student, app.hub.session_id("0b"))
    finish_part0(h.student)
    app.commit_finished_parts()
    assert subjects(h.student)[0] == "Part 0 done"
    shipped = git(h.student, "show", "--name-only", "--format=", "HEAD").split()
    assert {"WRITEUP.md", "TRANSCRIPT.md", "runs/part0/no-tools-1.json", "record/0b.json"} <= set(shipped)
    assert "Part 0 done" in subjects(h.fork, "main")                   # it reached GitHub's stand-in
    assert app.pushed is True and "push" not in app.notices
    text = (h.student / "TRANSCRIPT.md").read_text()
    assert "# 0b. Ask the model on its own" in text and "sk-ant-" not in text and "[key removed]" in text
    app.commit_finished_parts()
    assert subjects(h.student).count("Part 0 done") == 1                # once only


def test_a_part_commit_takes_everything_that_is_not_ignored(tmp_path):
    h = homework(tmp_path, {"instructions.md": "You check claims.\n", "agent.py": "print(1)\n",
                            ".gitignore": open(ROOT / ".gitignore").read()})
    app = server.App(h.student)
    (h.student / "instructions.md").write_text("You check claims. Read two pages.\n")
    (h.student / "agent.py").write_text("print(2)\n")
    for rel in ("data/my-claims.jsonl", "runs/part2/agent.jsonl", "runs/part1/after/agent.jsonl",
                "runs/part3/claude-labels.md", ".cache/abc.json", ".env", ".DS_Store",
                ".claude/settings.local.json", "__pycache__/x.pyc"):
        (h.student / rel).parent.mkdir(parents=True, exist_ok=True)
        (h.student / rel).write_text("x\n")
    finish_part0(h.student)
    app.commit_finished_parts()
    shipped = set(git(h.student, "show", "--name-only", "--format=", "HEAD").split())
    assert {"instructions.md", "agent.py", "data/my-claims.jsonl", "runs/part2/agent.jsonl",
            "runs/part1/after/agent.jsonl", "runs/part3/claude-labels.md", "WRITEUP.md"} <= shipped
    assert not shipped & {".cache/abc.json", ".env", ".DS_Store", ".claude/settings.local.json", "__pycache__/x.pyc"}


def test_a_20_megabyte_result_file_is_committed_and_pushed_while_the_page_answers(tmp_path):
    import os
    import time
    h = homework(tmp_path)
    app = server.App(h.student)
    finish_part0(h.student)
    (h.student / "runs/part2").mkdir(parents=True)
    (h.student / "runs/part2/agent.jsonl").write_bytes(os.urandom(20 * 1024 * 1024))   # incompressible
    srv, base = serving(app)
    try:
        worker = threading.Thread(target=app.commit_finished_parts)
        started = time.time()
        worker.start()
        slowest = 0.0
        while worker.is_alive():
            t = time.time()
            assert fetch(base + "/api/state")[0] == 200
            slowest = max(slowest, time.time() - t)
            time.sleep(0.05)
        worker.join()
        assert subjects(h.student)[0] == "Part 0 done" and subjects(h.fork, "main")[0] == "Part 0 done"
        assert "runs/part2/agent.jsonl" in git(h.student, "show", "--name-only", "--format=", "HEAD")
        assert slowest < 2.0, f"the page took {slowest:.1f}s to answer during a {time.time() - started:.1f}s commit"
    finally:
        srv.shutdown()
        srv.server_close()


def test_a_commit_made_during_a_push_is_pushed_after_it(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "SETTLE", 0)
    h = homework(tmp_path)
    app = server.App(h.student)
    real, entered, go, first = server.git, threading.Event(), threading.Event(), []

    def slow_first_push(repo, *args, **kw):
        if args[:1] == ("push",) and not first:          # the first push reads HEAD, then waits
            first.append(real(repo, "rev-parse", "HEAD").stdout.strip())
            entered.set()
            go.wait(10)
            return real(repo, "push", "-q", "origin", f"{first[0]}:refs/heads/main", **kw)
        return real(repo, *args, **kw)

    monkeypatch.setattr(server, "git", slow_first_push)
    monkeypatch.setattr(server.App, "push_soon", lambda self: None)   # pushes only when the test says
    finish_part0(h.student)
    app.commit_finished_parts()                             # commit A: "Part 0 done"
    pushing = threading.Thread(target=app.push)
    pushing.start()
    assert entered.wait(10)
    (h.student / "WRITEUP.md").write_text(FILLED.replace("it guessed", "it guessed, I think"))
    app.commit_changes()                                    # commit B, while A's push is running
    app.push()                                              # the call push_soon makes: busy, so later
    seen = [app.state()["push"]["ok"]]
    go.set()
    pushing.join(10)
    seen.append(app.state()["push"]["ok"])
    assert subjects(h.fork, "main")[0] == "Part 0 done"      # only A went with the first push
    assert app.push_due > 0                                 # B's push is scheduled, not forgotten
    monkeypatch.setattr(server.App, "push_soon", lambda self: self.push())
    for _ in range(100):                                    # the saving loop, until the retry fires
        app.tick()
        seen.append(app.state()["push"]["ok"])
        if subjects(h.fork, "main")[0] == "Part 0 updated":
            break
        time.sleep(0.2)
    assert subjects(h.fork, "main")[:2] == ["Part 0 updated", "Part 0 done"]
    assert seen[:2] == [None, None] and True not in seen[:-1] and seen[-1] is True
    assert app.push_due == 0.0


def test_a_push_that_fails_keeps_the_commit_and_says_how_to_push(tmp_path):
    h = homework(tmp_path)
    git(h.student, "remote", "set-url", "origin", str(tmp_path / "gone.git"))
    app = server.App(h.student)
    finish_part0(h.student)
    app.commit_finished_parts()
    assert subjects(h.student)[0] == "Part 0 done"
    assert app.pushed is False
    assert "committed on this laptop but not pushed" in app.notices["push"]["text"]
    assert "git push" in app.notices["push"]["text"]
    assert app.push_due > 0                                            # it tries again later


def test_a_change_to_a_committed_part_is_committed_as_an_update(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "SETTLE", 0)
    h = homework(tmp_path)
    app = server.App(h.student)
    finish_part0(h.student)
    app.commit_finished_parts()
    # An answer in Part 1, which isn't committed yet, is left for Part 1's own commit.
    (h.student / "WRITEUP.md").write_text(FILLED.replace("each turn?\n\n>", "each turn?\n\n> The messages."))
    app.commit_changes()
    assert subjects(h.student)[0] == "Part 0 done"
    # A change to Part 0's answers is committed and pushed.
    (h.student / "WRITEUP.md").write_text((h.student / "WRITEUP.md").read_text().replace("it guessed", "it guessed, I think"))
    app.commit_changes()
    assert subjects(h.student)[0] == "Part 0 updated"
    assert subjects(h.fork, "main")[0] == "Part 0 updated"
    app.commit_changes()
    assert subjects(h.student)[0] == "Part 0 updated" and subjects(h.student).count("Part 0 updated") == 1


def test_a_committed_parts_conversation_that_grew_is_saved_once_it_is_quiet(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "SETTLE", 0)
    h = homework(tmp_path)
    app = server.App(h.student)
    sid = app.hub.session_id("0b")
    chained_session(h.student, sid)
    finish_part0(h.student)
    app.commit_finished_parts()
    assert subjects(h.student)[0] == "Part 0 done"
    f = next(Path(transcript.projects()).glob(f"*/{sid}.jsonl"))
    with open(f, "a") as out:                               # the student and Claude go on talking
        out.write(json.dumps({"type": "user", "uuid": "late-1", "sessionId": sid, "cwd": str(h.student),
                              "timestamp": "2026-11-10T19:30:00.000Z",
                              "message": {"role": "user", "content": "One last question about the trace."}}) + "\n")
    app.commit_changes()
    assert subjects(h.student)[0] == "Part 0 done"         # still talking: not yet
    monkeypatch.setattr(server, "CONVO_SETTLE", 0)          # ...and now quiet for long enough
    app.commit_changes()
    assert subjects(h.student)[0] == "Part 0 updated"
    assert "One last question about the trace." in git(h.student, "show", "HEAD:TRANSCRIPT.md")
    app.commit_changes()
    assert subjects(h.student).count("Part 0 updated") == 1


def test_after_the_last_part_extra_credit_and_code_changes_are_saved(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "SETTLE", 0)
    h = homework(tmp_path, {"agent.py": "print(1)\n", "uv.lock": "version = 1\n"})
    app = server.App(h.student)
    finish_part0(h.student)
    (h.student / "WRITEUP.md").write_text(FILLED.replace("each turn?\n\n>", "each turn?\n\n> The messages."))
    app.commit_finished_parts()
    assert subjects(h.student)[:2] == ["Part 1 done", "Part 0 done"]
    (h.student / "uv.lock").write_text("version = 1\n# rewritten by a newer uv\n")
    app.commit_changes()
    assert subjects(h.student)[0] == "Part 1 done"          # uv.lock alone is no change
    (h.student / "WRITEUP.md").write_text((h.student / "WRITEUP.md").read_text() + "\n# Extra credit\n\nI tried two pages.\n")
    (h.student / "agent.py").write_text("print(2)\n")
    app.commit_changes()
    assert subjects(h.student)[0] == "Part 1 updated"
    shipped = git(h.student, "show", "--name-only", "--format=", "HEAD").split()
    assert "WRITEUP.md" in shipped and "agent.py" in shipped and "uv.lock" not in shipped
    (h.student / "notes.txt").write_text("ANTHROPIC_API_KEY=" + FAKE_KEY + "\n")
    app.commit_changes()                                    # left out, and not tried again and again
    first = subjects(h.student)
    app.commit_changes()
    assert subjects(h.student) == first and "key" in app.notices


COURSE_FILE = STEPS.replace('never_read = [".env"]',
                            'never_read = [".env", "reference_loop.py", "tests/test_loop_check.py", "secret.txt"]')


def test_a_tracked_never_read_file_is_committed_like_any_other(tmp_path):
    h = homework(tmp_path, {"steps.toml": COURSE_FILE, "reference_loop.py": "def run_agent():\n    pass\n"})
    app = server.App(h.student)
    (h.student / "reference_loop.py").write_bytes(b"def run_agent():\r\n    pass\r\n")   # line endings changed
    (h.student / "secret.txt").write_text("not a course file\n")                        # new, never_read
    finish_part0(h.student)
    app.commit_finished_parts()
    shipped = git(h.student, "show", "--name-only", "--format=", "HEAD").split()
    assert subjects(h.student)[0] == "Part 0 done"
    assert "reference_loop.py" in shipped and "secret.txt" not in shipped
    assert "reference_loop.py" not in app.notices["key"]["text"] and "secret.txt" in app.notices["key"]["text"]


def test_an_update_to_a_tracked_never_read_file_merges(tmp_path):
    h = homework(tmp_path, {"steps.toml": COURSE_FILE, "reference_loop.py": "def run_agent():\n    pass\n"})
    app = server.App(h.student, upstream=str(h.cls))
    app.updates.setup()
    finish_part0(h.student)
    app.commit_finished_parts()
    upstream_commit(h, "reference_loop.py", "def run_agent():\n    return 2\n", "A newer reference loop")
    app.updates.fetch()
    (h.student / "WRITEUP.md").write_text(FILLED.replace("it guessed", "it guessed, I think"))   # unsaved work
    assert app.update() == {"ok": True}                    # merged, not refused as a key
    assert (h.student / "reference_loop.py").read_text() == "def run_agent():\n    return 2\n"
    assert "key" not in app.notices and "update-failed" not in app.notices
    assert git(h.student, "status", "--porcelain") == ""
    (h.student / "WRITEUP.md").write_text(FILLED.replace("it guessed", "it guessed, I said"))
    server.SETTLE, settle = 0, server.SETTLE
    try:
        app.commit_changes()                                # and the next commit goes through
    finally:
        server.SETTLE = settle
    assert subjects(h.student)[0] == "Part 0 updated" and "key" not in app.notices


def test_the_guard_gives_each_kind_of_file_its_own_reason(tmp_path):
    h = homework(tmp_path, {"steps.toml": COURSE_FILE})
    guard = server.App(h.student).hub.dir / "guard.py"

    def reason(path):
        event = {"tool_name": "Read", "tool_input": {"file_path": str(h.student / path)}, "session_id": "s"}
        out = subprocess.run([sys.executable, str(guard), "pre"], input=json.dumps(event),
                             capture_output=True, text=True).stdout
        decision = json.loads(out)["hookSpecificOutput"]       # what Claude Code shows the step's Claude
        assert decision["permissionDecision"] == "deny"
        return decision["permissionDecisionReason"]

    assert reason(".env") == ("Never read, print or edit .env: it holds the student's own key. Ask them to "
                              "edit it themselves in their editor.")
    for f in ("reference_loop.py", "tests/test_loop_check.py"):
        assert reason(f) == (f"Never open {f}: it holds a finished version of what the student writes "
                             "themselves in this homework. Do not look for its contents anywhere else either.")


def test_the_guard_refuses_a_course_file_by_every_named_route(tmp_path):
    h = homework(tmp_path, {"steps.toml": COURSE_FILE})
    app = server.App(h.student)
    guard, here = app.hub.dir / "guard.py", str(h.student)

    def refused(tool, inp):
        event = {"tool_name": tool, "tool_input": inp, "session_id": "s"}
        out = subprocess.run([sys.executable, str(guard), "pre"], input=json.dumps(event),
                             capture_output=True, text=True).stdout
        return "deny" in out

    for path in ("reference_loop.py", "./reference_loop.py", here + "/reference_loop.py"):
        assert refused("Read", {"file_path": path}), path
        assert refused("Edit", {"file_path": path, "old_string": "a", "new_string": "b"}), path
        assert refused("Write", {"file_path": path, "content": "x"}), path
    for cmd in ("cat reference_loop.py", "head -40 ./reference_loop.py", "grep -n def reference_loop.py",
                "sed -n 1,20p " + here + "/reference_loop.py", "python3 reference_loop.py",
                "uv run python -c 'import reference_loop'", "cat reference_loop*",
                "python3 -c 'import inspect, reference_loop; print(inspect.getsource(reference_loop))'"):
        assert refused("Bash", {"command": cmd}), cmd
    for tool, inp in (("Bash", {"command": "cat my_loop.py"}), ("Bash", {"command": "uv run python check.py x"}),
                      ("Read", {"file_path": here + "/my_loop.py"}),
                      ("Bash", {"command": "test -f reference_loop.py && echo there"})):
        assert not refused(tool, inp), inp
    assert refused("Read", {"file_path": here + "/.env"}) and refused("Bash", {"command": "cat .env"})
    # An entry with a folder in it.
    for path in ("tests/test_loop_check.py", "./tests/test_loop_check.py", here + "/tests/test_loop_check.py"):
        assert refused("Read", {"file_path": path}), path
        assert refused("Edit", {"file_path": path, "old_string": "a", "new_string": "b"}), path
    for cmd in ("cat tests/test_loop_check.py", "head -30 ./tests/test_loop_check.py",
                "sed -n 1,40p tests/test_loop_check.py", "grep -n def tests/test_loop_check.py",
                'python3 -c "open(\'tests/test_loop_check.py\').read()"', "cd tests && cat test_loop_check.py",
                "uv run python -c 'import tests.test_loop_check'",
                "uv run pytest tests/test_loop_check.py"):        # names the file, so refused too
        assert refused("Bash", {"command": cmd}), cmd
    for cmd in ("uv run pytest -q", "uv run pytest tests/test_agent.py -q", "ls tests"):
        assert not refused("Bash", {"command": cmd}), cmd
    assert app.file("tests/test_loop_check.py")[1] == 403


def test_a_refused_read_of_a_never_read_file_is_never_a_link(tmp_path):
    h = homework(tmp_path, {"steps.toml": COURSE_FILE, "reference_loop.py": "x = 1\n"})
    app = server.App(h.student)
    save_session(h.student, app.hub.session_id("0b"), [
        ("user", "Start step 0b."),
        ("assistant", [{"type": "tool_use", "id": "t1", "name": "Read",
                        "input": {"file_path": str(h.student / "reference_loop.py")}}]),
        ("user", [{"type": "tool_result", "tool_use_id": "t1", "is_error": True, "content": "Refused."}]),
    ])
    s = app.hub.sessions["0b"]
    s.refresh()
    assert [e["category"] for e in s.events if e["kind"] == "tool"] == ["secret"]
    assert app.file("reference_loop.py")[1] == 403


def test_extra_credit_text_is_saved_once_the_required_parts_are_committed(tmp_path, monkeypatch):
    """Part 1 here is extra credit and not done; text added at the end of WRITEUP.md (under Part
    1's heading) is still committed, once Part 0, the only required part, is committed."""
    monkeypatch.setattr(server, "SETTLE", 0)
    extra = STEPS.replace('number = 1\ntitle = "The loop"', 'number = 1\ntitle = "The loop"\nextra_credit = true')
    h = homework(tmp_path, {"steps.toml": extra})
    app = server.App(h.student)
    finish_part0(h.student)
    app.commit_finished_parts()
    assert subjects(h.student)[0] == "Part 0 done"
    (h.student / "WRITEUP.md").write_text(FILLED + "\n## Extra credit\n\nI found a page that changed since the dataset.\n")
    app.commit_changes()
    assert subjects(h.student)[0] == "Part 0 updated"
    assert "I found a page that changed" in git(h.student, "show", "HEAD:WRITEUP.md")
    assert "Part 1 done" not in subjects(h.student)


def test_a_file_holding_a_key_is_never_committed(tmp_path):
    h = homework(tmp_path, {"notes.txt": "nothing yet\n"})
    app = server.App(h.student)
    (h.student / "notes.txt").write_text("ANTHROPIC_API_KEY=" + FAKE_KEY + "\n")
    finish_part0(h.student)
    app.commit_finished_parts()
    assert subjects(h.student)[0] == "Part 0 done"
    assert "notes.txt" not in git(h.student, "show", "--name-only", "--format=", "HEAD")
    assert "sk-ant" not in git(h.student, "show", "HEAD")
    assert "notes.txt" in app.notices["key"]["text"] and "Remove the key from it" in app.notices["key"]["text"]
    (h.student / "notes.txt").write_text("nothing here now\n")         # fixed: the next commit takes it
    (h.student / "WRITEUP.md").write_text(FILLED.replace("it guessed", "it guessed, I think"))
    server.SETTLE, settle = 0, server.SETTLE
    try:
        app.commit_changes()
    finally:
        server.SETTLE = settle
    assert "notes.txt" in git(h.student, "show", "--name-only", "--format=", "HEAD")
    assert "key" not in app.notices


def test_the_record_of_each_started_step_is_saved(tmp_path):
    h = homework(tmp_path)
    app = server.App(h.student)
    chained_session(h.student, app.hub.session_id("0b"))
    finish_part0(h.student)
    app.hub.record("0b", "checkpoint", n=1, text="You read the output with Claude")
    app.hub.save_records(h.student / "record")
    rec = json.loads((h.student / "record/0b.json").read_text())
    assert rec["step"] == "0b" and rec["complete"]
    assert [c["reached"] for c in rec["checkpoints"]] == [True, True, True]
    assert any(x["kind"] in ("expected", "said") for x in rec["record"])
    assert {a["written_by"] for a in rec["answers"]} == {"the student"}
    assert not (h.student / "record/1a.json").exists()                  # never started


def test_env_as_a_steps_file_is_only_ever_checked_for_existence(tmp_path, monkeypatch):
    h = homework(tmp_path, {"steps.toml": STEPS.replace('slots = ["Name"]', 'slots = ["Name"]\nfiles = [".env"]')})
    app = server.App(h.student)
    (h.student / "WRITEUP.md").write_text(FILLED)
    assert not {x["id"]: x for x in steps.status(app.a, h.student, set())}["0a"]["complete"]
    (h.student / ".env").write_text("ANTHROPIC_API_KEY=" + FAKE_KEY + "\n")
    opened = []
    real_open, real_read_text, real_read_bytes = open, Path.read_text, Path.read_bytes

    def watch(path):
        if Path(path).name == ".env":
            opened.append(str(path))

    monkeypatch.setattr("builtins.open", lambda f, *a, **k: (watch(f), real_open(f, *a, **k))[1])
    monkeypatch.setattr(Path, "read_text", lambda self, *a, **k: (watch(self), real_read_text(self, *a, **k))[1])
    monkeypatch.setattr(Path, "read_bytes", lambda self, *a, **k: (watch(self), real_read_bytes(self, *a, **k))[1])
    assert {x["id"]: x for x in steps.status(app.a, h.student, set())}["0a"]["complete"]
    for s in app.hub.sessions.values():
        s.snapshot()
        s.record(last=None)
    app.state()
    app.assignment()
    srv, base = serving(app)
    try:
        assert fetch(base + "/api/file?path=.env")[0] == 403
    finally:
        srv.shutdown()
        srv.server_close()
    finish_part0(h.student)
    app.commit_finished_parts()
    assert subjects(h.student)[0] == "Part 0 done"
    assert ".env" not in git(h.student, "show", "--name-only", "--format=", "HEAD").split()
    assert opened == []


def test_a_claim_with_quotes_and_an_apostrophe_reaches_every_place_intact(tmp_path):
    claims = ['The composer of "Persian Surgery Dervishes" was born on June 24, 1935.',
              "The film's director was born in O'Fallon, Illinois."]
    for n, claim in enumerate(claims):
        literal = "'''" + claim + "'''"          # a TOML literal string, as steps.toml carries it
        quoted = (STEPS.replace('title = "COMP 440 HW9: A small homework"',
                                'title = "COMP 440 HW9: A small homework"\nsample_claim = ' + literal)
                  .replace('title = "Ask the model on its own"', 'title = "Ask the model\'s own view"\nclaim = true'))
        (tmp_path / str(n)).mkdir()
        h = homework(tmp_path / str(n), {"steps.toml": quoted})
        app = server.App(h.student)
        assert app.a.sample_claim == claim
        assert json.loads(json.dumps(app.assignment()))["sample_claim"] == claim
        s = app.hub.sessions["0b"]
        (h.student / "WRITEUP.md").write_text(WRITEUP.replace("Name:", "Name: Sam"))
        snap = s.snapshot()
        assert claim in (app.hub.dir / "0b.md").read_text()
        import shlex
        words = shlex.split(snap["command"])
        assert words[words.index("-n") + 1] == "0b Ask the model's own view" and words[-1] == "Start step 0b."
    placeholder = STEPS.replace('title = "COMP 440 HW9: A small homework"',
                                'title = "COMP 440 HW9: A small homework"\nsample_claim = "[[SAMPLE_CLAIM]]"')
    (tmp_path / "p").mkdir()
    h = homework(tmp_path / "p", {"steps.toml": placeholder})
    assert server.App(h.student).assignment()["sample_claim"] == "[[SAMPLE_CLAIM]]"


def test_a_steps_prompt_carries_the_questions_not_the_answers(tmp_path):
    h = homework(tmp_path)
    app = server.App(h.student)
    secret_answer = "My own label is WRONG-PAGE, typed before Claude looks."
    (h.student / "WRITEUP.md").write_text(FILLED.replace("It said supported.", secret_answer))
    app.hub.sessions["0b"].prepare()
    prompt = (app.hub.dir / "0b.md").read_text()
    assert "What did it say?" in prompt and "How much would you trust it, and why?" in prompt
    assert secret_answer not in prompt and "Not much: it guessed" not in prompt and "Sam Student" not in prompt
    # The line about reading WRITEUP.md comes before the step's own brief, which may say "not yet".
    assert "Read it when you need them, unless this step's" in prompt
    assert prompt.index("Read it when you need them") < prompt.index("What you do in this step:")
    assert "Read it at the start" not in prompt
    assert "only where WRITEUP.md itself says to ask Claude" in prompt


# -- the conversations ---------------------------------------------------------------------------

def test_the_transcript_puts_each_steps_session_under_its_step(tmp_path):
    h = homework(tmp_path)
    app = server.App(h.student)
    sid = app.hub.session_id("0b")
    chained_session(h.student, sid)
    # A session started in this folder with plain `claude`, and one for another folder.
    save_session(h.student, "other-session", [("user", "hello"), ("assistant", [{"type": "text", "text": "Hi."}])])
    save_session(tmp_path / "elsewhere", "far-session", [("user", "not this one")], folder="-elsewhere")
    text = transcript.build(h.student, app.a, {"0b": sid})
    assert text.index("# 0b. Ask the model on its own") < text.index(f"<!-- transcript-session: {sid} | 2026-11-10T19:00:00.000Z -->")
    assert f"<!-- end-session: {sid} -->" in text
    assert "*2 user turns. Tool output shortened; reasoning omitted.*" in text
    assert "**User:**\nStart step 0b." in text and "**Claude:**\nWhat do you expect it to say?" in text
    assert "- 🔧 `Bash` — python3 .workbench/page.py 0b expected" in text
    assert "  ```\n  The page will set “supported” beside the result.\n  Claim: The director" in text
    assert "Verdict: supported" in text and "Saved to runs/part0/no-tools-1.json" in text
    assert "sk-ant-" not in text and "My key is [key removed]" in text
    assert "# Other Claude sessions in this folder" in text and "other-session" in text
    assert "far-session" not in text
    assert "# 0a." not in text                                         # no conversation, no heading


def test_the_transcript_keeps_a_conversation_it_can_no_longer_find(tmp_path):
    h = homework(tmp_path)
    app = server.App(h.student)
    sid = app.hub.session_id("0b")
    chained_session(h.student, sid)
    (h.student / transcript.NAME).write_text(transcript.build(h.student, app.a, {"0b": sid}))
    for f in Path(transcript.projects()).glob("*/*.jsonl"):
        f.unlink()                                                     # say, a new laptop
    new = transcript.build(h.student, app.a, {"0b": "a-new-session"})
    assert f"<!-- transcript-session: {sid} |" in new and "What do you expect it to say?" in new
    assert new.index("# 0b.") < new.index(sid)


def test_a_long_tool_result_is_shortened():
    out = transcript.result_text({"content": "\n".join(f"line {i}" for i in range(40))})
    assert out.startswith("line 0\n") and "line 11" in out and "line 12" not in out
    assert out.endswith("... (28 more lines)")


# -- updates from the class repository -----------------------------------------------------------

def test_an_update_is_listed_and_merged_with_uncommitted_answers(tmp_path):
    h = homework(tmp_path)
    app = server.App(h.student, upstream=str(h.cls))
    app.updates.setup()
    assert git(h.student, "remote", "get-url", "upstream").strip() == str(h.cls)
    assert git(h.student, "remote", "get-url", "origin").strip() == str(h.fork)   # never changed
    upstream_commit(h, "README.md", "# HW9\n\nA small homework, fixed.\n", "Fix a typo in the README")
    app.updates.fetch()
    assert app.updates.missing == ["Fix a typo in the README"]
    notice = next(x for x in app.current_notices() if x["kind"] == "update")
    assert notice["items"] == ["Fix a typo in the README"] and notice["button"] == "Update"
    (h.student / "WRITEUP.md").write_text(FILLED)                       # answers, not committed
    assert app.update() == {"ok": True}
    assert (h.student / "WRITEUP.md").read_text() == FILLED
    assert "fixed" in (h.student / "README.md").read_text()
    assert app.updates.missing == [] and not any(x["kind"] == "update" for x in app.current_notices())
    assert "Fix a typo in the README" in subjects(h.student)
    assert subjects(h.student)[0] == "Take the class repository's updates"


def test_an_update_to_a_file_with_uncommitted_edits_keeps_both(tmp_path):
    h = homework(tmp_path)
    app = server.App(h.student, upstream=str(h.cls))
    app.updates.setup()
    upstream_commit(h, "WRITEUP.md", WRITEUP.replace("What does Claude get sent on each turn?",
                                                     "What does the loop send Claude on each turn?"), "Reword 1a")
    app.updates.fetch()
    (h.student / "WRITEUP.md").write_text(WRITEUP.replace("Name:", "Name: Sam Student"))
    assert app.update() == {"ok": True}
    text = (h.student / "WRITEUP.md").read_text()
    assert "Name: Sam Student" in text and "What does the loop send Claude" in text
    assert "Save work before update" in subjects(h.student)


def test_a_true_conflict_changes_nothing_and_says_so(tmp_path):
    h = homework(tmp_path)
    app = server.App(h.student, upstream=str(h.cls))
    app.updates.setup()
    upstream_commit(h, "WRITEUP.md", WRITEUP.replace("What did it say?\n\n>", "What did it say?\n\n> (write here)"), "Prompt 0b")
    app.updates.fetch()
    mine = WRITEUP.replace("What did it say?\n\n>", "What did it say?\n\n> It said supported.")
    (h.student / "WRITEUP.md").write_text(mine)
    assert app.update() == {"ok": False}
    assert (h.student / "WRITEUP.md").read_text() == mine
    assert not (h.student / ".git/MERGE_HEAD").exists()
    assert git(h.student, "status", "--porcelain") == ""                 # nothing half-merged
    assert subjects(h.student)[0] == "Save work before update"
    text = app.notices["update-failed"]["text"]
    assert "could not be applied automatically" in text and "nothing in your files was changed" in text
    assert "#comp440-f26" in text
    assert not any(x["kind"] == "update" for x in app.current_notices())   # the button is gone
    upstream_commit(h, "README.md", "# HW9\n\nNewer.\n", "A newer fix")        # until there is more
    app.updates.fetch()
    notices = {x["kind"]: x for x in app.current_notices()}
    assert "update-failed" not in notices and "A newer fix" in notices["update"]["items"]


def test_an_untracked_file_in_the_way_changes_nothing(tmp_path):
    h = homework(tmp_path)
    app = server.App(h.student, upstream=str(h.cls))
    app.updates.setup()
    upstream_commit(h, "data/my-claims.jsonl", "{}\n", "Add a sample claims file")
    app.updates.fetch()
    (h.student / "data").mkdir()
    (h.student / "data/my-claims.jsonl").write_text('{"claim": "mine"}\n')
    assert app.update() == {"ok": False}
    assert (h.student / "data/my-claims.jsonl").read_text() == '{"claim": "mine"}\n'
    assert not (h.student / ".git/MERGE_HEAD").exists()


def test_a_lock_file_rewritten_by_uv_is_never_committed_nor_in_the_way(tmp_path):
    h = homework(tmp_path, {"uv.lock": "version = 1\n"})
    app = server.App(h.student, upstream=str(h.cls))
    app.updates.setup()
    (h.student / "uv.lock").write_text("version = 1\n# rewritten by a newer uv\n")
    finish_part0(h.student)
    app.commit_finished_parts()
    assert subjects(h.student)[0] == "Part 0 done"
    assert "uv.lock" not in git(h.student, "show", "--name-only", "--format=", "HEAD")
    upstream_commit(h, "uv.lock", "version = 2\n", "Update the lock file")
    app.updates.fetch()
    assert app.update() == {"ok": True}
    assert (h.student / "uv.lock").read_text() == "version = 2\n"


def test_after_an_update_the_steps_are_read_again_and_a_code_change_asks_for_a_restart(tmp_path):
    h = homework(tmp_path, {"workbench/note.py": "one\n"})
    app = server.App(h.student, upstream=str(h.cls))
    app.updates.setup()
    version = app.version
    upstream_commit(h, "steps.toml", STEPS.replace("A small homework", "A small homework, revised"), "Revise the steps")
    app.updates.fetch()
    assert app.update() == {"ok": True}
    assert app.a.title.endswith("revised") and app.version > version
    assert "restart" not in app.notices and "up to date" in app.notices["updated"]["text"]
    upstream_commit(h, "workbench/note.py", "two\n", "Fix the page")
    app.updates.fetch()
    assert app.update() == {"ok": True}
    assert "Restart it: press Ctrl-C" in app.notices["restart"]["text"]


def unpacked(where):
    """The homework as a ZIP unpacks it: the files, no .git of its own."""
    where.mkdir(parents=True)
    for name, text in {"steps.toml": STEPS, "WRITEUP.md": WRITEUP, "README.md": "# HW9\n"}.items():
        (where / name).write_text(text)
    return where


def test_a_folder_inside_another_repository_never_touches_it(tmp_path):
    h = homework(tmp_path)                                  # the class repository, for its address
    outer = tmp_path / "course"
    outer.mkdir()
    (outer / "notes.md").write_text("the instructor's notes\n")
    git(outer, "init", "-q", "-b", "main")
    git(outer, "add", ".")
    git(outer, "commit", "-q", "-m", "Course notes")
    hw = unpacked(outer / "copies" / "comp440-hw3")
    before = (git(outer, "remote", "-v"), git(outer, "log", "--format=%H %s"), git(outer, "status", "--porcelain"))
    app = server.App(hw, upstream=str(h.cls))
    upstream_commit(h, "README.md", "# HW9\n\nNewer.\n", "A fix")
    app.check_updates()                                     # setup, and a fetch
    app.updates.fetch()
    finish_part0(hw)
    app.tick()                                              # a round of the saving loop
    assert app.update() == {"ok": False, "why": server.NOT_A_CLONE}
    after = (git(outer, "remote", "-v"), git(outer, "log", "--format=%H %s"), git(outer, "status", "--porcelain"))
    assert after[:2] == before[:2]                          # no remote, no commit, no merge
    assert "A " not in after[2] and "M " not in after[2]    # nothing staged
    notices = {x["kind"]: x for x in app.current_notices()}
    assert notices["not-a-clone"]["text"] == server.NOT_A_CLONE and "update" not in notices
    assert app.state()["committed"] == []
    assert {x["id"]: x for x in app.state()["steps"]}["0b"]["complete"]    # the page still reads


def test_a_folder_outside_any_repository_says_so_and_carries_on(tmp_path):
    hw = unpacked(tmp_path / "comp440-hw3")
    app = server.App(hw, upstream="/nonexistent/class")
    app.check_updates()
    finish_part0(hw)
    app.tick()
    assert any(x["kind"] == "not-a-clone" for x in app.state()["notices"])
    assert app.hub.sessions["0b"].snapshot()["command"].startswith('claude -n "0b ')
    assert not (hw / ".git").exists() and not (hw / "TRANSCRIPT.md").exists()


def test_a_clone_made_later_is_noticed(tmp_path):
    hw = unpacked(tmp_path / "comp440-hw3")
    app = server.App(hw)
    assert not app.own_repo()
    git(hw, "init", "-q", "-b", "main")
    app.own_checked = 0                                     # five seconds later
    assert app.own_repo() and not any(x["kind"] == "not-a-clone" for x in app.current_notices())


def test_a_clone_of_the_class_repository_is_told_to_fork(tmp_path):
    h = homework(tmp_path)
    git(h.student, "remote", "set-url", "origin", str(h.cls) + "/")
    app = server.App(h.student, upstream=str(h.cls))
    app.updates.setup()
    assert app.updates.copy_of_class
    fork = next(x for x in app.current_notices() if x["kind"] == "fork")
    assert "not from your own fork" in fork["text"] and fork["code"].startswith("git remote set-url origin ")
    finish_part0(h.student)
    app.commit_finished_parts()
    assert app.pushed is None                                          # no push was tried
    assert "Part 0 done" not in subjects(h.cls, "main")


def test_an_upstream_remote_pointing_elsewhere_is_pointed_back(tmp_path):
    h = homework(tmp_path)
    git(h.student, "remote", "add", "upstream", str(tmp_path / "old.git"))
    app = server.App(h.student, upstream=str(h.cls))
    app.updates.setup()
    assert git(h.student, "remote", "get-url", "upstream").strip() == str(h.cls)


def test_the_upstream_address_can_be_set_from_the_environment(tmp_path, monkeypatch):
    h = homework(tmp_path)
    monkeypatch.setenv("WORKBENCH_UPSTREAM", str(h.cls))
    assert server.App(h.student).updates.url == str(h.cls)


def test_addresses_compare_however_they_are_written():
    from workbench.updates import same
    assert same("https://github.com/shilad/comp440-hw3", "git@github.com:shilad/comp440-hw3.git")
    assert same("https://github.com/Shilad/comp440-hw3.git/", "ssh://git@github.com/shilad/comp440-hw3")
    assert not same("https://github.com/student/comp440-hw3", "https://github.com/shilad/comp440-hw3")


# -- the server ----------------------------------------------------------------------------------

def test_a_taken_port_moves_the_page_to_the_next_one(tmp_path):
    h = homework(tmp_path)
    app = server.App(h.student)
    taken = socket.socket()
    taken.bind(("127.0.0.1", 0))
    taken.listen()
    port = taken.getsockname()[1]
    try:
        srv = server.serve(app, port, tries=5)
        assert srv.server_address[1] != port
        srv.server_close()
    finally:
        taken.close()


def serving(app):
    srv = server.serve(app, 0, tries=1)    # port 0: any free port
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


def fetch(url, data=None, headers=None):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    try:
        with opener.open(urllib.request.Request(url, data=data, headers=headers or {}), timeout=10) as r:
            return r.status, r.headers, r.read()
    except urllib.error.HTTPError as err:
        return err.code, err.headers, err.read()


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kw):
        return None


def test_the_page_and_every_steps_api_answer(tmp_path):
    h = homework(tmp_path)
    app = server.App(h.student)
    srv, base = serving(app)
    try:
        assert fetch(base + "/")[0] == 200 and fetch(base + "/static/app.js")[0] == 200
        a = json.loads(fetch(base + "/api/assignment")[2])
        assert [s["label"] for s in a["steps"]] == ["0a", "0b", "1a"]
        st = json.loads(fetch(base + "/api/state")[2])
        assert st["now"] == "0a" and st["version"] == a["version"]
        for s in a["steps"]:
            code, _, body = fetch(f"{base}/api/session/{s['id']}")
            assert code == 200 and "error" not in json.loads(body)
        assert json.loads(fetch(base + "/api/ping")[2])["repo"] == str(h.student)
        # A post from another web site is refused; the page skill's own post is not.
        assert fetch(base + "/api/step/0b/status", b'{"text": "x"}', {"Origin": "https://example.com"})[0] == 403
        assert fetch(base + "/api/step/0a/status", b'{"text": "Waiting"}', {"Content-Type": "application/json"})[0] == 200
    finally:
        srv.shutdown()
        srv.server_close()


def test_results_go_to_the_viewer_when_there_is_one(tmp_path, monkeypatch):
    for k in [k for k in sys.modules if k == "viewer" or k.startswith("viewer.")]:
        monkeypatch.delitem(sys.modules, k)          # the real viewer/ beside this test, if loaded
    monkeypatch.setattr(sys, "path", [p for p in sys.path if Path(p or ".").resolve() != ROOT])
    h = homework(tmp_path)
    app = server.App(h.student)
    srv, base = serving(app)
    try:
        assert b"not installed" in fetch(base + "/results/")[2]
        (h.student / "viewer").mkdir()
        (h.student / "viewer/__init__.py").write_text("")
        (h.student / "viewer/app.py").write_text(
            "def handle(method, path, query, repo):\n"
            "    return 200, 'text/plain', f'{method} {path} {query} {repo.name}'.encode()\n")
        for k in [k for k in sys.modules if k == "viewer" or k.startswith("viewer.")]:
            del sys.modules[k]
        code, headers, _ = fetch(base + "/results?x=1")
        assert code == 301 and headers["Location"] == "/results/?x=1"
        assert fetch(base + "/results/run?id=r1&id=r2")[2] == b"GET /run {'id': ['r1', 'r2']} student"
        assert fetch(base + "/results/")[2].startswith(b"GET / {}")
        # A viewer that also gives headers (respond) gets a real redirect.
        (h.student / "viewer/app.py").write_text(
            "def handle(method, path, query, repo):\n    return 200, 'text/plain', b'page'\n"
            "def respond(method, path, query, repo):\n"
            "    return 303, 'text/plain', b'', {'Location': '/results/check?id=1'}\n")
        for k in [k for k in sys.modules if k == "viewer" or k.startswith("viewer.")]:
            del sys.modules[k]
        code, headers, _ = fetch(base + "/results/open?path=runs/part0")
        assert code == 303 and headers["Location"] == "/results/check?id=1"
    finally:
        srv.shutdown()
        srv.server_close()
        for k in [k for k in sys.modules if k == "viewer" or k.startswith("viewer.")]:
            del sys.modules[k]
        sys.path[:] = [p for p in sys.path if p != str(h.student)]


def test_a_step_with_hide_results_offers_no_link_to_them(tmp_path):
    hidden = STEPS.replace('allow = ["Bash(uv run python check.py:*)"]',
                           'allow = ["Bash(uv run python check.py:*)"]\nhide_results = true')
    h = homework(tmp_path, {"steps.toml": hidden})
    app = server.App(h.student)
    finish_part0(h.student)
    snap = app.hub.sessions["0b"].snapshot()
    assert snap["results"] is None
    assert all(not f.startswith("runs/") for c in snap["record"]["checkpoints"] for f in c["files"])
    assert {x["id"]: x for x in steps.status(app.a, h.student, set())}["0b"]["complete"]   # still ticks
    (tmp_path / "plain").mkdir()
    shown = homework(tmp_path / "plain")                     # the same step without the key
    plain = server.App(shown.student)
    finish_part0(shown.student)
    assert plain.hub.sessions["0b"].snapshot()["results"] == "runs/part0/no-tools-1.json"
    assert (ROOT / "workbench/static/index.html").read_text().count('href="/results/"') == 1   # the header's


def test_a_step_with_results_links_to_the_newest(tmp_path):
    steps_ = STEPS.replace('slots = ["Name"]', 'slots = ["Name"]\nfiles = [".env"]').replace(
        'slots = ["1a.*"]', 'slots = ["1a.*"]\nfiles = ["data/my-claims.jsonl"]')
    h = homework(tmp_path, {"steps.toml": steps_})
    app = server.App(h.student)
    finish_part0(h.student)
    (h.student / "runs/part0/no-tools-2.json").write_text("{}")
    assert app.hub.sessions["0b"].snapshot()["results"] in ("runs/part0/no-tools-1.json", "runs/part0/no-tools-2.json")
    (h.student / ".env").write_text("not read\n")
    (h.student / "data").mkdir()
    (h.student / "data/my-claims.jsonl").write_text("{}\n")
    assert app.hub.sessions["0a"].snapshot()["results"] is None       # never .env
    assert app.hub.sessions["1a"].snapshot()["results"] is None       # only files under runs/
    assert all(c["files"] == [] for c in app.hub.sessions["0a"].record()["checkpoints"])


# -- the fallback CLAUDE.md ------------------------------------------------------------------

def test_claude_md_is_in_step_with_the_steps_file():
    a = steps.load(ROOT / "steps.toml")
    assert (ROOT / "CLAUDE.md").read_text() == claude_md.text(a), \
        "CLAUDE.md is out of date: run `uv run python -m workbench.claude_md`"
    assert a.tutor.strip() in (ROOT / "CLAUDE.md").read_text()


def test_every_step_says_how_to_start_it_with_claude_either_way():
    """The instructor, Nov 11: the tasks say how to start each step with Claude, and "i always have
    the option of continuing an existing claude session ... or starting a new one". There is no
    /exit task: the new-session box says to type /exit first if another session is open there."""
    a = steps.load(ROOT / "steps.toml")
    for s in a.steps:
        ask = a.session_tasks(s)
        assert ask["stop"] == "", s.id
        own = [c.task for c in steps.checkpoints(s) if "start this step's claude session" in c.task.lower()]
        if own:   # the step's own task says when to start (0a: after .env and the name)
            assert ask["start"] == "", s.id
        else:
            assert ask["start"] == ("First, start this step with Claude: paste the prompt on this page into the "
                                    "Claude session you have open, or paste the command into a terminal in your "
                                    "homework folder to start a new session."), s.id
    assert [s.id for s in a.steps if any("start this step's claude session" in c.task.lower()
                                         for c in steps.checkpoints(s))] == ["0a"]
    js = (ROOT / "workbench/static/app.js").read_text()
    assert "If another Claude session is open in that terminal, type /exit first." in js


def test_the_page_receives_the_two_session_tasks_and_ticks_only_the_first(tmp_path):
    h = homework(tmp_path, {"steps.toml": 'start_task = "Start Claude."\nstop_task = "Type /exit."\n' + STEPS})
    sent = [s["session_tasks"] for s in server.App(h.student).assignment()["steps"]]
    assert sent and all(x == {"start": "Start Claude.", "stop": "Type /exit."} for x in sent)
    js = (ROOT / "workbench/static/app.js").read_text()
    assert "if (ask.start) rows.unshift(row(started, ask.start" in js      # ticked once the session has started
    assert "if (ask.stop) rows.push(noTick(" in js                         # the page cannot see /exit
