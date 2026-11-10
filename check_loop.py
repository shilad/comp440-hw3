"""Check the loop in my_loop.py against the six rules of step 1a.

    uv run python check_loop.py

It runs your loop on twelve short made-up checks of one claim, with a scripted
stand-in for the model and for Wikipedia, so it needs no key and no network,
costs nothing and takes a few seconds. It prints one line per rule: ok, or
NOT YET and what happened. Anything your loop prints while the check runs is
not shown.

When every rule passes, it saves the lines it printed as
runs/part1/loop-check.txt, with "yours" on the first line, and from then on
your copy's agent runs on your loop. When a rule fails, it removes a file that
says "yours", so a later change that breaks your loop puts your copy back on
the reference loop.

If you cannot finish your loop and want to go on with the homework:

    uv run python check_loop.py --use-reference

saves the file with "reference" on the first line, and your copy keeps using
the reference loop. You can still finish your loop later and run the check
again without --use-reference.
"""

import argparse
import contextlib
import importlib.util
import io
import os
import sys
import threading
import time
import traceback
from pathlib import Path

from anthropic.types import Message, TextBlock, ToolUseBlock, Usage

import agent
import wiki

MY_LOOP = Path(__file__).resolve().parent / "my_loop.py"
RULES = ["Ask the model", "Run its lookups", "Send the results back", "Check the answer",
         "Enforce the limit", "Stop when the model stops"]
TIME_LIMIT = 2      # seconds your loop has for one made-up check
AFTER_A_HANG = 0.5  # seconds for each later one, once a loop has not stopped
MAX_LOOKUPS = 40    # far more lookups than any made-up check asks for
LOOKUPS = ("search", "read", "wikidata")
PLENTY = 20         # the limit of lookups in the made-up checks that do not test the limit
LIMIT = 2           # the limit in the two that do
PASSED = "Every rule passes. From now on your copy's agent runs on your loop (my_loop.py)."
FAILED = "Not yet. Fix the first NOT YET line, then run this again."
KEPT_REFERENCE = ("Recorded: your copy keeps using the reference loop. You can still finish "
                  "your loop later: run this check again without --use-reference.")

# ---------- the made-up claim, Wikipedia and model ----------

CLAIM = "The director of Forrest Gump was born in Chicago."
PAGES = {
    "Forrest Gump": "Forrest Gump is a 1994 American film directed by Robert Zemeckis.",
    "Robert Zemeckis": ("Robert Lee Zemeckis (born May 14, 1952) is an American filmmaker. "
                        "He was born in Chicago, Illinois."),
}


def wikipedia(name, args):
    """What the made-up Wikipedia returns for one lookup."""
    args = args if isinstance(args, dict) else {}
    if name == "search":
        return (f"Search results for {args.get('query')!r}:\n"
                "1. Forrest Gump: a 1994 film\n2. Robert Zemeckis: an American filmmaker")
    if name == "read":
        return PAGES.get(args.get("title"), f"There is no page called {args.get('title')!r}.")
    if name == "wikidata":
        return f"Wikidata: {args.get('entity')}, {args.get('property')}: Chicago"
    return f"There is no tool called {name!r}."


def reply(says, *blocks, stop=None):
    """One scripted reply. `says` finishes the sentence "the model's first reply ..."."""
    return {"says": says, "blocks": blocks, "stop": stop}


def text(words):
    return ("text", words)


def use(name, args):
    return ("tool_use", name, args)


def search(query):
    return use("search", {"query": query})


def read(title):
    return use("read", {"title": title})


BIRTHPLACE = use("wikidata", {"entity": "Robert Zemeckis", "property": "place of birth"})
GOOD = use("answer", {"verdict": "supported", "evidence": ["directed by Robert Zemeckis"],
                      "explanation": "The page names him as the director."})
MADE_UP = use("answer", {"verdict": "supported", "evidence": ["Zemeckis was born in Ohio."],
                         "explanation": "He was born in Ohio."})
NOT_SAID = use("answer", {"verdict": "doesn't say", "evidence": [],
                          "explanation": "The page does not say where he was born."})
QUOTES_GOOD = "gave an answer that quotes the page it had read"
QUOTES_NOTHING = "gave an answer with a quote that is in nothing it had read"
NO_TOOL = "had text and no tool call"

