"""A stand-in for finder/search.py, for tests/test_finder_page.py: the functions the screen calls,
with the same return shapes, over twenty made-up claims, so the claim finder's screen can be tested
without the real claims and word vectors. Never shipped and never used by the homework itself."""

import json
import re
from pathlib import Path

TOPICS = [("jazz", "Ella Fine", "American jazz singer"), ("jazz", "Duke Lane", "American jazz pianist"),
          ("basketball", "Tall Team", "basketball club in Minnesota"), ("river", "Long River", "river in Minnesota"),
          ("film", "Quiet Film", "1950 film")]
CLAIMS = [{"id": f"hover-{n:02d}", "claim": f"Claim {n} is about {topic} and {title}.",
           "label": "SUPPORTED" if n % 2 == 0 else "NOT_SUPPORTED", "hops": 2 + n % 3,
           "articles": sorted([title, f"Other {n}"]), "about": [about, ""] if title < f"Other {n}" else ["", about]}
          for n, (topic, title, about) in enumerate(TOPICS * 4, start=1)]
SAVED_CLAIMS = 8          # the real save wants exactly 112; twenty claims are too few to test that
SMALLEST_LABEL = 2        # the real save wants at least 30 of each label
DEVELOPMENT_PER_LABEL = 2


def claims():
    """Every claim the finder can offer."""
    return CLAIMS


def claims_by_id():
    """Every claim, as {id: claim}."""
    return {c["id"]: c for c in CLAIMS}


RUN_FOLDERS = ("part1/before", "part1/after", "part2")    # what steps 1c, 1d and 1e write


def locked(folder=None):
    """Whether one of the folders the runs of steps 1c, 1d and 1e write holds anything."""
    return any((Path(folder) / "runs" / d).is_dir() and any((Path(folder) / "runs" / d).iterdir()) for d in RUN_FOLDERS)


def words(text):
    """The lower-case words of a text."""
    return re.findall(r"[a-z0-9]+", text.lower())


def text_of(c):
    return " ".join([c["claim"], *c["articles"], *c["about"]])


def keyword_ranking(query):
    """Claim numbers, best first: the claims with the most of the query's words."""
    q = set(words(query))
    hits = [(sum(w in q for w in words(text_of(c))), i) for i, c in enumerate(CLAIMS)]
    return [i for n, i in sorted(hits, key=lambda h: (-h[0], h[1])) if n]


def keyword_counts(query):
    """How many claims contain any of the query's words, and how many contain all of them."""
    q = set(words(query))
    return {"any": sum(bool(q & set(words(text_of(c)))) for c in CLAIMS),
            "all": sum(q <= set(words(text_of(c))) for c in CLAIMS) if q else 0}


def vector(text):
    """A made-up vector: how often each topic word appears."""
    return [words(text).count(t) for t in ("jazz", "basketball", "river", "film")]


def meaning_ranking(query):
    """Every claim number, best first: the claims whose made-up vector shares most with the query's."""
    q = vector(query)
    score = [sum(a * b for a, b in zip(q, vector(text_of(c)))) for c in CLAIMS]
    return sorted(range(len(CLAIMS)), key=lambda i: (-score[i], i))


def search(query, how="both"):
    """The matching claims, best first, with "keyword_rank" and "meaning_rank"."""
    by_keyword = {i: r for r, i in enumerate(keyword_ranking(query), start=1)}
    by_meaning = {i: r for r, i in enumerate(meaning_ranking(query), start=1)}
    if how == "keyword":
        order = list(by_keyword)
    elif how == "meaning":
        order = list(by_meaning)
    else:
        def fused(i):
            return sum(1 / (60 + r[i]) for r in (by_keyword, by_meaning) if i in r)
        order = sorted(set(by_keyword) | set(by_meaning), key=lambda i: (-fused(i), i))
    return [{**CLAIMS[i], "keyword_rank": by_keyword.get(i), "meaning_rank": by_meaning.get(i)} for i in order]


def split(claims):
    """(development, evaluation): in the order of the ids, the first two of each label, and the rest."""
    claims = sorted(claims, key=lambda c: c["id"])
    first = {c["id"] for lab in ("SUPPORTED", "NOT_SUPPORTED")
             for c in [c for c in claims if c["label"] == lab][:DEVELOPMENT_PER_LABEL]}
    return [c for c in claims if c["id"] in first], [c for c in claims if c["id"] not in first]


def save(claims, queries, folder=None):
    """Write data/dev.jsonl, data/eval.jsonl and data/my-topic.json under `folder`, or refuse with a
    sentence."""
    folder = Path(folder)
    if locked(folder):
        raise ValueError("You have already run the agent on your claims, so they can no longer be changed.")
    first = {}
    for c, q in zip(claims, queries, strict=True):
        first.setdefault(c["id"], (c, q))
    claims, queries = [c for c, _ in first.values()], [q for _, q in first.values()]
    if len(claims) != SAVED_CLAIMS:
        raise ValueError(f"You have selected {len(claims)} claims, and you need exactly {SAVED_CLAIMS}.")
    for lab in ("SUPPORTED", "NOT_SUPPORTED"):
        if sum(c["label"] == lab for c in claims) < SMALLEST_LABEL:
            raise ValueError(f"You need at least {SMALLEST_LABEL} claims labeled {lab}.")
    (folder / "data").mkdir(exist_ok=True)
    keep = ("id", "claim", "label", "hops", "articles")
    for name, part in zip(("dev.jsonl", "eval.jsonl"), split(claims)):
        lines = [json.dumps({**{k: c[k] for k in keep}, "source": "hover"}) + "\n" for c in part]
        (folder / "data" / name).write_text("".join(lines))
    topics = list(dict.fromkeys(queries))
    note = {"topics": [{"query": t, "claims": queries.count(t)} for t in topics],
            "development": 2 * DEVELOPMENT_PER_LABEL, "evaluation": len(claims) - 2 * DEVELOPMENT_PER_LABEL}
    (folder / "data" / "my-topic.json").write_text(json.dumps(note))
