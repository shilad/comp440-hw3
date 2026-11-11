"""Checks on steps.toml, the homework page's list of HW3's steps.

Offline: no network, no key. Run with `uv run pytest -q`.

The step list is fixed: the fifteen steps from 0a to 3c, each with the sections, answers, files and
commands below, and Part 3 extra credit. These tests catch a step that drifts from that list, a
heading that the pages or WRITEUP.md do not have, a command a step's Claude session is told to run
but may not run without asking, a word students should not see, a rule that asks for a prediction,
and a placeholder that was never filled in.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from workbench import steps as stepmod  # noqa: E402
STEPS = REPO / "steps.toml"

PARTS = {
    0: "Set up and find your claims",
    1: "How the agent works",
    2: "The agent against the baselines",
    3: "Why the agent fails, and one change",
}
DUE = "8:00am Tuesday, November 24"

CHECK = ["Bash(uv run python check.py:*)"]
EVALUATE = ["Bash(uv run python evaluate.py:*)"]
LOOKUP = ["Bash(uv run python lookup.py:*)"]
FINDER = ["Bash(uv run python -m finder:*)"]
LOOP_CHECK = ["Bash(uv run python check_loop.py)", "Bash(uv run python check_loop.py --use-reference)",
              "Bash(uv run pytest:*)"]

# id: (part, section heading without "## ", files, allow, minutes)
EXPECTED = {
    "0a": (0, "0a. Get your copy running", [".env", "runs/part0/setup-check.txt"],
           ["Bash(uv sync)", "Bash(uv --version)", "Bash(uv run python check_setup.py)", "Bash(uv run pytest:*)"], 20),
    "0b": (0, "0b. Pick your topics and find your claims", ["data/my-topic.json"], FINDER, 40),
    "0c": (0, "0c. Ask the model to assess a claim without tools", ["runs/part0/no-tools-*.json"], CHECK, 10),
    "0d": (0, "0d. Give it one search", ["runs/part0/one-search-*.json"], CHECK, 15),
    "0e": (0, "0e. Run the agent and read its trace", ["runs/part0/agent-*.json"], CHECK, 15),
    "1a": (1, "1a. Write the loop", ["runs/part1/loop-check.txt"], LOOP_CHECK, 70),
    "1b": (1, "1b. Be the agent", ["runs/part1/lookups.jsonl"], LOOKUP, 25),
    "1c": (1, "1c. Watch the agent work", ["runs/part1/before/report.txt"], EVALUATE + CHECK, 25),
    "1d": (1, "1d. Write the agent's instructions", ["runs/part1/after/report.txt"], EVALUATE + CHECK, 45),
    "1e": (1, "1e. Start the full run, and predict", ["runs/part2/no-tools.jsonl"], EVALUATE, 20),
    "2a": (2, "2a. Compare accuracy", ["runs/part2/report.txt"], EVALUATE, 25),
    "2b": (2, "2b. Check the evidence yourself", [], LOOKUP, 35),
    "3a": (3, "3a. Sort the failures", [], [], 32),
    "3b": (3, "3b. Make one change", ["runs/part3/after/report.txt"],
           EVALUATE + CHECK + ["Edit(instructions.md)"], 18),
    "3c": (3, "3c. Write it up", [], [], 20),
}
# Minutes per part (the instructor's "split the difference", morning of Nov 11). Parts 0 to 2,
# the required work, make about 5 hours and 45 minutes. 0b is 40: halfway between his 25 and the
# 40 to 75 that a simulated student needed with the Select all shown button.
PART_MINUTES = {0: 100, 1: 185, 2: 60, 3: 70}

# Each step's summary, word for word from the instructor's outline (Nov 11).
SUMMARIES = {
    "0a": "In this step you get the homework running on your laptop, so the later steps can reach "
          "Wikipedia and the Claude API.",
    "0b": "In this step you pick a few topics you are interested in, and select 112 of the dataset's "
          "claims about them in the claim finder. You will use 12 claims for development and 100 for "
          "evaluation.",
    "0c": "In this step you find out how well the model checks a single claim about Persian Surgery "
          "Dervishes from memory alone, with no lookups. This is the no-tools baseline, the simplest of "
          "the three versions (no tools, one search, the agent).",
    "0d": "In this step you find out whether including information captured from one Wikipedia search "
          "improves your claim assessor.",
    "0e": "In this step you find out how the agent gets from the claim to a verdict when it chooses its "
          "own lookups.",
    "1a": "In this step you write the agent loop yourself. The loop asks the model for lookups, runs the "
          "lookups it chooses, sends back what they return, and stops.",
    "1b": "In this step you check one claim yourself, using only the agent's four tools.",
    "1c": "In this step you find out whether the agent matches the dataset's label on your 12 "
          "development claims.",
    "1d": "In this step you write the agent's instructions, and see how its traces change.",
    "1e": "In this step you start the run on your 100 evaluation claims.",
    "2a": "In this step you find out how often each of the three versions matched the dataset's label "
          "on your 100 evaluation claims. You compare those numbers with your predictions from 1e.",
    "2b": "In this step you find out whether the agent's quoted evidence really supports its verdicts.",
    "3a": "In this step you find out why the agent fails on your evaluation claims.",
    "3b": "In this step you make one change aimed at your most common failure. You find out whether it "
          "fixes that failure on your evaluation claims.",
    "3c": "In this step you say what you learned, in your own words.",
}

# Each step's tasks, in order, word for word from the outline: every checkpoint that has a task
# (the set-up step's name line has one too; the other answer checkpoints show their questions).
TASKS = {
    "0a": ["In a terminal tab of your own, in the homework's folder, copy .env.example to .env and fill "
           "in .env in your editor (your API key and your Macalester email) and save it.",
           "Type your name after Name: at the top of WRITEUP.md, and save the file.",
           "Start this step's Claude session with the command on this page.",
           "Ask Claude to run the set-up check, until it says everything is ready."],
    "0b": ["Select 112 claims in the [claim finder](/claims/) and save them."],
    "0c": ["Ask Claude to run the no-tools baseline on the claim. Its answer is saved in runs/part0/."],
    "0d": ["Ask Claude to run the one-search baseline on the claim. Its answer is saved in runs/part0/."],
    "0e": ["Ask Claude to run the agent on the claim. Its run is saved in runs/part0/.",
           "Read the trace, one entry at a time."],
    "1a": ["Read agent.py: the four tools, the evidence check and finish().",
           "Write your loop in my_loop.py until it passes every rule of the check, or choose to keep the "
           "reference loop. (Remember, Claude can help you!)"],
    "1b": ["By hand, make your first lookup. It is saved in runs/part1/lookups.jsonl.",
           "Decide on a verdict on the claim. If you've used all 12 lookups without answering it, your "
           "verdict is *doesn't say*."],
    "1c": ["Ask Claude to run the agent on your 12 development claims.",
           "Read three traces closely in the results viewer. Pick one claim each that needs 2, 3 and 4 "
           "Wikipedia articles, where your development claims have one."],
    "1d": ["Write your own instructions in instructions.md. They must say how to break a claim into "
           "pieces, when to use wikidata, when to stop, and when to answer \"doesn't say\".",
           "Ask Claude to run the agent on your 12 development claims again.",
           "Compare the two runs in the results viewer."],
    "1e": ["Start the full run yourself, in your own terminal tab."],
    "2a": ["Check that the full run has finished.", "Open the run in the results viewer."],
    "2b": ["Check the quoted evidence for the first five claims where the agent answered \"supported\" "
           "or \"refuted\"."],
    "3a": ["Label each of the eight failures in your table, with the entry of the trace that shows it, "
           "and say whether the dataset's label is right.",
           "Ask Claude to label the same claims. It gives its labels without seeing yours.",
           "Put Claude's labels in the last column of your table."],
    "3b": ["Make one change.",
           "Start the agent's run on your evaluation claims yourself, in your own terminal tab, and let "
           "it finish.",
           "Compare the two runs in the results viewer."],
    "3c": [],
}

RUN_NOTES = {
    "1e": "About 10 minutes and about 28 cents on your key. Leave that tab open and your laptop awake "
          "until it ends with two tables. Fill in your predictions while it runs, and don't look at its "
          "results before they are saved.",
    "3b": "About 6 minutes and about 21 cents on your key. Start it only after you have made your "
          "change. Leave that tab open, your laptop awake and your change alone until it ends with two "
          "tables.",
}

# The homework's learning goals (contract, Nov 11): the same five, word for word, in README.md,
# WRITEUP.md and the tutor text.
GOALS = [
    "Understand what makes a program an *agent*. You will study a language model that picks the next "
    "Wikipedia search query, reads the page that comes back, and decides when to stop.",
    "Gain hands-on experience with the loop around the model by writing it yourself: its tools, its "
    "instructions, its limit of 12 lookups, and the check that every sentence it quotes really appears "
    "in what it read.",
    "Build a small dataset of claims about topics you are interested in, and see how a retrieval system "
    "finds them by keyword and by meaning.",
    "Compare the agent with two simpler methods on your claims, and measure how effective each one is.",
    "Check the agent's evidence yourself, and decide whether accuracy alone is a fair measure of it.",
]

SAMPLE_CLAIM = 'The composer of "Persian Surgery Dervishes" was born on June 24, 1935.'
PART0_COMMANDS = {
    method: f"uv run python check.py --method {method} --out runs/part0 '{SAMPLE_CLAIM}'"
    for method in ("no-tools", "one-search", "agent")
}
# 1b's one claim (since Nov 11; the short first claim about Mel Duncan is gone).
CLAIM_1B = ("Vic & Anthony's Steakhouse is located at the American casino that was combined with the "
            "California Club. The casino is owned by Landry's, Inc.")

# grep -n: the tutor finds one claim's line in a run's agent.jsonl with it (the Grep tool is not
# in every Claude Code version).
GLOBAL_ALLOW = ["Bash(git status:*)", "Bash(git diff:*)",
                "Bash(ls:*)", "Bash(grep -n:*)", "Edit(WRITEUP.md)"]

# Words students must not see on the homework page (the step list's agreed vocabulary).
RULED_OUT = ["guardrail", "guardrails", "hop", "hops", "pipeline", "scaffold", "harness",
             "workbench", "step budget", "drive", "drives", "driving", "sample", "samples",
             "not enough info"]

# The first word of anything in a brief that is a shell command.
COMMAND_WORDS = {"uv", "python", "python3", "test", "git", "ls", "cat", "wc", "rm", "mv", "cp",
                 "grep", "head", "tail", "echo", "curl", "claude", "pytest"}


@pytest.fixture(scope="module")
def a() -> stepmod.Assignment:
    return stepmod.load(STEPS)


def raw() -> dict:
    """steps.toml as data, read from the file itself, so a check holds whatever version of the page
    reads it."""
    import tomllib
    return tomllib.loads(STEPS.read_text(encoding="utf-8"))


def student_text(a: stepmod.Assignment) -> list[tuple[str, str]]:
    """Every string from steps.toml that the homework page shows a student, with where it is."""
    out = [(f"part {n} title", p.get("title", "")) for n, p in a.parts.items()]
    for s in a.steps:
        out += [(f"{s.id} title", s.title), (f"{s.id} summary", s.summary)]
        out += [(f"{s.id} checkpoint {i}", c.text) for i, c in enumerate(stepmod.checkpoints(s), 1)]
        out += [(f"{s.id} task {i}", c.task) for i, c in enumerate(stepmod.checkpoints(s), 1) if c.task]
    return out


def commands(brief: str) -> list[str]:
    """The shell commands a brief gives: `inline code` and indented lines, whose first word is a
    command and which have at least two words (a bare `uv` is a mention, not a command)."""
    found = re.findall(r"`([^`\n]+)`", brief)
    found += [line.strip() for line in brief.splitlines() if line.startswith("    ") and line.strip()]
    return [c for c in found if len(c.split()) >= 2 and c.split()[0] in COMMAND_WORDS]


def allowed(command: str, rules: list[str]) -> bool:
    """Whether Claude Code would run `command` without asking, under these Bash(...) rules."""
    for rule in rules:
        m = re.fullmatch(r"Bash\((.+?)(:\*)?\)", rule)
        if not m:
            continue
        prefix, wild = m.group(1), m.group(2)
        if command == prefix or (wild and command.startswith(prefix + " ")):
            return True
    return False


def flat(text: str) -> str:
    """Text with its line breaks and runs of spaces as single spaces, for word-for-word checks."""
    return " ".join(text.split())


# ---- the file loads, and holds the agreed step list -----------------------------------------

def test_loads_the_way_the_page_does(a):
    assert a.title and a.tutor.strip() and a.writeup == "WRITEUP.md"
    assert a.model == "claude-opus-5-5" and a.effort == "medium"
    assert a.push is True and a.commit_parts is True
    assert a.never_read == [".env", "reference_loop.py", "tests/test_loop_check.py"]
    assert a.allow == GLOBAL_ALLOW


def test_top_level_keys():
    data = raw()
    assert data.get("upstream") == "https://github.com/shilad/comp440-hw3"
    assert "before_commit" not in data, "the page no longer reads before_commit"
    assert "demo" not in data


def test_parts(a):
    assert {n: p["title"] for n, p in a.parts.items()} == PARTS
    assert all(p.get("due") == DUE for p in a.parts.values())


def test_only_part_3_is_extra_credit(a):
    assert {n: p.get("extra_credit", False) for n, p in a.parts.items()} == {0: False, 1: False, 2: False, 3: True}


def test_fifteen_steps_in_order(a):
    assert [s.id for s in a.steps] == list(EXPECTED)
    # The page names a step by its part and its letter in the part; that must be its id.
    assert [a.label(s) for s in a.steps] == [s.id for s in a.steps]


def test_minutes_per_part(a):
    per = {n: sum(s.minutes for s in a.steps if s.part == n) for n in PARTS}
    assert per == PART_MINUTES
    assert sum(per[n] for n in (0, 1, 2)) == 345, "the required work is about 5 hours and 45 minutes"


def test_the_old_cost_step_and_the_id_2c_are_gone():
    text = STEPS.read_text(encoding="utf-8")
    assert "Compare cost" not in text
    assert not re.search(r"\b2c\b", text), "the old 2c is now 2b"


@pytest.mark.parametrize("step_id", list(EXPECTED))
def test_step_mechanics(a, step_id):
    part, section, files, allow, minutes = EXPECTED[step_id]
    s = a.step(step_id)
    assert s.part == part
    assert s.page == f"instructions/part{part}.md"
    assert s.section == section
    assert s.title == section.split(". ", 1)[1], "the title is the heading without its label"
    assert s.files == files
    assert s.allow == allow
    assert s.minutes == minutes
    assert s.slots == (["Name"] if step_id == "0a" else [f"{step_id}.*"])
    assert s.setup == (step_id == "0a")
    assert s.claim == (step_id in ("0c", "0d", "0e"))
    assert s.summary and s.brief.strip() and s.checkpoints


def test_one_summary_per_step_and_no_goal():
    """Each step has one summary, the outline's text, shown when the step is closed and when it is
    open. The page no longer has a second sentence, so no step has a goal."""
    steps = {s["id"]: s for s in raw()["step"]}
    assert not [i for i, s in steps.items() if "goal" in s]
    assert {i: s["summary"] for i, s in steps.items()} == SUMMARIES


def test_the_tasks_are_the_outlines(a):
    tasks = {s.id: [c.task for c in stepmod.checkpoints(s) if c.task] for s in a.steps}
    assert tasks == TASKS


def test_run_notes_are_the_outlines():
    steps = {s["id"]: s for s in raw()["step"]}
    assert {i: s["run_yourself"]["note"] for i, s in steps.items() if "run_yourself" in s} == RUN_NOTES


# ---- checkpoints -----------------------------------------------------------------------------

@pytest.mark.parametrize("step_id", list(EXPECTED))
def test_checkpoints_cover_the_step(a, step_id):
    """Every answer the step needs is named by a checkpoint (or the page adds a vague one of its
    own), and a checkpoint ticks only on the step's own files and answers."""
    s = a.step(step_id)
    cps = stepmod.checkpoints(s)
    assert sorted({x for c in cps for x in c.slots}) == sorted(s.slots)
    for c in cps:
        assert set(c.files) <= set(s.files), f"{step_id}: '{c.text}' ticks on a file the step doesn't need"


