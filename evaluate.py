"""Run the baselines and the agent on a file of claims, and compare them.

    uv run python evaluate.py data/eval.jsonl --out runs/part2

Each line of the claims file is a JSON object with: id, claim, source
("hover", "fever", or "mine" for claims you wrote), label and, for HoVer, hops
(how many Wikipedia articles the claim needs). For HoVer and FEVER the label is
the dataset's own; for your own claims it is your verdict, written as one of
"supported", "refuted" or "doesn't say".

Every result is saved as it finishes, so if a run stops partway you can start
it again and it picks up where it left off.
"""

import argparse
import json
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

import agent  # noqa: E402
import baselines  # noqa: E402

METHODS = {"no-tools": baselines.no_tools, "one-search": baselines.one_search,
           "agent": agent.run_agent}

# The dataset labels, as the three verdicts the agent can give.
FEVER = {"SUPPORTS": "supported", "REFUTES": "refuted", "NOT ENOUGH INFO": "doesn't say"}


def is_correct(item, verdict):
    """HoVer only says SUPPORTED or NOT_SUPPORTED, so for HoVer "refuted" and
    "doesn't say" both count as not supported. FEVER keeps all three, and so
    do your own claims, which carry your verdict as their label."""
    if item["source"] == "hover":
        return (verdict == "supported") == (item["label"] == "SUPPORTED")
    if item["source"] == "fever":
        return verdict == FEVER[item["label"]]
    return verdict == item["label"]


def run_one(method, item):
    start = time.time()
    try:
        result = METHODS[method](item["claim"])
    except Exception as error:  # a failed claim shouldn't stop the whole run
        result = {"verdict": None, "evidence": [], "explanation": f"error: {error}",
                  "trace": [], "steps": 0, "tokens": {"input": 0, "output": 0}, "cost_usd": 0}
    result.update(id=item["id"], method=method, seconds=round(time.time() - start, 2),
                  correct=is_correct(item, result["verdict"]))
    return result


def run_method(method, items, out_dir, workers):
    path = out_dir / f"{method}.jsonl"
    done = {}
    if path.exists():
        for line in path.read_text().splitlines():
            row = json.loads(line)
            done[row["id"]] = row
    todo = [item for item in items if item["id"] not in done]
    print(f"{method}: {len(done)} already done, running {len(todo)}")
    with path.open("a") as f, ThreadPoolExecutor(workers) as pool:
        for result in pool.map(lambda item: run_one(method, item), todo):
            f.write(json.dumps(result) + "\n")
            f.flush()
            done[result["id"]] = result
    return [done[item["id"]] for item in items]


def group_of(item):
    if item["source"] == "hover":
        return f"HoVer, {item['hops']} articles"
    if item["source"] == "fever":
        return "FEVER"
    return "Your claims"


def report(items, results_by_method):
    groups = sorted({group_of(item) for item in items})
    methods = list(results_by_method)
    print("\nShare of claims where the verdict matched the label (the dataset's, or yours):\n")
    print(f"{'':22}" + "".join(f"{m:>12}" for m in methods))
    for group in groups + ["All"]:
        row = f"{group:22}"
        for method in methods:
            rows = [r for item, r in zip(items, results_by_method[method])
                    if group == "All" or group_of(item) == group]
            row += f"{sum(r['correct'] for r in rows):>6}/{len(rows):<5}"
        print(row)

    print("\nAverage per claim:\n")
    print(f"{'':22}{'lookups':>10}{'tokens':>10}{'seconds':>10}{'cost':>10}")
    for method in methods:
        rows = results_by_method[method]
        n = len(rows) or 1
        tokens = sum(r["tokens"]["input"] + r["tokens"]["output"] for r in rows) / n
        print(f"{method:22}{sum(r['steps'] for r in rows) / n:>10.1f}{tokens:>10.0f}"
              f"{sum(r['seconds'] for r in rows) / n:>10.1f}"
              f"{sum(r['cost_usd'] for r in rows) / n:>10.4f}")
    errors = sum(r["verdict"] is None for rows in results_by_method.values() for r in rows)
    if errors:
        print(f"\n{errors} runs gave no verdict (an error, a refusal, out of steps or its "
              "answer rejected three times). "
              "They count as wrong. Look for them in the saved files.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("claims")
    parser.add_argument("--out", default="runs/eval")
    parser.add_argument("--methods", default="no-tools,one-search,agent")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()

    items = [json.loads(line) for line in Path(args.claims).read_text().splitlines() if line.strip()]
    items = items[: args.limit] if args.limit else items
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    results = {m: run_method(m, items, out_dir, args.workers) for m in args.methods.split(",")}
    report(items, results)


if __name__ == "__main__":
    main()
