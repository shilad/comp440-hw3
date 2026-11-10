"""Offline tests of the claim finder's screen (finder/web.py and finder/static/), with the search
functions replaced by the stand-in in finder_standin.py: the search address and its pages of 50,
saving the selected claims by id, the note about claims saved already, that the screen loads inside
the homework page even without the search package, and that a refusal from save reaches the browser
as its own sentence."""

import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlencode

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import finder_standin as standin  # noqa: E402
from finder import web  # noqa: E402
from test_workbench import fetch, homework, quiet_world, serving  # noqa: E402, F401
from workbench import server  # noqa: E402

STATIC = ROOT / "finder" / "static"
LOCKED = "You have already run the agent on your claims, so they can no longer be changed."
# Eight claims the stand-in will save: four of each label, from two searches.
EIGHT = [{"id": f"hover-{n:02d}", "query": "jazz" if n < 5 else "basketball"} for n in range(1, 9)]


@pytest.fixture
def stand_in(monkeypatch):
    monkeypatch.setattr(web, "engine", lambda: standin)


def get(path, repo, **params):
    status, ctype, body = web.handle("GET", path, {k: [str(v)] for k, v in params.items()}, b"", repo)
    return status, json.loads(body) if ctype == "application/json" else body


def post(path, repo, data):
    status, ctype, body = web.handle("POST", path, {}, json.dumps(data).encode(), repo)
    return status, json.loads(body)


def ids(claims):
    return [c["id"] for c in claims]


def test_search_answers_in_the_contracts_shape(stand_in, tmp_path):
    status, a = get("/search", tmp_path, q="jazz singer", how="keyword")
    assert status == 200
    assert set(a) == {"query", "how", "matches", "total", "start", "results"}
    assert (a["query"], a["how"], a["start"]) == ("jazz singer", "keyword", 0)
    assert a["matches"] == standin.keyword_counts("jazz singer") == {"any": 8, "all": 4}
    everything = standin.search("jazz singer", "keyword")
    assert a["total"] == len(everything) and ids(a["results"]) == ids(everything)
    first = a["results"][0]
    assert {"id", "claim", "label", "hops", "articles", "about", "keyword_rank", "meaning_rank"} <= set(first)


def test_results_come_fifty_at_a_time(stand_in, tmp_path, monkeypatch):
    monkeypatch.setattr(web, "PAGE", 6)
    everything = ids(standin.search("river", "both"))
    pages = [ids(get("/search", tmp_path, q="river", start=s)[1]["results"]) for s in (0, 6, 12, 18)]
    assert pages[0] == everything[:6] and pages[1] == everything[6:12] and sum(pages, []) == everything
    assert get("/search", tmp_path, q="river", start=99)[1]["results"] == []
    assert web.PAGE == 6 and "Show 50 more" in (STATIC / "index.html").read_text()


def test_search_tidies_what_it_is_given(stand_in, tmp_path):
    _, a = get("/search", tmp_path, q="  jazz   river ", how="sideways", start="lots")
    assert (a["query"], a["how"], a["start"]) == ("jazz river", "both", 0)
    assert get("/search", tmp_path, q="jazz", start=-5)[1]["start"] == 0
    status, a = get("/search", tmp_path, q="   ")
    assert status == 400 and a["error"].endswith(".")


def test_save_looks_the_claims_up_by_id_and_saves_them(stand_in, tmp_path):
    status, a = post("/save", tmp_path, {"selected": EIGHT})
    assert status == 200
    assert a == {"ok": True, "saved": True, "topics": ["jazz", "basketball"], "development": 4,
                 "evaluation": 4, "run": False}
    development, evaluation = standin.split([standin.CLAIMS[n - 1] for n in range(1, 9)])
    for name, part in (("dev.jsonl", development), ("eval.jsonl", evaluation)):
        saved = [json.loads(line) for line in (tmp_path / "data" / name).read_text().splitlines()]
        assert ids(saved) == ids(part) and saved[0]["claim"] == part[0]["claim"]     # the server's own text
    assert get("/saved", tmp_path)[1] == {k: v for k, v in a.items() if k != "ok"}


def test_a_claim_selected_twice_is_saved_once(stand_in, tmp_path):
    assert post("/save", tmp_path, {"selected": EIGHT + EIGHT[:1]})[1]["ok"] is True


