"""Do not open this file before step 1a is done: it holds complete loops, and
reading them first gives the exercise away.

Offline tests for check_loop.py, the check of the loop in my_loop.py, and for how
the agent chooses between that loop and the reference loop. Every test keeps
runs/part1/loop-check.txt in a temporary folder, so none of them reads or leaves
a runs/ folder in the repository."""

import json
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

REFERENCE = (ROOT / "reference_loop.py").read_text()
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
    assert printed[6:] == ["", check_loop.FAILED]
    assert not saved.exists()
    assert agent.which_loop() == "reference"


def test_the_skeleton_names_the_six_rules_and_gives_nothing_more():
    source = (ROOT / "my_loop.py").read_text()
    for n, title in enumerate(check_loop.RULES, 1):
        assert f"#   {n}. {title}." in source
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


def test_use_reference_records_reference(saved, capsys):
    assert check_loop.main(["--use-reference"]) == 0
    assert capsys.readouterr().out.strip() == check_loop.KEPT_REFERENCE
    assert saved.read_text().splitlines()[0] == "reference"
    assert agent.which_loop() == "reference"


def test_a_failing_check_removes_a_yours_file_but_keeps_reference(tmp_path, monkeypatch, saved):
    a_loop(tmp_path, REFERENCE, monkeypatch)
    assert check_loop.main([]) == 0 and agent.which_loop() == "yours"
    # A later change breaks the loop: the copy goes back to the reference loop.
    a_loop(tmp_path, broken(("                steps += 1\n", "")), monkeypatch)
    assert check_loop.main([]) == 1
    assert not saved.exists() and agent.which_loop() == "reference"
    # A student who chose the reference loop keeps that record when a check fails.
    check_loop.main(["--use-reference"])
    assert check_loop.main([]) == 1
    assert saved.read_text().startswith("reference\n")


def test_which_loop_follows_the_file(saved):
    assert agent.which_loop() == "reference"           # no file
    saved.parent.mkdir(parents=True)
    for text, loop in (("yours\nok ...\n", "yours"), ("yours", "yours"),
                       ("reference\n", "reference"), ("", "reference"),
                       ("yours \n", "reference"), ("Yours\n", "reference"),
                       ("ok\nyours\n", "reference")):
        saved.write_text(text)
        assert agent.which_loop() == loop, text
    saved.write_bytes(b"\xff\xfe\x00yours")              # not text
    assert agent.which_loop() == "reference"
    saved.unlink()
    saved.mkdir()                                        # not a file
    assert agent.which_loop() == "reference"


# ---------- fair to loops written differently ----------

# Two correct loops organised differently from the reference loop, and from each other.
# The first asks the model in a helper function, stops through another, keeps a flag for
# the reminder and for the limit, checks the limit for the whole turn, sends the reminder
# as a text block, and also records rejected answers.
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
    tokens = {"input": 0, "output": 0}
    steps = 0
    rejected = 0
    told_limit = False
    reminded = False

    def ask():
        reply = client.messages.create(model=MODEL, max_tokens=16000, system=system,
                                       tools=TOOLS, messages=messages)
        tokens["input"] += reply.usage.input_tokens
        tokens["output"] += reply.usage.output_tokens
        messages.append({"role": "assistant", "content": reply.content})
        return reply

    def no_verdict(why):
        return finish(claim, None, [], why, trace, tokens, steps)

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
                                  answer["explanation"], trace, tokens, steps)
                rejected += 1
                trace.append({"tool": "answer", "input": call.input, "result": REJECTED + problem})
                if rejected >= MAX_REJECTED:
                    return no_verdict(REJECTED_TOO_OFTEN.format(n=rejected))
                content = REJECTED + problem
            elif steps >= max_steps:
                told_limit = True
                content = OUT_OF_STEPS.format(n=max_steps)
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
# cleaned answer in the trace, records nothing for a rejected answer or a refused lookup,
# and runs a bounded number of turns.
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
    tokens = {"input": 0, "output": 0}
    steps = 0
    rejected = 0
    warned_on = None
    quiet = 0

    for turn in range(100):
        response = client.messages.create(model=MODEL, max_tokens=16000, system=system,
                                          tools=TOOLS, messages=messages)
        for key, used in (("input", response.usage.input_tokens),
                          ("output", response.usage.output_tokens)):
            tokens[key] = tokens[key] + used
        messages.append({"role": "assistant",
                         "content": [block.model_dump() for block in response.content]})
        calls = [block for block in response.content if block.type == "tool_use"]
        if response.stop_reason == "refusal":
            return finish(claim, None, [], DECLINED, trace, tokens, steps)
        if not calls:
            quiet += 1
            if quiet == 2:
                return finish(claim, None, [], NO_ANSWER, trace, tokens, steps)
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
                                  answer["explanation"], trace, tokens, steps)
                rejected = rejected + 1
                if rejected == MAX_REJECTED:
                    return finish(claim, None, [], REJECTED_TOO_OFTEN.format(n=rejected),
                                  trace, tokens, steps)
                sent[call.id] = REJECTED + problem
            elif steps < max_steps:
                found = lookup(call.name, call.input)
                steps = steps + 1
                trace.append({"tool": call.name, "input": call.input, "result": found})
                if call.name in ("read", "wikidata"):
                    read_so_far.append(found)
                sent[call.id] = found
            elif warned_on is not None and warned_on < turn:
                return finish(claim, None, [], RAN_OUT, trace, tokens, steps)
            else:
                warned_on = turn
                sent[call.id] = OUT_OF_STEPS.format(n=max_steps)
        messages.append({"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": call_id, "content": result}
            for call_id, result in sent.items()]})
    return finish(claim, None, [], RAN_OUT, trace, tokens, steps)
