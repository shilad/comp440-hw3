"""Run one of the agent's lookup tools by hand, for step 1b ("Be the agent").

    uv run python lookup.py search "<words to search for>"
    uv run python lookup.py read "<page title>"
    uv run python lookup.py read "<page title>" "<section>"
    uv run python lookup.py wikidata "<entity, such as a person's name>" "<property, such as place of birth>"

It prints exactly what the agent would see, and adds the call to
runs/part1/lookups.jsonl, so your calls are counted the same way the agent's
are. That file is your record for step 1b. To look something up in a later
step without adding to it, put --no-log before the tool's name:

    uv run python lookup.py --no-log read "<page title>"
"""

import argparse
import json
from pathlib import Path

from dotenv import load_dotenv

import wiki

LOG = Path(__file__).parent / "runs" / "part1" / "lookups.jsonl"


def main():
    load_dotenv()  # for WIKIPEDIA_CONTACT, so Wikipedia counts these lookups as yours
    parser = argparse.ArgumentParser(description="Run one lookup tool by hand.")
    parser.add_argument("--no-log", action="store_true",
                        help="don't add this call to runs/part1/lookups.jsonl, the record for step 1b")
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
    if args.no_log:
        return

    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as f:
        f.write(json.dumps({"tool": args.tool, "input": call}) + "\n")
    count = len(LOG.read_text().splitlines())
    print(f"\n(Call {count} in runs/part1/lookups.jsonl.)")


if __name__ == "__main__":
    main()
