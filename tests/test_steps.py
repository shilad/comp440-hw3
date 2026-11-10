"""Checks on steps.toml, the homework page's list of HW3's steps.

Offline: no network, no key. Run with `uv run pytest -q`.

The step list is fixed: the steps from 0a to 3e, each with the sections, answers, files and commands
below. These tests catch a step that drifts from that list, a heading that the pages or
WRITEUP.md do not have, a command a step's Claude session is told to run but may not run without
asking, a word students should not see, and a placeholder that was never filled in.
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
    0: "Set up",
    1: "How the agent works",
    2: "The agent against the baselines",
    3: "Your own claims",
}
DUE = "8:00am Tuesday, November 24"

CHECK = ["Bash(uv run python check.py:*)"]
EVALUATE = ["Bash(uv run python evaluate.py:*)"]
LOOKUP = ["Bash(uv run python lookup.py:*)"]
LOOP_CHECK = ["Bash(uv run python check_loop.py)", "Bash(uv run python check_loop.py --use-reference)",
              "Bash(uv run pytest:*)"]

# id: (part, section heading without "## ", files, allow, minutes)
EXPECTED = {
    "0a": (0, "0a. Get your copy running", [".env", "runs/part0/setup-check.txt"],
           ["Bash(uv sync)", "Bash(uv --version)", "Bash(uv run python check_setup.py)", "Bash(uv run pytest:*)"], 20),
    "0b": (0, "0b. Ask the model with no tools", ["runs/part0/no-tools-*.json"], CHECK, 8),
    "0c": (0, "0c. Give it one search", ["runs/part0/one-search-*.json"], CHECK, 8),
    "0d": (0, "0d. Run the agent and read its trace", ["runs/part0/agent-*.json"], CHECK, 12),
    "1a": (1, "1a. Write the loop", ["runs/part1/loop-check.txt"], LOOP_CHECK, 70),
    "1b": (1, "1b. Be the agent", ["runs/part1/lookups.jsonl"], LOOKUP, 25),
    "1c": (1, "1c. Watch the agent work", ["runs/part1/before/report.txt"], EVALUATE + CHECK, 15),
    "1d": (1, "1d. Write the agent's instructions", ["runs/part1/after/report.txt"], EVALUATE + CHECK, 28),
    "1e": (1, "1e. Start the full run, and predict", ["runs/part2/no-tools.jsonl"], EVALUATE, 15),
    "2a": (2, "2a. Compare accuracy", ["runs/part2/report.txt"], EVALUATE, 18),
    "2b": (2, "2b. Compare cost", [], EVALUATE, 12),
    "2c": (2, "2c. Check the evidence yourself", [], LOOKUP, 20),
    "3a": (3, "3a. Pick a topic and write your claims", ["data/my-claims.jsonl"],
           ["Edit(data/my-claims.jsonl)", "Write(data/my-claims.jsonl)"], 30),
    "3b": (3, "3b. Run the agent on your claims", ["runs/part3/before/report.txt"], EVALUATE + CHECK, 12),
    "3c": (3, "3c. Sort the failures", [], EVALUATE, 25),
    "3d": (3, "3d. Make one change", ["runs/part3/after/report.txt"],
           EVALUATE + CHECK + ["Edit(instructions.md)"], 20),
    "3e": (3, "3e. Write it up", [], [], 23),
}

SAMPLE_CLAIM = 'The composer of "Persian Surgery Dervishes" was born on June 24, 1935.'
PART0_COMMANDS = {
    method: f"uv run python check.py --method {method} --out runs/part0 '{SAMPLE_CLAIM}'"
    for method in ("no-tools", "one-search", "agent")
}
CLAIMS_1B = [
    "Mel Duncan holds a history degree from the private, coeducational liberal arts Macalester "
    "College located in Saint Paul, Minnesota, US.",
    "Vic & Anthony's Steakhouse is located at the American casino that was combined with the "
    "California Club. The casino is owned by Landry's, Inc.",
]

GLOBAL_ALLOW = ["Bash(git log:*)", "Bash(git status:*)", "Bash(git diff:*)", "Bash(git show:*)",
                "Bash(ls:*)", "Edit(WRITEUP.md)"]

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


def student_text(a: stepmod.Assignment) -> list[tuple[str, str]]:
    """Every string from steps.toml that the homework page shows a student, with where it is."""
    out = [(f"part {n} title", p.get("title", "")) for n, p in a.parts.items()]
    for s in a.steps:
        out += [(f"{s.id} title", s.title), (f"{s.id} summary", s.summary), (f"{s.id} goal", s.goal)]
        out += [(f"{s.id} checkpoint {i}", c.text) for i, c in enumerate(stepmod.checkpoints(s), 1)]
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


# ---- the file loads, and holds the agreed step list -----------------------------------------

def test_loads_the_way_the_page_does(a):
    assert a.title and a.tutor.strip() and a.writeup == "WRITEUP.md"
    assert a.model == "claude-opus-5-5" and a.effort == "medium"
    assert a.push is True and a.commit_parts is True
    assert a.never_read == [".env", "reference_loop.py", "tests/test_loop_check.py"]
    assert a.allow == GLOBAL_ALLOW


def test_top_level_keys():
    """Read from the file itself, so the check holds whatever version of the page reads it."""
    import tomllib
    data = tomllib.loads(STEPS.read_text(encoding="utf-8"))
    assert data.get("upstream") == "https://github.com/shilad/comp440-hw3"
    assert "before_commit" not in data, "the page no longer reads before_commit"
    assert "demo" not in data


def test_parts(a):
    assert {n: p["title"] for n, p in a.parts.items()} == PARTS
    assert all(p.get("due") == DUE for p in a.parts.values())


def test_eighteen_steps_in_order(a):
    assert [s.id for s in a.steps] == list(EXPECTED)
    # The page names a step by its part and its letter in the part; that must be its id.
    assert [a.label(s) for s in a.steps] == [s.id for s in a.steps]


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
    assert s.claim == (step_id in ("0b", "0c", "0d"))
    assert s.summary and s.goal and s.brief.strip() and s.checkpoints


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


def flat(text: str) -> str:
    """Text with its line breaks and runs of spaces as single spaces, for word-for-word checks."""
    return " ".join(text.split())


def test_part0_briefs_give_the_commands_whole():
    a = stepmod.load(STEPS)
    for step_id, method in (("0b", "no-tools"), ("0c", "one-search"), ("0d", "agent")):
        brief = a.step(step_id).brief
        assert PART0_COMMANDS[method] in brief, f"{step_id}: the brief lacks {PART0_COMMANDS[method]}"
        assert "single quotes" in brief, f"{step_id}: the brief doesn't say to keep the single quotes"


def test_1b_gives_both_claims_in_order(a):
    brief = flat(a.step("1b").brief)
    at = [brief.find(c) for c in CLAIMS_1B]
    assert all(i >= 0 for i in at), "1b: the brief doesn't give both claims word for word"
    assert at[0] < at[1], "1b: the claims are out of order"


def test_no_brief_reruns_the_long_runs_with_fresh(a):
    """--fresh is for 1d and 3d's short runs. A line that runs runs/part2 or the 3d rerun on the
    200 claims with --fresh would cost the full run again."""
    for s in a.steps:
        for c in commands(s.brief):
            if "--fresh" in c:
                assert "runs/part2" not in c and "after-eval" not in c, f"{s.id}: {c}"


def test_long_runs_are_shown_as_run_yourself():
    """1e's long run is the student's own, shown on the page as a second command box.
    Read from the file itself, since a page version without the key ignores it."""
    import tomllib
    steps = {s["id"]: s for s in tomllib.loads(STEPS.read_text(encoding="utf-8"))["step"]}
    want = {"1e": "uv run python evaluate.py data/eval.jsonl --out runs/part2"}
    for step_id, s in steps.items():
        if step_id in want:
            run = s.get("run_yourself") or {}
            assert run.get("command") == want[step_id], step_id
            assert run.get("note", "").startswith("About "), step_id
        else:
            assert "run_yourself" not in s, step_id


def test_only_1a_and_1e_hide_their_results():
    """1e asks the student not to look at results yet; 1a's file is the loop check's record, not a run."""
    import tomllib
    steps = {s["id"]: s for s in tomllib.loads(STEPS.read_text(encoding="utf-8"))["step"]}
    assert steps["1a"].get("hide_results") is True and steps["1e"].get("hide_results") is True
    assert not [i for i, s in steps.items() if i not in ("1a", "1e") and "hide_results" in s]


# Steps whose goal differs from the page's first line on purpose, with the reason.
GOAL_DIFFERS = {}


def test_goals_say_what_the_pages_say(a):
    """The homework page shows a step's goal and, folded below, its page section; both open on the
    same sentence, so they must be the same words."""
    differ = []
    for s in a.steps:
        if s.id in GOAL_DIFFERS:
            continue
        section = stepmod.body(s, a, REPO)
        first = " ".join(section.strip().split("\n\n")[0].split())
        first = re.sub(r"^\*\*(What you're finding out|What this step is for):\*\*\s*", "", first)
        if first != s.goal:
            differ.append(f"{s.id}:\n  page: {first}\n  goal: {s.goal}")
    assert not differ, "\n".join(differ)


def test_a_numbered_line_of_a_trace_is_an_entry():
    text = STEPS.read_text(encoding="utf-8")
    for old in ("Found in lookup", "one lookup per turn", "one lookup at a time", "wouldn't say \"doesn't say\"",
                "let it down", "doing its job", "Nothing yet."):
        assert old not in text, old


# Shapes of loop code: a for or while header, an if line ending in a colon, an append or create
# call, a dict key for a tool result, a return of finish(). The briefs may name words such as
# tool_use_id inside a quoted hint that is forbidden; they must never show code.
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
    for line in ('- naming what to write: "append a dict with tool_use_id", "check stop_reason first";',
                 "Explain Python: what a for loop, a dict, list.append or a return does."):
        assert not any(p.search(line) for p in CODE), line


def test_no_step_may_edit_the_students_loop():
    """my_loop.py is the student's code: no allow list, global or a step's, lets Claude change it."""
    import tomllib
    data = tomllib.loads(STEPS.read_text(encoding="utf-8"))
    rules = data.get("allow", []) + [r for s in data["step"] for r in s.get("allow", [])]
    assert not [r for r in rules if "my_loop.py" in r and not r.startswith("Bash(")], rules
    assert "reference_loop.py" in data["never_read"]


def test_1a_forbids_writing_the_loop_and_reading_the_reference(a):
    brief = flat(a.step("1a").brief)
    for must in ("Never write, dictate, complete or correct a line of my_loop.py",
                 "never describe it from memory", "uv run python check_loop.py --use-reference",
                 "only when they ask for exactly that"):
        assert must in brief, must
    tutor = flat(a.tutor)
    assert "never write, dictate, complete or correct a line of my_loop.py" in tutor
    assert "cannot be opened from any step's session" in tutor
    # The guard is a courtesy: the loop is also in the git history, so the rule is in words.
    assert "not in the git history" in tutor
    assert "never run `git show` or `git log -p` on agent.py, my_loop.py or reference_loop.py" in tutor


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
