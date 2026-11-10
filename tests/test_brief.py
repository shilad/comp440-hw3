"""The instruction pages and WRITEUP.md stay in step with each other.

The homework page shows each step's section of instructions/partN.md on its own, and reads the
student's answers from the same step's section of WRITEUP.md. So every step heading must appear once in
its page and once in WRITEUP.md, in the same order, and every question WRITEUP.md asks must appear word
for word in that step's section of the page. Offline: no network, no API key.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
WRITEUP = ROOT / "WRITEUP.md"

# The parts and steps, in order: the "## " headings of each page and of WRITEUP.md.
PARTS = {
    0: ("Set up", "instructions/part0.md", [
        "0a. Get your copy running",
        "0b. Ask the model with no tools",
        "0c. Give it one search",
        "0d. Run the agent and read its trace",
    ]),
    1: ("How the agent works", "instructions/part1.md", [
        "1a. Write the loop",
        "1b. Be the agent",
        "1c. Watch the agent work",
        "1d. Write the agent's instructions",
        "1e. Start the full run, and predict",
    ]),
    2: ("The agent against the baselines", "instructions/part2.md", [
        "2a. Compare accuracy",
        "2b. Compare cost",
        "2c. Check the evidence yourself",
    ]),
    3: ("Your own claims", "instructions/part3.md", [
        "3a. Pick a topic and write your claims",
        "3b. Run the agent on your claims",
        "3c. Sort the failures",
        "3d. Make one change",
        "3e. Write it up",
    ]),
}
ALL_STEPS = [step for _, _, steps in PARTS.values() for step in steps]

# Each step's section of a page uses these labels, in this order. The four marked True are required;
# the others appear only where a step needs them.
LABELS = [
    ("**What you're finding out:**", True),
    ("**Words in this step:**", False),
    ("**What to do:**", True),
    ("**What you'll see:**", False),
    ("**What to write:**", True),
    ("**You're done when:**", True),
    ("**If something goes wrong:**", False),
    ("**Hint:**", False),
]

# Steps that are not an investigation open with "What this step is for:" instead of "What you're
# finding out:". It takes the first label's place, so it is required in these four and nowhere else.
FIRST_LABEL = "**What you're finding out:**"
STEP_IS_FOR = "**What this step is for:**"
STEP_IS_FOR_STEPS = {"0a", "1e", "3a", "3e"}


def labels_for(step):
    """The label list for one step, with its own first label."""
    if step[:2] in STEP_IS_FOR_STEPS:
        return [(STEP_IS_FOR if label == FIRST_LABEL else label, required) for label, required in LABELS]
    return LABELS


# How many answers WRITEUP.md holds in all: one per question, table and pasted block, plus Name.
SLOTS = 46

# The files whose words students read, which must hold no placeholder when the homework ships.
OWNED = ["README.md", "WRITEUP.md", ".env.example"] + [page for _, page, _ in PARTS.values()]

STEP_HEADING = re.compile(r"^## (\d[a-z]\. .+?)\s*$")


def one_line(text):
    return re.sub(r"\s+", " ", text).strip()


def sections(text):
    """Each "## " heading's text, up to the next "## ", the way the homework page cuts a page."""
    out, name, lines = {}, None, []
    for line in text.splitlines():
        if line.startswith("## "):
            if name is not None:
                out[name] = "\n".join(lines)
            name, lines = line[3:].strip(), []
        elif name is not None:
            lines.append(line)
    if name is not None:
        out[name] = "\n".join(lines)
    return out


def step_headings(text):
    return [m.group(1) for line in text.splitlines() if (m := STEP_HEADING.match(line))]


def questions(section):
    """What a section of WRITEUP.md asks: the paragraph just above each answer slot (a ">" line, a
    table or a fenced block), on one line."""
    found, para, lines, i = [], [], section.splitlines(), 0
    while i < len(lines):
        line = lines[i]
        slot = line.startswith(">") or line.lstrip().startswith("|") or line.startswith("```")
        if slot:
            if para:
                found.append(one_line(" ".join(para)))
            para = []
            if line.startswith("```"):        # skip to the end of the block
                i += 1
                while i < len(lines) and not lines[i].startswith("```"):
                    i += 1
            elif line.lstrip().startswith("|"):
                while i + 1 < len(lines) and lines[i + 1].lstrip().startswith("|"):
                    i += 1
        elif line.startswith("#"):
            para = []
        elif line.strip():
            if i and not lines[i - 1].strip():
                para = []                     # a new paragraph replaces the one above
            para.append(line.strip())
        i += 1
    return found


def test_each_page_has_its_steps_once_and_in_order():
    for _, page, steps in PARTS.values():
        assert step_headings((ROOT / page).read_text(encoding="utf-8")) == steps, page


def test_writeup_has_every_step_once_and_in_order():
    assert step_headings(WRITEUP.read_text(encoding="utf-8")) == ALL_STEPS


