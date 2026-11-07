"""Run one of the agent's lookup tools by hand, for Part 1 Step 2 ("Be the agent").

    uv run python lookup.py search "1994 Best Picture"
    uv run python lookup.py read "Forrest Gump"
    uv run python lookup.py read "Robert Zemeckis" "Early life"
    uv run python lookup.py wikidata "Robert Zemeckis" "place of birth"

It prints exactly what the agent would see, and adds the call to
runs/part1/lookups.jsonl, so your calls are counted the same way the agent's
are.
"""

import argparse
import json
from pathlib import Path

import wiki

LOG = Path(__file__).parent / "runs" / "part1" / "lookups.jsonl"


def main():
    parser = argparse.ArgumentParser(description="Run one lookup tool by hand.")
    tools = parser.add_subparsers(dest="tool", required=True)
    tools.add_parser("search").add_argument("query")
    read = tools.add_parser("read")
    read.add_argument("title")
    read.add_argument("section", nargs="?")
    data = tools.add_parser("wikidata")
    data.add_argument("entity")
    data.add_argument("property")
    args = parser.parse_args()

    if args.tool == "search":
        call, result = {"query": args.query}, wiki.search(args.query)
    elif args.tool == "read":
        call, result = {"title": args.title, "section": args.section}, wiki.read(args.title, args.section)
    else:
        call, result = ({"entity": args.entity, "property": args.property},
                        wiki.wikidata(args.entity, args.property))
    print(result)

    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as f:
        f.write(json.dumps({"tool": args.tool, "input": call}) + "\n")
    count = len(LOG.read_text().splitlines())
    print(f"\n(Call {count} in runs/part1/lookups.jsonl.)")


if __name__ == "__main__":
    main()
