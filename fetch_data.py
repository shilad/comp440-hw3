"""Build data/dev.jsonl and data/eval.jsonl from HoVer.

    python fetch_data.py

The instructor runs this once; students get the files it writes. It draws a
fixed, seeded sample, so running it again gives the same claims. Every student
uses these claims: 12 in data/dev.jsonl and 100 in data/eval.jsonl.

HoVer's labelled dev set (4,000 claims) comes from the HoVer GitHub repository.
Its test set's labels are withheld, so the dev set is the one we can score
against. The sample is the one the instructor's baselines use: for each of 2,
3 and 4 articles, 50 supported and 50 not supported claims, drawn with
random.Random(440) after sorting by uid, 300 claims in all. Two thirds of it,
200 claims, are shuffled; the eval set is the first 100 of them that fill
EVAL_CELLS: 34, 33 and 33 claims that need 2, 3 and 4 articles, and 50 of
each label. The dev set is 12 claims from the other third, 2 for each number
of articles and label, so the two never share a claim.

Until Nov 11, 2026 the eval set was all 200, and a step of the homework had
each student replace both files with claims they selected in the claim finder
(finder/). The step is gone, and EVAL_CELLS cut the 200 to the 100 that ship.
"""

import json
import random
import urllib.request
from pathlib import Path

HOVER_URL = ("https://raw.githubusercontent.com/hover-nlp/hover/main/"
             "data/hover/hover_dev_release_v1.1.json")

DATA = Path(__file__).parent / "data"
SEED = 440
PER_CELL = 50        # sampled claims per (hops, label): 3 hop counts x 2 labels x 50 = 300
DEV_PER_CELL = 2     # dev claims per (hops, label), from the third not in eval: 12
# Eval claims per (hops, label), the first of each in the shuffled order: 34 / 33 / 33 by hops,
# 50 / 50 by label, 100 in all.
EVAL_CELLS = {(2, "SUPPORTED"): 17, (2, "NOT_SUPPORTED"): 17,
              (3, "SUPPORTED"): 17, (3, "NOT_SUPPORTED"): 16,
              (4, "SUPPORTED"): 16, (4, "NOT_SUPPORTED"): 17}


def first_of_each(rows, cells):
    """The first claims of each (hops, label) in rows, as many as cells gives, in the order of rows."""
    left, out = dict(cells), []
    for row in rows:
        key = (row["hops"], row["label"])
        if left.get(key, 0) > 0:
            out.append(row)
            left[key] -= 1
    return out


def download(url):
    request = urllib.request.Request(url, headers={"User-Agent": "COMP440-HW3/0.1"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read().decode()


def hover_sample():
    """The 300-claim sample, in the order it was drawn."""
    rows = json.loads(download(HOVER_URL))
    rng = random.Random(SEED)
    sample = []
    for hops in (2, 3, 4):
        for label in ("SUPPORTED", "NOT_SUPPORTED"):
            pool = sorted((r for r in rows if r["num_hops"] == hops and r["label"] == label),
                          key=lambda r: r["uid"])
            sample += rng.sample(pool, PER_CELL)
    return [{"id": f"hover-{r['uid']}", "claim": r["claim"], "source": "hover",
             "label": r["label"], "hops": r["num_hops"],
             "articles": sorted({title for title, _ in r["supporting_facts"]})}
            for r in sample]


def main():
    sample = hover_sample()
    eval_set = [x for i, x in enumerate(sample) if i % 3 != 2]
    rest = [x for i, x in enumerate(sample) if i % 3 == 2]
    dev_set = []
    for hops in (2, 3, 4):
        for label in ("SUPPORTED", "NOT_SUPPORTED"):
            dev_set += [x for x in rest if x["hops"] == hops and x["label"] == label][:DEV_PER_CELL]

    rng = random.Random(SEED)
    rng.shuffle(eval_set)
    rng.shuffle(dev_set)
    eval_set = first_of_each(eval_set, EVAL_CELLS)
    DATA.mkdir(exist_ok=True)
    for name, rows in (("eval", eval_set), ("dev", dev_set)):
        path = DATA / f"{name}.jsonl"
        path.write_text("".join(json.dumps(r) + "\n" for r in rows))
        print(f"Wrote {len(rows)} claims to {path}")


if __name__ == "__main__":
    main()