@pytest.mark.parametrize("step_id", list(EXPECTED))
def test_briefs_tick_only_checkpoints_claude_can_tick(a, step_id):
    """The page refuses a tick on a checkpoint that ticks itself, so a brief must not ask for one."""
    s = a.step(step_id)
    cps = stepmod.checkpoints(s)
    named = []
    for m in re.finditer(r"\b[Tt]ick\s+checkpoints?\s+(\d+(?:(?:,\s*|\s+and\s+)\d+)*)", s.brief):
        named += [int(n) for n in re.findall(r"\d+", m.group(1))]
    for n in named:
        assert 1 <= n <= len(cps), f"{step_id}: the brief ticks checkpoint {n}; there are {len(cps)}"
        c = cps[n - 1]
        assert not (c.files or c.slots), f"{step_id}: checkpoint {n} ('{c.text}') ticks itself"
    manual = [i for i, c in enumerate(cps, 1) if not (c.files or c.slots)]
    missing = [n for n in manual if n not in named]
    assert not missing, f"{step_id}: the brief never says when to tick checkpoint(s) {missing}"


# ---- the briefs ------------------------------------------------------------------------------

# Commands a brief names for the student to run in their own terminal, never Claude. No allow list
# may cover them, and the brief must say Claude never runs them.
STUDENT_ONLY = {"cp .env.example .env"}


