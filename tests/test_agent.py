"""Offline tests: a scripted stand-in for Claude and for Wikipedia, so the loop,
the step budget and the evidence check can be tested with no API key and no
network."""

import sys
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

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


def test_supported_or_refuted_needs_a_quote():
    claude = ScriptedClaude([
        reply(tool_use("read", {"title": "Forrest Gump"}, 1)),
        reply(tool_use("answer", {"verdict": "supported", "evidence": [],
                                  "explanation": "x"}, 2)),
        reply(tool_use("answer", {"verdict": "refuted", "evidence": [" "],
                                  "explanation": "x"}, 3)),
        reply(tool_use("answer", {"verdict": "doesn't say", "evidence": [],
                                  "explanation": "The page doesn't give a birthplace."}, 4)),
    ])
    result = agent.run_agent("claim", client=claude, lookup=fake_lookup)
    assert result["verdict"] == "doesn't say"
    rejected = [t for t in result["trace"] if t["result"].startswith("Answer rejected")]
    assert len(rejected) == 2
    assert all("needs at least one quote" in t["result"] for t in rejected)


def test_evidence_as_one_string_is_checked_as_one_quote():
    # The schema asks for a list, but Claude sometimes sends a plain string.
    claude = ScriptedClaude([
        reply(tool_use("read", {"title": "Forrest Gump"}, 1)),
        reply(tool_use("answer", {"verdict": "supported",
                                  "evidence": "Zemeckis was born in Ohio.",
                                  "explanation": "x"}, 2)),
        reply(tool_use("answer", {"verdict": "supported",
                                  "evidence": "directed by Robert Zemeckis",
                                  "explanation": "x"}, 3)),
    ])
    result = agent.run_agent("claim", client=claude, lookup=fake_lookup)
    rejected = [t for t in result["trace"] if t["result"].startswith("Answer rejected")]
    assert len(rejected) == 1
    assert "Zemeckis was born in Ohio." in rejected[0]["result"]
    assert result["verdict"] == "supported"
    assert result["evidence"] == ["directed by Robert Zemeckis"]


def test_missing_evidence_is_an_empty_list():
    claude = ScriptedClaude([
        reply(tool_use("answer", {"verdict": "doesn't say", "explanation": "x"}, 1)),
    ])
    result = agent.run_agent("claim", client=claude, lookup=fake_lookup)
    assert result["verdict"] == "doesn't say"
    assert result["evidence"] == []


def test_missing_explanation_is_empty():
    claude = ScriptedClaude([
        reply(tool_use("answer", {"verdict": "doesn't say", "evidence": []}, 1)),
    ])
    result = agent.run_agent("claim", client=claude, lookup=fake_lookup)
    assert result["verdict"] == "doesn't say"
    assert result["explanation"] == ""


def test_missing_or_unknown_verdict_is_rejected():
    claude = ScriptedClaude([
        reply(tool_use("answer", {"evidence": [], "explanation": "x"}, 1)),
        reply(tool_use("answer", {"verdict": "true", "evidence": [], "explanation": "x"}, 2)),
        reply(tool_use("answer", {"verdict": "doesn't say", "evidence": [],
                                  "explanation": "x"}, 3)),
    ])
    result = agent.run_agent("claim", client=claude, lookup=fake_lookup)
    assert result["verdict"] == "doesn't say"
    rejected = [t for t in result["trace"] if t["result"].startswith("Answer rejected")]
    assert len(rejected) == 2
    assert all("The verdict must be" in t["result"] for t in rejected)


def test_rejected_answers_stop_the_agent():
    made_up = {"verdict": "supported", "evidence": ["Zemeckis was born in Ohio."],
               "explanation": "x"}
    claude = ScriptedClaude([reply(tool_use("answer", made_up, i)) for i in range(10)])
    result = agent.run_agent("claim", client=claude, lookup=fake_lookup)
    assert result["verdict"] is None
    assert "rejected 3 times" in result["explanation"]
    assert len(claude.sent) == 3


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


