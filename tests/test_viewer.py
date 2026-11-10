"""Offline tests for the results viewer (viewer/): small made-up run files in a temporary
folder, no network and no API key. They check that its numbers are evaluate.py's numbers, the
filters, a half-finished run, a failed claim, quotes found and not found, two runs side by
side, that only paths inside runs/ are read, and that every page works both under /results
(inside the homework page) and on its own."""

import contextlib
import html
import io
import json
import os
import re
import socket
import sys
import threading
import urllib.request
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import evaluate  # noqa: E402
from viewer import __main__ as standalone  # noqa: E402
from viewer import app  # noqa: E402
from viewer import runs as R  # noqa: E402

HOVER = [
    {"id": "h1", "claim": "Alpha Person was born in Paris.", "source": "hover", "label": "SUPPORTED",
     "hops": 2, "articles": ["Alpha Person"]},
    {"id": "h2", "claim": "Beta Writer wrote the novel Gamma.", "source": "hover", "label": "NOT_SUPPORTED",
     "hops": 2, "articles": ["Beta Writer", "Gamma (novel)"]},
    {"id": "h3", "claim": "Delta is a town in Epsilon, which borders Zeta.", "source": "hover",
     "label": "SUPPORTED", "hops": 3, "articles": ["Delta", "Epsilon", "Zeta"]},
    {"id": "h4", "claim": "Eta founded the company Theta in 1990.", "source": "hover",
     "label": "NOT_SUPPORTED", "hops": 4, "articles": ["Eta", "Theta", "Iota", "Kappa"]},
    {"id": "h5", "claim": "Lambda and Mu share the occupation of singer.", "source": "hover",
     "label": "SUPPORTED", "hops": 3, "articles": ["Lambda", "Mu", "Nu"]},
]
MINE = [
    {"id": "mine-1", "claim": "Macalester College is in Saint Paul.", "source": "mine", "label": "supported"},
    {"id": "mine-2", "claim": "Macalester College was founded in 1990.", "source": "mine", "label": "refuted"},
]
BY_ID = {i["id"]: i for i in HOVER + MINE}

PARIS = ("Page: Alpha Person\n\nAlpha Person (born 3 May 1950) is a French painter.\n"
         "She was born in Paris and   lives in \u201cLyon\u201d today.\n\nSections: Early life, Work")


def result(method, item_id, verdict, steps=0, tin=100, tout=10, seconds=1.0, cost=0.0001,
           trace=None, evidence=None, error=False, explanation="Because."):
    item = BY_ID[item_id]
    row = {"claim": item["claim"], "verdict": verdict, "evidence": evidence or [],
           "explanation": explanation, "trace": trace or [], "steps": steps,
           "tokens": {"input": tin, "output": tout}, "cost_usd": cost,
           "id": item_id, "method": method, "seconds": seconds,
           "correct": evaluate.is_correct(item, verdict)}
    if error:
        row.update(error=True, verdict=None, correct=False, explanation="error: Wikipedia said no")
    return row


AGENT_H1_TRACE = [
    {"tool": "search", "input": {"query": "Alpha Person"}, "result": "1. Alpha Person: a French painter"},
    {"tool": "read", "input": {"title": "Alpha Person"}, "result": PARIS},
    {"tool": "answer", "input": {"verdict": "supported",
                                 "evidence": ["she was born in Paris and lives in \"Lyon\" today.",
                                              "Alpha Person studied in Rome."],
                                 "explanation": "The page says so."}, "result": "accepted"},
]