@pytest.mark.parametrize("step_id", list(EXPECTED))
def test_brief_commands_run_without_asking(a, step_id):
    s = a.step(step_id)
    rules = a.allow + s.allow
    bad = [c for c in commands(s.brief) if c not in STUDENT_ONLY and not allowed(c, rules)]
    assert not bad, f"{step_id}: its brief gives commands its allow list does not cover: {bad}"
    for c in commands(s.brief):
        if c in STUDENT_ONLY:
            assert not allowed(c, rules), f"{step_id}: {c} must not run without asking"
            assert "Never run that" in s.brief, f"{step_id}: the brief must say Claude never runs {c}"


def test_claim_steps_give_the_claim_word_for_word(a):
    assert a.sample_claim == SAMPLE_CLAIM
    for s in a.steps:
        if s.claim:
            assert a.sample_claim in s.brief, f"{s.id}: the brief doesn't give the claim"


def test_part0_briefs_give_the_commands_whole():
    a = stepmod.load(STEPS)
    for step_id, method in (("0c", "no-tools"), ("0d", "one-search"), ("0e", "agent")):
        brief = a.step(step_id).brief
        assert PART0_COMMANDS[method] in brief, f"{step_id}: the brief lacks {PART0_COMMANDS[method]}"
        assert "single quotes" in brief, f"{step_id}: the brief doesn't say to keep the single quotes"