def test_no_verdict_is_always_wrong():
    for label in ["SUPPORTED", "NOT_SUPPORTED"]:
        assert not evaluate.is_correct({"source": "hover", "label": label}, None)
    for label in ["SUPPORTS", "REFUTES", "NOT ENOUGH INFO"]:
        assert not evaluate.is_correct({"source": "fever", "label": label}, None)
    assert not evaluate.is_correct({"source": "mine", "label": "doesn't say"}, None)


def test_sections_and_read(monkeypatch):
    text = "Intro line.\n\n== Early life ==\nBorn in Chicago.\n\n=== School ===\nWent to school.\n"
    monkeypatch.setattr(wiki, "page_text", lambda title: (text, "Robert Zemeckis"))
    assert wiki.split_sections(text) == [("Introduction", "Intro line."),
                                         ("Early life", "Born in Chicago."),
                                         ("School", "Went to school.")]
    assert "Sections: Early life, School" in wiki.read("zemeckis")
    assert "Born in Chicago." in wiki.read("zemeckis", "early life")
    assert "no section called" in wiki.read("zemeckis", "Career")


class FakeResponse:
    """What requests.get() returns, for a scripted Wikipedia."""

    def __init__(self, status, data=None, retry_after=None):
        self.status_code = status
        self.headers = {"Retry-After": retry_after} if retry_after else {}
        self.data = data

    def json(self):
        return self.data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise wiki.requests.HTTPError(f"{self.status_code} error")


FOUND = {"query": {"search": [{"title": "Forrest Gump", "snippet": "1994 film"}]}}


