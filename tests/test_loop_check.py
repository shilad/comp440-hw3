"""Do not open this file before step 1a is done: it holds complete loops, and
reading them first gives the exercise away.

Offline tests for check_loop.py, the check of the loop in my_loop.py, and for how
the agent chooses between that loop and the reference loop. Every test keeps
runs/part1/loop-check.txt in a temporary folder, so none of them reads or leaves
a runs/ folder in the repository."""

import json
import re
import shutil
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import agent  # noqa: E402
import check  # noqa: E402
import check_loop  # noqa: E402
import evaluate  # noqa: E402
import wiki  # noqa: E402

# The reference loop as it was before the parts in loop_parts.py: written straight against the
# Claude API. It is still a right loop for the check, which judges what a loop does, so the
# broken loops below are made by editing it. KIT_REFERENCE is the reference loop in this
# copy, written with the parts.
REFERENCE = '''"""The reference loop. The homework uses it in Part 0, before your own loop, in
my_loop.py, has passed the check (uv run python check_loop.py), and not after.

Do not open this file before step 1a is done: reading it first gives the
exercise away. After that, compare it with yours (the write-up asks you to).
"""

import anthropic

from agent import (ACCEPTED, DECLINED, INSTRUCTIONS, MAX_REJECTED, MAX_STEPS, MODEL, NO_ANSWER,
                   OUT_OF_STEPS, RAN_OUT, REJECTED, REJECTED_TOO_OFTEN, REMINDED, REMINDER,
                   TOOLS, answer_problem, clean_answer, finish, run_tool)


def run_agent(claim, client=None, max_steps=MAX_STEPS, lookup=run_tool):
    """Check one claim. Returns a dict with the verdict, the evidence, the
    trace of every step, and the number of lookups."""
    client = client or anthropic.Anthropic()
    system = INSTRUCTIONS.read_text()
    messages = [{"role": "user", "content": f"Claim: {claim}"}]
    trace, read_so_far = [], []
    steps = 0
    rejected = 0        # how many answers the loop has sent back
    warned = False      # has it been told it is out of steps?

    while True:
        response = client.messages.create(
            model=MODEL, max_tokens=16000, system=system, tools=TOOLS, messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "refusal":
            return finish(claim, None, [], DECLINED, trace, steps)

        calls = [block for block in response.content if block.type == "tool_use"]
        if not calls:
            # Claude stopped without calling a tool. Remind it once how to finish.
            if trace and trace[-1]["tool"] == "(reminder)":
                return finish(claim, None, [], NO_ANSWER, trace, steps)
            trace.append({"tool": "(reminder)", "input": {}, "result": REMINDED})
            messages.append({"role": "user", "content": REMINDER})
            continue

        results = []
        warned_before = warned
        for call in calls:
            if call.name == "answer":
                answer = clean_answer(call.input)
                problem = answer_problem(answer, read_so_far)
                if problem is None:
                    trace.append({"tool": "answer", "input": call.input, "result": ACCEPTED})
                    return finish(claim, answer["verdict"], answer["evidence"],
                                  answer["explanation"], trace, steps)
                result = REJECTED + problem
                rejected += 1
                if rejected >= MAX_REJECTED:
                    trace.append({"tool": "answer", "input": call.input, "result": result})
                    return finish(claim, None, [], REJECTED_TOO_OFTEN.format(n=rejected),
                                  trace, steps)
            elif steps >= max_steps:
                if warned_before:
                    # It was told last turn that it was out of steps: stop here.
                    return finish(claim, None, [], RAN_OUT, trace, steps)
                result = OUT_OF_STEPS.format(n=max_steps)
                warned = True
            else:
                steps += 1
                result = lookup(call.name, call.input)
                if call.name != "search":  # snippets are too short to count as evidence
                    read_so_far.append(result)
            trace.append({"tool": call.name, "input": call.input, "result": result})
            results.append({"type": "tool_result", "tool_use_id": call.id, "content": result})

        messages.append({"role": "user", "content": results})
'''
KIT_REFERENCE = (ROOT / "reference_loop.py").read_text()
NOT_WRITTEN = "the loop is not written yet."


@pytest.fixture(autouse=True)
def saved(monkeypatch, tmp_path):
    """runs/part1/loop-check.txt, in a temporary folder."""
    path = tmp_path / "runs" / "part1" / "loop-check.txt"
    monkeypatch.setattr(agent, "LOOP_CHECK", path)
    return path


def a_loop(tmp_path, source, monkeypatch=None):
    """Write source as my_loop.py in its own folder; with monkeypatch, make it the one
    check_loop.py checks."""
    folder = tmp_path / f"loop{len(list(tmp_path.glob('loop*')))}"
    folder.mkdir()
    path = folder / "my_loop.py"
    path.write_text(source)
    if monkeypatch is not None:
        monkeypatch.setattr(check_loop, "MY_LOOP", path)
    return path


def broken(*edits):
    """The reference loop with each (old, new) edit made once."""
    source = REFERENCE
    for old, new in edits:
        assert source.count(old) == 1, old
        source = source.replace(old, new)
    return source


def shown(path):
    return check_loop.lines(check_loop.check(path))


# ---------- the skeleton, the reference loop and the way out ----------

def test_the_skeleton_gives_six_not_yet_lines_and_no_file(monkeypatch, saved, capsys):
    monkeypatch.setattr(check_loop, "MY_LOOP", ROOT / "my_loop.py")
    assert check_loop.main([]) == 1
    printed = capsys.readouterr().out.splitlines()
    assert printed[:6] == [f"NOT YET    {n}. {title}: {NOT_WRITTEN}"
                           for n, title in enumerate(check_loop.RULES, 1)]
    assert printed[6:] == ["", f"The rule (1. {check_loop.RULES[0]}): {check_loop.rule_text(1)}", "", check_loop.FAILED]
    assert not saved.exists()
    assert agent.which_loop() == "reference"


@pytest.mark.parametrize("name", ["only the first call", "no reminder", "the limit is MAX_STEPS"])
def test_the_check_states_the_rule_behind_the_first_not_yet_line(tmp_path, monkeypatch, capsys,
                                                                   name):
    """The page does not list the rules: the check states the one behind the first NOT YET line,
    in plain words, once, under the six lines."""
    rule, edits, _ = BROKEN[name]
    a_loop(tmp_path, broken(*edits), monkeypatch)
    assert check_loop.main([]) == 1
    printed = capsys.readouterr().out.splitlines()
    stated = [line for line in printed if line.startswith("The rule (")]
    assert stated == [f"The rule ({rule}. {check_loop.RULES[rule - 1]}): {check_loop.rule_text(rule)}"]
    assert printed.index(stated[0]) == 7


def test_the_rules_are_stated_without_code_names():
    for n in range(1, 7):
        text = check_loop.rule_text(n)
        assert not any(name in text for name in ("MAX_", "max_steps", "talk.", "()", "_"))


def test_no_rule_is_stated_when_every_rule_passes(tmp_path, monkeypatch, capsys):
    a_loop(tmp_path, REFERENCE, monkeypatch)
    assert check_loop.main([]) == 0
    assert "The rule (" not in capsys.readouterr().out


def test_the_skeleton_names_no_rule_and_gives_nothing_more():
    """The page does not list the rules: the student meets each one when the check states it."""
    source = (ROOT / "my_loop.py").read_text()
    assert "# The check's six lines name the rules your loop must follow" in source
    for title in check_loop.RULES:
        assert title not in source
    assert 'raise NotImplementedError("The loop is not written yet: see step 1a.")' in source
    below = source[source.index("# ---- your loop goes below this line"):].strip().splitlines()
    assert [line.strip() for line in below[1:]] == [
        'raise NotImplementedError("The loop is not written yet: see step 1a.")']
    assert "messages.create" not in source and "tool_result" not in source


def test_the_reference_loop_passes_and_is_saved_as_yours(tmp_path, monkeypatch, saved, capsys):
    a_loop(tmp_path, REFERENCE, monkeypatch)
    assert check_loop.main([]) == 0
    printed = capsys.readouterr().out.splitlines()
    assert printed == [f"ok         {n}. {title}" for n, title in enumerate(check_loop.RULES, 1)] \
        + ["", check_loop.PASSED]
    assert saved.read_text().splitlines() == ["yours"] + printed
    assert agent.which_loop() == "yours"
    assert not agent.counts_tokens()      # no token line: tokens and cost stay hidden


def test_there_is_no_way_to_keep_the_reference_loop(saved, capsys):
    """The instructor, Nov 11: "i don't want them to be able to use the reference loop." The option
    is gone, and an old record of that choice counts as a loop that has not passed."""
    with pytest.raises(SystemExit):
        check_loop.main(["--use-reference"])
    assert not saved.exists()
    saved.parent.mkdir(parents=True)
    saved.write_text("reference\nRecorded: your copy keeps using the reference loop.\n")
    assert agent.which_loop() == "not passed"
    with pytest.raises(agent.LoopNotPassed):
        agent.run_agent("c")