def test_1b_gives_its_one_claim(a):
    # The claim on one line of its own, so the tutor quotes and runs it word for word.
    assert f'"{CLAIM_1B}"' in a.step("1b").brief.splitlines()
    assert "Mel Duncan" not in STEPS.read_text(encoding="utf-8"), "1b has one claim now"


def test_no_brief_and_no_tutor_rule_asks_for_a_prediction(a):
    """The only predictions left are the two written ones in 1e, which 2a compares with. No rule
    asks the student what they expect before a run, and no checkpoint is ticked by one."""
    found = []
    for where, text in [("tutor", a.tutor)] + [(s.id, s.brief) for s in a.steps]:
        for phrase in ("what they expect", "what you expect", "`expected`", "ask what they predict"):
            if phrase in flat(text):
                found.append(f"{where}: {phrase}")
    assert not found, found
    for s in a.steps:
        for c in stepmod.checkpoints(s):
            assert "expect" not in c.text.lower() and "expect" not in c.task.lower(), (s.id, c.text)


def test_no_brief_reruns_the_long_runs_with_fresh(a):
    """--fresh is for 1d's and 3b's runs. A line that runs runs/part2 with --fresh would cost the
    full run again."""
    for s in a.steps:
        for c in commands(s.brief):
            if "--fresh" in c:
                assert "runs/part2" not in c and "after-eval" not in c, f"{s.id}: {c}"


