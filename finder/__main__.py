"""Try the claim finder in a terminal.

    uv run python -m finder "film"                       # the best ten by keyword, by meaning and by both
    uv run python -m finder --save "film" "basketball"   # saves the best 112, an even share from each topic

The usual way is the screen ("Find claims" on the homework page), where the student selects the
claims. --save is for a student whose browser will not run the screen.
"""
import argparse
import sys

from finder.search import SAVED_CLAIMS, keyword_counts, pick, save, search


def show(results, heading):
    """Print a heading and the best ten results under it."""
    print(f"\n{heading}")
    for number, result in enumerate(results[:10], start=1):
        label = "supported    " if result["label"] == "SUPPORTED" else "not supported"
        print(f"{number:3}. {label} {result['hops']} articles  {result['claim'][:100]}")


def best_for_topics(topics, how):
    """The best 112 claims over the topics, an even share from each (a claim found twice counts for
    the first topic), and the topic that found each claim. Refuses a topic that finds too few."""
    chosen, queries = [], []
    for number, topic in enumerate(topics):
        share = SAVED_CLAIMS // len(topics) + (1 if number < SAVED_CLAIMS % len(topics) else 0)
        picked = pick(search(topic, how), size=share, removed={claim["id"] for claim in chosen})
        if len(picked) < share:
            found = "1 claim" if len(picked) == 1 else f"{len(picked)} claims"
            raise ValueError(f'The topic "{topic}" found only {found}, and its share of the 112 is '
                             f"{share}. Try other words for it, or leave it out.")
        chosen += picked
        queries += [topic] * len(picked)
    return chosen, queries


def main():
    """Print what each way of searching finds for each topic, or save the best 112 if asked."""
    parser = argparse.ArgumentParser(description="Find HoVer claims about one or more topics.")
    parser.add_argument("topics", nargs="+", help="each topic in a few words, in quotes")
    parser.add_argument("--save", action="store_true",
                        help="save the best 112 over data/dev.jsonl (12) and data/eval.jsonl (100)")
    parser.add_argument("--how", choices=["keyword", "meaning", "both"], default="both",
                        help="which way of searching to save from")
    args = parser.parse_args()

    if not args.save:
        for topic in args.topics:
            counts = keyword_counts(topic)
            print(f"\n{topic}: {counts['any']} claims contain at least one of your words, "
                  f"and {counts['all']} contain all of them.")
            for how in ("keyword", "meaning", "both"):
                show(search(topic, how), f"Best ten by {how}:")
        return
    try:
        chosen, queries = best_for_topics(args.topics, args.how)
        paths = save(chosen, queries)
    except ValueError as problem:
        sys.exit(str(problem))
    supported = sum(1 for claim in chosen if claim["label"] == "SUPPORTED")
    print(f"Saved 12 development claims in {paths[0]} and 100 evaluation claims in {paths[1]} "
          f"({supported} supported and {len(chosen) - supported} not supported).")


if __name__ == "__main__":
    main()
