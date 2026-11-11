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
    0: ("Set up and check one claim", "instructions/part0.md", [
        "0a. Get your copy running",
        "0b. Ask the model to assess a claim without tools",
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
        "2b. Check the evidence yourself",
    ]),
    3: ("Why the agent fails, and one change", "instructions/part3.md", [
        "3a. Sort the failures",
        "3b. Make one change",
        "3c. Write it up",
    ]),
}
ALL_STEPS = [step for _, _, steps in PARTS.values() for step in steps]

# Each step's section of a page opens with a paragraph of full sentences saying what the step is for,
# with no label over it. After it come these labels, in this order. The two marked True are
# required; the others appear only where a step needs them.
LABELS = [
    ("**Words in this step:**", False),
    ("**Actions:**", True),
    ("**Interpreting output:**", False),
    ("**Write-up:**", True),
    ("**Troubleshooting:**", False),
    ("**Hint:**", False),
]

# Labels the pages used to carry. Each was the first half of a sentence; a label is now a short
# phrase, with a full sentence after it. No page uses the old ones.
OLD_FIRST_LABELS = ["**What you're finding out:**", "**What this step is for:**", "**What to do:**",
                    "**What you'll see:**", "**What to write:**", "**You're done when:**",
                    "**If something goes wrong:**", "**Output:**",
                    # Every Completion part said only when the page ticks the step, which the page shows.
                    "**Completion:**"]


# How many answers WRITEUP.md holds in all: one per question, table and pasted block, plus Name.
SLOTS = 32

# Part 3 is extra credit: its headings say so after the part's number.
EXTRA_CREDIT = {3}

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
        if m := re.match(r"^# Part (\d+)( \(extra credit\))?: (.+?)\s*$", line):
            current = int(m.group(1))
            assert m.group(3) == PARTS[current][0], line
            assert bool(m.group(2)) == (current in EXTRA_CREDIT), line
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
    labels = LABELS
    missing = [label for label, required in labels if required and label not in page]
    assert not missing, f"{step} is missing {missing}"
    old = [label for label in OLD_FIRST_LABELS if label in page]
    assert not old, f"{step} should not use {old}"
    opening = page.strip().split("\n\n")[0]
    assert opening.startswith("In this step you ") and opening.rstrip().endswith("."), f"{step} opens with: {opening[:60]}"
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

# The six rules, word for word as the page gives them (the check prints their titles).
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
    "send back `OUT_OF_STEPS`, and remember that you sent it. If the model asks for a lookup again on a later "
    "turn, stop with no verdict.",
    "6. **Stop when the model stops.** If a reply has no tool call, remind the model with `REMINDER`; if the "
    "next reply has none either, stop with no verdict. The model is reminded each time it stops calling tools, "
    "but never twice in a row. If a reply's `stop_reason` is `\"refusal\"`, stop with no verdict.",
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


def test_each_page_title_names_its_part():
    for n, (title, page, _) in PARTS.items():
        first = (ROOT / page).read_text(encoding="utf-8").splitlines()[0]
        mark = " (extra credit)" if n in EXTRA_CREDIT else ""
        assert first == f"# COMP 440 HW3 Part {n}{mark}: {title}", first


# ---- the learning goals -----------------------------------------------------------------------

# Word for word in README.md (after its opening sentence) and in WRITEUP.md (its "Learning goals"
# section). The tutor's copy in steps.toml is checked with the steps.
LEARNING_GOALS = [
    "Understand what makes a program an *agent*. You will study a language model that picks the next "
    "Wikipedia search query, reads the page that comes back, and decides when to stop.",
    "Gain hands-on experience with the loop around the model by writing it yourself: its tools, its "
    "instructions, its limit of 12 lookups, and the check that every sentence it quotes really appears in "
    "what it read.",
    "Compare the agent with two simpler methods on your claims, and measure how effective each one is.",
    "Check the agent's evidence yourself, and decide whether accuracy alone is a fair measure of it.",
]
EXTRA_CREDIT_GOAL = ("For extra credit, in Part 3, you find out why the agent fails on your claims, make "
                     "one change, and see where Wikipedia, which is written by its volunteer editors, is "
                     "thin, out of date or wrong.")