# Each made-up check: the model's replies, in order, and the limit of lookups.
SCENARIOS = {
    "ask": ([reply("asked for a search", text("I will start with a search."),
                   search("Forrest Gump director")),
             reply("asked for a read", read("Forrest Gump")),
             reply(QUOTES_GOOD, GOOD)], PLENTY),
    "lookups": ([reply("asked for a search", search("Forrest Gump")),
                 reply("asked for a read", text("Now the film's page."), read("Forrest Gump")),
                 reply("asked for a wikidata lookup and a read", BIRTHPLACE,
                       read("Robert Zemeckis"))], PLENTY),
    "results": ([reply("asked for a search and a read", search("Robert Zemeckis"),
                       read("Robert Zemeckis")),
                 reply("asked for a wikidata lookup", BIRTHPLACE)], PLENTY),
    "accept": ([reply("asked for a read", read("Forrest Gump")),
                reply(QUOTES_GOOD, GOOD)], PLENTY),
    "reject": ([reply("asked for a read", read("Forrest Gump")),
                reply(QUOTES_NOTHING, MADE_UP),
                reply("gave an answer of doesn't say", NOT_SAID)], PLENTY),
    # More answers than any MAX_REJECTED you might set in part 3.
    "reject_often": ([reply(QUOTES_NOTHING, MADE_UP)] * 12, PLENTY),
    "clean": ([reply("asked for a read", read("Robert Zemeckis")),
               reply("gave an answer with its evidence as one string and no explanation",
                     use("answer", {"verdict": "supported",
                                    "evidence": "He was born in Chicago, Illinois."}))],
              PLENTY),
    "limit_answer": ([reply("asked for a search", search("Forrest Gump")),
                      reply("asked for a second search", search("Robert Zemeckis")),
                      reply("asked for a third search", search("Zemeckis birthplace")),
                      reply("gave an answer of doesn't say", NOT_SAID)], LIMIT),
    "limit_again": ([reply("asked for a search", search("Forrest Gump")),
                     reply("asked for a second search", search("Robert Zemeckis")),
                     reply("asked for a third search", search("Zemeckis birthplace")),
                     reply("asked for a fourth search", search("Zemeckis Chicago")),
                     reply("asked for a fifth search", search("Zemeckis Illinois")),
                     reply("asked for a sixth search", search("Zemeckis early life"))], LIMIT),
    "remind": ([reply(NO_TOOL, text("I think the claim is true.")),
                reply("gave an answer of doesn't say", NOT_SAID)], PLENTY),
    "no_answer": ([reply(NO_TOOL, text("I think the claim is true.")),
                   reply(NO_TOOL + " again", text("It is true.")),
                   reply(NO_TOOL + " again", text("True."))], PLENTY),
    "refusal": ([reply('was a refusal (stop_reason "refusal")', text("I can't help with that."),
                       stop="refusal"),
                 reply("gave an answer of doesn't say", NOT_SAID)], PLENTY),
}


def build(script, tag):
    """The scripted replies as the Claude API's own objects, so the loop sees what it will
    see in a real run. Each reply uses a different number of tokens."""
    replies = []
    for i, spec in enumerate(script, 1):
        blocks = []
        for j, block in enumerate(spec["blocks"], 1):
            if block[0] == "text":
                blocks.append(TextBlock(type="text", text=block[1]))
            else:
                blocks.append(ToolUseBlock(type="tool_use", id=f"toolu_{tag}_{i}{j}",
                                           name=block[1], input=dict(block[2])))
        calls = any(block.type == "tool_use" for block in blocks)
        replies.append(Message(
            id=f"msg_{tag}_{i}", type="message", role="assistant", model=agent.MODEL,
            content=blocks, stop_reason=spec["stop"] or ("tool_use" if calls else "end_turn"),
            stop_sequence=None,
            usage=Usage(input_tokens=1000 + 211 * i, output_tokens=30 + 7 * i)))
    return replies


# ---------- running your loop on one made-up check ----------

class Stop(BaseException):
    """Raised inside your loop by the check, to end a made-up check. It is a BaseException,
    so an `except Exception` in your loop does not catch it."""


class AskedTooOften(Stop):
    """The loop asked the model again after the last scripted reply."""


class TooManyLookups(Stop):
    """The loop called lookup() more than MAX_LOOKUPS times."""


class DidNotStop(Stop):
    def __init__(self, line):
        super().__init__(line)
        self.line = line


class NotYet(Exception):
    """A rule that does not pass yet, with the sentence that says what happened."""


def stop_at(deadline, loop_file):
    """A trace function that stops the loop in loop_file once the deadline has passed."""
    def each_line(frame, event, arg):
        if time.monotonic() > deadline:
            raise DidNotStop(frame.f_lineno)
        return each_line

    def each_call(frame, event, arg):
        return each_line if frame.f_code.co_filename == loop_file else None
    return each_call