def test_a_failing_check_after_a_pass_stops_the_agent(tmp_path, monkeypatch, saved, capsys):
    a_loop(tmp_path, REFERENCE, monkeypatch)
    assert check_loop.main([]) == 0 and agent.which_loop() == "yours"
    capsys.readouterr()
    # A later change breaks the loop: no agent runs until it passes again, and the file stays,
    # so the homework page still counts step 1a as done.
    a_loop(tmp_path, broken(("                steps += 1\n", "")), monkeypatch)
    assert check_loop.main([]) == 1
    printed = capsys.readouterr().out.splitlines()
    assert printed[6:] == ["", f"The rule (2. {check_loop.RULES[1]}): {check_loop.rule_text(2)}", "", check_loop.FAILED,
                           check_loop.NOT_PASSING_NOW]
    assert saved.read_text().splitlines() == ["not passing", check_loop.FELL_BACK] + printed[:6]
    assert agent.which_loop() == "not passed"
    # Once it says "not passing", a failing check leaves the file as it is.
    before = saved.read_text()
    assert check_loop.main([]) == 1
    assert check_loop.NOT_PASSING_NOW not in capsys.readouterr().out
    assert saved.read_text() == before
    # And passing again puts the agent back on the student's loop.
    a_loop(tmp_path, REFERENCE, monkeypatch)
    assert check_loop.main([]) == 0 and agent.which_loop() == "yours"



def printing(source, what):
    """The loop, printing `what` after each reply from the model."""
    old = '        messages.append({"role": "assistant", "content": response.content})\n'
    assert source.count(old) == 1
    return source.replace(old, old + f"        {what}\n")


IDS = 'print("ids:", [b.id for b in response.content if b.type == "tool_use"])'


def test_what_the_loop_printed_is_shown_for_the_first_failing_rule(tmp_path, monkeypatch,
                                                                     saved, capsys):
    # Steps are not counted, so rule 2 is the first to fail (and rule 5 fails too).
    a_loop(tmp_path, printing(broken(("                steps += 1\n", "")),
                              IDS + "; print('to stderr', file=sys.stderr)"), monkeypatch)
    source = check_loop.MY_LOOP.read_text().replace("import anthropic\n",
                                                    "import sys\n\nimport anthropic\n", 1)
    check_loop.MY_LOOP.write_text(source)
    assert check_loop.main([]) == 1
    printed = capsys.readouterr().out.splitlines()
    assert printed[1].startswith("NOT YET    2. ") and printed[4].startswith("NOT YET    5. ")
    assert printed[6:11] == ["", f"The rule (2. {check_loop.RULES[1]}): {check_loop.rule_text(2)}", "", check_loop.FAILED, ""]
    assert printed[11] == "What your loop printed during the made-up check for rule 2:"
    shown = printed[12:]
    # Only the made-up check for rule 2, whose tool ids carry its name; stderr too.
    assert shown[0] == "ids: ['toolu_lookups_11']"
    assert shown[1] == "to stderr"
    assert all("toolu_" not in line or "toolu_lookups_" in line for line in shown)
    assert len(shown) == 2 * 4       # four replies before its answer is accepted, two lines each
    assert not saved.exists()        # and nothing of it is saved


def test_what_the_loop_printed_is_not_shown_when_every_rule_passes(tmp_path, monkeypatch, saved,
                                                                  capsys):
    a_loop(tmp_path, printing(REFERENCE, IDS), monkeypatch)
    assert check_loop.main([]) == 0
    out = capsys.readouterr().out
    assert "ids:" not in out and "What your loop printed" not in out
    assert "ids:" not in saved.read_text()


def test_long_output_is_cut_to_40_lines(tmp_path, monkeypatch, capsys):
    a_loop(tmp_path, printing(broken(("system=system, ", "")),
                              "print('\\n'.join(f'line {i}' for i in range(30)))"), monkeypatch)
    assert check_loop.main([]) == 1
    out = capsys.readouterr().out
    shown = out.split("What your loop printed during the made-up check for rule 1:\n")[1]
    shown = shown.splitlines()
    # The made-up check for rule 1 gets three replies: 90 lines printed, 40 shown.
    assert shown[:40] == [f"line {i % 30}" for i in range(40)]
    assert shown[40:] == ["(50 more lines not shown)"]


def test_nothing_is_shown_when_the_loop_printed_nothing(tmp_path, monkeypatch, capsys):
    a_loop(tmp_path, broken(("system=system, ", "")), monkeypatch)
    assert check_loop.main([]) == 1
    assert "What your loop printed" not in capsys.readouterr().out


def test_a_failing_check_makes_no_file_when_there_was_none(tmp_path, monkeypatch, saved, capsys):
    a_loop(tmp_path, broken(("                steps += 1\n", "")), monkeypatch)
    assert check_loop.main([]) == 1
    assert not saved.exists() and not saved.parent.exists()
    assert check_loop.NOT_PASSING_NOW not in capsys.readouterr().out


def test_which_loop_follows_the_file(saved):
    """No file: the loop has never passed, so Part 0 runs the reference loop. "yours": the loop
    passed. Anything else (a loop that fails now, an old record of keeping the reference loop, a
    file that cannot be read) is a loop that has not passed, and no agent runs on it."""
    assert agent.which_loop() == "reference"           # no file
    saved.parent.mkdir(parents=True)
    for text, loop in (("yours\nok ...\n", "yours"), ("yours", "yours"),
                       ("reference\n", "not passed"), ("not passing\n", "not passed"), ("", "not passed"),
                       ("yours \n", "not passed"), ("Yours\n", "not passed"),
                       ("ok\nyours\n", "not passed")):
        saved.write_text(text)
        assert agent.which_loop() == loop, text
    saved.write_bytes(b"\xff\xfe\x00yours")              # not text
    assert agent.which_loop() == "not passed"
    saved.unlink()
    saved.mkdir()                                        # not a file
    assert agent.which_loop() == "not passed"


# ---------- fair to loops written differently ----------

# Correct loops organised differently from the reference loop, and from each other.
# The first asks the model in a nested helper function, stops through another, keeps a flag
# for the reminder and for the limit, checks the limit for the whole turn, and sends the
# reminder as a text block.
HELPERS = '''
import anthropic

from agent import (ACCEPTED, DECLINED, INSTRUCTIONS, MAX_REJECTED, MAX_STEPS, MODEL, NO_ANSWER,
                   OUT_OF_STEPS, RAN_OUT, REJECTED, REJECTED_TOO_OFTEN, REMINDED, REMINDER,
                   TOOLS, answer_problem, clean_answer, finish, run_tool)


def run_agent(claim, client=None, max_steps=MAX_STEPS, lookup=run_tool):
    client = client or anthropic.Anthropic()
    system = INSTRUCTIONS.read_text()
    messages = [{"role": "user", "content": f"Claim: {claim}"}]
    trace, read_so_far = [], []
    steps = 0
    rejected = 0
    told_limit = False
    reminded = False

    def ask():
        reply = client.messages.create(model=MODEL, max_tokens=16000, system=system,
                                       tools=TOOLS, messages=messages)
        messages.append({"role": "assistant", "content": reply.content})
        return reply

    def no_verdict(why):
        return finish(claim, None, [], why, trace, steps)

    while True:
        reply = ask()
        if reply.stop_reason == "refusal":
            return no_verdict(DECLINED)
        calls = [block for block in reply.content if block.type == "tool_use"]
        if not calls:
            if reminded:
                return no_verdict(NO_ANSWER)
            reminded = True
            trace.append({"tool": "(reminder)", "input": {}, "result": REMINDED})
            messages.append({"role": "user", "content": [{"type": "text", "text": REMINDER}]})
            continue
        reminded = False
        if told_limit and steps >= max_steps and any(c.name != "answer" for c in calls):
            return no_verdict(RAN_OUT)
        results = []
        for call in calls:
            if call.name == "answer":
                answer = clean_answer(call.input)
                problem = answer_problem(answer, read_so_far)
                if problem is None:
                    trace.append({"tool": "answer", "input": call.input, "result": ACCEPTED})
                    return finish(claim, answer["verdict"], answer["evidence"],
                                  answer["explanation"], trace, steps)
                rejected += 1
                trace.append({"tool": "answer", "input": call.input, "result": REJECTED + problem})
                if rejected >= MAX_REJECTED:
                    return no_verdict(REJECTED_TOO_OFTEN.format(n=rejected))
                content = REJECTED + problem
            elif steps >= max_steps:
                told_limit = True
                content = OUT_OF_STEPS.format(n=max_steps)
                trace.append({"tool": call.name, "input": call.input, "result": content})
            else:
                content = lookup(call.name, call.input)
                steps += 1
                trace.append({"tool": call.name, "input": call.input, "result": content})
                if call.name != "search":
                    read_so_far.append(content)
            results.append({"type": "tool_result", "tool_use_id": call.id, "content": content})
        messages.append({"role": "user", "content": results})
'''

