"""Check one claim and print the result.

    uv run python check.py --method agent "The director of ... was born in Illinois."

Methods: no-tools, one-search, agent. The result is also saved as JSON in runs/.
"""

import argparse
import json
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

import agent  # noqa: E402  (after load_dotenv, so the API key is set)
import baselines  # noqa: E402

METHODS = {"no-tools": baselines.no_tools, "one-search": baselines.one_search,
           "agent": agent.run_agent}


def short(text, n=160):
    text = " ".join(str(text).split())
    return text if len(text) <= n else text[: n - 3] + "..."


def show(result):
    for i, step in enumerate(result["trace"], 1):
        args = ", ".join(f"{k}={v!r}" for k, v in step["input"].items() if k != "evidence")
        print(f"  {i:>2}. {step['tool']}({short(args, 100)})")
        print(f"      -> {short(step['result'])}")
    print(f"\nVerdict: {result['verdict']}")
    for quote in result["evidence"]:
        print(f'  evidence: "{short(quote, 200)}"')
    print(f"Explanation: {result['explanation']}")
    print(f"Lookups: {result['steps']}   tokens: {result['tokens']['input']} in, "
          f"{result['tokens']['output']} out   cost: ${result['cost_usd']:.4f}   "
          f"time: {result['seconds']:.1f}s")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("claim")
    parser.add_argument("--method", choices=METHODS, default="agent")
    parser.add_argument("--out", default="runs/checks")
    args = parser.parse_args()

    start = time.time()
    result = METHODS[args.method](args.claim)
    result["seconds"] = time.time() - start
    result["method"] = args.method
    print(f"Claim: {args.claim}\nMethod: {args.method}\n")
    show(result)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{args.method}-{int(start)}.json"
    path.write_text(json.dumps(result, indent=1))
    print(f"\nSaved to {path}")


if __name__ == "__main__":
    main()