def in_thread(work, loop_file, seconds=TIME_LIMIT):
    """Run work() with a time limit. Returns (value, error, still_running)."""
    box = {}

    def target():
        sys.settrace(stop_at(time.monotonic() + seconds, loop_file))
        try:
            box["value"] = work()
        except BaseException as error:  # noqa: BLE001  whatever the loop raised, report it
            box["error"] = error
        finally:
            sys.settrace(None)
    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    thread.join(seconds + 1)
    return box.get("value"), box.get("error"), thread.is_alive()


def line_in(error, loop_file):
    """The line of loop_file where the error happened, or None."""
    if isinstance(error, SyntaxError) and error.filename == loop_file:
        return error.lineno
    lines = [frame.lineno for frame in traceback.extract_tb(error.__traceback__)
             if frame.filename == loop_file]
    return lines[-1] if lines else None


def described(error):
    if isinstance(error, SyntaxError):
        return f"{type(error).__name__}: {error.msg}"
    message = " ".join(str(error).split())
    message = message if len(message) <= 160 else message[:157] + "..."
    return f"{type(error).__name__}: {message}" if message else type(error).__name__


def copy_request(request):
    """What the loop sent, copied, since the loop goes on to change its conversation."""
    request = dict(request)
    if isinstance(request.get("messages"), (list, tuple)):
        request["messages"] = [
            {**turn, "content": list(turn["content"])}
            if isinstance(turn, dict) and isinstance(turn.get("content"), list) else
            (dict(turn) if isinstance(turn, dict) else turn)
            for turn in request["messages"]]
    return request


def copy_value(value):
    if isinstance(value, list):
        return [dict(item) if isinstance(item, dict) else item for item in value]
    if isinstance(value, dict):
        return dict(value)
    return value


def loop_variables(frame, loop_file):
    """tokens, steps, trace and read_so_far, as the loop has them while it waits for the
    model. They are read from the loop's own variables, so rules 1 to 3 can be checked
    before the loop can stop."""
    found = {}
    while frame is not None:
        if frame.f_code.co_filename == loop_file:
            names = frame.f_locals
            for name in ("tokens", "steps", "trace", "read_so_far"):
                if name not in found and name in names:
                    found[name] = copy_value(names[name])
        frame = frame.f_back
    return found


class ScriptedModel:
    """The client your loop is given: client.messages.create(...) returns the next scripted
    reply."""

    def __init__(self, run):
        self.messages = self
        self.run = run

    def create(self, **request):
        return self.run.create(**request)