def test_long_runs_are_shown_as_run_yourself():
    """The long runs, 1e's on the student's 100 evaluation claims and 3b's after their change,
    are the student's own, shown on the page as a second command box."""
    steps = {s["id"]: s for s in raw()["step"]}
    want = {"1e": "uv run python evaluate.py data/eval.jsonl --out runs/part2",
            "3b": "uv run python evaluate.py data/eval.jsonl --methods agent --out runs/part3/after"}
    for step_id, s in steps.items():
        if step_id in want:
            run = s.get("run_yourself") or {}
            assert run.get("command") == want[step_id], step_id
            assert run.get("note", "").startswith("About "), step_id
        else:
            assert "run_yourself" not in s, step_id


def test_only_1a_and_1e_hide_their_results():
    """1e asks the student not to look at results yet; 1a's file is the loop check's record, not a run."""
    steps = {s["id"]: s for s in raw()["step"]}
    assert steps["1a"].get("hide_results") is True and steps["1e"].get("hide_results") is True
    assert not [i for i, s in steps.items() if i not in ("1a", "1e") and "hide_results" in s]


def test_every_summary_and_task_is_a_full_sentence(a):
    """A summary starts "In this step you" and ends with a full stop. Under "Tasks" the page lists
    each checkpoint that has no answers of its own by its task, a full sentence: a capital letter
    first, and a full stop last (inside closing brackets, as in 1a's "(Remember, Claude can help
    you!)"). A checkpoint that the student's answers tick shows its questions instead."""
    bad = []
    for s in a.steps:
        if not re.match(r"In this step you .*\.$", s.summary):
            bad.append(f"{s.id} summary: {s.summary}")
        for i, c in enumerate(stepmod.checkpoints(s), 1):
            if c.slots:
                continue
            if not (c.task and c.task[0].isupper() and re.search(r"[.!]\)?$", c.task)):
                bad.append(f"{s.id} checkpoint {i}: {c.task!r}")
    assert not bad, "\n".join(bad)