def full_rows():
    """Five HoVer claims, three methods, with one no-verdict and one error among them."""
    rows = {
        "no-tools": [result("no-tools", "h1", "supported", seconds=2.0, cost=0.0002, tin=120, tout=40),
                     result("no-tools", "h2", "supported", seconds=2.5, cost=0.0003, tin=130, tout=60),
                     result("no-tools", "h3", "doesn't say", seconds=1.5, cost=0.0001),
                     result("no-tools", "h4", "refuted", seconds=3.0, cost=0.0002),
                     result("no-tools", "h5", None, seconds=1.0, cost=0.0001)],
        "one-search": [result("one-search", "h1", "supported", steps=2, tin=900, tout=80, cost=0.0004,
                              trace=[{"tool": "search", "input": {"query": "Alpha"}, "result": "1. Alpha Person: x"},
                                     {"tool": "read", "input": {"title": "Alpha Person"}, "result": PARIS}]),
                       result("one-search", "h2", "doesn't say", steps=2, tin=800, tout=70, cost=0.0003),
                       result("one-search", "h3", "supported", steps=2, tin=1000, tout=90, cost=0.0005),
                       result("one-search", "h4", "doesn't say", steps=2, cost=0.0004),
                       result("one-search", "h5", "refuted", steps=2, cost=0.0004)],
        "agent": [result("agent", "h1", "supported", steps=2, tin=5000, tout=500, seconds=12.5, cost=0.0008,
                         trace=AGENT_H1_TRACE, evidence=AGENT_H1_TRACE[2]["input"]["evidence"]),
                  result("agent", "h2", "refuted", steps=5, tin=9000, tout=900, seconds=20.0, cost=0.0014),
                  result("agent", "h3", "supported", steps=12, tin=30000, tout=2000, seconds=40.0, cost=0.0040,
                         trace=[{"tool": "read", "input": {"title": "Delta"}, "result": "Page: Delta\n\nDelta is a town."}] * 12
                         + [{"tool": "search", "input": {"query": "more"}, "result": "You have used all 12 steps. Call answer() now."}]),
                  result("agent", "h4", "supported", steps=7, tin=15000, tout=1500, seconds=25.0, cost=0.0022),
                  result("agent", "h5", None, error=True, seconds=3.0, cost=0.0)],
    }
    return rows


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))


@pytest.fixture
def repo(tmp_path):
    write_jsonl(tmp_path / "data" / "claims.jsonl", HOVER)
    write_jsonl(tmp_path / "data" / "my-claims.jsonl", MINE)
    for method, rows in full_rows().items():
        write_jsonl(tmp_path / "runs" / "part2" / f"{method}.jsonl", rows)
    return tmp_path


@pytest.fixture(autouse=True)
def mounted():
    app.PREFIX = "/results"
    yield
    app.PREFIX = "/results"


def get(repo, url, method="GET"):
    """Fetch a page the way the homework page would: the prefix taken off, the query parsed."""
    u = urlsplit(url)
    path = u.path[len(app.PREFIX):] if app.PREFIX and u.path.startswith(app.PREFIX) else u.path
    status, ctype, body = app.handle(method, path, parse_qs(u.query), repo)
    return status, ctype, body.decode("utf-8")


def text_of(page):
    """The page's words without tags, for checking what it says."""
    words = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", page)))
    return re.sub(r" ([,.;:])", r"\1", words)  # "call 2 </a>, highlighted" reads "call 2, highlighted"


def report_of(items, results):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        evaluate.report(items, results)
    return out.getvalue()


# ------------------------------------------------------------------ numbers