class Run:
    """Your loop on one made-up check: every request it sent the model, its variables at
    each request, every lookup, what it returned, and how it ended."""

    def __init__(self, key, run_agent, loop_file, seconds=TIME_LIMIT):
        self.script, self.max_steps = SCENARIOS[key]
        self.replies = build(self.script, key)
        self.loop_file = loop_file
        self.requests, self.states, self.lookups = [], [], []
        self.result = self.error = self.line = None
        self.abandoned = False
        result, error, alive = in_thread(
            lambda: run_agent(CLAIM, client=ScriptedModel(self), max_steps=self.max_steps,
                              lookup=self.lookup),
            loop_file, seconds)
        if alive:
            self.abandoned, self.ended = True, "did not stop"
        elif error is None:
            self.ended, self.result = "returned", result
        else:
            self.error, self.line = error, line_in(error, loop_file)
            self.ended = {AskedTooOften: "asked too often", TooManyLookups: "too many lookups",
                          DidNotStop: "did not stop", NotImplementedError: "not written"}.get(
                              type(error), "error")
            if isinstance(error, DidNotStop):
                self.line = error.line

    def create(self, **request):
        if self.abandoned:
            raise DidNotStop(None)
        self.requests.append(copy_request(request))
        state = loop_variables(sys._getframe(1), self.loop_file)
        state["lookups so far"] = len(self.lookups)
        self.states.append(state)
        if len(self.requests) > len(self.replies):
            raise AskedTooOften()
        return self.replies[len(self.requests) - 1]

    def lookup(self, name, args):
        if self.abandoned:
            raise DidNotStop(None)
        self.lookups.append((name, args))
        if len(self.lookups) > MAX_LOOKUPS:
            raise TooManyLookups()
        return wikipedia(name, args)

    # ----- what happened, in words

    def said(self, n):
        """"the model's second reply asked for a read", for the nth reply."""
        return f"the model's {nth(n)} reply {self.script[n - 1]['says']}"

    def given(self):
        """How many replies the loop was given."""
        return min(len(self.requests), len(self.replies))

    def your_loop(self):
        n = self.given()
        return f"{self.said(n)}, and your loop" if n else "your loop"

    def ending(self):
        """How the run ended, for a rule that needed it to go further."""
        if self.ended == "not written" and not self.requests:
            return "the loop is not written yet"
        where = f" at line {self.line} of my_loop.py" if self.line else ""
        if self.ended == "returned":
            if not self.requests:
                return "your loop returned without asking the model anything"
            return f"{self.your_loop()} returned a result without asking the model again"
        if self.ended == "not written":
            return f"{self.your_loop()} reached raise NotImplementedError{where}"
        if self.ended == "did not stop":
            line = f" line {self.line} of my_loop.py" if self.line else ""
            return (f"{self.your_loop()} did not stop: it was still running{line} when the check "
                    "stopped it")
        if self.ended == "too many lookups":
            return f"{self.your_loop()} had called lookup() more than {MAX_LOOKUPS} times"
        if self.ended == "asked too often":
            return f"{self.your_loop()} asked the model again"
        return f"{self.your_loop()} stopped with an error{where}: {described(self.error)}"

    # ----- what the rules look at

    def request(self, k):
        """The kth request the loop sent the model."""
        if len(self.requests) < k:
            raise NotYet(self.ending())
        return self.requests[k - 1]

    def state(self, k, *names):
        """The loop's variables when it sent the kth request."""
        self.request(k)
        state = self.states[k - 1]
        for name in names:
            if name not in state:
                raise NotYet(f"while your loop was waiting for the model, my_loop.py had no "
                             f"variable called {name}")
        return state

    def calls(self, k):
        return [block for block in self.replies[k - 1].content if block.type == "tool_use"]

    def used(self, n):
        """The tokens the model's first n replies used."""
        return {"input": sum(r.usage.input_tokens for r in self.replies[:n]),
                "output": sum(r.usage.output_tokens for r in self.replies[:n])}

    def returned_after(self, k, asked_again, after=""):
        """The result, when the loop returned right after the model's kth reply."""
        if len(self.requests) > k:
            raise NotYet(f"{self.said(k)}{after}, and your loop {asked_again}")
        if self.ended != "returned" or len(self.requests) < k:
            raise NotYet(self.ending())
        if not is_finished(self.result):
            raise NotYet(f"{self.said(k)}, and your loop returned {short(self.result)}, which is "
                         "not what finish() returns")
        return self.result

    def expect(self, k, result, verdict, evidence, explanation, name=None, after=""):
        """The verdict, evidence and explanation the result should hold after the kth reply."""
        for field, want, label in (("verdict", verdict, repr(verdict)),
                                   ("evidence", evidence, repr(evidence)),
                                   ("explanation", explanation,
                                    f"{name} ({explanation!r})" if name else repr(explanation))):
            if result[field] != want:
                raise NotYet(f"{self.said(k)}{after}, and the result your loop returned had the "
                             f"{field} {short(result[field])}, not {label}")


FINISH_KEYS = set(agent.finish("", None, [], "", [], {"input": 0, "output": 0}, 0))


def is_finished(result):
    return isinstance(result, dict) and FINISH_KEYS <= set(result)


# ---------- small helpers ----------

ORDINALS = ["first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth",
            "ninth", "tenth"]


NUMBERS = ["no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"]


def nth(n):
    return ORDINALS[n - 1] if 1 <= n <= len(ORDINALS) else f"{n}th"


def count(n, word=None):
    """"two lookups", "one lookup", or just "two" with no word."""
    number = NUMBERS[n] if 0 <= n < len(NUMBERS) else str(n)
    return number if word is None else f"{number} {word}{'' if n == 1 else 's'}"


def short(value, n=120):
    shown = " ".join(repr(value).split())
    return shown if len(shown) <= n else shown[: n - 3] + "..."


def get(item, key):
    return item.get(key) if isinstance(item, dict) else getattr(item, key, None)


def view(block):
    """The parts of a content block that matter, whether it is the library's object or a dict."""
    kind = get(block, "type")
    if kind == "tool_use":
        return (kind, get(block, "id"), get(block, "name"), get(block, "input"))
    if kind == "text":
        return (kind, get(block, "text"))
    return (kind,)


def same_text(sent, words):
    """Text sent as a string, or as a list holding one text block."""
    return sent == words or (isinstance(sent, (list, tuple)) and len(sent) == 1
                             and view(sent[0]) == ("text", words))


def same_items(a, b):
    """The same items, in any order."""
    rest = list(b)
    for item in a:
        if item not in rest:
            return False
        rest.remove(item)
    return not rest


def after_reply(request):
    """The turns after the last assistant turn in a request: what the loop added after the
    model's latest reply."""
    messages = request.get("messages")
    messages = list(messages) if isinstance(messages, (list, tuple)) else []
    last = max((i for i, turn in enumerate(messages) if get(turn, "role") == "assistant"),
               default=None)
    return messages[last + 1:] if last is not None else messages[-1:]


MISSING = object()