# The second turns the reply into dicts for the conversation, counts quiet replies, keeps
# the results by call id and builds the user turn from them at the end, records the
# cleaned answer in the trace, and runs a bounded number of turns.
BY_ID = '''
import anthropic

from agent import (ACCEPTED, DECLINED, INSTRUCTIONS, MAX_REJECTED, MAX_STEPS, MODEL, NO_ANSWER,
                   OUT_OF_STEPS, RAN_OUT, REJECTED, REJECTED_TOO_OFTEN, REMINDED, REMINDER,
                   TOOLS, answer_problem, clean_answer, finish, run_tool)


def run_agent(claim, client=None, max_steps=MAX_STEPS, lookup=run_tool):
    client = client or anthropic.Anthropic()
    system = INSTRUCTIONS.read_text()
    messages = [{"role": "user", "content": f"Claim: {claim}"}]
    trace, read_so_far = [], []
    steps = 0
    rejected = 0
    warned_on = None
    quiet = 0

    for turn in range(100):
        response = client.messages.create(model=MODEL, max_tokens=16000, system=system,
                                          tools=TOOLS, messages=messages)
        messages.append({"role": "assistant",
                         "content": [block.model_dump() for block in response.content]})
        calls = [block for block in response.content if block.type == "tool_use"]
        if response.stop_reason == "refusal":
            return finish(claim, None, [], DECLINED, trace, steps)
        if not calls:
            quiet += 1
            if quiet == 2:
                return finish(claim, None, [], NO_ANSWER, trace, steps)
            trace.append({"tool": "(reminder)", "input": {}, "result": REMINDED})
            messages.append({"role": "user", "content": REMINDER})
            continue
        quiet = 0
        sent = {}
        for call in calls:
            if call.name == "answer":
                answer = clean_answer(call.input)
                problem = answer_problem(answer, read_so_far)
                if not problem:
                    trace.append({"tool": "answer", "input": answer, "result": ACCEPTED})
                    return finish(claim, answer["verdict"], answer["evidence"],
                                  answer["explanation"], trace, steps)
                rejected = rejected + 1
                trace.append({"tool": "answer", "input": answer, "result": REJECTED + problem})
                if rejected == MAX_REJECTED:
                    return finish(claim, None, [], REJECTED_TOO_OFTEN.format(n=rejected),
                                  trace, steps)
                sent[call.id] = REJECTED + problem
            elif steps < max_steps:
                found = lookup(call.name, call.input)
                steps = steps + 1
                trace.append({"tool": call.name, "input": call.input, "result": found})
                if call.name in ("read", "wikidata"):
                    read_so_far.append(found)
                sent[call.id] = found
            elif warned_on is not None and warned_on < turn:
                return finish(claim, None, [], RAN_OUT, trace, steps)
            else:
                warned_on = turn
                sent[call.id] = OUT_OF_STEPS.format(n=max_steps)
                trace.append({"tool": call.name, "input": call.input, "result": sent[call.id]})
        messages.append({"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": call_id, "content": result}
            for call_id, result in sent.items()]})
    return finish(claim, None, [], RAN_OUT, trace, steps)
'''


# The third asks the model through a helper function at the top of the file, which is given
# the client, the system text and the conversation, and checks answers in another.
MODULE_HELPERS = '''
import anthropic

from agent import (ACCEPTED, DECLINED, INSTRUCTIONS, MAX_REJECTED, MAX_STEPS, MODEL, NO_ANSWER,
                   OUT_OF_STEPS, RAN_OUT, REJECTED, REJECTED_TOO_OFTEN, REMINDED, REMINDER,
                   TOOLS, answer_problem, clean_answer, finish, run_tool)


def ask(client, system, messages):
    return client.messages.create(model=MODEL, max_tokens=16000, system=system, tools=TOOLS,
                                  messages=messages)


def checked(call, read_so_far):
    answer = clean_answer(call.input)
    return answer, answer_problem(answer, read_so_far)


def run_agent(claim, client=None, max_steps=MAX_STEPS, lookup=run_tool):
    client = client or anthropic.Anthropic()
    system = INSTRUCTIONS.read_text()
    messages = [{"role": "user", "content": f"Claim: {claim}"}]
    trace, read_so_far = [], []
    steps = 0
    rejected = 0
    warned = False
    quiet = False

    while True:
        reply = ask(client, system, messages)
        messages.append({"role": "assistant", "content": reply.content})
        if reply.stop_reason == "refusal":
            return finish(claim, None, [], DECLINED, trace, steps)
        calls = [block for block in reply.content if block.type == "tool_use"]
        if not calls:
            if quiet:
                return finish(claim, None, [], NO_ANSWER, trace, steps)
            quiet = True
            trace.append({"tool": "(reminder)", "input": {}, "result": REMINDED})
            messages.append({"role": "user", "content": REMINDER})
            continue
        quiet = False
        warned_last_turn = warned
        results = []
        for call in calls:
            if call.name == "answer":
                answer, problem = checked(call, read_so_far)
                if problem is None:
                    trace.append({"tool": "answer", "input": call.input, "result": ACCEPTED})
                    return finish(claim, answer["verdict"], answer["evidence"],
                                  answer["explanation"], trace, steps)
                rejected += 1
                result = REJECTED + problem
                trace.append({"tool": "answer", "input": call.input, "result": result})
                if rejected >= MAX_REJECTED:
                    return finish(claim, None, [], REJECTED_TOO_OFTEN.format(n=rejected),
                                  trace, steps)
            elif steps >= max_steps:
                if warned_last_turn:
                    return finish(claim, None, [], RAN_OUT, trace, steps)
                warned = True
                result = OUT_OF_STEPS.format(n=max_steps)
                trace.append({"tool": call.name, "input": call.input, "result": result})
            else:
                result = lookup(call.name, call.input)
                steps += 1
                trace.append({"tool": call.name, "input": call.input, "result": result})
                if call.name != "search":
                    read_so_far.append(result)
            results.append({"type": "tool_result", "tool_use_id": call.id, "content": result})
        messages.append({"role": "user", "content": results})
'''


@pytest.mark.parametrize("source", [HELPERS, BY_ID, MODULE_HELPERS,
                                    broken(("for call in calls:", "for call in reversed(calls):"))],
                         ids=["nested-helpers", "by-id", "module-helpers", "calls-in-reverse"])
def test_loops_written_differently_pass_every_rule(tmp_path, source):
    assert check_loop.check(a_loop(tmp_path, source)) == [None] * 6


@pytest.mark.parametrize("name, value", [("MAX_STEPS", 3), ("MAX_STEPS", 30),
                                         ("MAX_REJECTED", 1), ("MAX_REJECTED", 6),
                                         ("answer_problem", lambda answer, read_so_far: None)])
def test_a_change_to_agent_py_in_part_3_does_not_fail_a_correct_loop(tmp_path, monkeypatch,
                                                                    name, value):
    # Part 3 lets the student change agent.py, the limit of lookups above all.
    monkeypatch.setattr(agent, name, value)
    assert check_loop.check(a_loop(tmp_path, REFERENCE)) == [None] * 6
    assert check_loop.check(a_loop(tmp_path, BY_ID)) == [None] * 6


def renamed(source, *names):
    for name in names:
        source = re.sub(rf"\b{name}\b", f"my_{name}", source)
    return source


def test_a_complete_loop_with_other_names_for_the_set_up_variables_passes(tmp_path):
    # The check looks inside run_agent() only for a loop that does not stop yet.
    source = renamed(REFERENCE, "steps", "trace", "read_so_far")
    assert "my_steps += 1" in source and "max_steps" in source
    assert check_loop.check(a_loop(tmp_path, source)) == [None] * 6


def test_an_error_about_the_client_names_the_scripted_model(tmp_path):
    source = broken(("response = client.messages.create(", "response = client.messages.stream("))
    assert "AttributeError: 'ScriptedModel' object has no attribute 'stream'" in \
        check_loop.check(a_loop(tmp_path, source))[0]


# Rules 1 to 3 and nothing more: the page suggests writing these first and running the check.
FIRST_THREE = REFERENCE[:REFERENCE.index("    while True:")] + '''    while True:
        response = client.messages.create(model=MODEL, max_tokens=16000, system=system,
                                          tools=TOOLS, messages=messages)
        messages.append({"role": "assistant", "content": response.content})
        results = []
        for call in [block for block in response.content if block.type == "tool_use"]:
            result = lookup(call.name, call.input)
            steps += 1
            trace.append({"tool": call.name, "input": call.input, "result": result})
            if call.name != "search":
                read_so_far.append(result)
            results.append({"type": "tool_result", "tool_use_id": call.id, "content": result})
        messages.append({"role": "user", "content": results})
'''