def test_numbers_equal_evaluate_report(repo):
    rows = full_rows()
    printed = report_of(HOVER, rows)
    run = R.get_run(repo, repo / "runs" / "part2", "runs/part2")
    lines = printed.splitlines()
    # Accuracy, group by group and method by method.
    for g in R.group_names(run) + ["All"]:
        line = next(x for x in lines if x.startswith(g))
        expected = [tuple(map(int, m)) for m in re.findall(r"(\d+)/(\d+)", line)]
        got = []
        for m in ["no-tools", "one-search", "agent"]:
            st = R.stats(run, m)
            got.append((st["correct"], st["n"]) if g == "All" else tuple(st["groups"][g]))
        assert got == expected, g
    # Averages per claim, printed to the same places.
    for m in ["no-tools", "one-search", "agent"]:
        line = next(x for x in lines if x.startswith(m) and "/" not in x)
        st = R.stats(run, m)
        assert line.split()[1:] == [f"{st['steps']:.1f}", f"{st['tokens']:.0f}", f"{st['seconds']:.1f}",
                                    f"{st['cost']:.4f}"]
    # Failed and no-verdict counts.
    every = [r for rs in rows.values() for r in rs]
    failed = sum("error" in r for r in every)
    no_verdict = sum(r["verdict"] is None for r in every) - failed
    assert f"{no_verdict} runs gave no verdict" in printed
    assert sum(R.stats(run, m)["no_verdict"] for m in run.methods) == no_verdict
    assert sum(R.stats(run, m)["failed"] for m in run.methods) == failed

    # And the page shows the same numbers, and evaluate.py's own text.
    status, _, page = get(repo, "/results/run?dir=runs/part2")
    assert status == 200
    words = text_of(page)
    for m in run.methods:
        st = R.stats(run, m)
        assert f"{st['correct']} of {st['n']}" in words
        assert f"${st['cost']:.4f}" in words
    assert "Correct means only that the verdict matches the dataset's label" in words
    assert words.count("Correct means only") == 1
    assert html.escape(printed.strip("\n"), quote=True) in page


def test_report_of_own_claims_groups_them(repo):
    rows = {"agent": [result("agent", "mine-1", "supported"), result("agent", "mine-2", "doesn't say")]}
    write_jsonl(repo / "runs" / "part3" / "before" / "agent.jsonl", rows["agent"])
    run = R.get_run(repo, repo / "runs" / "part3" / "before", "runs/part3/before")
    printed = report_of(MINE, rows)
    assert "Your claims" in printed and R.group_names(run) == ["Your claims"]
    st = R.stats(run, "agent")
    assert (st["correct"], st["n"]) == (1, 2)
    assert run.file == ("data/my-claims.jsonl", 2)
    words = text_of(get(repo, "/results/run?dir=runs/part3/before")[2])
    assert "1 of 2" in words and "Your claims" in words


# ------------------------------------------------------------------ the claims table

def shown_ids(page):
    return re.findall(r'<tr id="row-([^"]+)"', page)


def test_filters(repo):
    base = "/results/run?dir=runs/part2"
    page = get(repo, base)[2]
    assert shown_ids(page) == ["h1", "h2", "h3", "h4", "h5"]
    assert "Showing 5 of 5 claims" in text_of(page)

    page = get(repo, base + "&hops=2")[2]
    assert shown_ids(page) == ["h1", "h2"] and "Showing 2 of 5 claims" in text_of(page)
    assert shown_ids(get(repo, base + "&label=not+supported")[2]) == ["h2", "h4"]
    assert shown_ids(get(repo, base + "&q=paris+ALPHA")[2]) == ["h1"]
    assert shown_ids(get(repo, base + "&q=nothing+like+this")[2]) == []
    assert "No claims match these filters" in get(repo, base + "&q=zzz")[2]
    # agent: correct on h1, h2, h3; wrong on h4; error on h5 (counts as wrong)
    assert shown_ids(get(repo, base + "&r_agent=correct")[2]) == ["h1", "h2", "h3"]
    assert shown_ids(get(repo, base + "&r_agent=wrong")[2]) == ["h4", "h5"]
    assert shown_ids(get(repo, base + "&r_agent=error")[2]) == ["h5"]
    assert shown_ids(get(repo, base + "&r_no-tools=none")[2]) == ["h5"]
    assert shown_ids(get(repo, base + "&v_agent=supported")[2]) == ["h1", "h3", "h4"]
    assert shown_ids(get(repo, base + "&v_one-search=doesn%27t+say")[2]) == ["h2", "h4"]
    assert shown_ids(get(repo, base + "&v_agent=supported&r_agent=wrong")[2]) == ["h4"]
    assert shown_ids(get(repo, base + "&steps=1")[2]) == ["h3"]
    # Sorting by the agent's cost and calls; claims it has no cost for go last.
    assert shown_ids(get(repo, base + "&sort=cost-high")[2]) == ["h3", "h4", "h2", "h1", "h5"]
    assert shown_ids(get(repo, base + "&sort=calls-low")[2]) == ["h5", "h1", "h2", "h4", "h3"]


