"""The fact-checking agent: everything but its loop.

Read this file top to bottom. It holds the settings, the four tools the model
can ask for, the evidence check that answers must pass, the sentences a loop
sends back and records, and finish(), which every loop returns.

The loop itself is in another file. Each turn it sends the model the
conversation so far, runs the lookups the model asked for, and adds what they
returned to the conversation, until the model gives an answer that passes the
evidence check or a limit ends it first. You design it in step 1a, as an
outline that Claude translates into my_loop.py. In Part 0, before your loop
has ever passed the check (uv run python check_loop.py), the agent uses the
reference loop in reference_loop.py. Once your loop has passed, the agent runs
on your loop and no other: if a later check finds a rule broken, no agent run
starts until your loop passes again. run_agent(), at the bottom of this file,
decides.
"""

import re
from pathlib import Path

import wiki

MODEL = "claude-haiku-5-5"
MAX_STEPS = 12          # the most lookups the agent may make for one claim
MAX_REJECTED = 3        # the most answers the loop sends back before it gives up
INSTRUCTIONS = Path(__file__).parent / "instructions.md"
VERDICTS = ["supported", "refuted", "doesn't say"]

# Price per million tokens for MODEL (prompts under 100K tokens), used only to
# report cost, once your loop counts tokens (extra credit, step 3b). Input, output.
PRICE = (0.10, 0.50)

# ---------- the tools Claude can ask for ----------

TOOLS = [
    {
        "name": "search",
        "description": "Search Wikipedia. Returns the top page titles, each with a short snippet.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    {
        "name": "read",
        "description": ("Read one section of a Wikipedia page. With no section, returns the "
                        "opening paragraphs and the list of the page's sections."),
        "input_schema": {
            "type": "object",
            "properties": {"title": {"type": "string"}, "section": {"type": "string"}},
            "required": ["title"],
            "additionalProperties": False,
        },
    },
    {
        "name": "wikidata",
        "description": ("Look up one structured fact on Wikidata, Wikipedia's sister site. "
                        "Example: entity 'Robert Zemeckis', property 'place of birth'."),
        "input_schema": {
            "type": "object",
            "properties": {"entity": {"type": "string"}, "property": {"type": "string"}},
            "required": ["entity", "property"],
            "additionalProperties": False,
        },
    },
    {
        "name": "answer",
        "description": ("Give your final verdict and end the check. A verdict of supported or "
                        "refuted needs at least one evidence item. Each evidence item must be "
                        "copied word for word from a read() or wikidata() result in this check."),
        "input_schema": {
            "type": "object",
            "properties": {
                "verdict": {"type": "string", "enum": VERDICTS},
                "evidence": {"type": "array", "items": {"type": "string"}},
                "explanation": {"type": "string"},
            },
            "required": ["verdict", "evidence", "explanation"],
            "additionalProperties": False,
        },
    },
]


def run_tool(name, args):
    """Run one lookup tool and return its text result."""
    if name == "search":
        return wiki.search(args["query"])
    if name == "read":
        return wiki.read(args["title"], args.get("section"))
    if name == "wikidata":
        return wiki.wikidata(args["entity"], args["property"])
    return f"There is no tool called {name!r}."


# ---------- the evidence check ----------