def test_rules_1_to_3_can_pass_before_the_loop_can_stop(tmp_path):
    assert shown(a_loop(tmp_path, FIRST_THREE)) == [
        "ok         1. Ask the model",
        "ok         2. Run its lookups",
        "ok         3. Send the results back",
        "NOT YET    4. Check the answer: the model's second reply gave an answer that quotes the "
        "page it had read, and your loop ran it as a lookup.",
        "NOT YET    5. Enforce the limit: the model's third reply asked for a third search with "
        "the limit of 2 lookups reached, and your loop made it: it had made 2 lookups before that "
        "one; in another made-up check the model asked for one search in each of 6 replies, and "
        "your loop made all 6 and never sent back the warning.",
        "NOT YET    6. Stop when the model stops: the model's first reply had text and no tool "
        "call, and your loop asked the model again without sending it the reminder ('Please "
        "finish by calling answer().').",
    ]


# A half-written loop does not stop, so rule 2 looks inside run_agent() for it.
HALF_BROKEN = {
    "steps not counted": (2, [("            steps += 1\n", "")],
                          "after the model's first reply, your loop had made one lookup, and "
                          "its count of lookups was 0 when it asked the model again"),
    "search kept": (2, [('if call.name != "search":', "if True:")],
                    "the model's first reply asked for a search, and what the search found was "
                    "counted as read by the agent when your loop asked the model again"),
    "steps renamed": (2, [], "the check could not find `steps` in run_agent(): keep the names "
                             "of the set-up lines at the top of the function"),
}


@pytest.mark.parametrize("name", HALF_BROKEN)
def test_a_half_written_loop_is_checked_from_inside(tmp_path, name):
    rule, edits, problem = HALF_BROKEN[name]
    source = FIRST_THREE
    for old, new in edits:
        assert source.count(old) == 1, old
        source = source.replace(old, new)
    if name.endswith("renamed"):
        source = renamed(source, name.split()[0])
    problems = check_loop.check(a_loop(tmp_path, source))
    assert problems[:rule - 1] == [None] * (rule - 1)
    assert problems[rule - 1] == problem
    assert problems.count(problem) == 1      # said once, on the first rule that needed it


# ---------- one broken loop per rule, and what each line says ----------

EXPLANATION_LINE = 1 + REFERENCE[:REFERENCE.index('answer["explanation"]')].count("\n")
REFUSAL = ('        if response.stop_reason == "refusal":\n'
           '            return finish(claim, None, [], DECLINED, trace, steps)\n')
BROKEN = {
    "no assistant turn": (1, [('        messages.append({"role": "assistant", '
                               '"content": response.content})\n', "")],
                          ["the model's first reply asked for a search, and the next request "
                           "your loop sent did not have that reply in the conversation"]),
    "reply added twice": (1, [('        messages.append({"role": "assistant", "content": response.content})\n',
                               '        messages.append({"role": "assistant", "content": response.content})\n' * 2)],
                          ["the model's first reply asked for a search, and the next request "
                           "your loop sent had that reply in the conversation two times"]),
    "text block dropped": (1, [('"content": response.content}',
                                '"content": [b for b in response.content if b.type == "tool_use"]}')],
                           ["the model's first reply asked for a search, and the next request "
                            "your loop sent had that reply in the conversation with parts of it "
                            "missing or changed"]),
    "no system text": (1, [("system=system, ", "")], ["the first request your loop sent the "
                                                      "model did not have the text of "
                                                      "instructions.md as its system text"]),
    "wrong model": (1, [("model=MODEL,", "model='claude-opus-5-5',")],
                    ["the first request your loop sent the model named the model "
                     "'claude-opus-5-5', not 'claude-haiku-5-5'"]),
    "only the newest turn": (1, [("messages=messages,", "messages=messages[-2:],")],
                             ["the model's first reply asked for a search, and the next request "
                              "your loop sent did not hold the whole conversation so far"]),
    "steps not counted": (2, [("                steps += 1\n", "")],
                          ["the model asked for four lookups before its answer, and when your "
                           "loop stopped its count of lookups was 0"]),
    "search kept": (2, [('if call.name != "search":', "if True:")],
                    ["the model's first reply asked for a search, and what the search found was "
                     "counted as read by the agent when your loop checked the answer"]),
    "read not kept": (2, [("                    read_so_far.append(result)\n",
                           "                    pass\n")],
                      ["the model's second reply asked for a read, and what the read found was "
                       "not counted as read by the agent when your loop checked the answer"]),
    "lookup not in the trace": (2, [('            trace.append({"tool": call.name, "input": '
                                     'call.input, "result": result})\n', "")],
                                ["the model's first reply asked for a search, and the trace "
                                 "your loop stopped with had no entry for the search"]),
    "only the first call": (2, [("for call in calls:", "for call in calls[:1]:")],
                            ["the model's third reply asked for a wikidata lookup and a read, "
                             "and your loop made the wikidata lookup only, then asked the model "
                             "again without making the read"]),
    "results not sent": (3, [('        messages.append({"role": "user", "content": results})\n', "")],
                         ["the model's first reply asked for a search and a read, and the next "
                          "request your loop sent ended with that reply: the results for it had "
                          "not been sent"]),
    "wrong id": (3, [('"tool_use_id": call.id', '"tool_use_id": calls[0].id')],
                 ["the model's first reply asked for a search and a read, and the next request "
                  "your loop sent held two results for the search"]),
    "a result as a list": (3, [('"tool_use_id": call.id, "content": result}',
                                '"tool_use_id": call.id, "content": [{"type": "text", "text": result}]}')],
                           ["the model's first reply asked for a search and a read, and the "
                            "result given for the search was a list rather than text"]),
    "a refused lookup gets no result": (3, [("                warned = True\n",
                                             "                warned = True\n                continue\n")],
                                        ["the model's third reply asked for a third search, and "
                                         "the next request your loop sent held no result for "
                                         "the search"]),
    "a rejected answer gets no result": (3, [
        ('            results.append({"type": "tool_result", "tool_use_id": call.id, "content": result})\n',
         '            if call.name != "answer":\n'
         '                results.append({"type": "tool_result", "tool_use_id": call.id, '
         '"content": result})\n')],
        ["the model's second reply gave an answer with a quote that is in nothing it had read, "
         "and the next request your loop sent held no result for the answer"]),
    "a turn per result": (3, [('            results.append({"type": "tool_result", '
                               '"tool_use_id": call.id, "content": result})\n',
                               '            messages.append({"role": "user", "content": [{"type": '
                               '"tool_result", "tool_use_id": call.id, "content": result}]})\n'),
                              ('        messages.append({"role": "user", "content": results})\n', "")],
                          ["the model's first reply asked for a search and a read, and your "
                           "loop sent the results for that reply in two separate turns, where "
                           "the model is sent them all together, once every call in the reply "
                           "has its result"]),
    "answer not cleaned": (4, [("answer = clean_answer(call.input)", "answer = call.input")],
                           ["the model's second reply gave an answer with its evidence as one "
                            "string and no explanation, and your loop stopped with an error at "
                            "line 53 of my_loop.py: KeyError: 'explanation'"]),
    "one rejection too many": (4, [("rejected >= MAX_REJECTED", "rejected > MAX_REJECTED")],
                               ["the model's first three replies were answers with a quote that "
                                "is in nothing it had read, and your loop asked the model again "
                                "after the third was rejected"]),
    "rejection without REJECTED": (4, [("result = REJECTED + problem", "result = problem")],
                                   ["the model's second reply gave an answer with a quote that "
                                    "is in nothing it had read, and your loop sent back 'These "
                                    "quotes are not in anything you read in this check: "
                                    "Zemeckis was born in Ohio.' rather than what the evidence "
                                    "check said was wrong"]),
    "evidence left out": (4, [('return finish(claim, answer["verdict"], answer["evidence"],',
                               'return finish(claim, answer["verdict"], [],')],
                          ["the model's second reply gave an answer that quotes the page it had "
                           "read, and your loop stopped with the evidence [], where this case "
                           "ends with the evidence ['directed by Robert Zemeckis']"]),
    "lookups only in the trace": (4, [
        ('                    trace.append({"tool": "answer", "input": call.input, "result": ACCEPTED})\n', ""),
        ('                    trace.append({"tool": "answer", "input": call.input, "result": result})\n', ""),
        ('            trace.append({"tool": call.name, "input": call.input, "result": result})\n', ""),
        ("                result = lookup(call.name, call.input)\n",
         "                result = lookup(call.name, call.input)\n"
         '                trace.append({"tool": call.name, "input": call.input, "result": result})\n')],
        ["the model's second reply gave an answer that quotes the page it had read, and the "
         "trace your loop stopped with does not record that answer as accepted"]),
    "a rejected answer not in the trace": (4, [
        ('            trace.append({"tool": call.name, "input": call.input, "result": result})\n',
         '            if call.name != "answer":\n'
         '                trace.append({"tool": call.name, "input": call.input, "result": result})\n')],
        ["the model's second reply gave an answer with a quote that is in nothing it had read, "
         "and the trace your loop stopped with has no entry for it with what was sent back"]),
    "a refused lookup not in the trace": (5, [
        ("                result = OUT_OF_STEPS.format(n=max_steps)\n                warned = True\n",
         "                warned = True\n"
         '                results.append({"type": "tool_result", "tool_use_id": call.id,\n'
         '                                "content": OUT_OF_STEPS.format(n=max_steps)})\n'
         "                continue\n")],
        ["the model's third reply asked for a third search with the limit of 2 lookups reached, "
         "and the trace your loop stopped with has no entry for it with what was sent back"]),
    "the limit is MAX_STEPS": (5, [("elif steps >= max_steps:", "elif steps >= MAX_STEPS:")],
                               ["the model's third reply asked for a third search with the "
                                "limit of 2 lookups reached, and your loop made it: it had made "
                                "2 lookups before that one; in another made-up check the model "
                                "asked for one search in each of 6 replies, and your loop made "
                                "all 6 and never sent back the warning"]),
    "stops at once": (5, [("if warned_before:", "if True:")],
                      ["the model's third reply asked for a third search with the limit of 2 "
                       "lookups reached, and your loop stopped instead of sending back the "
                       "warning: it had made 2 lookups, the limit, and this was the first time "
                       "the model asked for one more"]),
    # A limit reached one lookup late, and one reached one lookup early: the numbers in the
    # sentence tell them apart from a limit that is never checked.
    "the limit checked one late": (5, [("elif steps >= max_steps:", "elif steps > max_steps:")],
                                   ["the model's third reply asked for a third search with the "
                                    "limit of 2 lookups reached, and your loop made it: it had "
                                    "made 2 lookups before that one; in another made-up check "
                                    "the model asked for one search in each of 6 replies, and "
                                    "your loop first sent back the warning for the fourth "
                                    "search, when it had made 3 lookups"]),
    "the limit checked one early": (5, [("elif steps >= max_steps:",
                                         "elif steps >= max_steps - 1:")],
                                    ["the model's second reply asked for a second search, and "
                                     "your loop sent back the warning instead of making it, "
                                     "though it had made only 1 lookup and the limit is 2"]),
    "never stops at the limit": (5, [("if warned_before:", "if False:")],
                                 ["the model's fourth reply asked for a fourth search after the "
                                  "warning had been sent back, and your loop asked the model "
                                  "again instead of stopping: it had made 2 lookups, the limit, "
                                  "and for that search it sent back the warning again"]),
    "no reminder": (6, [('            trace.append({"tool": "(reminder)"',
                         '            return finish(claim, None, [], NO_ANSWER, trace, steps)\n'
                         '            trace.append({"tool": "(reminder)"')],
                    ["the model's first reply had text and no tool call, and your loop stopped "
                     "instead of reminding the model to answer"]),
    "a break out of the while loop": (6, [
        ('            trace.append({"tool": "(reminder)", "input": {}, "result": REMINDED})\n',
         '            break\n'
         '            trace.append({"tool": "(reminder)", "input": {}, "result": REMINDED})\n')],
        ["the model's first reply had text and no tool call, and your loop ended without an "
         "answer or a verdict (it returned nothing) instead of reminding the model to answer"]),
    # The limit is reached, then one reply asks for two lookups: each must get OUT_OF_STEPS.
    "the first lookup at the limit warns, the second stops": (5, [
        ("                if warned_before:\n", "                if warned:\n")],
        ["the model's third reply asked for a search and a read in one reply, with the limit of "
         "2 lookups reached, and your loop stopped, with the explanation 'The agent ran out of "
         "steps.', instead of sending back the warning for each of the two"]),
    "the second lookup at the limit gets no result": (3, [
        ("                result = OUT_OF_STEPS.format(n=max_steps)\n",
         "                if warned:\n                    continue\n"
         "                result = OUT_OF_STEPS.format(n=max_steps)\n")],
        ["the model's third reply asked for a search and a read in one reply, and the next "
         "request your loop sent held no result for the read"]),
    "reminds forever": (6, [('            if trace and trace[-1]["tool"] == "(reminder)":\n'
                             '                return finish(claim, None, [], NO_ANSWER, trace, '
                             'steps)\n', "")],
                        ["the model's second reply had text and no tool call again, and your "
                         "loop asked the model a third time instead of stopping"]),
    "refusal not stopped": (6, [(REFUSAL, "")],
                            ["the model's first reply refused to check the claim, and your loop "
                             "asked the model again instead of stopping"]),
}