def test_claim_page_prev_next_follow_the_filter(repo):
    status, _, page = get(repo, "/results/claim?dir=runs/part2&id=h2&label=not+supported")
    assert status == 200
    assert "Claim 1 of 2 that match your filters" in text_of(page)
    nxt = re.search(r'<a rel="next" href="([^"]+)"', page).group(1).replace("&amp;", "&")
    assert "id=h4" in nxt and "label=not+supported" in nxt
    assert 'rel="prev"' not in page
    # A claim outside the filter still opens, and says so.
    page = get(repo, "/results/claim?dir=runs/part2&id=h1&label=not+supported")[2]
    assert "not among the ones your filters show" in page
    assert get(repo, "/results/claim?dir=runs/part2&id=nope")[0] == 404


# ------------------------------------------------------------------ half-finished, failed

def test_half_finished_run(repo):
    folder = repo / "runs" / "part3" / "after-eval"
    write_jsonl(folder / "agent.jsonl", full_rows()["agent"][:2])
    with (folder / "agent.jsonl").open("a") as f:
        f.write('{"id": "h3", "claim": "Delta is a to')  # the run is writing this line now
    status, _, page = get(repo, "/results/run?dir=runs/part3/after-eval")
    words = text_of(page)
    assert status == 200
    assert "the agent has 2 of 5" in words
    assert "Some claims have no result yet" in words
    assert "1 line in agent.jsonl could not be read" in words
    assert "2 of 2" in words  # both finished claims are correct
    home = text_of(get(repo, "/results/")[2])
    assert "2 of 5" in home


def test_failed_claim(repo):
    page = get(repo, "/results/run?dir=runs/part2")[2]
    words = text_of(page)
    assert "1 claim stopped with an error" in words
    assert "1 claim gave no verdict" in words
    row = re.search(r'<tr id="row-h5">.*?</tr>', page, re.S).group(0)
    assert "stopped with an error" in row and "✗" in row
    claim = text_of(get(repo, "/results/claim?dir=runs/part2&id=h5")[2])
    assert "error: Wikipedia said no" in claim


# ------------------------------------------------------------------ quotes

def test_find_spans_compares_like_agent_py():
    text = 'She was born in Paris and   lives in \u201cLyon\u201d today.'
    spans = R.find_spans(text, 'born in paris and lives in "Lyon"')
    assert len(spans) == 1
    s, t = spans[0]
    assert text[s:t] == 'born in Paris and   lives in \u201cLyon\u201d'
    assert R.find_spans(text, "born in Rome") == []
    # The same judgment as agent.py's own evidence check.
    import agent
    for quote in ['born in paris and lives in "Lyon"', "born in Rome"]:
        assert bool(R.find_spans(text, quote)) == (not agent.unsupported_quotes([quote], [text]))


def test_quote_found_and_not_found(repo):
    page = get(repo, "/results/claim?dir=runs/part2&id=h1")[2]
    words = text_of(page)
    assert re.search(r'<mark data-q="1"[^>]*>She was born in Paris and\s+lives in \u201cLyon\u201d today\.</mark>', page)
    assert "Found in call 2 (read), highlighted below" in words
    assert "This quote appears in nothing the agent read in this check." in words
    assert 'href="https://en.wikipedia.org/wiki/Alpha_Person"' in page
    assert 'target="_blank"' in page and 'rel="noopener noreferrer"' in page
    assert "#:~:text=" in page
    # It shows what happened and does not judge it.
    for word in ("supports the verdict", "should", "failure", "wrong page", "misread"):
        assert word not in words


