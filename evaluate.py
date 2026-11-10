"""Run the baselines and the agent on a file of claims, and compare them.

    uv run python evaluate.py data/eval.jsonl --out runs/part2

Each line of the claims file is a JSON object with: id, claim, source ("hover"
for the dataset's claims, "mine" for claims you wrote), label and, for HoVer,
hops (how many Wikipedia articles the claim needs). For HoVer the label is the
dataset's own; for your own claims it is your verdict: "supported" if the
claim is true, "refuted" if it is false.

Every result is saved as it finishes, so if a run stops partway you can start
it again and it picks up where it left off. A claim that fails with an error,
such as Wikipedia refusing requests, is not saved, so the next run tries it
again. While it runs, it prints how far it has got. When every claim has a
result, it prints two tables and saves them as report.txt in the run's folder.
Running the same command again prints them again and costs nothing.

Saved results are never run again, even after you change the agent. To run a
folder's claims again with the agent as it is now, add --fresh:

    uv run python evaluate.py data/dev.jsonl --methods agent --out runs/part1/after --fresh
"""

import argparse
import hashlib
import json
import sys
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

# The files that decide how the agent behaves. A change to any of them makes a new
# version of the agent.
AGENT_FILES = ["instructions.md", "agent.py", "wiki.py"]
NOTES = []  # said again after the tables, where they will be seen


def agent_version():
    """A short fingerprint of the agent's files. It is saved with each of the
    agent's results, so a later run can tell whether the results in a folder
    were made by the agent as it is now."""
    digest = hashlib.sha256()
    for name in AGENT_FILES:
        digest.update((Path(__file__).parent / name).read_bytes())
    return digest.hexdigest()[:12]


def saved(path):
    """The results already saved in a file, by claim id."""
    if not path.exists():
        return {}
    return {row["id"]: row for row in map(json.loads, path.read_text().splitlines())}


def check_saved_agent(out_dir, items):
    """Results saved by an earlier version of the agent are easy to mistake for
    new ones. Say so, and refuse to mix old and new results in one folder."""
    done = saved(out_dir / "agent.jsonl")
    old = [row for row in done.values() if row.get("agent_version") not in (None, agent_version())]
    if not old:
        return
    todo = [item for item in items if item["id"] not in done]
    why = "instructions.md, agent.py or wiki.py has changed since"
    if todo:
        sys.exit(f"Stopped: {out_dir} has {len(old)} saved results from an earlier version of "
                 f"your agent ({why}), and {len(todo)} still to run. Mixing the two would "
                 "give results you could not interpret. To start this run over with the agent "
                 "as it is now, add --fresh to the command.")
    NOTES.append(f"Note: the agent's saved results in {out_dir} were made by an earlier version "
                 f"of your agent ({why}), and nothing was run again. That is fine if you meant "
                 "to keep them. To replace them with a new run, add --fresh to the command.")

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
    if method == "agent":
        result["agent_version"] = agent_version()
    return result


def run_method(method, items, out_dir, workers):
    path = out_dir / f"{method}.jsonl"
    done = saved(path)
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
    if any(item["source"] == "hover" for item in items):
        say("")  # the same count, split by the dataset's label
        for label, name in (("SUPPORTED", "HoVer, supported"), ("NOT_SUPPORTED", "HoVer, not supported")):
            row = f"{name:22}"
            for method in methods:
                rows = [r for item, r in zip(items, results_by_method[method])
                        if item["source"] == "hover" and item["label"] == label]
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
    parser.add_argument("--fresh", action="store_true",
                        help="forget this folder's saved results for these methods and run them again")
    args = parser.parse_args()

    items = [json.loads(line) for line in Path(args.claims).read_text().splitlines() if line.strip()]
    items = items[: args.limit] if args.limit else items
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    methods = args.methods.split(",")
    NOTES.clear()
    if args.fresh:
        for method in methods:
            (out_dir / f"{method}.jsonl").unlink(missing_ok=True)
        (out_dir / "report.txt").unlink(missing_ok=True)
    if "agent" in methods:
        check_saved_agent(out_dir, items)
    # Which claims file this run used, so the results viewer can find the claims.
    (out_dir / "run.json").write_text(json.dumps({"claims": args.claims}) + "\n")
    results = {m: run_method(m, items, out_dir, args.workers) for m in methods}
    report(items, results, out_dir)
    for note in NOTES:
        print("\n" + note, flush=True)


if __name__ == "__main__":
    main()