def bullets_after(text, lead):
    """The "- " items of the list that follows the line ending in `lead`, each on one line, and the
    paragraph after the list."""
    lines = text.splitlines()
    at = next(i for i, line in enumerate(lines) if line.rstrip().endswith(lead))
    items, i = [], at + 1
    while i < len(lines) and not lines[i].strip():
        i += 1
    while i < len(lines) and lines[i].strip():
        if lines[i].startswith("- "):
            items.append(lines[i][2:])
        else:
            items[-1] += " " + lines[i].strip()
        i += 1
    after = []
    while i < len(lines) and not lines[i].strip():
        i += 1
    while i < len(lines) and lines[i].strip():
        after.append(lines[i].strip())
        i += 1
    return [one_line(item) for item in items], one_line(" ".join(after))


def test_readme_and_writeup_give_the_same_four_learning_goals():
    readme, readme_after = bullets_after((ROOT / "README.md").read_text(encoding="utf-8"), "You will:")
    writeup, writeup_after = bullets_after(WRITEUP.read_text(encoding="utf-8"), "In this homework you will:")
    assert readme == LEARNING_GOALS
    assert writeup == LEARNING_GOALS
    assert readme_after == writeup_after == EXTRA_CREDIT_GOAL


def test_the_learning_goals_come_before_part_0_and_hold_no_answer():
    text = WRITEUP.read_text(encoding="utf-8")
    assert text.index("## Learning goals") < text.index("# Part 0")
    assert "Learning goals" in sections(text)
    assert not questions(sections(text)["Learning goals"].split("# Part 0")[0])


# ---- what the outline of Nov 10 removed --------------------------------------------------------

REMOVED = [
    "Mel Duncan",                      # 1b has one claim now
    "Compare cost",                    # the old step 2b
    "2c",                              # the old 2c is 2b
    "How I used AI",                   # the AI-use question in 3c
    "what you expect",                 # no step asks for an expectation before a run
    "Claim (1 or 2)",                  # 1b's table has no claim column
    "Which rule took you longest",     # a removed 1a question
    "Was that the change you expected",  # a removed 1d question
]


@pytest.mark.parametrize("name", OWNED)
def test_nothing_removed_comes_back(name):
    text = one_line((ROOT / name).read_text(encoding="utf-8"))
    left = [old for old in REMOVED if old in text]
    assert not left, f"{name} still has {left}"


@pytest.mark.parametrize("name", OWNED)
def test_nothing_students_read_sends_them_to_the_claim_finder(name):
    """Step 0b is gone (the instructor, Nov 11: "drop 0b"), and with it the claim finder, the
    student's topics and the 112 claims they selected; the later steps of Part 0 are 0b to 0d.
    README's Resources section keeps the licence notices for the claim finder's data, which stays in
    the repository."""
    text = (ROOT / name).read_text(encoding="utf-8")
    if name == "README.md":
        text = re.sub(r"(?s)\n## Resources\n.*?(?=\n## )", "\n", text)
    text = one_line(text)
    for gone in ("claim finder", "**Find claims**", "my-topic", "finder/search.py", "topics", "112",
                 "dataset of claims about", "retrieval"):
        assert gone not in text, f"{name} still has {gone!r}"
    assert not re.search(r"\b0e\b", text), f"{name} still names step 0e"


# ---- what each part holds -----------------------------------------------------------------------

# The page shows a step's opening (its summary, and in Part 0 and 1b the claim it checks) and then each
# labeled part as a line that opens with a click. Actions, Write-up and, in 1a, The six rules hold only
# what the student does and answers, as lists, so that a student who opens them finds the steps and
# not an explanation; explanations go under the other labels.
FOLDED = ["Words in this step", "Interpreting output", "Troubleshooting", "Hint"]
OPEN_LABELS = ["Actions", "Write-up", "The six rules"]


def parts(section):
    """A step's section cut the way the page cuts it: the opening, then each part that starts with a
    paragraph opening on a bold label, as {label: [paragraph, ...]}."""
    out, name, para, paras = {}, "(opening)", [], []
    fence = False
    for line in section.splitlines() + [""]:
        if line.startswith("```"):
            fence = not fence
        if not line.strip() and not fence:
            if para:
                paras.append("\n".join(para))
                para = []
            continue
        m = re.match(r"^\*\*([^*]+):\*\*", line) if not para and not fence else None
        if m:
            out[name] = paras
            name, paras = m.group(1), []
        para.append(line)
    out[name] = paras
    return out