def test_links_in_tasks_go_to_the_page_or_the_web(a):
    """A task may hold a Markdown link; the page makes it a link only for these addresses."""
    for s in a.steps:
        for c in stepmod.checkpoints(s):
            for _, address in re.findall(r"\[([^\]]+)\]\(([^)]+)\)", c.task):
                assert address.startswith(("https://", "http://", "/")), (s.id, address)


# Steps whose summary differs from the page's first paragraph on purpose, with the reason.
SUMMARY_DIFFERS = {}


def test_summaries_say_what_the_pages_say(a):
    """The homework page shows a step's summary and, below it, its page section, which opens on the
    same sentence, so they must be the same words."""
    differ = []
    for s in a.steps:
        if s.id in SUMMARY_DIFFERS:
            continue
        section = stepmod.body(s, a, REPO)
        first = " ".join(section.strip().split("\n\n")[0].split())
        if first != s.summary:
            differ.append(f"{s.id}:\n  page:    {first}\n  summary: {s.summary}")
    assert not differ, "\n".join(differ)


def test_a_numbered_line_of_a_trace_is_an_entry():
    text = STEPS.read_text(encoding="utf-8")
    for old in ("Found in lookup", "one lookup per turn", "one lookup at a time", "wouldn't say \"doesn't say\"",
                "let it down", "doing its job", "Nothing yet."):
        assert old not in text, old


# ---- the tutor text --------------------------------------------------------------------------

def goal_lists(text: str) -> list[list[str]]:
    """Each list that follows a line ending "you will:", as its items' text with the list marks
    and line breaks taken out."""
    lists, items, inside = [], [], False
    for line in text.splitlines() + [""]:
        if re.search(r"you will:\s*$", line, re.I):
            inside, items = True, []
            continue
        if not inside:
            continue
        m = re.match(r"\s*(?:[-*]|\d+\.)\s+(.*)", line)
        if m:
            items.append(m.group(1).strip())
        elif line.strip() and items and line.startswith(" "):
            items[-1] += " " + line.strip()
        elif items:
            lists.append(items)
            inside = False
    return lists


def test_tutor_opens_with_the_student_and_the_learning_goals(a):
    tutor = a.tutor
    assert goal_lists(tutor) == [GOALS]
    principle = ("Your rules exist to keep the thinking those goals name with the student. Outside that, "
                 "help as much as you can. These students want to learn: assume good faith.")
    assert principle in flat(tutor)
    # The student, then the goals, then the principle, before any rule.
    assert flat(tutor).index("The student is taking COMP 440") < flat(tutor).index(GOALS[0]) \
        < flat(tutor).index(principle) < flat(tutor).index("## ")


def test_the_learning_goals_are_the_same_in_readme_writeup_and_tutor(a):
    for name in ("README.md", "WRITEUP.md"):
        path = REPO / name
        assert path.is_file(), name
        assert GOALS in goal_lists(path.read_text(encoding="utf-8")), f"{name} lacks the five learning goals word for word"


def test_the_tutor_text_is_shorter_than_before(a):
    """It was 3,965 words on Nov 10. The rules now say why they exist, and fewer of them are left."""
    assert len(a.tutor.split()) < 3000


