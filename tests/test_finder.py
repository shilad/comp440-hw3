"""Offline tests for the claim finder (finder/search.py): its data files, the two rankings and
their fusion, pick's balance, save's format and refusals, and a few searches on the real data."""

import json
import re
import socket
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from finder import search  # noqa: E402


def made_up_claim(number, text, label="SUPPORTED", hops=2):
    return {"id": f"hover-{number}", "claim": text, "label": label, "hops": hops,
            "articles": [f"Article {number}"], "about": [""]}


FAKE_CLAIMS = [
    made_up_claim(0, "Miles Davis played jazz trumpet."),
    made_up_claim(1, "The Lakers play basketball in Los Angeles.", "NOT_SUPPORTED"),
    made_up_claim(2, "Jazz jazz jazz, and more jazz from New Orleans."),
    made_up_claim(3, "A saxophone quartet recorded an album.", "NOT_SUPPORTED"),
    made_up_claim(4, "The Lakers won a game."),
]
FAKE_WORDS = {"jazz": [1, 0], "trumpet": [1, 0], "saxophone": [1, 0], "music": [1, 0],
              "basketball": [0, 1], "lakers": [0, 1], "game": [0, 1]}


@pytest.fixture
def fake_data(monkeypatch):
    """Replace the real data files with the five claims and seven word vectors above."""
    monkeypatch.setattr(search, "claims", lambda: FAKE_CLAIMS)
    monkeypatch.setattr(search, "word_vectors", lambda: FAKE_WORDS)
    vectors = [search.unit(search.vector(search.searched_text(c))) for c in FAKE_CLAIMS]
    monkeypatch.setattr(search, "claim_vectors", lambda: vectors)
    search.keyword_index.cache_clear()
    yield
    search.keyword_index.cache_clear()


def results(labels):
    """Made-up search results, best first, with the given labels."""
    return [dict(made_up_claim(number, f"claim {number}", label), keyword_rank=number + 1,
                 meaning_rank=None) for number, label in enumerate(labels)]


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


# The data files

def test_data_files_load_and_agree():
    claims = search.claims()
    vectors = search.claim_vectors()
    assert len(claims) == len(vectors)
    assert 11_000 < len(claims) < 12_500  # at most one claim of each label per HoVer source question
    assert len({c["id"] for c in claims}) == len(claims)
    for claim in claims:
        assert set(claim) == {"id", "claim", "label", "hops", "articles", "about"}
        assert claim["label"] in ("SUPPORTED", "NOT_SUPPORTED")
        assert claim["hops"] in (2, 3, 4)
        assert claim["articles"] == sorted(claim["articles"])
        assert len(claim["about"]) == len(claim["articles"])
    lengths = {len(v) for v in search.word_vectors().values()} | {len(v) for v in vectors}
    assert lengths == {128}


def same_text(text):
    return " ".join(text.lower().split())


def test_no_claim_the_homework_already_uses():
    used = [row for name in ("eval.jsonl", "dev.jsonl") for row in read_jsonl(ROOT / "data" / name)]
    if len(used) != 212:
        pytest.skip("data/eval.jsonl and data/dev.jsonl hold claims saved by the claim finder, not the sample")
    assert not {row["id"] for row in used} & {c["id"] for c in search.claims()}
    assert not {same_text(row["claim"]) for row in used} & {same_text(c["claim"]) for c in search.claims()}


def test_no_claim_text_repeats():
    texts = [same_text(c["claim"]) for c in search.claims()]
    assert len(set(texts)) == len(texts)


@pytest.mark.parametrize("query", ["Minnesota", "basketball", "jazz"])
def test_no_cluster_of_near_identical_claims(query):
    # HoVer made up to 12 claims from one question; the build keeps one of each label per question.
    best = search.search(query)[:30]
    kinds = [(tuple(c["articles"]), c["label"]) for c in best]
    assert len(set(kinds)) == len(kinds)


def test_data_files_stay_small():
    total = sum((search.DATA / name).stat().st_size
                for name in ("claims.json.gz", "word_vectors.json.gz", "claim_vectors.json.gz"))
    assert total <= 12_000_000


# The rankings, on made-up data

def test_words_are_lower_case_without_common_words():
    assert search.words("The Lakers, of Los Angeles!") == ["lakers", "los", "angeles"]
    assert search.words("women's soccer") == ["women", "soccer"]


def test_searched_text_has_the_claim_titles_and_descriptions(monkeypatch):
    claim = dict(made_up_claim(9, "A claim."), articles=["Dan &quot;OGRE 1&quot; Ryan"],
                 about=["American magazine editor"])
    assert search.searched_text(claim) == 'A claim. Dan "OGRE 1" Ryan American magazine editor'
    monkeypatch.setattr(search, "SEARCH_DESCRIPTIONS", False)
    assert search.searched_text(claim) == 'A claim. Dan "OGRE 1" Ryan'