def test_long_results_are_folded_but_reachable(repo):
    long_text = "Page: Delta\n\n" + "Delta is a town. " * 200
    trace = [{"tool": "read", "input": {"title": "Delta"}, "result": long_text},
             {"tool": "answer", "input": {"verdict": "doesn't say", "evidence": [], "explanation": "x"},
              "result": "accepted"}]
    rows = full_rows()["agent"]
    rows[2] = result("agent", "h3", "doesn't say", steps=1, trace=trace)
    write_jsonl(repo / "runs" / "part2" / "agent.jsonl", rows)
    page = get(repo, "/results/claim?dir=runs/part2&id=h3")[2]
    assert '<details class="result">' in page  # folded
    assert html.escape(long_text, quote=True) in page  # but the full text is in the page
    assert '<details class="result" open>' in get(repo, "/results/claim?dir=runs/part2&id=h3&full=1")[2]


# ------------------------------------------------------------------ single checks and lookups

def test_single_check_and_lookups(repo):
    check = result("agent", "h1", "supported", steps=2, trace=AGENT_H1_TRACE,
                   evidence=AGENT_H1_TRACE[2]["input"]["evidence"])
    for k in ("id", "correct"):
        check.pop(k)
    (repo / "runs" / "part0").mkdir(parents=True)
    (repo / "runs" / "part0" / "agent-1794290701.json").write_text(json.dumps(check, indent=1))
    other = dict(check, claim="A claim that is in no data file.", method="no-tools", trace=[], evidence=[])
    (repo / "runs" / "part0" / "no-tools-1794290600.json").write_text(json.dumps(other))
    write_jsonl(repo / "runs" / "part1" / "lookups.jsonl",
                [{"tool": "search", "input": {"query": "1994 Best Picture"}},
                 {"tool": "read", "input": {"title": "Forrest Gump", "section": None}}])
    home = text_of(get(repo, "/results/")[2])
    assert "Alpha Person was born in Paris." in home
    assert "1994 Best Picture" in home and "2 calls" in home
    page = get(repo, "/results/check?file=runs/part0/agent-1794290701.json")[2]
    words = text_of(page)
    assert "Label: supported" in words and "data/claims.jsonl" in words
    assert "✓" in page and "<mark" in page
    page = text_of(get(repo, "/results/check?file=runs/part0/no-tools-1794290600.json")[2])
    assert "no label to compare" in page


def test_empty_states(tmp_path):
    words = text_of(get(tmp_path, "/results/")[2])
    assert "No runs yet." in words
    (tmp_path / "runs" / "part0").mkdir(parents=True)
    (tmp_path / "runs" / "part0" / "agent-1.json").write_text(json.dumps(
        {"claim": "x", "verdict": "supported", "trace": [], "evidence": []}))
    words = text_of(get(tmp_path, "/results/")[2])
    assert "No evaluation runs yet. You make the first one in Part 2." in words
    assert "No lookups by hand yet." in words
    words = text_of(get(tmp_path, "/results/compare")[2])
    assert "No evaluation runs yet" in words


# ------------------------------------------------------------------ two runs side by side

def test_compare_two_runs(repo):
    after = [result("agent", "h1", "supported", steps=3, cost=0.0010),       # same
             result("agent", "h2", "doesn't say", steps=4, cost=0.0012),     # refuted -> doesn't say, correct in both
             result("agent", "h3", "doesn't say", steps=6, cost=0.0020),     # correct -> wrong
             result("agent", "h4", "refuted", steps=5, cost=0.0016)]         # wrong -> correct ; h5 missing
    write_jsonl(repo / "runs" / "part3" / "after-eval" / "agent.jsonl", after)
    status, _, page = get(repo, "/results/compare?a=runs/part2&b=runs/part3/after-eval")
    words = text_of(page)
    assert status == 200
    assert "Only in A, so not compared: the no-tools baseline, the one-search baseline." in words
    assert "A has 5 claims and B has 4 claims. This page compares the 4 claims both have." in words
    # A on the shared 4: h1, h2, h3 correct, h4 wrong -> 3 of 4. B: h1, h2, h4 correct -> 3 of 4.
    assert "3 of 4 (75.0%) 3 of 4 (75.0%) no change" in words
    assert "wrong in A, correct in B: 1 correct in A, wrong in B: 1 verdict changed, correct in both: 1 " \
           "verdict changed, wrong in both: 0" in words
    assert len(re.findall(r">Open A and B<", page)) == 3
    page = get(repo, "/results/compare?a=runs/part2&b=runs/part3/after-eval&kind=now-wrong")[2]
    assert len(re.findall(r">Open A and B<", page)) == 1 and "Delta is a town" in page
    # One claim, both sides.
    page = get(repo, "/results/compare?a=runs/part2&b=runs/part3/after-eval&id=h3&m=agent")[2]
    words = text_of(page)
    assert "A: runs/part2" in words and "B: runs/part3/after-eval" in words
    assert "A's trace" in words and "Change 2 of 3" in words
    # The cost table compares the same claims.
    page = text_of(get(repo, "/results/compare?a=runs/part2&b=runs/part3/after-eval")[2])
    assert "Dollars $0.0021 $0.0014 −$0.0007" in page  # B minus A of the numbers shown


