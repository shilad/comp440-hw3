"""The two baselines the agent is compared against.

no_tools: Claude answers from what it already knows, with no lookups.
one_search: Claude writes one Wikipedia search query, the program reads the top
page's opening paragraphs, and Claude answers from that page. A fixed
pipeline: one search, one page, no second chance. (Searching for the whole
claim as written usually finds nothing, because Wikipedia's search wants
every word to match.)
"""

import json
import re

import anthropic

import wiki
from agent import MODEL, PRICE, VERDICTS

ASK = (
    "Is this claim supported or refuted by English Wikipedia, or does Wikipedia not say? "
    'Reply with only a JSON object: {"verdict": one of ' + json.dumps(VERDICTS)
    + ', "explanation": one sentence}.\n\nClaim: '
)


def _ask(client, prompt):
    response = client.messages.create(
        model=MODEL, max_tokens=4000, messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(b.text for b in response.content if b.type == "text")
    tokens = {"input": response.usage.input_tokens, "output": response.usage.output_tokens}
    match = re.search(r"\{.*\}", text, re.S)
    try:
        parsed = json.loads(match.group(0)) if match else {}
    except json.JSONDecodeError:
        parsed = {}
    verdict = parsed.get("verdict") if parsed.get("verdict") in VERDICTS else None
    return verdict, parsed.get("explanation", text.strip()), tokens


def _result(claim, verdict, explanation, trace, tokens):
    cost = (tokens["input"] * PRICE[0] + tokens["output"] * PRICE[1]) / 1_000_000
    return {"claim": claim, "verdict": verdict, "evidence": [], "explanation": explanation,
            "trace": trace, "steps": sum(1 for t in trace if t["tool"] != "answer"),
            "tokens": tokens, "cost_usd": round(cost, 6)}


def no_tools(claim, client=None):
    client = client or anthropic.Anthropic()
    verdict, explanation, tokens = _ask(client, ASK + claim)
    return _result(claim, verdict, explanation, [], tokens)


QUERY = ("Write the one Wikipedia search query most likely to find the page that settles this "
         "claim. Reply with only the query, a few words long.\n\nClaim: ")


def one_search(claim, client=None, search=wiki.search, read=wiki.read):
    client = client or anthropic.Anthropic()
    response = client.messages.create(
        model=MODEL, max_tokens=4000, messages=[{"role": "user", "content": QUERY + claim}],
    )
    query = "".join(b.text for b in response.content if b.type == "text").strip().strip('"')
    first = {"input": response.usage.input_tokens, "output": response.usage.output_tokens}
    hits = search(query)
    trace = [{"tool": "search", "input": {"query": query}, "result": hits}]
    top = re.match(r"1\. (.+?):", hits)
    page = read(top.group(1)) if top else "(no page found)"
    trace.append({"tool": "read", "input": {"title": top.group(1) if top else None}, "result": page})
    verdict, explanation, tokens = _ask(
        client, "Answer using only this Wikipedia text.\n\n" + page + "\n\n" + ASK + claim)
    tokens = {k: tokens[k] + first[k] for k in tokens}
    return _result(claim, verdict, explanation, trace, tokens)
