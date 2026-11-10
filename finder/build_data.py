"""Build the claim finder's three data files in finder/data/. Run once by the instructor, never by a student.

It needs numpy and model2vec, which the homework does not install, so it runs in a separate
virtual environment, from the homework folder:

    uv venv /tmp/finder-build
    uv pip install --python /tmp/finder-build/bin/python model2vec numpy
    /tmp/finder-build/bin/python finder/build_data.py /path/to/hover-data

The folder holds hover_train.json and hover_dev.json (from github.com/hover-nlp/hover, CC BY-SA 4.0)
and descriptions.json ({article title: Wikipedia's one-line description}). The word vectors come
from model2vec's minishlab/potion-base-8M (MIT licence). Nothing imports this file.

It leaves out the homework's own claims (data/eval.jsonl, data/dev.jsonl) and repeated claims:
HoVer has some claim texts more than once. Comparing texts in lower case with runs of spaces made
one, it keeps one copy where the copies have the same label, and none where their labels differ,
since then neither label can be trusted. It also leaves out a claim whose text is one the homework
already uses. Then it keeps at most one supported and one not-supported claim from each of
HoVer's source questions, because HoVer turned one question into up to 12 nearly identical claims,
and a student's claims would otherwise repeat the same sentence over and over. Whether
descriptions are searched is set by SEARCH_DESCRIPTIONS in finder/search.py.
"""
import gzip
import json
import sys
from pathlib import Path

import numpy as np
from model2vec import StaticModel

HOMEWORK = Path(__file__).parent.parent
sys.path.insert(0, str(HOMEWORK))
from finder import search  # noqa: E402  (search.vector() must be the same at build and search time)

MODEL = "minishlab/potion-base-8M"
LENGTH = 128  # numbers per word: the first 128 of the model's 256, which vary the most (64 lost too much)


def write(name, data):
    """Write data as compact JSON to finder/data/<name>, gzipped the same way every time."""
    with gzip.GzipFile(search.DATA / name, "wb", mtime=0) as file:
        file.write(json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))


def homework_claims():
    """The claims the homework already uses, in data/eval.jsonl and data/dev.jsonl."""
    lines = []
    for name in ("eval.jsonl", "dev.jsonl"):
        lines += (HOMEWORK / "data" / name).read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def same_text(text):
    """A claim's text in lower case with runs of spaces made one, for finding repeated claims."""
    return " ".join(text.lower().split())


def without_repeats(claims):
    """The claims less repeats: one copy of a text whose copies agree on the label (the first id),
    no copy of a text whose copies disagree, and no claim with the text of one the homework uses."""
    used = {same_text(claim["claim"]) for claim in homework_claims()}
    copies = {}
    for claim in claims:
        copies.setdefault(same_text(claim["claim"]), []).append(claim)
    keep = {min(c["id"] for c in group) for text, group in copies.items()
            if text not in used and len({c["label"] for c in group}) == 1}
    return [claim for claim in claims if claim["id"] in keep]


def one_per_question(claims):
    """At most one supported and one not-supported claim from each HoVer source question (the first id)."""
    first = {}
    for claim in sorted(claims, key=lambda claim: claim["id"]):
        first.setdefault((claim["question"], claim["label"]), claim["id"])
    keep = set(first.values())
    return [claim for claim in claims if claim["id"] in keep]


def build_claims(source):
    """Every HoVer claim from train and dev but the homework's own, with the articles' descriptions."""
    descriptions = json.loads((source / "descriptions.json").read_text(encoding="utf-8"))
    rows = json.loads((source / "hover_train.json").read_text(encoding="utf-8"))
    rows += json.loads((source / "hover_dev.json").read_text(encoding="utf-8"))
    used_ids = {claim["id"] for claim in homework_claims()}
    claims = []
    for row in rows:
        if f"hover-{row['uid']}" in used_ids:
            continue
        articles = sorted({title for title, _ in row["supporting_facts"]})
        claims.append({"id": f"hover-{row['uid']}", "claim": row["claim"], "label": row["label"],
                       "hops": row["num_hops"], "articles": articles,
                       "about": [descriptions.get(title, "") for title in articles],
                       "question": row["hpqa_id"]})
    claims = one_per_question(without_repeats(claims))
    for claim in claims:
        del claim["question"]  # needed only to build; the finder does not use it
    return claims


def build_word_vectors(claims):
    """{word: LENGTH whole numbers from -127 to 127} for every word in the claims and the model's own whole words."""
    model = StaticModel.from_pretrained(MODEL, normalize=False)
    vocabulary = {word for claim in claims for word in search.words(search.searched_text(claim))}
    vocabulary |= {token for token in model.tokenizer.get_vocab() if token.isalpha()}
    vocabulary -= search.COMMON_WORDS
    vocabulary = sorted(vocabulary)
    vectors = model.encode(vocabulary, use_multiprocessing=False)[:, :LENGTH]
    scale = 127 / np.percentile(np.abs(vectors), 99.9)  # one scale for all words keeps their lengths comparable
    numbers = np.clip(np.rint(vectors * scale), -127, 127).astype(int)
    return {word: row.tolist() for word, row in zip(vocabulary, numbers)}


def scaled(v):
    """A vector's numbers scaled to whole numbers from -127 to 127 (a claim's length does not matter)."""
    largest = max(abs(x) for x in v) if v else 0
    return [round(x * 127 / largest) for x in v] if largest else [0] * LENGTH


def main():
    """Build the three files from the folder of HoVer files named on the command line."""
    source = Path(sys.argv[1])
    search.DATA.mkdir(exist_ok=True)
    claims = build_claims(source)
    write("claims.json.gz", claims)
    write("word_vectors.json.gz", build_word_vectors(claims))
    search.word_vectors.cache_clear()
    write("claim_vectors.json.gz", [scaled(search.vector(search.searched_text(c))) for c in claims])
    described = sum(1 for c in claims for about in c["about"] if about)
    articles = sum(len(c["articles"]) for c in claims)
    print(f"{len(claims)} claims; {described} of {articles} article mentions have a description.")
    for name in ("claims.json.gz", "word_vectors.json.gz", "claim_vectors.json.gz"):
        print(f"{name}: {(search.DATA / name).stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