@pytest.mark.parametrize("name", BROKEN)
def test_a_broken_loop_fails_its_rule_and_says_what_happened(tmp_path, name):
    rule, edits, phrases = BROKEN[name]
    printed = shown(a_loop(tmp_path, broken(*edits)))
    first = next(i for i, line in enumerate(printed, 1) if line.startswith("NOT YET"))
    assert first == rule, printed
    line = printed[rule - 1]
    assert line.startswith(f"NOT YET    {rule}. {check_loop.RULES[rule - 1]}: ")
    for phrase in phrases:
        assert phrase in line, line
    assert line.endswith(".") and "\n" not in line


# A student's loop that stopped at the second lookup of one reply at the limit, and the same
# student's fix: a flag for "a lookup was refused in this reply", turned into "warned" only
# after the whole reply is handled.
STUDENT_GAP = """
import anthropic

from agent import (ACCEPTED, DECLINED, INSTRUCTIONS, MAX_REJECTED, MAX_STEPS, MODEL, NO_ANSWER,
                   OUT_OF_STEPS, RAN_OUT, REJECTED, REJECTED_TOO_OFTEN, REMINDED, REMINDER,
                   TOOLS, answer_problem, clean_answer, finish, run_tool)


def run_agent(claim, client=None, max_steps=MAX_STEPS, lookup=run_tool):
    client = client or anthropic.Anthropic()
    system = INSTRUCTIONS.read_text()
    messages = [{"role": "user", "content": f"Claim: {claim}"}]
    trace, read_so_far = [], []
    steps = 0
    rejected = 0

    warned = False
    reminded = False
    while True:
        reply = client.messages.create(model=MODEL, max_tokens=16000, system=system,
                                       tools=TOOLS, messages=messages)
        messages.append({"role": "assistant", "content": reply.content})
        if reply.stop_reason == "refusal":
            return finish(claim, None, [], DECLINED, trace, steps)
        tool_calls = [block for block in reply.content if block.type == "tool_use"]
        if len(tool_calls) == 0:
            if reminded:
                return finish(claim, None, [], NO_ANSWER, trace, steps)
            reminded = True
            trace.append({"tool": "(reminder)", "input": {}, "result": REMINDED})
            messages.append({"role": "user", "content": REMINDER})
            continue
        results = []
        for call in tool_calls:
            if call.name == "answer":
                answer = clean_answer(call.input)
                problem = answer_problem(answer, read_so_far)
                if problem is None:
                    trace.append({"tool": call.name, "input": call.input, "result": ACCEPTED})
                    return finish(claim, answer["verdict"], answer["evidence"],
                                  answer["explanation"], trace, steps)
                rejected += 1
                trace.append({"tool": call.name, "input": call.input, "result": REJECTED + problem})
                if rejected >= MAX_REJECTED:
                    return finish(claim, None, [], REJECTED_TOO_OFTEN.format(n=rejected),
                                  trace, steps)
                results.append({"type": "tool_result", "tool_use_id": call.id,
                                "content": REJECTED + problem})
                continue
            if steps >= max_steps:
                if warned:
                    return finish(claim, None, [], RAN_OUT, trace, steps)
                warned = True
                out = OUT_OF_STEPS.format(n=max_steps)
                trace.append({"tool": call.name, "input": call.input, "result": out})
                results.append({"type": "tool_result", "tool_use_id": call.id, "content": out})
                continue
            result = lookup(call.name, call.input)
            steps += 1
            trace.append({"tool": call.name, "input": call.input, "result": result})
            if call.name == "read" or call.name == "wikidata":
                read_so_far.append(result)
            results.append({"type": "tool_result", "tool_use_id": call.id, "content": result})
        messages.append({"role": "user", "content": results})
"""
STUDENT_FIXED = (STUDENT_GAP
                 .replace("        results = []\n",
                          "        results = []\n        refused_this_turn = False\n")
                 .replace("                warned = True\n", "                refused_this_turn = True\n")
                 .replace('        messages.append({"role": "user", "content": results})\n',
                          "        if refused_this_turn:\n            warned = True\n"
                          '        messages.append({"role": "user", "content": results})\n'))