def test_the_api_key_rules_are_kept(a):
    tutor = flat(a.tutor)
    for must in ("## The API key and .env",
                 "Never ask for the key or the email. Never open, read, print, copy or edit .env, and never put a "
                 "key in a file or a command.",
                 "If the student pastes a key into the chat, do not repeat it, use it or write it anywhere."):
        assert must in tutor, must


def test_the_tutor_drops_internal_words_but_not_the_fields_own(a):
    """He uses "retrieval code" himself, so only our own internal words are banned."""
    tutor = flat(a.tutor)
    assert "guardrails, hops, harness, pipeline, scaffold, workbench, step budget" in tutor
    for word in ("embedding", "corpus", "hybrid"):
        assert word not in tutor, word


# Shapes of loop code: a for or while header, an if line ending in a colon, an append or create
# call, a dict key for a tool result, a return of finish(). The briefs may describe the API; they
# must never show loop code themselves.
CODE = [re.compile(x) for x in (
    r"\bfor \w+ in [\w.\[\]()]+\s*:",
    r"\bwhile [^\n:]+:\s*$",
    r"^\s*if [^\n]+:\s*$",
    r"\.append\(",
    r"messages\.create\(",
    r"[\"']tool_use_id[\"']\s*:",
    r"[\"']type[\"']\s*:\s*[\"']tool_result[\"']",
    r"return finish\(",
)]


def test_no_brief_and_no_tutor_rule_shows_loop_code(a):
    found = []
    for where, text in [("tutor", a.tutor)] + [(s.id, s.brief) for s in a.steps]:
        for n, line in enumerate(text.splitlines(), 1):
            for pattern in CODE:
                if pattern.search(line):
                    found.append(f"{where} line {n}: {line.strip()}")
    assert not found, "Loop code in the text Claude is given:\n" + "\n".join(found)


def test_code_finder_sees_loop_code():
    """The test above only means something if it finds code."""
    for line in ("for block in response.content:", "    messages.append({'role': 'user'})",
                 'results.append({"type": "tool_result", "tool_use_id": call.id})',
                 "while True:", "if steps >= max_steps:", "return finish(claim, None, [], why)"):
        assert any(p.search(line) for p in CODE), line
    for line in ("- Explain the Claude API's call: what client.messages.create takes;",
                 "Explain Python: what a for loop, a dict, list.append or a return does."):
        assert not any(p.search(line) for p in CODE), line


def test_no_step_may_edit_the_students_loop():
    """my_loop.py is the student's code, which they type in their editor: no allow list, global or a
    step's, lets Claude change it."""
    data = raw()
    rules = data.get("allow", []) + [r for s in data["step"] for r in s.get("allow", [])]
    assert not [r for r in rules if "my_loop.py" in r and not r.startswith("Bash(")], rules
    assert "reference_loop.py" in data["never_read"]


def test_1a_helps_with_the_loop_but_never_writes_it(a):
    """Goal 2: the student writes the loop and knows each part, with Claude's help ("Remember, Claude
    can help you!"). Claude explains, reads their code, says what failed and why, and suggests a fix
    for one part; it does not write the whole loop, paste a finished one or look for one."""
    brief = flat(a.step("1a").brief)
    for must in ("When the check fails, say what went wrong in that run and why",
                 "suggest how to fix that part, with a few lines of example code",
                 "Do not write the whole loop for them, and never paste a finished loop",
                 "do not edit my_loop.py yourself",
                 "never describe it from memory or guesswork",
                 "uv run python check_loop.py --use-reference",
                 "only when they ask for exactly that"):
        assert must in brief, must
    for gone in ("Never write, dictate, complete or correct a line of my_loop.py", "Hints that hand over the code"):
        assert gone not in brief, gone
    tutor = flat(a.tutor)
    assert "do not write the whole loop for them or paste a finished one" in tutor
    assert "not in the git history" in tutor
    assert "cannot be opened from any session" in tutor


def test_the_strict_rules_about_claims_live_where_the_student_does_the_agents_job(a):
    """Goal 1: in 1b the student is the agent, and in 0e, 1c, 2b and 3a they judge its reasoning.
    The tutor text says the short form once; those briefs say the strict form."""
    for step_id in ("1b", "0e", "1c", "2b", "3a"):
        assert "word for word" in flat(a.step(step_id).brief), step_id
    for step_id in ("1b", "0e", "1c", "2b"):
        assert "does the same work" in flat(a.step(step_id).brief), step_id
    assert "Never break a claim into parts" not in flat(a.tutor)
    assert "Do not do the student's reading of a claim for them" in flat(a.tutor)