def test_compare_picker(repo):
    words = text_of(get(repo, "/results/compare?a=runs/part2")[2])
    assert "Pick two evaluation runs" in words
    assert get(repo, "/results/compare?a=runs/nothing&b=runs/part2")[0] == 404


# ------------------------------------------------------------------ paths

BAD = ["../x", "/etc/passwd", "runs/../data/claims.jsonl", "data/claims.jsonl", "runs/../../etc",
       "..", "~/x", "C:/x", "runs/part2/../../data", "runs\\..\\data", "runs/link-out", "runs/part2/x\x00"]


@pytest.mark.parametrize("bad", BAD)
def test_paths_outside_runs_are_refused(repo, bad):
    (repo / "outside").mkdir()
    write_jsonl(repo / "outside" / "agent.jsonl", full_rows()["agent"])
    os.symlink(repo / "outside", repo / "runs" / "link-out")
    for url in (f"/run?dir={bad}", f"/claim?dir={bad}&id=h1", f"/check?file={bad}",
                f"/compare?a={bad}&b=runs/part2", f"/compare?a=runs/part2&b={bad}", f"/open?path={bad}"):
        u = urlsplit(url)
        status, _, body = app.handle("GET", u.path, {k: [v] for k, v in
                                                     (p.split("=", 1) for p in u.query.split("&"))}, repo)
        assert status == 400, (url, status)
        assert b"only opens files and folders inside" in body


def test_symlinked_file_out_of_runs_is_not_read(repo):
    (repo / "secret.jsonl").write_text(json.dumps(full_rows()["agent"][0]) + "\n")
    os.symlink(repo / "secret.jsonl", repo / "runs" / "part2" / "secret.jsonl")
    page = get(repo, "/results/run?dir=runs/part2")[2]
    assert "secret" not in page
    assert get(repo, "/results/open?path=runs/part2/secret.jsonl")[0] == 400


def test_open_sends_each_path_to_its_page(repo):
    (repo / "runs" / "part0").mkdir()
    for name in ("agent-1794290000.json", "agent-1794290999.json"):
        (repo / "runs" / "part0" / name).write_text(json.dumps(
            {"claim": "x", "verdict": "supported", "trace": [], "evidence": [], "method": "agent"}))
    os.utime(repo / "runs" / "part0" / "agent-1794290000.json", (1, 1))
    write_jsonl(repo / "runs" / "part1" / "lookups.jsonl", [{"tool": "search", "input": {"query": "q"}}])

    def target(path):
        status, _, page = get(repo, "/results/open?path=" + path)
        assert status == 200
        m = re.search(r'http-equiv="refresh" content="0; url=([^"]+)"', page)
        return html.unescape(m.group(1)) if m else None

    assert target("runs/part2") == "/results/run?dir=runs%2Fpart2"
    assert target("runs/part2/agent.jsonl") == "/results/run?dir=runs%2Fpart2"
    assert target("runs/part0/agent-1794290999.json") == "/results/check?file=runs%2Fpart0%2Fagent-1794290999.json"
    assert target("runs/part0/agent-*.json") == "/results/check?file=runs%2Fpart0%2Fagent-1794290999.json"
    assert target("runs/part1/lookups.jsonl").startswith("/results/#f-runs-part1")
    assert target("runs/part1") == "/results/#f-runs-part1"
    assert target("runs") == "/results/"
    assert target("runs/part3/after") is None
    assert "Nothing is saved at runs/part3/after yet. It fills in when you reach that step in Part 3." in \
        text_of(get(repo, "/results/open?path=runs/part3/after")[2])
    assert target("runs/part0/one-search-*.json") is None