def sent_back(request, call_id):
    """What the loop sent back for one tool call in a request, or MISSING."""
    for turn in after_reply(request):
        content = get(turn, "content")
        for item in content if isinstance(content, list) else []:
            if get(item, "tool_use_id") == call_id:
                return get(item, "content")
    return MISSING


def has_entry(trace, want):
    return isinstance(trace, list) and any(
        isinstance(entry, dict) and all(entry.get(key) == want[key] for key in want)
        for entry in trace)


# ---------- the six rules ----------

def rule_1(runs):
    """Ask the model."""
    run = runs["ask"]
    system = agent.INSTRUCTIONS.read_text()
    if not run.requests:
        raise NotYet(run.ending())
    for k, request in enumerate(run.requests, 1):
        sent = ("the first request your loop sent the model" if k == 1 else
                f"{run.said(k - 1)}, and the next request your loop sent")
        if request.get("model") != agent.MODEL:
            raise NotYet(f"{sent} named the model {short(request.get('model'))}, not MODEL "
                         f"({agent.MODEL!r})")
        if request.get("max_tokens") != 16000:
            raise NotYet(f"{sent} had max_tokens {short(request.get('max_tokens'))}, where the "
                         "call in the details has 16000")
        if not same_text(request.get("system"), system):
            raise NotYet(f"{sent} did not have the text of instructions.md as its system text")
        if request.get("tools") != agent.TOOLS:
            raise NotYet(f"{sent} did not have the four tools (TOOLS)")
        messages = request.get("messages")
        if k == 1:
            if messages != [{"role": "user", "content": f"Claim: {CLAIM}"}]:
                raise NotYet(f"{sent} did not hold the conversation the set-up lines make, "
                             "just the claim")
            continue
        before = run.requests[k - 2].get("messages")
        if not isinstance(messages, list) or messages[:len(before)] != before:
            raise NotYet(f"{sent} did not hold the whole conversation so far")
        turn = messages[len(before)] if len(messages) > len(before) else None
        content = get(turn, "content") if turn is not None else None
        if (get(turn, "role") != "assistant" or not isinstance(content, (list, tuple))
                or [view(b) for b in content] != [view(b) for b in run.replies[k - 2].content]):
            raise NotYet(f"{sent} did not have that reply in the conversation as the "
                         "assistant's turn")
        tokens = run.state(k, "tokens")["tokens"]
        if tokens != run.used(k - 1):
            used = run.used(k - 1)
            replies = ("the model's first reply" if k == 2 else
                       f"the model's first {count(k - 1)} replies")
            raise NotYet(f"{replies} used {used['input']:,} input and {used['output']:,} output "
                         f"tokens, and tokens held {short(tokens)} when your loop asked the model "
                         "again")
    run.request(len(run.script))
    # The tokens in every result the loop returned, in every made-up check.
    for run in runs.values():
        if run.ended == "returned" and is_finished(run.result):
            n = len(run.requests)
            if run.result["tokens"] != run.used(n):
                used = run.used(n)
                replies = "its reply" if n == 1 else f"its {count(n)} replies"
                raise NotYet(f"{run.said(n)}, and the result your loop returned had tokens "
                             f"{short(run.result['tokens'])}, where {replies} used "
                             f"{used['input']:,} input and {used['output']:,} output tokens")