def test_a_loop_that_stops_at_the_second_lookup_of_one_reply_at_the_limit_is_not_yet(tmp_path):
    problems = check_loop.check(a_loop(tmp_path, STUDENT_GAP))
    assert problems[:4] == [None] * 4                               # rules 1 to 4 pass
    assert problems[5] == STALL     # its reminder memory is never reset, which the stall case finds
    assert problems[4] == (
        "the model's third reply asked for a search and a read in one reply, with the limit of 2 "
        "lookups reached, and your loop stopped, with the explanation 'The agent ran out of "
        "steps.', instead of sending back the warning for each of the two")


# A second, separate stall must be reminded again. These students'
# loops set their reminder memory and never reset it, which the check did not find before.
STALL = ("the model's first reply asked for nothing and your loop reminded it, its second reply asked "
        "for a search, and its third reply asked for nothing again; your loop stopped there instead "
        "of reminding the model again")


def test_the_students_fixed_loop_passes_rule_5_and_meets_the_stall_case(tmp_path):
    assert STUDENT_FIXED.count("refused_this_turn") == 3
    assert check_loop.check(a_loop(tmp_path, STUDENT_FIXED)) == [None] * 5 + [STALL]
    reset = STUDENT_FIXED.replace("        results = []\n",
                                  "        reminded = False\n        results = []\n")
    assert check_loop.check(a_loop(tmp_path, reset)) == [None] * 6


# ---------- loops written with the parts in loop_parts.py ----------

def kit(*edits):
    """The reference loop written with the parts, with each (old, new) edit made once."""
    source = KIT_REFERENCE
    for old, new in edits:
        assert source.count(old) == 1, old
        source = source.replace(old, new)
    return source


def test_the_reference_loop_with_the_parts_does_what_the_old_one_did(tmp_path):
    """On every made-up check: the same requests to the model, the same lookups, the same end
    and the same result as the reference loop written straight against the API."""
    def record(source):
        path = str(a_loop(tmp_path, source).resolve())
        module = check_loop.load(path)
        seen = {}
        with check_loop.offline(), check_loop.watching_answer_checks(module):
            for key in check_loop.SCENARIOS:
                run = check_loop.Run(key, module.run_agent, path)
                requests = [[{**turn, "content": [check_loop.view(b) if not isinstance(b, dict)
                                                  else b for b in turn["content"]]}
                             if isinstance(turn.get("content"), list) else turn
                             for turn in request["messages"]] for request in run.requests]
                seen[key] = (requests, run.lookups, run.ended, run.result, run.checked)
        return seen
    assert record(KIT_REFERENCE) == record(REFERENCE)
    assert check_loop.check(a_loop(tmp_path, KIT_REFERENCE)) == [None] * 6


KIT_LIMIT = """            elif steps >= max_steps:
                if warned_before:
                    # It was told on an earlier reply that it was out of lookups: stop here.
                    return talk.stop(RAN_OUT, steps)
                talk.give(call, OUT_OF_STEPS.format(n=max_steps))
                warned = True
            else:
                talk.give(call, talk.run(call))
                steps += 1
"""
KIT_WRONG = {
    "handles only the first call": (2, [("for call in reply.calls:",
                                         "for call in reply.calls[:1]:")],
        "the model's third reply asked for a wikidata lookup and a read, and your loop made the "
        "wikidata lookup only, then asked the model again without making the read."),
    "no result for an answer sent back": (3, [("                talk.give(call, problem)\n", "")],
        "the model's second reply gave an answer with a quote that is in nothing it had read, "
        "and the next request your loop sent held no result for the answer."),
    "results sent inside the for loop": (3, [("""                steps += 1
        talk.send_results()
""", """                steps += 1
            talk.send_results()
""")],
        "the model's first reply asked for a search and a read, and your loop sent the results "
        "for that reply in two separate turns, where the model is sent them all together, once "
        "every call in the reply has its result."),
    "the limit checked after running the lookup": (5, [(KIT_LIMIT, """            else:
                found = talk.run(call)
                steps += 1
                if steps > max_steps:
                    if warned_before:
                        return talk.stop(RAN_OUT, steps)
                    talk.give(call, OUT_OF_STEPS.format(n=max_steps))
                    warned = True
                else:
                    talk.give(call, found)
""")],
        "the model's third reply asked for a third search with the limit of 2 lookups reached, "
        "and your loop made it: it had made 2 lookups before that one; in another made-up check "
        "the model asked for one search in each of 6 replies, and your loop first sent back the "
        "warning for the third search, which it also made."),
    "stops at the limit without the warning": (5, [("""                if warned_before:
                    # It was told on an earlier reply that it was out of lookups: stop here.
                    return talk.stop(RAN_OUT, steps)
                talk.give(call, OUT_OF_STEPS.format(n=max_steps))
                warned = True
""", """                return talk.stop(RAN_OUT, steps)
""")],
        "the model's third reply asked for a third search with the limit of 2 lookups reached, "
        "and your loop stopped instead of sending back the warning: it had made 2 lookups, the "
        "limit, and this was the first time the model asked for one more."),
    "checks the limit once per reply": (5, [
        ("        warned_before = warned\n",
         "        warned_before = warned\n        over = steps >= max_steps\n"),
        ("            elif steps >= max_steps:", "            elif over:")],
        "the model's second reply asked for a search and a read in one reply, when your loop "
        "had made 1 lookup and the limit is 2, so one more lookup was allowed, and your loop "
        "made both, the second as lookup number 3."),
    "reminder memory never reset": (6, [("        reminded = False\n\n", "\n")],
        "the model's first reply asked for nothing and your loop reminded it, its second reply "
        "asked for a search, and its third reply asked for nothing again; your loop stopped "
        "there instead of reminding the model again."),
    "reminds again and again": (6, [("""            if reminded:
                return talk.stop(NO_ANSWER, steps)
""", "")],
        "the model's second reply had text and no tool call again, and your loop asked the "
        "model a third time instead of stopping."),
    "sends results after the reminder too": (6, [("""            reminded = True
            continue
""", """            reminded = True
""")],
        "the model's first reply had text and no tool call, and your loop sent the model the "
        "reminder and also an empty turn of results, where the reminder is all it is sent."),
}


@pytest.mark.parametrize("name", KIT_WRONG)
def test_a_wrong_loop_with_the_parts_gets_a_sentence_about_what_it_did(tmp_path, name):
    rule, edits, sentence = KIT_WRONG[name]
    printed = shown(a_loop(tmp_path, kit(*edits)))
    first = next(i for i, line in enumerate(printed, 1) if line.startswith("NOT YET"))
    assert first == rule, printed
    assert printed[rule - 1] == f"NOT YET    {rule}. {check_loop.RULES[rule - 1]}: {sentence}"


def test_stopping_on_the_last_failed_answer_before_giving_it_a_result_passes(tmp_path):
    """The parts record every answer when it is checked, so a loop that stops on the third failed
    answer before giving it a result still leaves a complete trace, and passes."""
    source = kit(("""                talk.give(call, problem)
                rejected += 1
                if rejected >= MAX_REJECTED:
                    return talk.stop(REJECTED_TOO_OFTEN.format(n=rejected), steps)
""", """                rejected += 1
                if rejected >= MAX_REJECTED:
                    return talk.stop(REJECTED_TOO_OFTEN.format(n=rejected), steps)
                talk.give(call, problem)
"""))
    assert check_loop.check(a_loop(tmp_path, source)) == [None] * 6


def test_the_parts_record_each_answer_once_whatever_the_order(tmp_path):
    """With the parts, the trace has one entry for each answer checked: give() for an answer sets
    only what is sent back. The guard on the count stays in the check, for loops written without
    the parts."""
    import loop_parts
    trace = []
    talk = loop_parts.Conversation("c", None, "", [], trace, [], None)
    block = type("Block", (), {"name": "answer", "id": "a1", "type": "tool_use",
                               "input": {"verdict": "supported", "evidence": ["nowhere"],
                                         "explanation": "x"}})()
    call = loop_parts.Call(block)
    problem = talk.problem_with(call)
    assert problem.startswith(agent.REJECTED) and len(trace) == 1
    talk.give(call, problem)
    assert len(trace) == 1 and talk.results[0]["content"] == problem
    assert trace[0] == {"tool": "answer", "input": block.input, "result": problem}


