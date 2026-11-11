"""Offline tests of the claim finder's screen (finder/web.py and finder/static/), with the search
functions replaced by the stand-in in finder_standin.py: the search address and its pages of 50,
saving the selected claims by id, the note about claims saved already, that the screen loads inside
the homework page even without the search package, that a refusal from save reaches the browser
as its own sentence, and the "Select all shown" button, whose tests run the screen's script in
Node (they skip where Node is not installed)."""

import json
import re
import shutil
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
        "ok": False, "why": "The claim hover-gone is no longer in the dataset. Remove it, select another claim, "
                            "and save again."}
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
                 "Show my selection", "Show 50 more", 'value="both" checked'):
        assert name in page, name
    for name in ('"Remove" : "Select"', "Back to the search results", "localStorage", "data/dev.jsonl",
                 "data/eval.jsonl"):
        assert name in js, name
    # In view: what to do and the saving rule. Behind one click, closed: how the search works.
    lede = " ".join(re.search(r'<p class="lede">(.*?)</p>', page, re.S).group(1).split())
    assert lede == ("Search for topics you are interested in, and select the HoVer claims about them. You need "
                    "exactly 112 claims, with at least 30 supported and 30 not supported, so that an agent that "
                    "always gives the same answer cannot score well.")
    assert page.count('class="lede"') == 1
    how = re.search(r'<details class="fold how">\s*<summary>How the search works</summary>(.*?)</details>', page, re.S)
    assert how and "<details class=\"fold how\" open" not in page
    for words in ("retrieval", "finder/search.py", "step 0b\n        asks you to read it", "embedding search",
                  "one-line descriptions"):
        assert words in how.group(1), words
    # How the code ranks is what step 0b asks the student to find by reading finder/search.py, so the
    # screen does not say it.
    for words in ("BM25", "reciprocal rank fusion", "fusion", "averag", "cosine"):
        assert words not in page + js, words
    # The button that selects every claim shown sits beside the count of claims with all the words.
    assert re.search(r'<p class="matches" id="matches"></p>\s*<button class="pick" id="all" type="button">'
                     r"Select all shown</button>", page)
    for sentence in (
            # the line at the top, and a selected claim
            "You have selected ${n} of ${NEEDED} claims: ${yes} supported and ${n - yes} not ",
            "You have selected this claim.",
            # each claim's ranks, in the word the pages use: "rank"
            "Its rank is ${k} by keyword and ${m} by meaning.",
            "Its rank is ${k} by keyword. The search by meaning did not put it among its best 1,000.",
            "Its rank is ${m} by meaning. It contains none of your words, so the search by keyword did not find it.",
            # the count of claims with all the words, and the calm sentence for a narrow topic
            "return `${contain(all)} all of your words.`;",
            "return `Only ${contain(all)} all of your words, so further down, the list may stop being about your topic. ` +\n"
            "      \"Select the ones that are on your topic, and search another topic for the rest.\";",
            "\"No claim contains all of your words, which is usual when you type several words. \" +\n"
            "      \"Select the claims on your topic.\";",
            "\"No claim contains your word, so the claims below were found by meaning alone and may be off your topic.\"",
            # saving
            "evaluation claims in data/eval.jsonl. Every run from step 1c on uses them."):
        assert sentence in js, sentence
    assert re.findall(r"^const FEW_CLAIMS = (\d+);", js, re.M) == ["200"]       # one named threshold
    assert "if (all < FEW_CLAIMS) {" in js and "NARROW" not in js
    assert "The dataset has few claims" not in js and "or were found by meaning alone" not in js
    assert len(re.findall(r"^const NEEDED = 112;", js, re.M)) == 1
    # Nothing left from the versions where the screen picked the claims.
    for stale in ('id="size"', "Put them back", "150", "100 to 200", "my-topic.jsonl", "step 3b", "Part 3",
                  "number ${"):
        assert stale not in page + js, stale
    words = (page + js).lower()
    assert words.count("embedding") == 1      # once, to say what the search by meaning is
    for word in ("hybrid", "corpus", "pool"):
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
    assert f"You need exactly {saved} claims, with at least {least} supported and {least} not supported," in intro
    assert len(re.findall(r"^const NEEDED = (\d+);", (STATIC / "finder.js").read_text(), re.M)) == 1
    assert f"const NEEDED = {saved};" in (STATIC / "finder.js").read_text()