def rule_2(runs):
    """Run its lookups. The rule gives no order, so none is required."""
    run = runs["lookups"]
    asked = []      # (reply number, name, input) of every lookup asked for so far
    for k in range(1, len(run.script) + 1):
        before = run.state(k)["lookups so far"]
        state = run.state(k + 1, "steps", "trace", "read_so_far")
        asked += [(k, call.name, call.input) for call in run.calls(k)]
        left = run.lookups[before:state["lookups so far"]]     # the lookups made for reply k
        made = len(left)
        for call in run.calls(k):
            if (call.name, call.input) in left:
                left.remove((call.name, call.input))
            elif left:
                raise NotYet(f"{run.said(k)}, and your loop called lookup{short(left[0])}, "
                             f"where the call's name and input were {call.name!r} and "
                             f"{call.input!r}")
            else:
                raise NotYet(f"{run.said(k)}, and your loop had not called lookup() for the "
                             f"{call.name} when it asked the model again")
        if left:
            raise NotYet(f"{run.said(k)}, and your loop called lookup() {count(made, 'time')} "
                         "for it before asking the model again")
        if state["steps"] != len(asked):
            raise NotYet(f"after the model's {nth(k)} reply, your loop had run "
                         f"{count(len(asked), 'lookup')}, and steps held {short(state['steps'])} "
                         "when it asked the model again")
        trace = state["trace"] if isinstance(state["trace"], list) else []
        entries = [e for e in trace if isinstance(e, dict) and e.get("tool") in LOOKUPS]
        left = list(entries)
        for j, name, args in asked:
            want = {"tool": name, "input": args, "result": wikipedia(name, args)}
            match = next((e for e in left if has_entry([e], want)), None)
            if match is not None:
                left.remove(match)
                continue
            same_tool = [e for e in left if e.get("tool") == name]
            if same_tool:
                raise NotYet(f"{run.said(j)}, and the trace entry for the {name} was "
                             f"{short(same_tool[0])}, which does not hold its tool, input and "
                             "result")
            other = [e for e in trace if e not in entries]
            if other:
                raise NotYet(f"after the model's {nth(k)} reply, the trace held "
                             f"{short(other[0])}, which is not a lookup's entry with its tool, "
                             "input and result")
            raise NotYet(f"{run.said(j)}, and the trace had no entry for the {name} when your "
                         "loop asked the model again")
        if left:
            raise NotYet(f"after the model's {nth(k)} reply, the trace held entries for "
                         f"{count(len(entries), 'lookup')}, where your loop had run "
                         f"{count(len(asked))}")
        kept = state["read_so_far"]
        kept = kept if isinstance(kept, list) else []
        for j, name, args in asked:
            result = wikipedia(name, args)
            if name == "search" and result in kept:
                raise NotYet(f"{run.said(j)}, and what the search returned was in read_so_far "
                             "when your loop asked the model again")
            if name != "search" and result not in kept:
                raise NotYet(f"{run.said(j)}, and what the {name} returned was not in "
                             "read_so_far when your loop asked the model again")
        reads = [wikipedia(name, args) for _, name, args in asked if name != "search"]
        if not same_items(kept, reads):
            raise NotYet(f"after the model's {nth(k)} reply, read_so_far held "
                         f"{count(len(kept), 'item')}, where {count(len(reads), 'read')} and "
                         "wikidata lookups had been run")


def rule_3(runs):
    """Send the results back."""
    run = runs["results"]
    for k in range(1, len(run.script) + 1):
        request = run.request(k + 1)
        said = f"{run.said(k)}, and"
        tail = after_reply(request)
        if not tail:
            raise NotYet(f"{said} the next request your loop sent ended with that reply, with "
                         "no user turn of results after it")
        if len(tail) > 1:
            raise NotYet(f"{said} the next request your loop sent had {count(len(tail))} turns "
                         "after that reply, where the rule says one")
        if get(tail[0], "role") != "user":
            raise NotYet(f"{said} in the next request your loop sent, the turn after that reply "
                         f"had the role {short(get(tail[0], 'role'))}, not 'user'")
        content = get(tail[0], "content")
        if not isinstance(content, list):
            raise NotYet(f"{said} in the next request your loop sent, the turn after that reply "
                         f"held {short(content)} rather than a list of results")
        for call in run.calls(k):
            matching = [item for item in content if get(item, "tool_use_id") == call.id]
            if not matching:
                raise NotYet(f"{said} the next request your loop sent held no result with the "
                             f"{call.name} call's id")
            if len(matching) > 1:
                raise NotYet(f"{said} the next request your loop sent held "
                             f"{count(len(matching))} results with the {call.name} call's id")
            if get(matching[0], "type") != "tool_result":
                raise NotYet(f"{said} the result with the {call.name} call's id had the type "
                             f"{short(get(matching[0], 'type'))}, not 'tool_result'")
            if not same_text(get(matching[0], "content"), wikipedia(call.name, call.input)):
                raise NotYet(f"{said} the result with the {call.name} call's id held "
                             f"{short(get(matching[0], 'content'))} rather than what lookup() "
                             "returned for that call")
        ids = {call.id for call in run.calls(k)}
        for item in content:
            if get(item, "type") == "tool_result" and get(item, "tool_use_id") not in ids:
                raise NotYet(f"{said} the next request your loop sent held {short(item)}, which "
                             "is not a result for any call in that reply")


