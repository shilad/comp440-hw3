"""The claim finder's search: find HoVer claims about a topic, by keyword, by meaning, or both.

This is a small retrieval system of the kind the class built on Oct 13, in plain Python.
"By keyword" scores claims with BM25, which rewards claims that use the query's words,
rare words most. "By meaning" turns the query and every claim into a vector (the average
of their words' vectors) and ranks claims by how close their vector is to the query's.
"Both" combines the two rankings with reciprocal rank fusion.

The data lives in finder/data/, built once by finder/build_data.py.
"""
import functools
import gzip
import html
import json
import math
import re
from collections import Counter
from pathlib import Path

DATA = Path(__file__).parent / "data"
HOMEWORK = Path(__file__).parent.parent

COMMON_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "have", "he",
    "her", "his", "in", "is", "it", "its", "of", "on", "or", "s", "she", "that", "the", "their",
    "this", "to", "was", "were", "which", "who", "with",
}  # "s" is what is left of "women's" once the apostrophe splits it
BM25_K1 = 1.5        # how quickly repeating a word stops adding to a claim's score
BM25_B = 0.75        # how much a long claim is marked down for being long
MEANING_LIMIT = 1000  # search keeps this many claims by meaning
FUSION_K = 60        # in "both", a claim at rank r adds 1 / (60 + r)
SEARCH_DESCRIPTIONS = True  # also search the articles' one-line descriptions (run build_data.py after changing this)
SAVED_CLAIMS = 112          # what a student saves: 12 development claims and 100 evaluation claims
DEVELOPMENT_PER_LABEL = 6   # the development claims: the first six supported and six not supported
LEAST_PER_LABEL = 30        # a saved set needs at least this many claims of each label


def read(name):
    """One of the data files in finder/data/."""
    with gzip.open(DATA / name, "rt", encoding="utf-8") as file:
        return json.load(file)


@functools.lru_cache(maxsize=None)
def claims():
    """Every claim the finder can offer, loaded once."""
    return read("claims.json.gz")


@functools.lru_cache(maxsize=None)
def claims_by_id():
    """Every claim the finder can offer, as {id: claim}, made once."""
    return {claim["id"]: claim for claim in claims()}


def words(text):
    """The lower-case words of a text, leaving out a few very common ones."""
    return [word for word in re.findall(r"\w+", text.lower()) if word not in COMMON_WORDS]


def searched_text(claim):
    """The text a claim is searched by: the claim, its article titles and their descriptions."""
    descriptions = claim["about"] if SEARCH_DESCRIPTIONS else []
    # HoVer writes some characters in titles as codes, such as "&amp;" for "&"; unescape turns them back.
    return html.unescape(" ".join([claim["claim"], *claim["articles"], *descriptions]))


@functools.lru_cache(maxsize=None)
def keyword_index():
    """For each word, the claims that contain it and how often; and each claim's length in words."""
    claims_with = {}
    lengths = []
    for number, claim in enumerate(claims()):
        counts = Counter(words(searched_text(claim)))
        lengths.append(sum(counts.values()))
        for word, count in counts.items():
            claims_with.setdefault(word, []).append((number, count))
    return claims_with, lengths


def keyword_ranking(query):
    """Claim numbers, best first, by BM25: how well the claim's words match the query's words."""
    claims_with, lengths = keyword_index()
    average_length = sum(lengths) / len(lengths)
    scores = Counter()
    for word in set(words(query)):
        matches = claims_with.get(word, [])
        rarity = math.log(1 + (len(lengths) - len(matches) + 0.5) / (len(matches) + 0.5))
        for number, count in matches:
            length_penalty = 1 - BM25_B + BM25_B * lengths[number] / average_length
            scores[number] += rarity * count * (BM25_K1 + 1) / (count + BM25_K1 * length_penalty)
    return sorted(scores, key=lambda number: (-scores[number], number))


def keyword_counts(query):
    """How many claims contain at least one of the query's words ("any") and every one of them ("all")."""
    claims_with, _ = keyword_index()
    found = [{number for number, _ in claims_with.get(word, [])} for word in set(words(query))]
    if not found:
        return {"any": 0, "all": 0}
    return {"any": len(set.union(*found)), "all": len(set.intersection(*found))}


@functools.lru_cache(maxsize=None)
def word_vectors():
    """Each word's vector: {word: [128 whole numbers from -127 to 127]}, loaded once."""
    return read("word_vectors.json.gz")


def vector(text):
    """The average of the vectors of the words in a text."""
    known = [word_vectors()[word] for word in words(text) if word in word_vectors()]
    if not known:
        return []
    return [sum(column) / len(known) for column in zip(*known)]


def unit(v):
    """The vector scaled to length 1, so that the dot product of two such vectors is their cosine."""
    length = math.sqrt(sum(x * x for x in v))
    return [x / length for x in v] if length else v


@functools.lru_cache(maxsize=None)
def claim_vectors():
    """Each claim's vector, scaled to length 1, in the order of claims(); loaded once."""
    return [unit(v) for v in read("claim_vectors.json.gz")]


def meaning_ranking(query):
    """Claim numbers, best first, by how close the claim's vector is to the query's vector."""
    q = unit(vector(query))
    if not q:
        return []
    closeness = [sum(a * b for a, b in zip(q, c)) for c in claim_vectors()]
    return sorted(range(len(closeness)), key=lambda number: (-closeness[number], number))


def fuse(*rankings):
    """Reciprocal rank fusion: a claim at rank r in a ranking adds 1 / (60 + r) to its score."""
    scores = Counter()
    for ranking in rankings:
        for rank, number in enumerate(ranking, start=1):
            scores[number] += 1 / (FUSION_K + rank)
    return sorted(scores, key=lambda number: (-scores[number], number))


