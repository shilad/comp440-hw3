"""Offline tests of the homework page (workbench/): no network, no Claude, no GitHub.

Each test builds what it needs in a temporary folder: a small steps file, a WRITEUP.md in the
"## 0b. Title" heading style, git repositories that stand in for the class repository and the
student's fork, and saved Claude Code conversations under a temporary CLAUDE_CONFIG_DIR.
"""

import json
import socket
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
  "You said what you expect before it ran",
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


def save_session(repo, session_id, lines, folder="-tmp-student"):
    """A conversation as Claude Code saves it, under CLAUDE_CONFIG_DIR/projects/."""
    d = Path(transcript.projects()) / folder
    d.mkdir(parents=True, exist_ok=True)
    out = []
    for n, (kind, content) in enumerate(lines):
        out.append(json.dumps({"type": kind, "uuid": f"{session_id}-{n}", "sessionId": session_id,
                               "cwd": str(repo), "timestamp": f"2026-11-10T19:{n:02d}:00.000Z",
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


def test_each_command_carries_the_model_and_the_line_about_it(tmp_path):
    h = homework(tmp_path)
    snap = server.App(h.student).hub.sessions["0a"].snapshot()
    assert snap["model_flags"] == "--model claude-opus-5-5 --effort medium"
    assert "--model claude-opus-5-5 --effort medium" in snap["command"]
    js = (ROOT / "workbench/static/app.js").read_text()
    assert "If Claude says the model is not available, delete" in js


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
    two = STEPS.replace('"You said what you expect before it ran",', '"You said what you expect before it ran", "You asked it to run",')
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
    assert marked == {None: ["You said what you expect before it ran"], "Run it.": ["You asked it to run"]}


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


def test_a_file_holding_a_key_is_never_committed(tmp_path):
    h = homework(tmp_path, {"notes.txt": "nothing yet\n"})
    app = server.App(h.student)
    (h.student / "notes.txt").write_text("ANTHROPIC_API_KEY=" + FAKE_KEY + "\n")
    finish_part0(h.student)
    app.commit_finished_parts()
    assert subjects(h.student)[0] == "Part 0 done"
    assert "notes.txt" not in git(h.student, "show", "--name-only", "--format=", "HEAD")
    assert "sk-ant" not in git(h.student, "show", "HEAD")
    assert "notes.txt" in app.notices["key"]["text"]


def test_the_record_of_each_started_step_is_saved(tmp_path):
    h = homework(tmp_path)
    app = server.App(h.student)
    chained_session(h.student, app.hub.session_id("0b"))
    finish_part0(h.student)
    app.hub.record("0b", "checkpoint", n=1, text="You said what you expect before it ran")
    app.hub.save_records(h.student / "record")
    rec = json.loads((h.student / "record/0b.json").read_text())
    assert rec["step"] == "0b" and rec["complete"]
    assert [c["reached"] for c in rec["checkpoints"]] == [True, True, True]
    assert any(x["kind"] in ("expected", "said") for x in rec["record"])
    assert {a["written_by"] for a in rec["answers"]} == {"the student"}
    assert not (h.student / "record/1a.json").exists()                  # never started


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


def test_after_an_update_the_steps_are_read_again_and_a_code_change_asks_for_a_restart(tmp_path):
    h = homework(tmp_path, {"workbench/note.txt": "one\n"})
    app = server.App(h.student, upstream=str(h.cls))
    app.updates.setup()
    version = app.version
    upstream_commit(h, "steps.toml", STEPS.replace("A small homework", "A small homework, revised"), "Revise the steps")
    app.updates.fetch()
    assert app.update() == {"ok": True}
    assert app.a.title.endswith("revised") and app.version > version
    assert "restart" not in app.notices and "up to date" in app.notices["updated"]["text"]
    upstream_commit(h, "workbench/note.txt", "two\n", "Fix the page")
    app.updates.fetch()
    assert app.update() == {"ok": True}
    assert "Restart it: press Ctrl-C" in app.notices["restart"]["text"]


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


def test_results_go_to_the_viewer_when_there_is_one(tmp_path):
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
    finally:
        srv.shutdown()
        srv.server_close()
        for k in [k for k in sys.modules if k == "viewer" or k.startswith("viewer.")]:
            del sys.modules[k]
        sys.path[:] = [p for p in sys.path if p != str(h.student)]


def test_a_step_with_results_links_to_the_newest(tmp_path):
    h = homework(tmp_path)
    app = server.App(h.student)
    finish_part0(h.student)
    (h.student / "runs/part0/no-tools-2.json").write_text("{}")
    assert app.hub.sessions["0b"].snapshot()["results"] in ("runs/part0/no-tools-1.json", "runs/part0/no-tools-2.json")
    assert app.hub.sessions["0a"].snapshot()["results"] is None


# -- the fallback CLAUDE.md ------------------------------------------------------------------

def test_claude_md_is_in_step_with_the_steps_file():
    a = steps.load(ROOT / "steps.toml")
    assert (ROOT / "CLAUDE.md").read_text() == claude_md.text(a), \
        "CLAUDE.md is out of date: run `uv run python -m workbench.claude_md`"
    assert a.tutor.strip() in (ROOT / "CLAUDE.md").read_text()
