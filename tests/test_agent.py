"""Offline tests: a scripted stand-in for Claude and for Wikipedia, so the loop,
the step budget and the evidence check can be tested with no API key and no
network."""

import sys
from pathlib import Path
from types import SimpleNamespace as NS

sys.path.insert(0, str(Path(__file__).parent.parent))

import agent  # noqa: E402
import baselines  # noqa: E402
import evaluate  # noqa: E402
import wiki  # noqa: E402


def tool_use(name, args, i):
    return NS(type="tool_use", name=name, input=args, id=f"call{i}")


def reply(*blocks, stop="tool_use"):
    return NS(content=list(blocks), stop_reason=stop, usage=NS(input_tokens=100, output_tokens=10))


class ScriptedClaude:
    """Returns the scripted responses in order, and records what it was sent."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.sent = []
        self.messages = self

    def create(self, **kwargs):
        self.sent.append(kwargs)
        return self.responses.pop(0)


PAGES = {
    "Forrest Gump": "Forrest Gump is a 1994 American film directed by Robert Zemeckis.",
    "Robert Zemeckis": "Robert Lee Zemeckis (born May 14, 1952) is an American filmmaker. "
                       "He was born in Chicago, Illinois.",
}


def fake_lookup(name, args):
    if name == "search":
        return "1. Forrest Gump: 1994 film"
    if name == "read":
        return PAGES.get(args["title"], "no such page")
    return "Wikidata: nothing"


def test_answer_with_real_evidence_is_accepted():
    claude = ScriptedClaude([
        reply(tool_use("search", {"query": "1994 Best Picture"}, 1)),
        reply(tool_use("read", {"title": "Forrest Gump"}, 2)),
        reply(tool_use("read", {"title": "Robert Zemeckis"}, 3)),
        reply(tool_use("answer", {"verdict": "supported",
                                  "evidence": ["directed by Robert Zemeckis",
                                               "He was born in Chicago,  Illinois."],
                                  "explanation": "Zemeckis was born in Chicago."}, 4)),
    ])
    result = agent.run_agent("claim", client=claude, lookup=fake_lookup)
    assert result["verdict"] == "supported"
    assert result["steps"] == 3
    assert result["tokens"] == {"input": 400, "output": 40}
    # Each tool result went back with the id of the call it answers.
    # (The list is shared, so the last entry is Claude's answer; the one before is ours.)
    last_user = claude.sent[-1]["messages"][-2]
    assert last_user["content"][0]["tool_use_id"] == "call3"


def test_made_up_evidence_is_rejected():
    claude = ScriptedClaude([
        reply(tool_use("read", {"title": "Forrest Gump"}, 1)),
        reply(tool_use("answer", {"verdict": "supported",
                                  "evidence": ["Zemeckis was born in Ohio."],
                                  "explanation": "x"}, 2)),
        reply(tool_use("answer", {"verdict": "doesn't say", "evidence": [],
                                  "explanation": "The page doesn't give a birthplace."}, 3)),
    ])
    result = agent.run_agent("claim", client=claude, lookup=fake_lookup)
    assert result["verdict"] == "doesn't say"
    rejected = [t for t in result["trace"] if t["result"].startswith("Answer rejected")]
    assert len(rejected) == 1


def test_step_budget_stops_the_agent():
    claude = ScriptedClaude([reply(tool_use("search", {"query": f"q{i}"}, i)) for i in range(10)])
    result = agent.run_agent("claim", client=claude, max_steps=3, lookup=fake_lookup)
    assert result["verdict"] is None
    assert result["steps"] == 3
    assert "ran out of steps" in result["explanation"]
    assert any(t["result"].startswith("You have used all 3 steps") for t in result["trace"])


def test_agent_can_answer_after_the_warning():
    claude = ScriptedClaude(
        [reply(tool_use("search", {"query": f"q{i}"}, i)) for i in range(3)]
        + [reply(tool_use("answer", {"verdict": "doesn't say", "evidence": [],
                                     "explanation": "ran short"}, 9))])
    result = agent.run_agent("claim", client=claude, max_steps=2, lookup=fake_lookup)
    assert result["verdict"] == "doesn't say"
    assert result["steps"] == 2


def test_stopping_without_answer_gets_one_reminder():
    text = NS(type="text", text="I think it's true.")
    claude = ScriptedClaude([reply(text, stop="end_turn"), reply(text, stop="end_turn")])
    result = agent.run_agent("claim", client=claude, lookup=fake_lookup)
    assert result["verdict"] is None
    assert len(claude.sent) == 2


def test_refusal_ends_the_check():
    claude = ScriptedClaude([reply(stop="refusal")])
    result = agent.run_agent("claim", client=claude, lookup=fake_lookup)
    assert result["verdict"] is None


def test_scoring_hover_and_fever():
    hover_true = {"source": "hover", "label": "SUPPORTED"}
    hover_false = {"source": "hover", "label": "NOT_SUPPORTED"}
    fever_nei = {"source": "fever", "label": "NOT ENOUGH INFO"}
    assert evaluate.is_correct(hover_true, "supported")
    assert evaluate.is_correct(hover_false, "refuted")
    assert evaluate.is_correct(hover_false, "doesn't say")
    assert not evaluate.is_correct(hover_true, None)
    assert evaluate.is_correct(fever_nei, "doesn't say")
    assert not evaluate.is_correct(fever_nei, "refuted")
    mine = {"source": "mine", "label": "refuted"}
    assert evaluate.is_correct(mine, "refuted")
    assert not evaluate.is_correct(mine, "doesn't say")
    assert evaluate.group_of(mine) == "Your claims"
    assert evaluate.group_of(fever_nei) == "FEVER"


def test_sections_and_read(monkeypatch):
    text = "Intro line.\n\n== Early life ==\nBorn in Chicago.\n\n=== School ===\nWent to school.\n"
    monkeypatch.setattr(wiki, "page_text", lambda title: (text, "Robert Zemeckis"))
    assert wiki.split_sections(text) == [("Introduction", "Intro line."),
                                         ("Early life", "Born in Chicago."),
                                         ("School", "Went to school.")]
    assert "Sections: Early life, School" in wiki.read("zemeckis")
    assert "Born in Chicago." in wiki.read("zemeckis", "early life")
    assert "no section called" in wiki.read("zemeckis", "Career")


def test_one_search_reads_the_top_hit():
    query = NS(type="text", text='"1994 Best Picture"')
    answer = NS(type="text", text='{"verdict": "refuted", "explanation": "wrong state"}')
    claude = ScriptedClaude([reply(query, stop="end_turn"), reply(answer, stop="end_turn")])
    read_titles, queries = [], []
    result = baselines.one_search(
        "claim", client=claude,
        search=lambda q: queries.append(q) or "1. Forrest Gump: snippet\n2. Other: x",
        read=lambda title: read_titles.append(title) or "page text")
    assert queries == ["1994 Best Picture"]
    assert read_titles == ["Forrest Gump"]
    assert result["tokens"] == {"input": 200, "output": 20}
    assert result["verdict"] == "refuted"
    assert result["steps"] == 2


def test_lookup_prints_and_logs(monkeypatch, tmp_path, capsys):
    import lookup
    monkeypatch.setattr(lookup, "LOG", tmp_path / "lookups.jsonl")
    monkeypatch.setattr(wiki, "search", lambda q: f"1. Forrest Gump: {q}")
    monkeypatch.setattr(sys, "argv", ["lookup.py", "search", "1994 Best Picture"])
    lookup.main()
    assert "1. Forrest Gump: 1994 Best Picture" in capsys.readouterr().out
    assert '"tool": "search"' in (tmp_path / "lookups.jsonl").read_text()
