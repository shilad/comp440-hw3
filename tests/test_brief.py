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
        "1a. Read the loop",
        "1b. Be the agent",
        "1c. Watch the agent work",
        "1d. Write the agent's instructions",
        "1e. Start the full run, and predict",
    ]),
    2: ("The agent against the baselines", "instructions/part2.md", [
        "2a. Compare accuracy",
        "2b. Compare cost",
        "2c. Check the evidence yourself",
        "2d. Find where Wikipedia has changed",
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

# Each step's section of a page has these labels, in this order.
LABELS = ["**What you're finding out:**", "**What to do:**", "**What to write:**", "**You're done when:**"]

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
def test_every_step_section_has_the_four_labels_in_order(step):
    page = sections((ROOT / PARTS[int(step[0])][1]).read_text(encoding="utf-8"))[step]
    places = [page.find(label) for label in LABELS]
    assert -1 not in places, f"{step} is missing {[l for l, p in zip(LABELS, places) if p == -1]}"
    assert places == sorted(places), f"{step}: the labels are out of order"


@pytest.mark.parametrize("name", OWNED)
def test_no_placeholder_is_left(name):
    text = (ROOT / name).read_text(encoding="utf-8")
    left = re.findall(r"\[\[[^\]]*\]\]|\[TBD[^\]]*\]", text)
    assert not left, f"{name} still has {sorted(set(left))}"