# -- "Select all shown", run in Node -----------------------------------------------------------------
#
# These run finder.js itself in Node, with a small stand-in for the browser's page, storage and
# network, and then the test's own lines. They skip where Node is not installed.

BROWSER = r"""
const fs = require("fs"), vm = require("vm");
// Anything the script touches that the tests do not look at: it accepts every call and every property.
const any = new Proxy(function () {}, {
  get: (t, p) => (p === Symbol.toPrimitive ? () => "" : p === "then" ? undefined : any),
  apply: () => any,
  construct: () => any,
});
const elements = {}, storage = JSON.parse(process.argv[4]), sent = [];   // storage: what the browser kept
const element = () => new Proxy({ textContent: "", hidden: false, disabled: false },
                                 { get: (t, p) => (p in t ? t[p] : any) });
const context = vm.createContext({
  document: { getElementById: (id) => (elements[id] ||= element()), querySelectorAll: () => [],
              querySelector: () => any, addEventListener: () => {} },
  localStorage: { getItem: (k) => storage[k] ?? null, setItem: (k, v) => { storage[k] = v; } },
  fetch: (url, options) => { sent.push({ url: url, body: options && options.body }); return new Promise(() => {}); },
  location: { search: "" }, URLSearchParams, CSS: { escape: (s) => s }, DOMParser: any,
  elements, storage, sent,
});
vm.runInContext(fs.readFileSync(process.argv[2], "utf8"), context);
vm.runInContext("current = { query: 'jazz', how: 'both', total: 60 };", context);
console.log(JSON.stringify(vm.runInContext(process.argv[3], context)));
"""
# Fifty claims shown, c1 to c50, every other one supported, and a function that says what is on the
# screen: the button's label, whether it is disabled, the sentence under it and the line at the top.
SHOWN = """
for (let i = 1; i <= 50; i++) {
  shown.set("c" + i, { id: "c" + i, claim: "Claim " + i, label: i % 2 ? "SUPPORTED" : "NOT_SUPPORTED", hops: 2,
                       articles: ["A"], about: [""], keyword_rank: i, meaning_rank: i });
}
allButton();
var screen = () => ({ label: byId("all").textContent, disabled: byId("all").disabled,
                      said: byId("all-said").textContent, count: byId("count").textContent,
                      selected: [...selection.keys()] });
"""