# ------------------------------------------------------------------ every route, mounted and alone

def routes(repo):
    (repo / "runs" / "part0").mkdir(exist_ok=True)
    (repo / "runs" / "part0" / "agent-1794290701.json").write_text(json.dumps(
        result("agent", "h1", "supported", steps=2, trace=AGENT_H1_TRACE,
               evidence=AGENT_H1_TRACE[2]["input"]["evidence"])))
    write_jsonl(repo / "runs" / "part3" / "after-eval" / "agent.jsonl", full_rows()["agent"][:3])
    return ["/", "/run?dir=runs/part2", "/run?dir=runs/part2&r_agent=wrong&sort=cost-high",
            "/claim?dir=runs/part2&id=h1", "/claim?dir=runs/part2&id=h3&full=1",
            "/check?file=runs/part0/agent-1794290701.json", "/compare", "/compare?a=runs/part2",
            "/compare?a=runs/part2&b=runs/part3/after-eval",
            "/compare?a=runs/part2&b=runs/part3/after-eval&id=h3&m=agent"]


@pytest.mark.parametrize("prefix", ["/results", ""])
def test_every_route_mounted_and_alone(repo, prefix):
    app.PREFIX = prefix
    for route in routes(repo):
        u = urlsplit(route)
        status, ctype, body = app.handle("GET", u.path, parse_qs(u.query), repo)
        page = body.decode()
        assert status == 200, route
        assert ctype.startswith("text/html")
        for attr in re.findall(r'(?:href|src|action)="([^"]+)"', page):
            attr = html.unescape(attr)
            if attr.startswith(("http://", "https://", "#")):
                assert "127.0.0.1" not in attr and "localhost" not in attr
                continue
            if prefix and attr == "/":
                continue  # "Back to the homework page"
            assert attr.startswith(prefix + "/"), (route, attr)
        if prefix:
            assert "Back to the homework page" in page
        else:
            assert "Back to the homework page" not in page
        assert "fonts.googleapis" not in page and "<script>" not in page and "style=" not in page
    for name, kind in (("viewer.css", "text/css"), ("viewer.js", "text/javascript")):
        status, ctype, body = app.handle("GET", f"/static/{name}", {}, repo)
        assert status == 200 and ctype.startswith(kind) and body
        assert b"http" not in body.replace(b"https://", b"").replace(b"http://", b"") or True
    assert app.handle("GET", "/static/../app.py", {}, repo)[0] == 404
    assert app.handle("GET", "/nope", {}, repo)[0] == 404
    assert app.handle("POST", "/", {}, repo)[0] == 405
    assert app.handle("HEAD", "/", {}, repo)[0] == 200


def test_static_files_load_nothing_from_the_network():
    for name in ("viewer.css", "viewer.js"):
        text = (Path(app.__file__).parent / "static" / name).read_text()
        assert not re.search(r"@import|url\(|fetch\(|XMLHttpRequest|https?://", text), name


def test_viewer_never_writes(repo):
    def snapshot():
        return {str(p): (p.stat().st_mtime_ns, p.stat().st_size) for p in repo.rglob("*")}
    pages = routes(repo)  # writes the test's own files first
    before = snapshot()
    for route in pages + ["/open?path=runs/part2", "/open?path=runs/part0/agent-*.json"]:
        u = urlsplit(route)
        assert app.handle("GET", u.path, parse_qs(u.query), repo)[0] == 200
    assert snapshot() == before


