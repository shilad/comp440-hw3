"""Build data/dev.jsonl and data/eval.jsonl from HoVer and FEVER.

    python fetch_data.py

The instructor runs this once; students get the files it writes. It draws a
fixed, seeded sample, so running it again gives the same claims.

- HoVer's labelled dev set (4,000 claims) comes from the HoVer GitHub
  repository. Its test set's labels are withheld, so the dev set is the one we
  can score against.
- FEVER's "paper_dev" set comes from fever.ai. If that download fails, the
  files are written with HoVer claims only and a warning is printed.
"""

import json
import random
import urllib.request
from pathlib import Path

HOVER_URL = ("https://raw.githubusercontent.com/hover-nlp/hover/main/"
             "data/hover/hover_dev_release_v1.1.json")
FEVER_URL = "https://fever.ai/download/fever/paper_dev.jsonl"

DATA = Path(__file__).parent / "data"
SEED = 440
EVAL_PER_CELL = 10   # HoVer claims per (hops, label): 3 hop counts x 2 labels x 10 = 60
DEV_PER_CELL = 2     # 3 x 2 x 2 = 12
FEVER_EVAL = {"SUPPORTS": 7, "REFUTES": 7, "NOT ENOUGH INFO": 6}
FEVER_DEV = {"SUPPORTS": 1, "REFUTES": 1, "NOT ENOUGH INFO": 1}


def download(url):
    request = urllib.request.Request(url, headers={"User-Agent": "COMP440-HW3/0.1"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read().decode()


def hover_claims():
    rows = json.loads(download(HOVER_URL))
    return [{"id": f"hover-{r['uid']}", "claim": r["claim"], "source": "hover",
             "label": r["label"], "hops": r["num_hops"],
             "articles": sorted({title for title, _ in r["supporting_facts"]})}
            for r in rows]


def fever_claims():
    rows = [json.loads(line) for line in download(FEVER_URL).splitlines() if line.strip()]
    return [{"id": f"fever-{r['id']}", "claim": r["claim"], "source": "fever",
             "label": r["label"]} for r in rows]


def sample(items, key, counts, rng, taken):
    picked = []
    for cell, n in counts.items():
        pool = [x for x in items if key(x) == cell and x["id"] not in taken]
        chosen = rng.sample(pool, n)
        taken.update(x["id"] for x in chosen)
        picked += chosen
    return picked


def main():
    rng = random.Random(SEED)
    taken = set()
    hover = hover_claims()
    cells = [(hops, label) for hops in (2, 3, 4) for label in ("SUPPORTED", "NOT_SUPPORTED")]
    key = lambda x: (x["hops"], x["label"])  # noqa: E731
    eval_set = sample(hover, key, {c: EVAL_PER_CELL for c in cells}, rng, taken)
    dev_set = sample(hover, key, {c: DEV_PER_CELL for c in cells}, rng, taken)

    try:
        fever = fever_claims()
        eval_set += sample(fever, lambda x: x["label"], FEVER_EVAL, rng, taken)
        dev_set += sample(fever, lambda x: x["label"], FEVER_DEV, rng, taken)
    except OSError as error:
        print(f"Warning: could not download FEVER ({error}). Writing HoVer claims only.")

    rng.shuffle(eval_set)
    rng.shuffle(dev_set)
    DATA.mkdir(exist_ok=True)
    for name, rows in (("eval", eval_set), ("dev", dev_set)):
        path = DATA / f"{name}.jsonl"
        path.write_text("".join(json.dumps(r) + "\n" for r in rows))
        print(f"Wrote {len(rows)} claims to {path}")


if __name__ == "__main__":
    main()