def test_a_loop_written_before_the_parts_still_passes_in_the_new_my_loop(tmp_path):
    """A student who started 1a before it changed wrote Python against the old starter file. Their
    loop, below the line of the new my_loop.py, must still pass: the new file imports every name
    the old one did."""
    skeleton = (ROOT / "my_loop.py").read_text()
    marker = '    raise NotImplementedError("The loop is not written yet: see step 1a.")\n'
    assert skeleton.count(marker) == 1
    body = REFERENCE[REFERENCE.index("    warned = False"):]
    assert check_loop.check(a_loop(tmp_path, skeleton.replace(marker, body))) == [None] * 6


def test_every_broken_rule_is_covered():
    assert {rule for rule, _, _ in BROKEN.values()} == set(range(1, 7))


# ---------- the token line: the extra credit in step 3b ----------

# The instructor, Nov 11: "have it gone entirely. for the extra credit we can have the student go
# back and add it?" The reference loop with the count added as step 3b asks: a tokens dict, each
# reply's usage added to it, and tokens passed to finish() as its last argument.
TOKENS = ('        tokens["input"] += response.usage.input_tokens\n'
          '        tokens["output"] += response.usage.output_tokens\n')
TURN = '        messages.append({"role": "assistant", "content": response.content})\n'
COUNTING = broken(("    steps = 0\n", '    tokens = {"input": 0, "output": 0}\n    steps = 0\n'),
                  (TURN, TOKENS + TURN)).replace("trace, steps)", "trace, steps, tokens)")
TOKEN_LINE = f"ok         {agent.TOKEN_RULE}"


def counting(*edits):
    source = COUNTING
    for old, new in edits:
        assert source.count(old) == 1, old
        source = source.replace(old, new)
    return source


def test_a_loop_that_counts_tokens_gets_the_token_line_and_turns_on_cost(tmp_path, monkeypatch, saved,
                                                                       capsys):
    assert COUNTING.count("trace, steps, tokens)") == 5
    a_loop(tmp_path, COUNTING, monkeypatch)
    assert check_loop.main([]) == 0
    printed = capsys.readouterr().out.splitlines()
    assert printed == [f"ok         {n}. {title}" for n, title in enumerate(check_loop.RULES, 1)] \
        + [TOKEN_LINE, "", check_loop.PASSED]
    assert saved.read_text().splitlines() == ["yours"] + printed
    assert agent.which_loop() == "yours" and agent.counts_tokens()
    # Without the count again, the loop still passes, and tokens and cost are hidden again.
    a_loop(tmp_path, REFERENCE, monkeypatch)
    assert check_loop.main([]) == 0 and not agent.counts_tokens()


def test_a_loop_written_with_the_old_order_of_finish_still_counts(tmp_path):
    """Before Nov 12, finish() took tokens, then steps. A loop written then still passes."""
    old = COUNTING.replace("trace, steps, tokens)", "trace, tokens, steps)")
    assert check_loop.check(a_loop(tmp_path, old)) == [None] * 7
    assert agent.finish("c", None, [], "x", [], {"input": 2, "output": 1}, 3)["steps"] == 3


TOKEN_BROKEN = {
    "no tokens": ([(TOKENS, "")],
                  ["your loop stopped with tokens {'input': 0, 'output': 0}",
                   "where its three replies used 4,266 input and 132 output tokens"]),
    "output not counted": ([('        tokens["output"] += response.usage.output_tokens\n', "")],
                           ["stopped with tokens {'input': 4266, 'output': 0}"]),
    "refusal tokens not counted": ([(TOKENS + TURN, TURN), (REFUSAL.replace("steps)", "steps, tokens)"),
                                                            REFUSAL.replace("steps)", "steps, tokens)") + TOKENS)],
                                   ["refused to check the claim", "stopped with tokens"]),
    "one result without them": ([("DECLINED, trace, steps, tokens)", "DECLINED, trace, steps)")],
                                ["refused to check the claim", "stopped with tokens None"]),
}


@pytest.mark.parametrize("name", TOKEN_BROKEN)
def test_a_wrong_count_fails_the_token_line_and_nothing_else(tmp_path, monkeypatch, saved, capsys, name):
    edits, phrases = TOKEN_BROKEN[name]
    path = a_loop(tmp_path, counting(*edits), monkeypatch)
    printed = shown(path)
    assert printed[:6] == [f"ok         {n}. {title}" for n, title in enumerate(check_loop.RULES, 1)]
    assert printed[6].startswith(f"NOT YET    {agent.TOKEN_RULE}: ")
    for phrase in phrases:
        assert phrase in printed[6], printed[6]
    assert len(printed) == 7
    # A wrong count fails the check: the agent stops, and tokens and cost stay hidden.
    saved.parent.mkdir(parents=True)
    saved.write_text("yours\n")
    assert check_loop.main([]) == 1
    assert agent.which_loop() == "not passed" and not agent.counts_tokens()


# The same count in a loop built with the parts (step 3b): each reply's usage added up, and the
# count passed last to talk.accept() and talk.stop().
KIT_COUNTING = kit(("    rejected = 0        # answers sent back so far\n",
                    "    rejected = 0        # answers sent back so far\n"
                    '    tokens = {"input": 0, "output": 0}\n'),
                   ("        reply = talk.ask()\n",
                    "        reply = talk.ask()\n"
                    '        tokens["input"] += reply.usage.input_tokens\n'
                    '        tokens["output"] += reply.usage.output_tokens\n')
                   ).replace(", steps)", ", steps, tokens)")


def test_a_loop_built_with_the_parts_can_count_tokens(tmp_path, monkeypatch, saved, capsys):
    assert KIT_COUNTING.count(", steps, tokens)") == 5
    a_loop(tmp_path, KIT_COUNTING, monkeypatch)
    assert check_loop.main([]) == 0
    printed = capsys.readouterr().out.splitlines()
    assert printed == [f"ok         {n}. {title}" for n, title in enumerate(check_loop.RULES, 1)] \
        + [TOKEN_LINE, "", check_loop.PASSED]
    assert agent.which_loop() == "yours" and agent.counts_tokens()


@pytest.mark.parametrize("old, new, phrase", [
    ('        tokens["output"] += reply.usage.output_tokens\n', "",
     "stopped with tokens {'input': 4266, 'output': 0}"),
    ("talk.stop(DECLINED, steps, tokens)", "talk.stop(DECLINED, steps)",
     "the model's first reply refused to check the claim, and your loop stopped with tokens None"),
])
def test_a_wrong_count_with_the_parts_fails_the_token_line_only(tmp_path, old, new, phrase):
    assert KIT_COUNTING.count(old) == 1
    printed = shown(a_loop(tmp_path, KIT_COUNTING.replace(old, new)))
    assert printed[:6] == [f"ok         {n}. {title}" for n, title in enumerate(check_loop.RULES, 1)]
    assert printed[6].startswith(f"NOT YET    {agent.TOKEN_RULE}: ") and phrase in printed[6], printed[6]


def test_the_parts_count_nothing_by_themselves(tmp_path):
    """A loop built with the parts, as 1a leaves it, passes no count: no token line, no cost."""
    assert check_loop.check(a_loop(tmp_path, KIT_REFERENCE)) == [None] * 6


def test_counts_tokens_follows_the_file(saved):
    six = [f"ok         {n}. {title}" for n, title in enumerate(check_loop.RULES, 1)]
    assert not agent.counts_tokens()                     # no file
    saved.parent.mkdir(parents=True)
    for lines, counts in ((["yours"] + six + [TOKEN_LINE], True), (["yours"] + six, False),
                          (["not passing", check_loop.FELL_BACK] + six + [TOKEN_LINE], False),
                          (["yours", f"NOT YET    {agent.TOKEN_RULE}: x."], False)):
        saved.write_text("\n".join(lines) + "\n")
        assert agent.counts_tokens() is counts, lines


def test_finish_holds_tokens_and_cost_only_when_given_them():
    plain = agent.finish("c", "supported", ["q"], "x", [], 2)
    assert set(plain) == {"claim", "verdict", "evidence", "explanation", "trace", "steps"}
    counted = agent.finish("c", "supported", ["q"], "x", [], 2, {"input": 1000, "output": 100})
    assert counted["tokens"] == {"input": 1000, "output": 100}
    assert counted["cost_usd"] == round((1000 * agent.PRICE[0] + 100 * agent.PRICE[1]) / 1_000_000, 6)


# ---------- an error, a loop that never stops, and a file that will not load ----------

def test_an_error_is_reported_with_its_line(tmp_path):
    source = broken(("result = lookup(call.name, call.input)",
                     "result = lookup(call.name, call.inputs)"))
    line = 1 + source[:source.index("call.inputs")].count("\n")
    printed = shown(a_loop(tmp_path, source))
    assert printed[0] == (
        "NOT YET    1. Ask the model: the model's first reply asked for a search, and your loop "
        f"stopped with an error at line {line} of my_loop.py: AttributeError: 'ToolUseBlock' "
        "object has no attribute 'inputs'.")
    # Rule 6's stall case makes a lookup, so it meets the same error.
    assert "AttributeError: 'ToolUseBlock' object has no attribute 'inputs'" in printed[5]