def test_keyword_ranking_only_has_claims_with_a_query_word(fake_data):
    assert search.keyword_ranking("jazz") == [2, 0]  # the claim that says jazz four times first
    assert search.keyword_ranking("lakers") == [4, 1]  # the shorter claim first
    assert search.keyword_ranking("hockey") == []


def test_vector_is_the_average_of_known_words(fake_data):
    assert search.vector("jazz basketball unknown") == [0.5, 0.5]
    assert search.vector("nothing known here") == []


def test_meaning_ranking_ranks_every_claim_by_closeness(fake_data):
    ranking = search.meaning_ranking("music")
    assert sorted(ranking) == [0, 1, 2, 3, 4]
    assert set(ranking[:3]) == {0, 2, 3}  # the saxophone claim has no word "music" but is close
    assert search.meaning_ranking("nothing known") == []


def test_fusion_adds_one_over_sixty_plus_rank():
    # Claim 7 is second in both rankings: 2/62 beats 1/61 + nothing for claims 5 and 9.
    assert search.fuse([5, 7], [9, 7]) == [7, 5, 9]
    assert search.fuse([], [3, 4]) == [3, 4]


def test_search_gives_both_ranks(fake_data):
    assert [r["id"] for r in search.search("jazz", "keyword")] == ["hover-2", "hover-0"]
    assert search.search("hockey", "keyword") == []
    found ={r["id"]: r for r in search.search("jazz", "both")}
    assert len(found) == 5  # the two keyword matches and every claim ranked by meaning
    assert (found["hover-2"]["keyword_rank"], found["hover-2"]["meaning_rank"]) == (1, 2)
    assert (found["hover-3"]["keyword_rank"], found["hover-3"]["meaning_rank"]) == (None, 3)
    with pytest.raises(ValueError):
        search.search("jazz", "neither")


# pick

def test_pick_takes_half_of_each_label():
    picked = search.pick(results(["SUPPORTED"] * 10 + ["NOT_SUPPORTED"] * 10), size=8)
    assert [r["label"] for r in picked].count("SUPPORTED") == 4
    assert [r["id"] for r in picked] == [f"hover-{n}" for n in (0, 1, 2, 3, 10, 11, 12, 13)]


def test_pick_fills_from_the_other_label_when_one_runs_out():
    picked = search.pick(results(["SUPPORTED"] * 10 + ["NOT_SUPPORTED"] * 2), size=8)
    assert len(picked) == 8
    assert [r["label"] for r in picked].count("NOT_SUPPORTED") == 2


def test_pick_leaves_out_removed_and_brings_in_the_next_of_that_label():
    labels = ["SUPPORTED", "NOT_SUPPORTED"] * 5
    picked = search.pick(results(labels), size=4, removed={"hover-0"})
    assert [r["id"] for r in picked] == ["hover-1", "hover-2", "hover-3", "hover-4"]


def test_pick_with_too_few_results_takes_them_all():
    assert len(search.pick(results(["SUPPORTED"] * 3), size=150)) == 3


# split, save and locked

def selection(labels):
    """Made-up selected claims with ids that sort in number order (hover-000, hover-001, ...)."""
    return [dict(made_up_claim(f"{n:03d}", f"claim {n}", label)) for n, label in enumerate(labels)]


ALTERNATING = ["SUPPORTED", "NOT_SUPPORTED"] * 56  # 112 labels, 56 of each
LOCKED = ("You have already run the agent on your claims. To choose different claims, first rename "
          "the folders runs/part1/before, runs/part1/after and runs/part2 (for example by adding -old "
          "to each name); you will then have to do the runs of steps 1c, 1d and 1e again.")


def test_split_puts_the_claims_in_id_order_and_takes_six_of_each_label():
    selected = selection(["NOT_SUPPORTED"] * 8 + ["SUPPORTED"] * 8)[::-1]  # selected in any order
    development, evaluation = search.split(selected)
    assert [c["id"] for c in development] == [f"hover-{n:03d}" for n in (0, 1, 2, 3, 4, 5, 8, 9, 10, 11, 12, 13)]
    assert [c["id"] for c in evaluation] == ["hover-006", "hover-007", "hover-014", "hover-015"]