def rule_4(runs):
    """Check the answer. What counts as a problem is whatever answer_problem() in agent.py says
    now, and the number of rejections is MAX_REJECTED as it is now, since part 3 lets you
    change agent.py."""
    def problem(call, page):
        return agent.answer_problem(agent.clean_answer(call.input), [PAGES[page]])

    def accepted(run, k, page, evidence, explanation):
        call = run.calls(k)[0]
        if problem(call, page) is not None:
            return      # agent.py's evidence check now rejects this answer
        if any(name == "answer" for name, _ in run.lookups):
            raise NotYet(f"{run.said(k)}, and your loop called lookup() for it")
        if len(run.requests) > k:
            back = sent_back(run.requests[k], call.id)
            if isinstance(back, str) and back.startswith(agent.REJECTED):
                raise NotYet(f"{run.said(k)}, and your loop sent it back as rejected: "
                             f"{short(back, 160)}")
        result = run.returned_after(k, "asked the model again instead of stopping")
        run.expect(k, result, "supported", evidence, explanation)
        if not any(has_entry(result["trace"], {"tool": "answer", "input": answer,
                                               "result": agent.ACCEPTED})
                   for answer in (call.input, agent.clean_answer(call.input))):
            raise NotYet(f"{run.said(k)}, and the trace your loop returned had no entry for that "
                         f"answer with the result ACCEPTED ({agent.ACCEPTED!r})")

    accepted(runs["accept"], 2, "Forrest Gump", ["directed by Robert Zemeckis"],
             "The page names him as the director.")

    n = max(agent.MAX_REJECTED, 1)
    run = runs["reject"]
    call = run.calls(2)[0]
    wrong = problem(call, "Forrest Gump")
    if wrong is not None and n > 1:
        if len(run.requests) == 2 and run.ended == "returned":
            raise NotYet(f"{run.said(2)}, and your loop returned a result instead of sending the "
                         "answer back")
        back = sent_back(run.request(3), call.id)
        if back is MISSING:
            raise NotYet(f"{run.said(2)}, and the next request your loop sent held no result "
                         "with that answer call's id")
        if not same_text(back, agent.REJECTED + wrong):
            raise NotYet(f"{run.said(2)}, and your loop sent back {short(back)}, where the rule "
                         "says REJECTED followed by the problem")
        result = run.returned_after(3, "asked the model again instead of stopping")
        run.expect(3, result, "doesn't say", [], "The page does not say where he was born.")

    run = runs["reject_often"]
    if wrong is not None:
        if len(run.requests) > n:
            answers = "reply was an answer" if n == 1 else f"{count(n)} replies were answers"
            raise NotYet(f"the model's first {answers} with a quote that is in nothing it had "
                         f"read, and your loop asked the model again after the {nth(n)} was "
                         "rejected")
        result = run.returned_after(n, "asked the model again")
        run.expect(n, result, None, [], agent.REJECTED_TOO_OFTEN.format(n=n),
                   f"REJECTED_TOO_OFTEN with n={n}")

    accepted(runs["clean"], 2, "Robert Zemeckis", ["He was born in Chicago, Illinois."], "")


def rule_5(runs):
    """Enforce the limit."""
    for key in ("limit_answer", "limit_again"):
        run = runs[key]
        m = run.max_steps
        over = m + 1    # the reply that asks for one lookup more than the limit
        call = run.calls(over)[0]
        said = f"{run.said(over)} with the limit of {m} lookups reached, and"
        run.request(over)
        if len(run.requests) == over and run.ended == "returned":
            raise NotYet(f"{said} your loop returned a result instead of sending back "
                         "OUT_OF_STEPS the first time")
        state = run.state(over + 1)
        ran = [lookup for lookup in run.lookups[:state["lookups so far"]]
               if lookup[0] in LOOKUPS]
        if len(ran) > m:
            raise NotYet(f"{said} your loop ran it")
        back = sent_back(run.request(over + 1), call.id)
        want = agent.OUT_OF_STEPS.format(n=m)
        if back is MISSING:
            raise NotYet(f"{said} the next request your loop sent held no result with that "
                         "call's id")
        if not same_text(back, want):
            raise NotYet(f"{said} your loop sent back {short(back)}, where the rule says "
                         f"OUT_OF_STEPS with n={m}: {want!r}")
        last, after = over + 1, " after OUT_OF_STEPS had been sent back"
        if any(lookup[0] in LOOKUPS for lookup in run.lookups[state["lookups so far"]:]):
            raise NotYet(f"{run.said(last)}{after}, and your loop ran it")
        result = run.returned_after(last, "asked the model again instead of stopping", after)
        if key == "limit_answer":
            run.expect(last, result, "doesn't say", [], "The page does not say where he was born.",
                       after=after)
        else:
            run.expect(last, result, None, [], agent.RAN_OUT, "RAN_OUT", after=after)
        if result["steps"] != m:
            raise NotYet(f"{run.said(last)}{after}, and the result your loop returned had steps "
                         f"{short(result['steps'])}, where {count(m, 'lookup')} had been run")