'''


@pytest.mark.parametrize("source", [HELPERS, BY_ID, broken(("for call in calls:",
                                                            "for call in reversed(calls):"))],
                         ids=["helpers", "by-id", "calls-in-reverse"])
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


def test_an_error_about_the_client_names_the_scripted_model(tmp_path):
    source = broken(("response = client.messages.create(", "response = client.messages.stream("))
    assert "AttributeError: 'ScriptedModel' object has no attribute 'stream'" in \
        check_loop.check(a_loop(tmp_path, source))[0]


# Rules 1 to 3 and nothing more: the page suggests writing these first and running the check.
FIRST_THREE = REFERENCE[:REFERENCE.index("    while True:")] + '''    while True:
        response = client.messages.create(model=MODEL, max_tokens=16000, system=system,
                                          tools=TOOLS, messages=messages)
        tokens["input"] += response.usage.input_tokens
        tokens["output"] += response.usage.output_tokens
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
    problems = check_loop.check(a_loop(tmp_path, FIRST_THREE))
    assert problems[:3] == [None] * 3
    assert all(problems[3:])
    assert problems[3].endswith("gave an answer that quotes the page it had read, and your loop "
                                "called lookup() for it")


# ---------- one broken loop per rule, and what each line says ----------

EXPLANATION_LINE = 1 + REFERENCE[:REFERENCE.index('answer["explanation"]')].count("\n")
TOKENS = ('        tokens["input"] += response.usage.input_tokens\n'
          '        tokens["output"] += response.usage.output_tokens\n')
REFUSAL = ('        if response.stop_reason == "refusal":\n'
           '            return finish(claim, None, [], DECLINED, trace, tokens, steps)\n')
