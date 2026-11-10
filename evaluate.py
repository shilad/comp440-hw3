"""Run the baselines and the agent on a file of claims, and compare them.

    uv run python evaluate.py data/eval.jsonl --out runs/part2

Each line of the claims file is a JSON object with: id, claim, source ("hover"
for the dataset's claims, "mine" for claims you wrote), label and, for HoVer,
hops (how many Wikipedia articles the claim needs). For HoVer the label is the
dataset's own; for your own claims it is your verdict, written as one of
"supported", "refuted" or "doesn't say".

Every result is saved as it finishes, so if a run stops partway you can start
it again and it picks up where it left off. A claim that fails with an error,
such as Wikipedia refusing requests, is not saved, so the next run tries it
again. While it runs, it prints how far it has got. When every claim has a
result, it prints two tables and saves them as report.txt in the run's folder.
Running the same command again prints them again and costs nothing.
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
    do your own claims, which carry your verdict as their label. A run that
    gave no verdict is wrong, whatever the label."""
    if verdict is None:  # otherwise None would count as "not supported" on HoVer
        return False
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
        print(f"{method}: {item['id']} failed and was not saved: {error}")
        result = {"verdict": None, "evidence": [], "explanation": f"error: {error}",
                  "error": True,
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
    print(f"{method}: {len(done)} already done, running {len(todo)}", flush=True)
    start = time.time()
    with path.open("a") as f, ThreadPoolExecutor(workers) as pool:
        for n, result in enumerate(pool.map(lambda item: run_one(method, item), todo), 1):
            done[result["id"]] = result
            if n % 10 == 0 or n == len(todo):  # so a long run shows that it is still going
                print(f"{method}: {n} of {len(todo)} done, "
                      f"{(time.time() - start) / 60:.0f} min so far", flush=True)
            if "error" in result:
                continue  # not saved, so the next run tries this claim again
            f.write(json.dumps(result) + "\n")
            f.flush()
    return [done[item["id"]] for item in items]


def group_of(item):
    if item["source"] == "hover":
        return f"HoVer, {item['hops']} articles"
    if item["source"] == "fever":
        return "FEVER"
    return "Your claims"


def report(items, results_by_method, out_dir=None):
    """Print the two tables. With out_dir, also save them there as report.txt
    once every claim has a saved result: that file marks a finished run."""
    lines = []
    say = lines.append
    groups = sorted({group_of(item) for item in items})
    methods = list(results_by_method)
    say("\nShare of claims where the verdict matched the label (the dataset's, or yours):\n")
    say(f"{'':22}" + "".join(f"{m:>12}" for m in methods))
    for group in groups + ["All"]:
        row = f"{group:22}"
        for method in methods:
            rows = [r for item, r in zip(items, results_by_method[method])
                    if group == "All" or group_of(item) == group]
            row += f"{sum(r['correct'] for r in rows):>6}/{len(rows):<5}"
        say(row)

    say("\nAverage per claim:\n")
    say(f"{'':22}{'lookups':>10}{'tokens':>10}{'seconds':>10}{'cost':>10}")
    for method in methods:
        rows = results_by_method[method]
        n = len(rows) or 1
        tokens = sum(r["tokens"]["input"] + r["tokens"]["output"] for r in rows) / n
        say(f"{method:22}{sum(r['steps'] for r in rows) / n:>10.1f}{tokens:>10.0f}"
            f"{sum(r['seconds'] for r in rows) / n:>10.1f}"
            f"{sum(r['cost_usd'] for r in rows) / n:>10.4f}")
    every_run = [r for rows in results_by_method.values() for r in rows]
    failed = sum("error" in r for r in every_run)
    no_verdict = sum(r["verdict"] is None for r in every_run) - failed
    if no_verdict:
        say(f"\n{no_verdict} runs gave no verdict (for example a refusal, out of steps or "
            "its answer rejected three times). "
            "They count as wrong. Look for them in the saved files.")
    if failed:
        say(f"\n{failed} runs stopped with an error, such as Wikipedia refusing requests. "
            "They count as wrong above, but they were not saved: run the same command "
            "again to retry them.")
    text = "\n".join(lines)
    print(text, flush=True)
    if out_dir is not None:
        saved = Path(out_dir) / "report.txt"
        if failed:
            saved.unlink(missing_ok=True)  # not finished: some claims have no saved result
        else:
            saved.write_text(text.lstrip("\n") + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("claims")
    parser.add_argument("--out", default="runs/eval")
    parser.add_argument("--methods", default="no-tools,one-search,agent")
    parser.add_argument("--limit", type=int, default=None)
    # How many claims are checked at the same time. Wikipedia asks programs to
    # send at most 3 requests at once, and each claim makes its requests one
    # after another, so 3 claims at a time keeps to that.
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()

    items = [json.loads(line) for line in Path(args.claims).read_text().splitlines() if line.strip()]
    items = items[: args.limit] if args.limit else items
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    # Which claims file this run used, so the results viewer can find the claims.
    (out_dir / "run.json").write_text(json.dumps({"claims": args.claims}) + "\n")
    results = {m: run_method(m, items, out_dir, args.workers) for m in args.methods.split(",")}
    report(items, results, out_dir)


if __name__ == "__main__":
    main()