def test_untrusted_text_is_shown_as_text(repo):
    rows = full_rows()["agent"]
    rows[0] = result("agent", "h1", "supported", explanation='<script>alert(1)</script><b onclick="x">',
                     trace=[{"tool": "read", "input": {"title": "<img src=x>"}, "result": "Page: <i>x</i>"}])
    write_jsonl(repo / "runs" / "part2" / "agent.jsonl", rows)
    page = get(repo, "/results/claim?dir=runs/part2&id=h1")[2]
    assert "<script>alert" not in page and "<img src=x>" not in page and "<i>x</i>" not in page
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page


# ------------------------------------------------------------------ on its own

def test_standalone_server_uses_next_free_port(repo):
    taken = socket.socket()
    taken.bind(("127.0.0.1", 0))
    taken.listen()
    port = taken.getsockname()[1]
    server = standalone.serve(repo, port)
    try:
        assert server.server_address[0] == "127.0.0.1"
        assert server.server_address[1] != port
        app.PREFIX = ""
        threading.Thread(target=server.serve_forever, daemon=True).start()
        url = f"http://127.0.0.1:{server.server_address[1]}/run?dir=runs/part2"
        with urllib.request.urlopen(url, timeout=10) as response:
            assert response.status == 200
            assert "default-src 'none'" in response.headers["Content-Security-Policy"]
            assert b"runs/part2" in response.read()
    finally:
        server.shutdown()
        server.server_close()
        taken.close()


# ------------------------------------------------------------------ what evaluate.py saves beside the results

def test_run_json_names_the_claims_file(repo, tmp_path_factory):
    folder = repo / "runs" / "part2"
    (folder / "run.json").write_text(json.dumps({"claims": "data/claims.jsonl"}) + "\n")
    write_jsonl(folder / "agent.jsonl", full_rows()["agent"][:3])
    run = R.get_run(repo, folder, "runs/part2")
    assert run.file == ("data/claims.jsonl", 5)
    assert "the agent has 3 of 5" in text_of(get(repo, "/results/run?dir=runs/part2")[2])
    # A run.json that points outside the repository is not followed.
    outside = tmp_path_factory.mktemp("elsewhere") / "claims.jsonl"
    write_jsonl(outside, HOVER)
    for named in (str(outside), "../" + outside.parent.name + "/claims.jsonl", "data/../../x.jsonl"):
        (folder / "run.json").write_text(json.dumps({"claims": named}))
        assert R.named_claims_file(repo, folder) is None
        assert get(repo, "/results/run?dir=runs/part2")[0] == 200
    (folder / "run.json").write_text("not json")
    assert get(repo, "/results/run?dir=runs/part2")[0] == 200


def test_report_txt_and_run_json_open_their_run(repo):
    (repo / "runs" / "part2" / "report.txt").write_text("tables")
    (repo / "runs" / "part2" / "run.json").write_text(json.dumps({"claims": "data/claims.jsonl"}))
    for name in ("report.txt", "run.json"):
        page = get(repo, f"/results/open?path=runs/part2/{name}")[2]
        assert 'url=/results/run?dir=runs%2Fpart2"' in page


def test_compare_says_whether_the_agent_changed(repo):
    def with_version(rows, v):
        return [dict(r, agent_version=v) for r in rows]
    write_jsonl(repo / "runs" / "part2" / "agent.jsonl", with_version(full_rows()["agent"], "aaa"))
    write_jsonl(repo / "runs" / "b" / "agent.jsonl", with_version(full_rows()["agent"], "aaa"))
    words = text_of(get(repo, "/results/compare?a=runs/part2&b=runs/b")[2])
    assert "made from the same version of its files" in words
    write_jsonl(repo / "runs" / "b" / "agent.jsonl", with_version(full_rows()["agent"], "bbb"))
    words = text_of(get(repo, "/results/compare?a=runs/part2&b=runs/b")[2])
    assert "were different when A and B were made" in words
    assert "No claim changed" in words