def test_refusals_come_back_as_their_sentences(stand_in, tmp_path):
    assert post("/save", tmp_path, {"selected": EIGHT[:5]})[1] == {
        "ok": False, "why": "You have selected 5 claims, and you need exactly 8."}
    unknown = EIGHT[:7] + [{"id": "hover-gone", "query": "jazz"}]
    assert post("/save", tmp_path, {"selected": unknown})[1] == {
        "ok": False, "why": "The claim hover-gone is not in the dataset any more. Remove it from your selection, "
                            "select another claim, and save again."}
    for body in ({}, {"selected": "hover-01"}, {"selected": [{"query": "jazz"}]}):
        a = post("/save", tmp_path, body)[1]
        assert a["ok"] is False and a["why"].endswith("."), body
    assert not (tmp_path / "data").exists()


def test_nothing_saved_yet_while_the_sample_claims_are_there(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data/dev.jsonl").write_text('{"id": "sample"}\n')
    (tmp_path / "data/eval.jsonl").write_text('{"id": "sample"}\n')
    assert get("/saved", tmp_path)[1] == {"saved": False}


def test_the_note_can_hold_topics_as_text(stand_in, tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data/my-topic.json").write_text('{"topics": ["film", "jazz"]}')
    assert get("/saved", tmp_path)[1]["topics"] == ["film", "jazz"]


def test_the_claims_are_locked_once_the_agent_has_run_on_them(stand_in, tmp_path):
    post("/save", tmp_path, {"selected": EIGHT})
    for run in ("runs/part1/before", "runs/part1/after", "runs/part2"):
        (tmp_path / run).mkdir(parents=True)
        assert get("/saved", tmp_path)[1]["run"] is False       # an empty folder is not a run
        (tmp_path / run / "agent.jsonl").write_text("{}\n")
        assert get("/saved", tmp_path)[1]["run"] is True
        assert post("/save", tmp_path, {"selected": EIGHT})[1] == {"ok": False, "why": LOCKED}
        (tmp_path / run / "agent.jsonl").unlink()
    # Part 0's runs, and steps 1a's and 1b's files in runs/part1, do not lock them.
    for f in ("runs/part0/no-tools-1.json", "runs/part1/loop-check.txt", "runs/part1/lookups.jsonl"):
        (tmp_path / f).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / f).write_text("{}")
    assert get("/saved", tmp_path)[1]["run"] is False


def test_the_screen_is_served_from_static(tmp_path):
    status, ctype, body = web.handle("GET", "/", {}, b"", tmp_path)
    assert status == 200 and ctype.startswith("text/html")
    for name in ("finder.js", "finder.css"):
        assert web.handle("GET", f"/static/{name}", {}, b"", tmp_path)[0] == 200
    assert web.handle("GET", "/static/../web.py", {}, b"", tmp_path)[0] == 404
    assert web.handle("GET", "/nowhere", {}, b"", tmp_path)[0] == 404


def test_the_screen_uses_the_names_the_student_sees():
    page = (STATIC / "index.html").read_text()
    js = (STATIC / "finder.js").read_text()
    for name in ("Find claims", ">Search<", "by keyword", "by meaning", "> both<", "Save these as my claims",
                 "Show my selection", "Show 50 more", 'value="both" checked', "select 112 of them",
                 "with at least 30\n      supported and 30 not supported, so that an agent that always gives the same",
                 "data/dev.jsonl", "data/eval.jsonl"):
        assert name in page, name
    for name in ('"Remove" : "Select"', "Back to the search results", "localStorage"):
        assert name in js, name
    for sentence in (
            # the line at the top, and a selected claim
            "You have selected ${n} of ${NEEDED} claims: ${yes} supported and ${n - yes} not ",
            "You have selected this claim.",
            # each claim's ranks, in the word the pages use: "rank"
            "Its rank is ${k} by keyword and ${m} by meaning.",
            "Its rank is ${k} by keyword. The search by meaning did not put it among its best 1,000.",
            "Its rank is ${m} by meaning. It contains none of your words, so the search by keyword did not find it.",
            # the count of claims with all the words, and the calm sentence for a narrow topic
            "all of your words.`",
            "The dataset has few claims on this topic, so the list ",
            "Select the ones that are on your topic, and search another topic for the rest.",
            # saving
            "evaluation claims in data/eval.jsonl. Every run from step 1c on uses them."):
        assert sentence in js, sentence
    assert len(re.findall(r"^const NARROW = [\d.]+;", js, re.M)) == 1
    assert len(re.findall(r"^const NEEDED = 112;", js, re.M)) == 1
    # Nothing left from the versions where the screen picked the claims.
    for stale in ('id="size"', "Put them back", "150", "100 to 200", "my-topic.jsonl", "step 3b", "Part 3",
                  "number ${"):
        assert stale not in page + js, stale
    words = (page + js).lower()
    assert words.count("embedding") == 1      # once, to say what the search by meaning is
    for word in ("hybrid", "corpus", "pool", "retrieval"):
        assert word not in words, word


def test_web_does_not_import_the_search_until_asked():
    code = "import sys; import finder.web; print('finder.search' in sys.modules)"
    r = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0 and r.stdout.strip() == "False", r.stderr


def test_the_homework_page_mounts_the_screen_under_claims(stand_in, tmp_path):
    h = homework(tmp_path)
    srv, base = serving(server.App(h.student))
    try:
        code, headers, _ = fetch(base + "/claims")
        assert code == 301 and headers["Location"] == "/claims/"
        code, headers, body = fetch(base + "/claims/")
        assert code == 200 and b"Save these as my claims" in body
        for f in ("/claims/static/finder.js", "/claims/static/finder.css", "/static/style.css"):
            assert fetch(base + f)[0] == 200, f
        a = json.loads(fetch(base + "/claims/search?" + urlencode({"q": "basketball"}))[2])
        assert a["how"] == "both" and a["total"] == len(standin.CLAIMS) and a["matches"]["all"] == 4
        # Saving, then a refusal reaching the browser word for word.
        ask = {"Content-Type": "application/json"}
        ok = json.loads(fetch(base + "/claims/save", json.dumps({"selected": EIGHT}).encode(), ask)[2])
        assert ok["ok"] is True and ok["development"] == 4
        (h.student / "runs/part2").mkdir(parents=True)
        (h.student / "runs/part2/agent.jsonl").write_text("{}\n")
        no = json.loads(fetch(base + "/claims/save", json.dumps({"selected": EIGHT}).encode(), ask)[2])
        assert no == {"ok": False, "why": LOCKED}
        saved = json.loads(fetch(base + "/claims/saved")[2])
        assert saved["topics"] == ["jazz", "basketball"] and saved["run"] is True
        # A post from another web site is refused, as everywhere on the page.
        assert fetch(base + "/claims/save", b"{}", {"Origin": "https://example.com"})[0] == 403
    finally:
        srv.shutdown()
        srv.server_close()


def test_the_screen_loads_while_the_search_cannot(monkeypatch, tmp_path):
    def missing():
        raise FileNotFoundError("finder/data/claims.json.gz")
    monkeypatch.setattr(web, "engine", missing)
    h = homework(tmp_path)
    srv, base = serving(server.App(h.student))
    try:
        assert fetch(base + "/claims/")[0] == 200
        code, _, body = fetch(base + "/claims/search?q=jazz")
        assert code == 500 and body.decode().startswith("The claim finder ran into a problem:")
    finally:
        srv.shutdown()
        srv.server_close()


def test_the_screen_searches_the_real_claims_once_they_are_here(tmp_path):
    if not (ROOT / "finder/search.py").exists() or not (ROOT / "finder/data/claims.json.gz").exists():
        pytest.skip("finder/search.py and its data are not in this copy yet")
    status, a = get("/search", tmp_path, q="Formula One", how="both")
    assert status == 200 and len(a["results"]) == 50 and a["total"] > 50
    assert 0 < a["matches"]["all"] <= a["matches"]["any"]
    assert ids(get("/search", tmp_path, q="Formula One", start=50)[1]["results"])[0] not in ids(a["results"])


def test_the_intro_states_the_search_packages_numbers():
    if not (ROOT / "finder/search.py").exists():
        pytest.skip("finder/search.py is not in this copy yet")
    from finder import search
    intro = " ".join((STATIC / "index.html").read_text().split())
    least, saved = search.LEAST_PER_LABEL, search.SAVED_CLAIMS
    assert f"You need exactly {saved}, with at least {least} supported and {least} not supported," in intro
    assert len(re.findall(r"^const NEEDED = (\d+);", (STATIC / "finder.js").read_text(), re.M)) == 1
    assert f"const NEEDED = {saved};" in (STATIC / "finder.js").read_text()


def test_the_homework_page_links_to_the_screen():
    page = (ROOT / "workbench/static/index.html").read_text()
    assert '<a href="/claims/" target="_blank" rel="noopener">Find claims</a>' in page
    assert page.index("Results</a>") < page.index("Find claims</a>")