def scripted_wikipedia(monkeypatch, tmp_path, responses):
    """Send wiki.py's requests to the scripted responses, in order, with the
    cache in tmp_path. Returns the headers of each request and each pause.
    WIKIPEDIA_CONTACT starts unset, whatever your own environment or .env says,
    and the warning about it starts unprinted, as at the start of a run."""
    sent, pauses = [], []
    responses = list(responses)
    monkeypatch.setattr(wiki, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(wiki.requests, "get",
                        lambda url, **kwargs: sent.append(kwargs["headers"]) or responses.pop(0))
    monkeypatch.setattr(wiki.time, "sleep", pauses.append)
    monkeypatch.delenv("WIKIPEDIA_CONTACT", raising=False)
    monkeypatch.setattr(wiki, "_warned", False)
    return sent, pauses


def test_user_agent_gives_your_contact(monkeypatch, tmp_path, capsys):
    sent, _ = scripted_wikipedia(monkeypatch, tmp_path, [FakeResponse(200, FOUND)])
    # Set after wiki.py was imported, as when a script loads .env late.
    monkeypatch.setenv("WIKIPEDIA_CONTACT", "student@macalester.edu")
    assert wiki.search("Forrest Gump").startswith("1. Forrest Gump")
    assert sent[0]["User-Agent"] == ("COMP440-HW3/0.1 (student@macalester.edu; "
                                     "Macalester College course assignment)")
    assert "WIKIPEDIA_CONTACT" not in capsys.readouterr().err


def test_without_a_contact_it_gives_the_course_site_and_warns_once(monkeypatch, tmp_path, capsys):
    sent, _ = scripted_wikipedia(monkeypatch, tmp_path,
                                 [FakeResponse(200, FOUND), FakeResponse(200, FOUND)])
    wiki.search("Forrest Gump")
    wiki.search("Robert Zemeckis")
    assert len(sent) == 2
    assert all(h["User-Agent"] == wiki.SHARED_USER_AGENT for h in sent)
    assert "https://shilad.github.io/comp440-website/" in wiki.SHARED_USER_AGENT
    assert capsys.readouterr().err.count("WIKIPEDIA_CONTACT is not set") == 1


def test_too_many_requests_waits_as_long_as_asked(monkeypatch, tmp_path):
    _, pauses = scripted_wikipedia(monkeypatch, tmp_path, [
        FakeResponse(429, retry_after="7"), FakeResponse(200, FOUND)])
    assert wiki.search("Forrest Gump").startswith("1. Forrest Gump")
    assert pauses == [7]
    # With no Retry-After header, it waits 2, 4, 8, ... seconds.
    _, pauses = scripted_wikipedia(monkeypatch, tmp_path, [
        FakeResponse(429), FakeResponse(429), FakeResponse(200, FOUND)])
    assert wiki.search("Robert Zemeckis").startswith("1. Forrest Gump")
    assert pauses == [2, 4]


def test_too_many_requests_for_too_long_is_an_error(monkeypatch, tmp_path):
    _, pauses = scripted_wikipedia(monkeypatch, tmp_path,
                                   [FakeResponse(429, retry_after="100")] * 20)
    with pytest.raises(wiki.RateLimited):
        wiki.search("Forrest Gump")
    assert pauses == [wiki.MAX_PAUSE] * 5   # 60 seconds at most each time, 300 in all
    assert list(tmp_path.iterdir()) == []   # nothing cached


def test_a_claim_that_fails_is_not_saved_and_runs_again(monkeypatch, tmp_path, capsys):
    item = {"id": "c1", "claim": "claim", "source": "hover", "label": "NOT_SUPPORTED", "hops": 2}

    def rate_limited(claim):
        raise wiki.RateLimited("too many requests")

    monkeypatch.setitem(evaluate.METHODS, "agent", rate_limited)
    [result] = evaluate.run_method("agent", [item], tmp_path, workers=1)
    assert result["verdict"] is None and not result["correct"]
    assert (tmp_path / "agent.jsonl").read_text() == ""
    evaluate.report([item], {"agent": [result]})
    assert "run the same command again" in capsys.readouterr().out

    answer = {"verdict": "doesn't say", "evidence": [], "explanation": "x"}
    monkeypatch.setitem(evaluate.METHODS, "agent", lambda claim: agent.run_agent(
        claim, client=ScriptedClaude([reply(tool_use("answer", answer, 1))]), lookup=fake_lookup))
    [result] = evaluate.run_method("agent", [item], tmp_path, workers=1)
    assert result["verdict"] == "doesn't say" and result["correct"]
    assert len((tmp_path / "agent.jsonl").read_text().splitlines()) == 1


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


def test_one_search_unwraps_only_a_wholly_quoted_query():
    cases = {'"1994 Best Picture"': "1994 Best Picture",
             '"One Dance" Drake Wizkid Kyla song': '"One Dance" Drake Wizkid Kyla song',
             '"One Dance" "Drake"': '"One Dance" "Drake"',
             "Forrest Gump director": "Forrest Gump director"}
    for written, searched in cases.items():
        query = NS(type="text", text=written)
        answer = NS(type="text", text='{"verdict": "refuted", "explanation": "x"}')
        claude = ScriptedClaude([reply(query, stop="end_turn"), reply(answer, stop="end_turn")])
        queries = []
        baselines.one_search("claim", client=claude,
                             search=lambda q: queries.append(q) or "1. Forrest Gump: snippet",
                             read=lambda title: "page text")
        assert queries == [searched]


def test_lookup_prints_and_logs(monkeypatch, tmp_path, capsys):
    import lookup
    monkeypatch.setattr(lookup, "load_dotenv", lambda: None)  # leave your own .env alone
    monkeypatch.setattr(lookup, "LOG", tmp_path / "lookups.jsonl")
    monkeypatch.setattr(wiki, "search", lambda q: f"1. Forrest Gump: {q}")
    monkeypatch.setattr(sys, "argv", ["lookup.py", "search", "1994 Best Picture"])
    lookup.main()
    assert "1. Forrest Gump: 1994 Best Picture" in capsys.readouterr().out
    assert '"tool": "search"' in (tmp_path / "lookups.jsonl").read_text()