def search(query, how="both"):
    """The matching claims, best first. how is "keyword", "meaning" or "both".
    Each result is the claim's dictionary plus "keyword_rank" and "meaning_rank"
    (1 is best; None when the claim is not in that ranking)."""
    if how not in ("keyword", "meaning", "both"):
        raise ValueError(f'The way to search must be "keyword", "meaning" or "both", not {how!r}.')
    by_keyword = keyword_ranking(query)
    by_meaning = meaning_ranking(query)[:MEANING_LIMIT]
    if how == "keyword":
        order = by_keyword
    elif how == "meaning":
        order = by_meaning
    else:
        order = fuse(by_keyword, by_meaning)
    keyword_place = {number: rank for rank, number in enumerate(by_keyword, start=1)}
    meaning_place = {number: rank for rank, number in enumerate(by_meaning, start=1)}
    return [dict(claims()[number], keyword_rank=keyword_place.get(number),
                 meaning_rank=meaning_place.get(number)) for number in order]


def pick(results, size=SAVED_CLAIMS, removed=()):
    """The best `size` results, half supported and half not supported where the results allow it,
    leaving out the ids in `removed`. (Only the command line uses it; on the screen the student selects.)"""
    removed = set(removed)
    kept = [result for result in results if result["id"] not in removed]
    supported = [result for result in kept if result["label"] == "SUPPORTED"]
    not_supported = [result for result in kept if result["label"] == "NOT_SUPPORTED"]
    take_supported = min(len(supported), (size + 1) // 2)
    take_not_supported = min(len(not_supported), size - take_supported)
    take_supported = min(len(supported), size - take_not_supported)  # fill up if one label ran out
    chosen = {result["id"] for result in supported[:take_supported] + not_supported[:take_not_supported]}
    return [result for result in kept if result["id"] in chosen]


def split(selected):
    """The development claims (the first six supported and first six not supported) and the evaluation
    claims (all the others), both in the order of the claims' ids, which is as good as random and so
    mixes the student's topics."""
    ordered = sorted(selected, key=lambda claim: claim["id"])
    supported = [claim for claim in ordered if claim["label"] == "SUPPORTED"]
    not_supported = [claim for claim in ordered if claim["label"] == "NOT_SUPPORTED"]
    chosen = {claim["id"] for claim in supported[:DEVELOPMENT_PER_LABEL] + not_supported[:DEVELOPMENT_PER_LABEL]}
    development = [claim for claim in ordered if claim["id"] in chosen]
    evaluation = [claim for claim in ordered if claim["id"] not in chosen]
    return development, evaluation


RUN_FOLDERS = ("part1/before", "part1/after", "part2")  # what steps 1c, 1d and 1e write


def locked(folder=None):
    """Whether the agent has already run on the saved claims: a folder that step 1c, 1d or 1e writes holds anything."""
    runs = Path(folder or HOMEWORK) / "runs"
    return any((runs / run).is_dir() and any((runs / run).iterdir()) for run in RUN_FOLDERS)


def write_claims(path, claims):
    """Write claims to a .jsonl file in data/eval.jsonl's format, one claim per line."""
    with open(path, "w", encoding="utf-8") as file:
        for claim in claims:
            row = {"id": claim["id"], "claim": claim["claim"], "source": "hover",
                   "label": claim["label"], "hops": claim["hops"], "articles": claim["articles"]}
            file.write(json.dumps(row) + "\n")


def save(selected, queries, folder=None):
    """Write the 112 selected claims over data/dev.jsonl (12 development claims) and data/eval.jsonl
    (100 evaluation claims), and the topics that found them to data/my-topic.json. `queries` holds
    the search that found each claim, in the same order. Returns the paths of the two claim files."""
    folder = Path(folder or HOMEWORK)
    if locked(folder):
        raise ValueError("You have already run the agent on your claims. To choose different claims, "
                         "first rename the folders runs/part1/before, runs/part1/after and runs/part2 "
                         "(for example by adding -old to each name); you will then have to do the runs "
                         "of steps 1c, 1d and 1e again.")
    found_by = {}  # each distinct claim, with the search that found it first
    for claim, query in zip(selected, queries, strict=True):
        found_by.setdefault(claim["id"], (claim, query))
    chosen = [claim for claim, _ in found_by.values()]
    if len(chosen) != SAVED_CLAIMS:
        count = "1 claim" if len(chosen) == 1 else f"{len(chosen)} claims"
        raise ValueError(f"You have selected {count}, and you need exactly 112: 12 development "
                         "claims and 100 evaluation claims.")
    for label, name in (("SUPPORTED", "supported"), ("NOT_SUPPORTED", "not supported")):
        have = sum(1 for claim in chosen if claim["label"] == label)
        if have < LEAST_PER_LABEL:
            raise ValueError(f"Only {have} of your claims are labeled {name}, and you need at least {LEAST_PER_LABEL} "
                             "of each label, so that an agent that always gives the same answer cannot "
                             f"score well. Select more claims that the dataset labels {name}.")
    development, evaluation = split(chosen)
    data = folder / "data"
    data.mkdir(parents=True, exist_ok=True)
    write_claims(data / "dev.jsonl", development)
    write_claims(data / "eval.jsonl", evaluation)
    topics = Counter(query for _, query in found_by.values())  # in the order each topic was first used
    supported = sum(1 for claim in chosen if claim["label"] == "SUPPORTED")
    note = {"topics": [{"query": query, "claims": count} for query, count in topics.items()],
            "development": len(development), "evaluation": len(evaluation),
            "supported": supported, "not_supported": len(chosen) - supported}
    (data / "my-topic.json").write_text(json.dumps(note, indent=2) + "\n", encoding="utf-8")
    return data / "dev.jsonl", data / "eval.jsonl"