def test_save_writes_development_and_evaluation_claims_and_a_note(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    (data / "eval.jsonl").write_text("the sample that ships\n")
    selected = selection(ALTERNATING)[::-1]
    queries = ["film"] * 60 + ["jazz"] * 52
    paths = search.save(selected, queries, folder=tmp_path)
    assert paths == (data / "dev.jsonl", data / "eval.jsonl")
    development, evaluation = read_jsonl(data / "dev.jsonl"), read_jsonl(data / "eval.jsonl")
    assert [c["id"] for c in development] == [f"hover-{n:03d}" for n in range(12)]
    assert [c["id"] for c in evaluation] == [f"hover-{n:03d}" for n in range(12, 112)]
    assert list(development[0]) == ["id", "claim", "source", "label", "hops", "articles"]
    assert development[0]["source"] == "hover"
    note = json.loads((data / "my-topic.json").read_text())
    assert note == {"topics": [{"query": "film", "claims": 60}, {"query": "jazz", "claims": 52}],
                    "development": 12, "evaluation": 100, "supported": 56, "not_supported": 56}
    assert not (data / "my-topic.jsonl").exists()


def test_save_counts_a_claim_selected_twice_once_for_the_first_search(tmp_path):
    selected = selection(ALTERNATING)
    search.save(selected + selected[:3], ["film"] * 112 + ["jazz"] * 3, folder=tmp_path)
    note = json.loads((tmp_path / "data" / "my-topic.json").read_text())
    assert note["topics"] == [{"query": "film", "claims": 112}]


def test_save_refuses_anything_but_112_claims(tmp_path):
    for count, said in ((87, "87 claims"), (1, "1 claim"), (113, "113 claims")):
        labels = (ALTERNATING * 2)[:count]
        selected = selection(labels)
        sentence = (f"You have selected {said}, and you need exactly 112: 12 development claims "
                    "and 100 evaluation claims.")
        with pytest.raises(ValueError, match="^" + re.escape(sentence) + "$"):
            search.save(selected, ["film"] * count, folder=tmp_path)
    assert not (tmp_path / "data" / "eval.jsonl").exists()


@pytest.mark.parametrize("supported, name", [(90, "not supported"), (25, "supported")])
def test_save_refuses_fewer_than_30_of_a_label(tmp_path, supported, name):
    selected = selection(["SUPPORTED"] * supported + ["NOT_SUPPORTED"] * (112 - supported))
    have = min(supported, 112 - supported)
    sentence = (f"Only {have} of your claims are labeled {name}, and you need at least 30 of each "
                "label, so that an agent that always gives the same answer cannot score well. Select "
                f"more claims that the dataset labels {name}.")
    with pytest.raises(ValueError, match="^" + re.escape(sentence) + "$"):
        search.save(selected, ["film"] * 112, folder=tmp_path)


def test_save_accepts_exactly_30_of_a_label(tmp_path):
    selected = selection(["SUPPORTED"] * 82 + ["NOT_SUPPORTED"] * 30)
    search.save(selected, ["film"] * 112, folder=tmp_path)
    assert json.loads((tmp_path / "data" / "my-topic.json").read_text())["not_supported"] == 30


@pytest.mark.parametrize("run", ["part1/before", "part1/after", "part2"])
def test_save_refuses_once_the_agent_has_run_on_the_claims(tmp_path, run):
    (tmp_path / "runs" / run).mkdir(parents=True)
    (tmp_path / "runs" / run / "agent.jsonl").write_text("")
    assert search.locked(tmp_path)
    with pytest.raises(ValueError, match="^" + re.escape(LOCKED) + "$"):
        search.save(selection(ALTERNATING), ["film"] * 112, folder=tmp_path)


def test_empty_run_folders_and_part0_do_not_lock(tmp_path):
    assert not search.locked(tmp_path)
    (tmp_path / "runs" / "part1" / "before").mkdir(parents=True)  # empty
    (tmp_path / "runs" / "part2").mkdir(parents=True)  # empty
    (tmp_path / "runs" / "part0" / "x").mkdir(parents=True)  # step 0's runs use a fixed claim
    assert not search.locked(tmp_path)


def test_the_files_of_steps_1a_and_1b_do_not_lock(tmp_path):
    part1 = tmp_path / "runs" / "part1"
    part1.mkdir(parents=True)
    (part1 / "loop-check.txt").write_text("yours\n")  # check_loop.py, step 1a
    (part1 / "lookups.jsonl").write_text("{}\n")  # lookup.py, step 1b
    assert not search.locked(tmp_path)
    search.save(selection(ALTERNATING), ["film"] * 112, folder=tmp_path)
    assert (tmp_path / "data" / "eval.jsonl").exists()


def test_save_needs_one_query_per_claim(tmp_path):
    with pytest.raises(ValueError):
        search.save(selection(ALTERNATING), ["film"] * 111, folder=tmp_path)


def test_saved_claims_are_scored_by_evaluate_like_hover_claims(tmp_path):
    import evaluate
    for path in search.save(search.pick(search.search("jazz")), ["jazz"] * 112, folder=tmp_path):
        for row in read_jsonl(path):
            assert evaluate.is_correct(row, "supported") == (row["label"] == "SUPPORTED")
            assert evaluate.group_of(row) == f"HoVer, {row['hops']} articles"


# keyword_counts and claims_by_id

def test_keyword_counts_any_and_all_words(fake_data):
    assert search.keyword_counts("jazz") == {"any": 2, "all": 2}
    assert search.keyword_counts("jazz lakers") == {"any": 4, "all": 0}
    assert search.keyword_counts("Miles Davis jazz") == {"any": 2, "all": 1}
    assert search.keyword_counts("the of") == {"any": 0, "all": 0}


def test_keyword_counts_on_the_real_data():
    one_word = search.keyword_counts("basketball")
    assert one_word["any"] == one_word["all"] == len(search.keyword_ranking("basketball"))
    two_words = search.keyword_counts("video games")
    assert two_words["all"] < two_words["any"] == len(search.keyword_ranking("video games"))


def test_claims_by_id_finds_every_claim():
    by_id = search.claims_by_id()
    assert len(by_id) == len(search.claims())
    first = search.claims()[0]
    assert by_id[first["id"]] is first


# The real data

@pytest.mark.parametrize("query, word", [("basketball", "basketball"), ("jazz", "jazz"),
                                         ("Minnesota", "minnesota")])
def test_the_best_results_are_on_topic(query, word):
    for how in ("keyword", "both"):
        best = search.search(query, how)[:10]
        assert all(word in search.searched_text(r).lower() for r in best), how
    best_by_meaning = search.search(query, "meaning")[:10]
    assert sum(word in search.searched_text(r).lower() for r in best_by_meaning) >= 5


def test_pick_on_real_data_is_balanced():
    picked = search.pick(search.search("jazz"))
    assert len(picked) == 112
    assert [r["label"] for r in picked].count("SUPPORTED") == 56


def test_same_query_same_results_and_same_files(tmp_path):
    saved = []
    for name in ("a", "b"):
        paths = search.save(search.pick(search.search("horror films")), ["horror films"] * 112,
                            folder=tmp_path / name)
        saved.append([path.read_text() for path in paths])
    assert saved[0] == saved[1]


def test_works_with_the_network_off(monkeypatch, tmp_path):
    def no_network(*args, **kwargs):
        raise OSError("the network is off in this test")
    monkeypatch.setattr(socket, "socket", no_network)
    monkeypatch.setattr(socket, "create_connection", no_network)
    for loaded_once in (search.claims, search.claims_by_id, search.word_vectors, search.claim_vectors,
                        search.keyword_index):
        loaded_once.cache_clear()  # so that the data files are read again with the network off
    picked = search.pick(search.search("astronomy", "meaning"))
    development, evaluation = search.save(picked, ["astronomy"] * 112, folder=tmp_path)
    assert len(evaluation.read_text().splitlines()) == 100


def test_command_line_prints_three_lists_and_the_counts():
    printed = subprocess.run([sys.executable, "-m", "finder", "jazz musicians"], cwd=ROOT,
                             capture_output=True, text=True, check=True).stdout
    for how in ("keyword", "meaning", "both"):
        assert f"Best ten by {how}:" in printed
    assert re.search(r"jazz musicians: \d+ claims contain at least one of your words, and \d+ contain all", printed)


def test_command_line_save_refuses_a_topic_that_finds_too_few(monkeypatch, tmp_path):
    from finder import __main__ as command_line
    monkeypatch.setattr(search, "HOMEWORK", tmp_path)
    monkeypatch.setattr(sys, "argv", ["finder", "--save", "film", "xyzzy"])
    with pytest.raises(SystemExit) as stopped:
        command_line.main()
    assert str(stopped.value) == ('The topic "xyzzy" found only 0 claims, and its share of the 112 is 56. '
                                  "Try other words for it, or leave it out.")
    assert not (tmp_path / "data").exists()


def test_command_line_save_takes_an_even_share_from_each_topic(monkeypatch, tmp_path, capsys):
    from finder import __main__ as command_line
    monkeypatch.setattr(search, "HOMEWORK", tmp_path)
    monkeypatch.setattr(sys, "argv", ["finder", "--save", "film", "basketball", "television"])
    command_line.main()
    assert "Saved 12 development claims in" in capsys.readouterr().out
    assert len(read_jsonl(tmp_path / "data" / "eval.jsonl")) == 100
    note = json.loads((tmp_path / "data" / "my-topic.json").read_text())
    assert note["topics"] == [{"query": "film", "claims": 38}, {"query": "basketball", "claims": 37},
                              {"query": "television", "claims": 37}]