@pytest.mark.parametrize("step", ALL_STEPS)
def test_actions_and_write_up_hold_no_loose_explanation(step):
    page = sections((ROOT / PARTS[int(step[0])][1]).read_text(encoding="utf-8"))[step]
    cut = parts(page)
    loose = []
    listed = re.compile(r"^([-*]|\d+\.)\s|^```|^\|")
    for label in OPEN_LABELS:
        paras = cut.get(label, [])
        for i, para in enumerate(paras[1:], 1):
            # A list, a block or a table; or the line that leads into the list right after it.
            leads_in = para.endswith(":") and i + 1 < len(paras) and listed.match(paras[i + 1].lstrip())
            if not (listed.match(para.lstrip()) or leads_in):
                loose.append(f"{label}: {one_line(para)[:70]}")
    opening = cut["(opening)"]
    for i, para in enumerate(opening[1:], 1):
        is_quote = para.startswith(">")
        leads_to_quote = i + 1 < len(opening) and opening[i + 1].startswith(">") and para.endswith(":")
        if not (is_quote or leads_to_quote):
            loose.append(f"opening: {one_line(para)[:70]}")
    assert not loose, f"{step}: move these under Words in this step, Interpreting output, Troubleshooting or Hint: {loose}"


@pytest.mark.parametrize("step", ALL_STEPS[1:])           # 0a's only answer is the name
def test_actions_say_where_the_answers_are_typed(step):
    """The instructor, Nov 11: "Should I be talking with Claude? Should I be typing in the writeup?
    Clarify." Each step's Actions end the same way: the answers are typed in WRITEUP.md, in the
    student's editor, under the step's heading."""
    page = sections((ROOT / PARTS[int(step[0])][1]).read_text(encoding="utf-8"))[step]
    actions = one_line("\n\n".join(parts(page).get("Actions", [])))
    label = step.split(".")[0]
    assert f"in `WRITEUP.md`, in your editor, under {label}." in actions, actions[-200:]
    assert not re.search(r"\d\. Answer the", actions), actions


@pytest.mark.parametrize("step", ALL_STEPS)
def test_every_label_is_one_the_page_knows(step):
    page = sections((ROOT / PARTS[int(step[0])][1]).read_text(encoding="utf-8"))[step]
    unknown = [label for label in parts(page) if label != "(opening)" and label not in FOLDED + OPEN_LABELS]
    assert not unknown, f"{step} has labels the homework does not use: {unknown}"


# ---- the due date, once ------------------------------------------------------------------------

# The instructor (Nov 11): "The whole things is due Nov 24th. You don't need to keep repeating that.
# Put it up top and not again." README states it once, after the goals and the extra-credit sentence
# (the page reads README's first paragraph and the bullets after it, so it cannot come before them).
DUE = "Everything is due 8:00am Tuesday, November 24."
PART_OPENINGS = {
    0: "In this part you get your copy of the homework running. Then you check one claim",
    1: "In this part you build and study the agent.",
    2: "In this part you read the full run you started in 1e:",
    3: "In this part you sort out why the agent fails on your evaluation claims,",
}


def test_the_due_date_is_stated_once_at_the_top_of_readme():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    flat = one_line(readme)
    assert flat.count(DUE) == 1
    assert flat.index(EXTRA_CREDIT_GOAL) < flat.index(DUE) < flat.index("## The claim checking task")
    lines = [line for line in readme.splitlines() if re.search(r"November 24|Nov\.? 24|\bdue\b", line, re.I)]
    assert lines == [DUE], lines


@pytest.mark.parametrize("name", ["WRITEUP.md"] + [page for _, page, _ in PARTS.values()])
def test_no_other_file_states_the_due_date(name):
    text = (ROOT / name).read_text(encoding="utf-8")
    assert not re.search(r"November 24|Nov\.? 24|\bdue\b|8:00am", text, re.I), name


@pytest.mark.parametrize("n", sorted(PARTS))
def test_each_page_opens_with_its_part_and_links_back(n):
    import sys
    sys.path.insert(0, str(ROOT))
    from workbench.steps import intro
    text = (ROOT / PARTS[n][1]).read_text(encoding="utf-8")
    assert intro(text).startswith(PART_OPENINGS[n]), intro(text)[:80]
    assert "Back to the [assignment page](../README.md)." in text
    before_first_step = text.split("\n## ", 1)[0]
    assert "Back to the [assignment page](../README.md)." in before_first_step