BROKEN = {
    "no tokens": (1, [(TOKENS, "")],
                  ["the model's first reply used 1,211 input and 37 output tokens",
                   "tokens held {'input': 0, 'output': 0}"]),
    "no assistant turn": (1, [('        messages.append({"role": "assistant", '
                               '"content": response.content})\n', "")],
                          ["asked for a search", "as the assistant's turn"]),
    "no system text": (1, [("system=system, ", "")], ["system text"]),
    "wrong model": (1, [("model=MODEL,", "model='claude-opus-5-5',")],
                    ["named the model 'claude-opus-5-5'"]),
    "only the newest turn": (1, [("messages=messages,", "messages=messages[-2:],")],
                             ["did not hold the whole conversation so far"]),
    "refusal tokens not counted": (1, [(TOKENS + "        messages.append", "        messages.append"),
                                       (REFUSAL, REFUSAL + TOKENS)],
                                   ['was a refusal (stop_reason "refusal")', "had tokens"]),
    "steps not counted": (2, [("                steps += 1\n", "")],
                          ["had run one lookup, and steps held 0"]),
    "search kept": (2, [('if call.name != "search":', "if True:")],
                    ["asked for a search", "what the search returned was in read_so_far"]),
    "read not kept": (2, [("                    read_so_far.append(result)\n",
                           "                    pass\n")],
                      ["asked for a read", "what the read returned was not in read_so_far"]),
    "lookup not in the trace": (2, [('            trace.append({"tool": call.name, "input": '
                                     'call.input, "result": result})\n', "")],
                                ["the trace had no entry for the search"]),
    "results not sent": (3, [('        messages.append({"role": "user", "content": results})\n', "")],
                         ["asked for a search and a read", "no user turn of results"]),
    "wrong id": (3, [('"tool_use_id": call.id', '"tool_use_id": calls[0].id')],
                 ["held two results with the search call's id"]),
    "a turn per result": (3, [('            results.append({"type": "tool_result", '
                               '"tool_use_id": call.id, "content": result})\n',
                               '            messages.append({"role": "user", "content": [{"type": '
                               '"tool_result", "tool_use_id": call.id, "content": result}]})\n'),
                              ('        messages.append({"role": "user", "content": results})\n', "")],
                          ["had two turns after that reply, where the rule says one"]),
    "answer not cleaned": (4, [("answer = clean_answer(call.input)", "answer = call.input")],
                           ["evidence as one string and no explanation", "KeyError: 'explanation'",
                            f"line {EXPLANATION_LINE} of my_loop.py"]),
    "one rejection too many": (4, [("rejected >= MAX_REJECTED", "rejected > MAX_REJECTED")],
                               ["first three replies were answers",
                                "asked the model again after the third was rejected"]),
    "rejection without REJECTED": (4, [("result = REJECTED + problem", "result = problem")],
                                   ["your loop sent back 'These quotes are not in anything",
                                    "REJECTED followed by the problem"]),
    "evidence left out": (4, [('return finish(claim, answer["verdict"], answer["evidence"],',
                               'return finish(claim, answer["verdict"], [],')],
                          ["gave an answer that quotes the page it had read",
                           "had the evidence [], not ['directed by Robert Zemeckis']"]),
    "the limit is MAX_STEPS": (5, [("elif steps >= max_steps:", "elif steps >= MAX_STEPS:")],
                               ["asked for a third search with the limit of 2 lookups reached",
                                "your loop ran it"]),
    "stops at once": (5, [("if warned_before:", "if True:")],
                      ["instead of sending back OUT_OF_STEPS the first time"]),
    "never stops at the limit": (5, [("if warned_before:", "if False:")],
                                 ["asked for a fourth search after OUT_OF_STEPS had been sent back",
                                  "asked the model again instead of stopping"]),
    "no reminder": (6, [('            trace.append({"tool": "(reminder)"',
                         '            return finish(claim, None, [], NO_ANSWER, trace, tokens, steps)\n'
                         '            trace.append({"tool": "(reminder)"')],
                    ["had text and no tool call", "instead of reminding the model"]),
    "reminds forever": (6, [('            if trace and trace[-1]["tool"] == "(reminder)":\n'
                             '                return finish(claim, None, [], NO_ANSWER, trace, '
                             'tokens, steps)\n', "")],
                        ["asked the model a third time instead of stopping"]),
    "refusal not stopped": (6, [(REFUSAL, "")],
                            ['was a refusal (stop_reason "refusal")',
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


def test_every_broken_rule_is_covered():
    assert {rule for rule, _, _ in BROKEN.values()} == set(range(1, 7))


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
    assert printed[5].startswith("ok ")   # rule 6's checks make no lookups


def test_a_loop_that_never_stops_is_reported(tmp_path, monkeypatch):
    monkeypatch.setattr(check_loop, "TIME_LIMIT", 0.3)
    monkeypatch.setattr(check_loop, "AFTER_A_HANG", 0.1)
    source = broken((TOKENS, TOKENS + "        while True:\n            pass\n"))
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
                    "trace": [], "steps": 0, "tokens": {"input": 1, "output": 1}, "cost_usd": 0}
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


def test_check_py_says_which_loop_when_the_agent_runs(monkeypatch, tmp_path, saved, capsys):
    fake_loops(monkeypatch)
    monkeypatch.setitem(check.METHODS, "agent", agent.run_agent)
    monkeypatch.setitem(check.METHODS, "no-tools", lambda claim: sys.modules["my_loop"].run_agent(claim))

    def run(method):
        monkeypatch.setattr(sys, "argv", ["check.py", "--method", method, "--out", str(tmp_path), "c"])
        check.main()
        return capsys.readouterr().out.splitlines()

    assert run("agent")[0] == "Agent loop: the reference loop (reference_loop.py)"
    saved.parent.mkdir(parents=True)
    saved.write_text("yours\n")
    assert run("agent")[0] == "Agent loop: yours (my_loop.py)"
    assert not any(line.startswith("Agent loop") for line in run("no-tools"))


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

    assert run("no-tools,agent", "a")[0] == "Agent loop: the reference loop (reference_loop.py)"
    saved.parent.mkdir(parents=True)
    saved.write_text("yours\n")
    assert run("agent", "b")[0] == "Agent loop: yours (my_loop.py)"
    assert not any(line.startswith("Agent loop") for line in run("no-tools", "c"))


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