def test_no_rule_names_the_grep_tool(a):
    """Claude Code 2.1.322 has no Grep tool ("No such tool available: Grep"), so a rule that names it
    sends the tutor to a pipeline. The rules name `grep -n` through the Bash tool instead, one plain
    command on one file, which the global allow list runs without asking."""
    for where, text in [("tutor", a.tutor)] + [(s.id, s.brief) for s in a.steps]:
        assert "Grep tool" not in text, where
    for s in a.steps:
        for c in commands(s.brief):
            if c.startswith("grep"):
                assert c.startswith("grep -n ") and not re.search(r"\s-\w*[rR]|\||\*", c), (s.id, c)


def test_the_loop_has_more_than_two_ways_to_end():
    assert "two ways" not in STEPS.read_text(encoding="utf-8")


def test_command_finder_sees_commands():
    """The command check above only means something if it finds the commands."""
    brief = 'Run `uv run pytest -q`, then:\n\n    uv run python lookup.py read "<page title>"\n\nIf `uv` fails.'
    assert commands(brief) == ["uv run pytest -q", 'uv run python lookup.py read "<page title>"']
    assert allowed("uv run python lookup.py read \"X\"", ["Bash(uv run python lookup.py:*)"])
    assert not allowed("uv run python lookup.pyx", ["Bash(uv run python lookup.py:*)"])
    assert allowed("test -f .env", ["Bash(test -f .env)"])
    assert not allowed("test -f .env && cat .env", ["Bash(test -f .env)"])


# ---- what students see -----------------------------------------------------------------------

def test_no_ruled_out_words_in_what_students_see(a):
    found = []
    for where, text in student_text(a):
        for word in RULED_OUT:
            if re.search(r"\b" + re.escape(word) + r"\b", text, re.I):
                found.append(f"{where}: '{word}' in '{text}'")
    assert not found, "Words students should not see:\n" + "\n".join(found)


def test_no_tbd():
    assert "TBD" not in STEPS.read_text(encoding="utf-8")


def test_no_placeholders_left():
    """No token in double square brackets, such as one left to fill in, reaches students."""
    left = sorted(set(re.findall(r"\[\[[A-Z][A-Z0-9_]*\]\]", STEPS.read_text(encoding="utf-8"))))
    assert not left, f"steps.toml still has placeholders to fill in: {left}"


# ---- the pages and WRITEUP.md ----------------------------------------------------------------

def headings(path: Path) -> set[str]:
    return {line[3:].strip() for line in path.read_text(encoding="utf-8").splitlines()
            if line.startswith("## ")}


def test_every_section_is_a_heading_in_its_page(a):
    missing = []
    for s in a.steps:
        page = REPO / s.page
        if not page.is_file():
            missing.append(f"{s.id}: {s.page} does not exist")
        elif s.section not in headings(page):
            missing.append(f'{s.id}: {s.page} has no heading "## {s.section}"')
    assert not missing, "\n".join(missing)


def test_every_section_is_a_heading_in_writeup(a):
    writeup = REPO / a.writeup
    have = headings(writeup) if writeup.is_file() else set()
    missing = [f'{s.id}: {a.writeup} has no heading "## {s.section}"' for s in a.steps if s.section not in have]
    assert not missing, "\n".join(missing)


def test_every_step_names_answers_that_exist(a):
    """Each slot a step names matches at least one answer, table or block in WRITEUP.md, so the
    step can be completed."""
    writeup = REPO / a.writeup
    slots = stepmod.read_slots(writeup.read_text(encoding="utf-8")) if writeup.is_file() else {}
    assert stepmod.layout(writeup.read_text(encoding="utf-8")) == "quote", \
        f"{a.writeup} should answer each question on a '>' line"
    missing = []
    for s in a.steps:
        for label in s.slots:
            one = stepmod.Step(id=s.id, part=s.part, title="", slots=[label])
            if not [k for k in stepmod.step_keys(one, slots) if k in slots]:
                missing.append(f'{s.id}: no answer in {a.writeup} matches "{label}"')
    assert not missing, "\n".join(missing)
