"""Checks on steps.toml, the homework page's list of HW3's steps.

Offline: no network, no key. Run with `uv run pytest -q`.

The step list is fixed: 18 steps, 0a to 3e, each with the sections, answers, files and commands
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

# id: (part, section heading without "## ", files, allow, minutes)
EXPECTED = {
    "0a": (0, "0a. Get your copy running", [".env", "runs/part0/setup-check.txt"],
           ["Bash(uv sync)", "Bash(uv --version)", "Bash(uv run python check_setup.py)", "Bash(uv run pytest:*)"], 20),
    "0b": (0, "0b. Ask the model with no tools", ["runs/part0/no-tools-*.json"], CHECK, 8),
    "0c": (0, "0c. Give it one search", ["runs/part0/one-search-*.json"], CHECK, 8),
    "0d": (0, "0d. Run the agent and read its trace", ["runs/part0/agent-*.json"], CHECK, 12),
    "1a": (1, "1a. Read the loop", [], [], 30),
    "1b": (1, "1b. Be the agent", ["runs/part1/lookups.jsonl"], LOOKUP, 25),
    "1c": (1, "1c. Watch the agent work", ["runs/part1/before/report.txt"], EVALUATE + CHECK, 25),
    "1d": (1, "1d. Write the agent's instructions", ["runs/part1/after/report.txt"], EVALUATE + CHECK, 35),
    "1e": (1, "1e. Start the full run, and predict", ["runs/part2/no-tools.jsonl"], EVALUATE, 15),
    "2a": (2, "2a. Compare accuracy", ["runs/part2/report.txt"], EVALUATE, 18),
    "2b": (2, "2b. Compare cost", [], EVALUATE, 12),
    "2c": (2, "2c. Check the evidence yourself", [], LOOKUP, 35),
    "2d": (2, "2d. Find where Wikipedia has changed", [], LOOKUP, 30),
    "3a": (3, "3a. Pick a topic and write your claims", ["data/my-claims.jsonl"],
           ["Edit(data/my-claims.jsonl)", "Write(data/my-claims.jsonl)"], 30),
    "3b": (3, "3b. Run the agent on your claims", ["runs/part3/before/report.txt"], EVALUATE + CHECK, 12),
    "3c": (3, "3c. Sort the failures", [], EVALUATE, 25),
    "3d": (3, "3d. Make one change", ["runs/part3/after/report.txt", "runs/part3/after-eval/report.txt"],
           EVALUATE + CHECK + ["Edit(instructions.md)"], 20),
    "3e": (3, "3e. Write it up", [], [], 30),
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
    assert a.never_read == [".env"]
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

@pytest.mark.parametrize("step_id", list(EXPECTED))
def test_brief_commands_run_without_asking(a, step_id):
    s = a.step(step_id)
    rules = a.allow + s.allow
    bad = [c for c in commands(s.brief) if not allowed(c, rules)]
    assert not bad, f"{step_id}: its brief gives commands its allow list does not cover: {bad}"


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
