"""The fact-checking agent: a loop around Claude.

Read this file top to bottom. The whole agent is the function run_agent()
below. Each turn of the loop:

  1. sends Claude the conversation so far,
  2. runs whatever tool Claude asked for,
  3. adds the tool's result to the conversation,

and stops when Claude calls answer() with evidence that checks out, when it
runs out of steps, or when its answer has been sent back three times.
"""

import re
from pathlib import Path

import anthropic

import wiki

MODEL = "claude-haiku-5-5"
MAX_STEPS = 12          # the most tool calls the agent may make for one claim
MAX_REJECTED = 3        # the most answers the loop sends back before it gives up
INSTRUCTIONS = Path(__file__).parent / "instructions.md"
VERDICTS = ["supported", "refuted", "doesn't say"]

# Price per million tokens for MODEL (prompts under 100K tokens), used only to
# report cost. Input, output.
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


def answer_problem(answer, read_so_far):
    """Say what is wrong with an answer, or return None if it passes."""
    quotes = [quote for quote in answer["evidence"] if quote.strip()]
    if answer["verdict"] != "doesn't say" and not quotes:
        return ("A verdict of supported or refuted needs at least one quote from something "
                "you read in this check. If you found none, the verdict is \"doesn't say\".")
    bad = unsupported_quotes(quotes, read_so_far)
    if bad:
        return "These quotes are not in anything you read in this check: " + " | ".join(bad)
    return None


# ---------- the loop ----------

def run_agent(claim, client=None, max_steps=MAX_STEPS, lookup=run_tool):
    """Check one claim. Returns a dict with the verdict, the evidence, the
    trace of every step, and the tokens used."""
    client = client or anthropic.Anthropic()
    system = INSTRUCTIONS.read_text()
    messages = [{"role": "user", "content": f"Claim: {claim}"}]
    trace, read_so_far = [], []
    tokens = {"input": 0, "output": 0}
    steps = 0
    rejected = 0        # how many answers the loop has sent back
    warned = False      # has it been told it is out of steps?

    while True:
        response = client.messages.create(
            model=MODEL, max_tokens=16000, system=system, tools=TOOLS, messages=messages,
        )
        tokens["input"] += response.usage.input_tokens
        tokens["output"] += response.usage.output_tokens
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "refusal":
            return finish(claim, None, [], "The model declined to check this claim.",
                          trace, tokens, steps)

        calls = [block for block in response.content if block.type == "tool_use"]
        if not calls:
            # Claude stopped without calling a tool. Remind it once how to finish.
            if trace and trace[-1]["tool"] == "(reminder)":
                return finish(claim, None, [], "The agent stopped without answering.",
                              trace, tokens, steps)
            trace.append({"tool": "(reminder)", "input": {}, "result": "Asked it to call answer()."})
            messages.append({"role": "user", "content": "Please finish by calling answer()."})
            continue

        results = []
        warned_before = warned
        for call in calls:
            if call.name == "answer":
                problem = answer_problem(call.input, read_so_far)
                if problem is None:
                    trace.append({"tool": "answer", "input": call.input, "result": "accepted"})
                    return finish(claim, call.input["verdict"], call.input["evidence"],
                                  call.input["explanation"], trace, tokens, steps)
                result = "Answer rejected. " + problem
                rejected += 1
                if rejected >= MAX_REJECTED:
                    trace.append({"tool": "answer", "input": call.input, "result": result})
                    return finish(claim, None, [],
                                  f"The agent's answer was rejected {rejected} times.",
                                  trace, tokens, steps)
            elif steps >= max_steps:
                if warned_before:
                    # It was told last turn that it was out of steps: stop here.
                    return finish(claim, None, [], "The agent ran out of steps.",
                                  trace, tokens, steps)
                result = f"You have used all {max_steps} steps. Call answer() now."
                warned = True
            else:
                steps += 1
                result = lookup(call.name, call.input)
                if call.name != "search":  # snippets are too short to count as evidence
                    read_so_far.append(result)
            trace.append({"tool": call.name, "input": call.input, "result": result})
            results.append({"type": "tool_result", "tool_use_id": call.id, "content": result})

        messages.append({"role": "user", "content": results})


def finish(claim, verdict, evidence, explanation, trace, tokens, steps):
    cost = (tokens["input"] * PRICE[0] + tokens["output"] * PRICE[1]) / 1_000_000
    return {
        "claim": claim, "verdict": verdict, "evidence": evidence,
        "explanation": explanation, "trace": trace,
        "steps": steps,
        "tokens": tokens, "cost_usd": round(cost, 6),
    }