def test_a_loop_that_never_stops_is_reported(tmp_path, monkeypatch):
    monkeypatch.setattr(check_loop, "TIME_LIMIT", 0.3)
    monkeypatch.setattr(check_loop, "AFTER_A_HANG", 0.1)
    turn = '        messages.append({"role": "assistant", "content": response.content})\n'
    source = broken((turn, turn + "        while True:\n            pass\n"))
    first = 1 + source[:source.index("        while True:\n            pass")].count("\n")
    for problem in check_loop.check(a_loop(tmp_path, source)):
        assert "and your loop did not stop: it was still running line" in problem, problem
        assert (f" line {first} of my_loop.py" in problem
                or f" line {first + 1} of my_loop.py" in problem), problem


def test_a_loop_that_keeps_asking_the_model_is_stopped(tmp_path):
    source = ("def run_agent(claim, client=None, max_steps=12, lookup=None):\n"
              "    while True:\n"
              "        try:\n"
              "            client.messages.create(model='x', messages=[])\n"
              "        except Exception:\n"
              "            pass\n")
    start = time.monotonic()
    problems = check_loop.check(a_loop(tmp_path, source))
    assert time.monotonic() - start < check_loop.TIME_LIMIT
    assert problems[3].endswith("gave an answer that quotes the page it had read, and your loop "
                                "asked the model again instead of stopping")


def test_a_file_that_will_not_load_is_reported_on_every_line(tmp_path):
    problems = check_loop.check(a_loop(tmp_path, "def run_agent(claim:\n    pass\n"))
    assert len(set(problems)) == 1
    assert problems[0].startswith("my_loop.py could not be loaded, because of an error at line 1: "
                                  "SyntaxError")
    problems = check_loop.check(a_loop(tmp_path, "import nothing_called_this\n"))
    assert "line 1: ModuleNotFoundError" in problems[0]
    problems = check_loop.check(a_loop(tmp_path, "def run(claim):\n    pass\n"))
    assert problems == ["my_loop.py has no function called run_agent"] * 6


def test_the_check_has_no_network_and_hides_what_the_loop_prints(tmp_path, monkeypatch, capsys):
    requests = []
    monkeypatch.setattr(wiki.requests, "get", lambda *args, **kwargs: requests.append(args))
    source = broken(("result = lookup(call.name, call.input)",
                     "print('looking up'); result = run_tool(call.name, call.input)"))
    problems = check_loop.check(a_loop(tmp_path, source))
    assert requests == []
    assert "RuntimeError: this check has no network, and Wikipedia was called directly" in problems[1]
    assert "looking up" not in capsys.readouterr().out
    assert wiki.search.__name__ == "search"    # put back afterwards


# ---------- which loop the agent runs, and what check.py and evaluate.py say ----------

def fake_loops(monkeypatch):
    """Stand-ins for my_loop and reference_loop that say which one ran, with what."""
    calls = []
    for name in ("my_loop", "reference_loop"):
        def run_agent(claim, client=None, max_steps=None, lookup=None, name=name):
            calls.append((name, claim, client, max_steps, lookup))
            return {"claim": claim, "verdict": "supported", "evidence": [], "explanation": "x",
                    "trace": [], "steps": 0}
        monkeypatch.setitem(sys.modules, name, SimpleNamespace(run_agent=run_agent))
    return calls


def test_run_agent_runs_the_loop_in_use(monkeypatch, saved):
    calls = fake_loops(monkeypatch)
    lookup = object()
    agent.run_agent("c1", client="client", max_steps=5, lookup=lookup)
    saved.parent.mkdir(parents=True)
    saved.write_text("yours\n")
    agent.run_agent("c2", client="client", max_steps=5, lookup=lookup)
    agent.run_agent("c3")
    assert calls == [("reference_loop", "c1", "client", 5, lookup),
                     ("my_loop", "c2", "client", 5, lookup),
                     ("my_loop", "c3", None, agent.MAX_STEPS, agent.run_tool)]
    # A loop that passed and fails now runs nothing, and never the reference loop.
    saved.write_text("not passing\n")
    with pytest.raises(agent.LoopNotPassed, match="has not passed the check"):
        agent.run_agent("c4")
    assert len(calls) == 3


def test_check_py_says_which_loop_when_the_agent_runs(monkeypatch, tmp_path, saved, capsys):
    fake_loops(monkeypatch)
    monkeypatch.setitem(check.METHODS, "agent", agent.run_agent)
    monkeypatch.setitem(check.METHODS, "no-tools", lambda claim: sys.modules["my_loop"].run_agent(claim))

    def run(method):
        monkeypatch.setattr(sys, "argv", ["check.py", "--method", method, "--out", str(tmp_path), "c"])
        check.main()
        return capsys.readouterr().out.splitlines()

    assert run("agent")[0] == "Agent loop: the reference loop (reference_loop.py)"    # Part 0
    saved.parent.mkdir(parents=True)
    saved.write_text("yours\n")
    assert run("agent")[0] == "Agent loop: yours (my_loop.py)"
    assert not any(line.startswith("Agent loop") for line in run("no-tools"))
    saved.write_text("not passing\n")
    with pytest.raises(SystemExit) as stopped:
        run("agent")
    assert stopped.value.code == 1
    assert capsys.readouterr().out.strip() == agent.NOT_PASSED


def test_evaluate_py_says_which_loop_when_the_agent_runs(monkeypatch, tmp_path, saved, capsys):
    fake_loops(monkeypatch)
    claims = tmp_path / "claims.jsonl"
    claims.write_text(json.dumps({"id": "c1", "claim": "c", "source": "hover",
                                  "label": "SUPPORTED", "hops": 2}) + "\n")
    monkeypatch.setitem(evaluate.METHODS, "agent", agent.run_agent)
    monkeypatch.setitem(evaluate.METHODS, "no-tools", agent.run_agent)

    def run(methods, out):
        monkeypatch.setattr(sys, "argv", ["evaluate.py", str(claims), "--methods", methods,
                                          "--out", str(tmp_path / out)])
        evaluate.main()
        return capsys.readouterr().out.splitlines()

    # Before the student's loop has passed, evaluate.py runs no agent, and never the reference loop.
    with pytest.raises(SystemExit) as stopped:
        run("no-tools,agent", "a")
    assert stopped.value.code == 1 and capsys.readouterr().out.strip() == agent.NOT_PASSED
    assert not (tmp_path / "a").exists()
    saved.parent.mkdir(parents=True)
    saved.write_text("yours\n")
    assert run("agent", "b")[0] == "Agent loop: yours (my_loop.py)"
    assert not any(line.startswith("Agent loop") for line in run("no-tools", "c"))
    # A loop that fails now stops the run before anything is run or forgotten, --fresh or not.
    kept = (tmp_path / "b" / "agent.jsonl").read_text()
    saved.write_text("not passing\n")
    for extra in ([], ["--fresh"]):
        monkeypatch.setattr(sys, "argv", ["evaluate.py", str(claims), "--methods", "agent",
                                          "--out", str(tmp_path / "b"), *extra])
        with pytest.raises(SystemExit):
            evaluate.main()
        assert capsys.readouterr().out.strip() == agent.NOT_PASSED
        assert (tmp_path / "b" / "agent.jsonl").read_text() == kept


def test_the_fingerprint_covers_the_loop_in_use(monkeypatch, tmp_path, saved):
    # A copy of the files the fingerprint reads, so the test can change them.
    for name in evaluate.AGENT_FILES + ["my_loop.py", "reference_loop.py"]:
        shutil.copy(ROOT / name, tmp_path / name)
    monkeypatch.setattr(evaluate, "__file__", str(tmp_path / "evaluate.py"))
    on_reference = evaluate.agent_version()
    (tmp_path / "my_loop.py").write_text("# changed\n")
    assert evaluate.agent_version() == on_reference     # my_loop.py is not in use yet

    saved.parent.mkdir(parents=True)
    saved.write_text("yours\n")
    on_yours = evaluate.agent_version()
    assert on_yours != on_reference
    (tmp_path / "my_loop.py").write_text("# changed again\n")
    assert evaluate.agent_version() != on_yours
    on_yours = evaluate.agent_version()
    (tmp_path / "reference_loop.py").write_text("# not in use now\n")
    assert evaluate.agent_version() == on_yours

    # The same bytes in both loop files still make two versions.
    (tmp_path / "my_loop.py").write_text(REFERENCE)
    (tmp_path / "reference_loop.py").write_text(REFERENCE)
    on_yours = evaluate.agent_version()
    saved.unlink()
    assert evaluate.agent_version() != on_yours