def run_screen(tmp_path, lines, storage=None):
    """What finder.js shows after `lines` run, in Node, starting from what the browser kept in
    `storage` (its localStorage), as a reload would."""
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is not installed, so the screen's script cannot run outside a browser")
    (tmp_path / "browser.js").write_text(BROWSER)
    r = subprocess.run([node, str(tmp_path / "browser.js"), str(STATIC / "finder.js"), SHOWN + lines,
                        json.dumps(storage or {})], capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_select_all_says_how_many_it_would_select(tmp_path):
    s = run_screen(tmp_path, "screen()")
    assert (s["label"], s["disabled"]) == ("Select all 50 shown", False)
    s = run_screen(tmp_path, "toggle('c2'); toggle('c7'); screen()")       # selected one at a time
    assert s["label"] == "Select all 48 shown"
    s = run_screen(tmp_path, """
      for (let i = 51; i <= 100; i++) shown.set("c" + i, { id: "c" + i, label: "SUPPORTED" });   // Show 50 more
      allButton(); screen()""")
    assert s["label"] == "Select all 100 shown"


def test_select_all_selects_every_claim_shown_as_select_would(tmp_path):
    s = run_screen(tmp_path, """
      const KEPT = "comp440-hw3-claim-finder-selection";
      selectAll();
      const afterAll = screen(), kept = JSON.parse(storage[KEPT]);
      toggle("c1"); toggle("c1");                  // c1 removed, then selected again with its own Select
      ({ afterAll, kept, one: JSON.parse(storage[KEPT]).at(-1), said: byId("all-said").textContent })""")
    assert s["afterAll"]["selected"] == [f"c{i}" for i in range(1, 51)]
    assert s["afterAll"]["count"] == "You have selected 50 of 112 claims: 25 supported and 25 not supported."
    assert [c["id"] for c in s["kept"]] == [f"c{i}" for i in range(1, 51)]
    # Each claim is stored as its own Select stores it: the claim's data and the search that found it.
    assert s["kept"][0] == s["one"]
    assert s["one"] == {"id": "c1", "claim": "Claim 1", "label": "SUPPORTED", "hops": 2, "articles": ["A"],
                        "about": [""], "keyword_rank": 1, "meaning_rank": 1, "query": "jazz"}
    assert s["said"] == ""                         # a single Select clears the button's sentence


def test_select_all_says_what_it_did_and_then_has_nothing_left(tmp_path):
    s = run_screen(tmp_path, "selectAll(); screen()")
    assert s["said"] == "You selected 50 more claims. You have now selected 50 of 112."
    assert (s["label"], s["disabled"]) == ("Select all shown", True)


def test_select_all_skips_claims_already_selected(tmp_path):
    s = run_screen(tmp_path, "toggle('c3'); toggle('c10'); selectAll(); screen()")
    assert s["selected"][:2] == ["c3", "c10"] and len(s["selected"]) == 50 and len(set(s["selected"])) == 50
    assert s["said"] == "You selected 48 more claims. You have now selected 50 of 112."


def test_select_all_never_goes_past_112(tmp_path):
    hundred = """
      for (let i = 1; i <= 100; i++) selection.set("old" + i, { id: "old" + i, label: "SUPPORTED", query: "film" });
      allButton();
    """
    s = run_screen(tmp_path, hundred + "screen()")
    assert (s["label"], s["disabled"]) == ("Select the first 12 shown", False)
    s = run_screen(tmp_path, hundred + "selectAll(); screen()")
    assert s["selected"][100:] == [f"c{i}" for i in range(1, 13)]          # from the top of the list
    assert s["said"] == "You selected 12 more claims, the first 12 in the list. You have 112, which is all you need."
    assert s["count"] == "You have selected 112 of 112 claims: 106 supported and 6 not supported."
    assert (s["label"], s["disabled"]) == ("Select all shown", True)
    # With room for one more claim, the label and the sentence say "one".
    room_for_one = hundred.replace("i <= 100", "i <= 111")
    assert run_screen(tmp_path, room_for_one + "screen()")["label"] == "Select the first one shown"
    s = run_screen(tmp_path, room_for_one + "selectAll(); screen()")
    assert s["said"] == "You selected 1 more claim, the first one in the list. You have 112, which is all you need."
    s = run_screen(tmp_path, room_for_one + "shown.clear(); shown.set('c9', { id: 'c9' }); allButton(); screen()")
    assert s["label"] == "Select the 1 shown"


def test_select_all_is_disabled_with_nothing_to_select(tmp_path):
    assert run_screen(tmp_path, "shown.clear(); allButton(); screen()")["disabled"] is True
    s = run_screen(tmp_path, """
      for (let i = 1; i <= 113; i++) selection.set("old" + i, { id: "old" + i, label: "SUPPORTED", query: "film" });
      allButton(); screen()""")
    assert (s["label"], s["disabled"]) == ("Select all shown", True)


def test_a_selection_made_with_select_all_saves_like_any_other(stand_in, tmp_path):
    # The screen shows the stand-in's first eight claims for "jazz"; Select all, then Save.
    eight = get("/search", tmp_path, q="jazz")[1]["results"][:8]
    s = run_screen(tmp_path, f"""
      shown.clear();
      {json.dumps(eight)}.forEach((c) => shown.set(c.id, c));
      selectAll(); save();
      sent.filter((s) => s.url === "/claims/save").map((s) => JSON.parse(s.body))""")
    body = s[0]
    assert body == {"selected": [{"id": c["id"], "query": "jazz"} for c in eight]}
    assert post("/save", tmp_path, body)[1]["ok"] is True
    assert len((tmp_path / "data/eval.jsonl").read_text().splitlines()) == 4


# Step 0b's way of working: Select all shown, Remove two claims that are off the topic, Show 50 more,
# Select all shown again.
REMOVE_TWO = """
  selectAll(); toggle("c3"); toggle("c8");
  for (let i = 51; i <= 100; i++) shown.set("c" + i, { id: "c" + i, label: "SUPPORTED" });   // Show 50 more
  allButton();
"""


def test_select_all_leaves_out_the_claims_the_student_removed(tmp_path):
    s = run_screen(tmp_path, REMOVE_TWO + "screen()")
    assert (s["label"], s["disabled"]) == ("Select all 50 shown", False)    # c51 to c100, not c3 or c8
    s = run_screen(tmp_path, REMOVE_TWO + "selectAll(); screen()")
    assert "c3" not in s["selected"] and "c8" not in s["selected"] and len(s["selected"]) == 98
    assert s["said"] == ("You selected 50 more claims. You have now selected 98 of 112. "
                         "The 2 claims you removed earlier stay removed.")
    assert (s["label"], s["disabled"]) == ("Select all shown", True)       # only removed claims are left
    # Fifty shown, all selected, then one removed: the button has nothing to select.
    s = run_screen(tmp_path, "selectAll(); toggle('c3'); screen()")
    assert (s["label"], s["disabled"]) == ("Select all shown", True) and "c3" not in s["selected"]


def test_a_removed_claims_own_select_brings_it_back(tmp_path):
    s = run_screen(tmp_path, REMOVE_TWO + "toggle('c3'); ({ ...screen(), removed: [...removed] })")
    assert "c3" in s["selected"] and s["removed"] == ["c8"]
    assert s["label"] == "Select all 50 shown"                               # c3 is selected, c8 still left out
    s = run_screen(tmp_path, REMOVE_TWO + "toggle('c3'); selectAll(); screen()")
    assert "c8" not in s["selected"] and len(s["selected"]) == 99
    assert s["said"].endswith(" The claim you removed earlier stays removed.")


def test_the_removed_claims_are_kept_across_a_reload(tmp_path):
    kept = run_screen(tmp_path, REMOVE_TWO + "storage")
    assert json.loads(kept["comp440-hw3-claim-finder-removed"]) == ["c3", "c8"]
    # A reload: the script starts again from what the browser kept, and a new search shows c1 to c50.
    s = run_screen(tmp_path, "({ ...screen(), removed: [...removed] })", storage=kept)
    assert s["removed"] == ["c3", "c8"] and len(s["selected"]) == 48
    assert (s["label"], s["disabled"]) == ("Select all shown", True)        # c3 and c8 are the only ones left


def test_the_cap_at_112_holds_with_removed_claims(tmp_path):
    s = run_screen(tmp_path, """
      for (let i = 1; i <= 100; i++) selection.set("old" + i, { id: "old" + i, label: "SUPPORTED", query: "film" });
      removed.add("c1"); removed.add("c2"); allButton();
      const label = byId("all").textContent;
      selectAll(); ({ ...screen(), label })""")
    assert s["label"] == "Select the first 12 shown"
    assert s["selected"][100:] == [f"c{i}" for i in range(3, 15)]           # from the top, without c1 and c2
    assert s["said"] == ("You selected 12 more claims, the first 12 in the list. You have 112, which is all you "
                         "need. The 2 claims you removed earlier stay removed.")


def test_the_homework_page_no_longer_links_to_the_screen():
    """Step 0b, which used the screen, is gone (the instructor, Nov 11: "drop 0b"). The screen's
    routes stay under /claims, but the homework page's header has no link to them."""
    page = (ROOT / "workbench/static/index.html").read_text()
    assert "/claims" not in page and "Find claims" not in page
    assert '<a href="/results/" target="_blank" rel="noopener">Results</a>' in page