def rule_6(runs):
    """Stop when the model stops."""
    run = runs["remind"]
    if len(run.requests) == 1 and run.ended == "returned":
        raise NotYet(f"{run.said(1)}, and your loop returned a result instead of reminding the "
                     "model")
    tail = after_reply(run.request(2))
    if len(tail) != 1 or get(tail[0], "role") != "user" or not same_text(
            get(tail[0], "content"), agent.REMINDER):
        raise NotYet(f"{run.said(1)}, and the next request your loop sent did not end with one "
                     f"user turn holding REMINDER ({agent.REMINDER!r})")
    result = run.returned_after(2, "asked the model again instead of stopping")
    run.expect(2, result, "doesn't say", [], "The page does not say where he was born.")
    if not has_entry(result["trace"], {"tool": "(reminder)", "input": {},
                                       "result": agent.REMINDED}):
        raise NotYet(f"{run.said(1)}, and the trace your loop returned had no entry for the "
                     f"reminder (tool '(reminder)', input {{}}, result REMINDED)")

    run = runs["no_answer"]
    result = run.returned_after(2, "asked the model a third time instead of stopping")
    run.expect(2, result, None, [], agent.NO_ANSWER, "NO_ANSWER")

    run = runs["refusal"]
    result = run.returned_after(1, "asked the model again instead of stopping")
    run.expect(1, result, None, [], agent.DECLINED, "DECLINED")


# ---------- putting it together ----------

@contextlib.contextmanager
def offline():
    """No key and no network while the check runs, whatever the loop does."""
    keys = {name: os.environ.pop(name) for name in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")
            if name in os.environ}
    real = {name: getattr(wiki, name) for name in LOOKUPS}

    def no_network(*args, **kwargs):
        raise RuntimeError("this check has no network, and Wikipedia was called directly")
    for name in LOOKUPS:
        setattr(wiki, name, no_network)
    try:
        yield
    finally:
        os.environ.update(keys)
        for name, function in real.items():
            setattr(wiki, name, function)


def load(path):
    """my_loop.py as a module, loaded fresh from its file."""
    spec = importlib.util.spec_from_file_location("my_loop", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check(path=None):
    """One entry per rule: None if it passes, or the sentence saying what happened."""
    path = Path(path or MY_LOOP).resolve()
    loop_file = str(path)
    with offline(), contextlib.redirect_stdout(io.StringIO()):
        module, error, alive = in_thread(lambda: load(loop_file), loop_file)
        if alive or isinstance(error, DidNotStop):
            return [f"my_loop.py did not finish loading: after {TIME_LIMIT} seconds it was "
                    "still running"] * len(RULES)
        if error is not None:
            line = line_in(error, loop_file)
            where = f" at line {line}" if line else ""
            return [f"my_loop.py could not be loaded, because of an error{where}: "
                    f"{described(error)}"] * len(RULES)
        run_agent = getattr(module, "run_agent", None)
        if not callable(run_agent):
            return ["my_loop.py has no function called run_agent"] * len(RULES)
        runs, seconds = {}, TIME_LIMIT
        for key in SCENARIOS:
            runs[key] = Run(key, run_agent, loop_file, seconds)
            if runs[key].ended == "did not stop":
                seconds = AFTER_A_HANG   # so a loop that never stops is not waited for 12 times
    problems = []
    for rule in (rule_1, rule_2, rule_3, rule_4, rule_5, rule_6):
        try:
            rule(runs)
            problems.append(None)
        except NotYet as not_yet:
            problems.append(str(not_yet))
        except Exception as error:  # noqa: BLE001  something the loop made that cannot be read
            problems.append(f"the check could not read what your loop did ({described(error)})")
    return problems


def lines(problems):
    """The six lines the check prints."""
    shown = []
    for number, (title, problem) in enumerate(zip(RULES, problems), 1):
        if problem is None:
            shown.append(f"ok         {number}. {title}")
        else:
            shown.append(f"NOT YET    {number}. {title}: {problem}"
                         f"{'' if problem.endswith('.') else '.'}")
    return shown


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check the loop in my_loop.py.")
    parser.add_argument("--use-reference", action="store_true",
                        help="keep your copy on the reference loop")
    args = parser.parse_args(argv)
    saved = agent.LOOP_CHECK
    if args.use_reference:
        saved.parent.mkdir(parents=True, exist_ok=True)
        saved.write_text(f"reference\n{KEPT_REFERENCE}\n")
        print(KEPT_REFERENCE)
        return 0

    problems = check(MY_LOOP)
    printed = lines(problems)
    print("\n".join(printed))
    if all(problem is None for problem in problems):
        print(f"\n{PASSED}")
        # The agent runs on my_loop.py once this file's first line is "yours".
        saved.parent.mkdir(parents=True, exist_ok=True)
        saved.write_text("yours\n" + "\n".join(printed) + f"\n\n{PASSED}\n")
        return 0
    print(f"\n{FAILED}")
    if agent.which_loop() == "yours":
        saved.unlink(missing_ok=True)   # back on the reference loop until the check passes again
    return 1


if __name__ == "__main__":
    sys.exit(main())