def normalize(text):
    text = text.replace("’", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", text).strip().lower()


def unsupported_quotes(evidence, read_so_far):
    """Return the evidence items that don't appear in anything the agent read."""
    seen = normalize(" ".join(read_so_far))
    return [quote for quote in evidence if normalize(quote) not in seen]


def clean_answer(args):
    """The answer() call's input, with the evidence always a list of quotes and
    always an explanation. Claude doesn't always follow the tool's schema: it
    sometimes sends one quote as a plain string (and looping over a string
    would check it one letter at a time), or leaves the explanation out."""
    evidence = args.get("evidence") or []
    if isinstance(evidence, str):
        evidence = [evidence]
    return {**args, "evidence": evidence, "explanation": args.get("explanation") or ""}


def answer_problem(answer, read_so_far):
    """Say what is wrong with an answer, or return None if it passes."""
    if answer.get("verdict") not in VERDICTS:
        return "The verdict must be \"supported\", \"refuted\" or \"doesn't say\"."
    quotes = [quote for quote in answer["evidence"] if quote.strip()]
    if answer["verdict"] != "doesn't say" and not quotes:
        return ("A verdict of supported or refuted needs at least one quote from something "
                "you read in this check. If you found none, the verdict is \"doesn't say\".")
    bad = unsupported_quotes(quotes, read_so_far)
    if bad:
        return "These quotes are not in anything you read in this check: " + " | ".join(bad)
    return None


# ---------- what a loop sends back and records ----------

# The exact sentences a loop uses, so that check_loop.py, the results viewer
# and both loops agree on them.
ACCEPTED = "accepted"                                   # the result recorded for an accepted answer
REJECTED = "Answer rejected. "                          # followed by what answer_problem() said
REJECTED_TOO_OFTEN = "The agent's answer was rejected {n} times."
OUT_OF_STEPS = "You have used all {n} steps. Call answer() now."
RAN_OUT = "The agent ran out of steps."
REMINDER = "Please finish by calling answer()."          # sent to the model
REMINDED = "Asked it to call answer()."                  # recorded in the trace, tool "(reminder)"
NO_ANSWER = "The agent stopped without answering."
DECLINED = "The model declined to check this claim."


def finish(claim, verdict, evidence, explanation, trace, steps, tokens=None):
    """What a loop returns when it stops: the verdict, the evidence, the
    explanation, the trace and the number of lookups. A loop that counts the
    tokens the model's replies used (extra credit, step 3b) passes them last,
    as {"input": ..., "output": ...}; then the result also holds them and what
    they cost."""
    if isinstance(steps, dict):  # a loop written before Nov 12 passed tokens, then steps
        steps, tokens = tokens, steps
    result = {
        "claim": claim, "verdict": verdict, "evidence": evidence,
        "explanation": explanation, "trace": trace,
        "steps": steps,
    }
    if tokens is not None:
        cost = (tokens["input"] * PRICE[0] + tokens["output"] * PRICE[1]) / 1_000_000
        result.update(tokens=tokens, cost_usd=round(cost, 6))
    return result


# ---------- which loop runs ----------

LOOP_CHECK = Path(__file__).parent / "runs" / "part1" / "loop-check.txt"
# The line check_loop.py prints, after its six, for a loop that passes finish() a token count.
TOKEN_RULE = "Count the tokens (extra credit)"


NOT_PASSED = ("The agent runs only on your own loop from step 1a on, and the loop in my_loop.py has not "
              "passed the check: run uv run python check_loop.py, fix the first NOT YET line, then run "
              "this command again.")


class LoopNotPassed(Exception):
    """The student's loop passed the check once and does not pass it now."""


def which_loop():
    """From runs/part1/loop-check.txt, which check_loop.py writes: "yours" while its first line
    says the loop in my_loop.py passed; "reference" while there is no such file, because the loop
    has never passed (Part 0, which the reference loop runs); "not passed" for any other file: the
    loop passed once and a later check found a rule broken, or the file is an old record of a
    choice to keep the reference loop, which the homework no longer offers."""
    try:
        lines = LOOP_CHECK.read_text().splitlines()
    except FileNotFoundError:
        return "reference"
    except (OSError, UnicodeDecodeError):  # a file that cannot be read
        return "not passed"
    return "yours" if lines and lines[0] == "yours" else "not passed"


def counts_tokens(path=None):
    """Whether this copy's loop counts tokens: runs/part1/loop-check.txt says the loop in
    my_loop.py passes, with the token line ok. Token and cost numbers are shown (by check.py,
    evaluate.py and the results viewer) only then, for every run, the baselines' too."""
    try:
        lines = Path(path or LOOP_CHECK).read_text().splitlines()
    except (OSError, UnicodeDecodeError):
        return False
    return bool(lines) and lines[0] == "yours" and f"ok         {TOKEN_RULE}" in lines


def run_agent(claim, client=None, max_steps=MAX_STEPS, lookup=run_tool):
    """Check one claim with the loop in use: yours (my_loop.py), or, before
    your loop has ever passed the check, the reference loop (reference_loop.py).
    Returns what finish() returns."""
    # Imported here, not at the top, because both files import from this one.
    loop_now = which_loop()
    if loop_now == "not passed":
        raise LoopNotPassed(NOT_PASSED)
    if loop_now == "yours":
        import my_loop as loop
    else:
        import reference_loop as loop
    return loop.run_agent(claim, client=client, max_steps=max_steps, lookup=lookup)