def test_writeup_parts_come_in_order_with_their_steps():
    current, seen = None, []
    for line in WRITEUP.read_text(encoding="utf-8").splitlines():
        if m := re.match(r"^# Part (\d+): (.+?)\s*$", line):
            current = int(m.group(1))
            assert m.group(2) == PARTS[current][0], line
            seen.append(current)
        elif m := STEP_HEADING.match(line):
            assert current is not None and m.group(1) in PARTS[current][2], line
    assert seen == sorted(PARTS)


def test_writeup_starts_with_name():
    assert re.search(r"^Name:", WRITEUP.read_text(encoding="utf-8"), re.M)


@pytest.mark.parametrize("step", ALL_STEPS)
def test_every_writeup_question_is_in_the_steps_page_word_for_word(step):
    part = int(step[0])
    page = sections((ROOT / PARTS[part][1]).read_text(encoding="utf-8"))[step]
    asked = questions(sections(WRITEUP.read_text(encoding="utf-8"))[step])
    if step != "0a. Get your copy running":
        assert asked, f"{step} asks nothing in WRITEUP.md"
    missing = [q for q in asked if q not in one_line(page)]
    assert not missing, f"{step}: in WRITEUP.md but not in {PARTS[part][1]}: {missing}"


@pytest.mark.parametrize("step", ALL_STEPS)
def test_every_step_section_has_its_labels_once_and_in_order(step):
    page = sections((ROOT / PARTS[int(step[0])][1]).read_text(encoding="utf-8"))[step]
    labels = labels_for(step)
    missing = [label for label, required in labels if required and label not in page]
    assert not missing, f"{step} is missing {missing}"
    other = STEP_IS_FOR if labels is LABELS else FIRST_LABEL
    assert other not in page, f"{step} should not use {other}"
    twice = [label for label, _ in labels if page.count(label) > 1]
    assert not twice, f"{step} has these labels more than once: {twice}"
    places = [page.find(label) for label, _ in labels if label in page]
    assert places == sorted(places), f"{step}: the labels are out of order"


def test_writeup_has_one_slot_per_answer():
    text = WRITEUP.read_text(encoding="utf-8")
    asked = sum(len(questions(body)) for body in sections(text).values())
    assert asked + 1 == SLOTS, f"WRITEUP.md has {asked} answers plus Name, not {SLOTS}"


@pytest.mark.parametrize("name", OWNED)
def test_no_placeholder_is_left(name):
    text = (ROOT / name).read_text(encoding="utf-8")
    left = re.findall(r"\[\[[^\]]*\]\]|\[TBD[^\]]*\]", text)
    assert not left, f"{name} still has {sorted(set(left))}"


# ---- step 1a: the student writes the loop -----------------------------------------------------

# The six rules, word for word as the check prints them and the tutor's brief gives them.
LOOP_RULES = [
    "1. **Ask the model.** Each turn, send the model the system text, the tools and the whole conversation so "
    "far. Add the tokens the reply used to `tokens`, and add the reply to the conversation as the assistant's "
    "turn.",
    "2. **Run its lookups.** For each lookup the reply asks for, call `lookup(name, input)`, add 1 to `steps`, "
    "and add an entry to `trace`. Keep what `read` and `wikidata` return in `read_so_far`; do not keep what "
    "`search` returns.",
    "3. **Send the results back.** After the reply's tool calls are handled, add one user turn to the "
    "conversation that holds a result for every call, each marked with the id of the call it answers.",
    "4. **Check the answer.** When the reply calls `answer`, check it with `answer_problem()`. If there is no "
    "problem, stop and return `finish(...)` with the answer's verdict, evidence and explanation. If there is "
    "a problem, send back `REJECTED` followed by the problem, and after `MAX_REJECTED` rejected answers stop "
    "with no verdict.",
    "5. **Enforce the limit.** Once `steps` has reached `max_steps`, do not run another lookup. The first time, "
    "send back `OUT_OF_STEPS`. If the model asks for a lookup again on a later turn, stop with no verdict.",
    "6. **Stop when the model stops.** If a reply has no tool call, remind the model once with `REMINDER`; if "
    "the next reply has none either, stop with no verdict. If a reply's `stop_reason` is `\"refusal\"`, stop "
    "with no verdict.",
]


def section_1a():
    return one_line(sections((ROOT / "instructions/part1.md").read_text(encoding="utf-8"))["1a. Write the loop"])


def test_1a_gives_the_six_rules_word_for_word_and_in_order():
    page = section_1a()
    at = [page.find(rule) for rule in LOOP_RULES]
    assert -1 not in at, f"1a lacks rule(s) {[i + 1 for i, a in enumerate(at) if a == -1]}"
    assert at == sorted(at)


def test_1a_says_what_is_given_and_what_is_theirs():
    page = section_1a()
    for name in ("`agent.py`", "`my_loop.py`", "`reference_loop.py`", "`check_loop.py`",
                 "uv run python check_loop.py", "uv run python check_loop.py --use-reference",
                 "runs/part1/loop-check.txt"):
        assert name in page, f"1a doesn't name {name}"


def test_nothing_still_says_the_student_reads_the_loop():
    for name in OWNED:
        text = (ROOT / name).read_text(encoding="utf-8")
        for old in ("Read the loop", "read its loop", "Read the agent's loop", "which is the loop"):
            assert old not in text, f"{name} still says {old!r}"
