"""Check that this copy of the homework is ready to run: the .env file, your API
key and Wikipedia.

    uv run python check_setup.py

It prints one line for each thing it checks. It never prints your key or your
email: only whether each line of .env is filled in. Checking the key sends one
very short request to the Claude API, which costs a small fraction of a cent.
"""

import sys
from pathlib import Path

from dotenv import dotenv_values, load_dotenv

ENV = Path(__file__).parent / ".env"


def filled_in():
    """Which of the two lines of .env have something after the = sign."""
    values = dotenv_values(ENV)
    return {name: bool((values.get(name) or "").strip())
            for name in ("ANTHROPIC_API_KEY", "WIKIPEDIA_CONTACT")}


def wikipedia_problem():
    """None if a Wikipedia search works, or a sentence saying what went wrong."""
    import wiki
    try:
        wiki.search("Macalester College")
    except Exception as error:  # any failure is reported the same way
        return f"{type(error).__name__}: {error}"
    return None


def key_problem():
    """None if the Claude API accepts the key, or a sentence saying what went wrong."""
    import anthropic
    from agent import MODEL
    try:
        anthropic.Anthropic().messages.create(
            model=MODEL, max_tokens=4000, messages=[{"role": "user", "content": "Reply with OK."}])
    except anthropic.AuthenticationError:
        return ("the Claude API did not accept the key. Check that you pasted the whole key "
                "after ANTHROPIC_API_KEY= in .env, with no spaces or quote marks.")
    except Exception as error:
        return f"{type(error).__name__}: {error}"
    return None


def main():
    if not ENV.exists():
        print("NOT READY  There is no .env file. In your editor, copy .env.example to .env "
              "and fill in both lines.")
        return 1
    print("ok         .env file found")
    ready = True
    lines = filled_in()
    if lines["ANTHROPIC_API_KEY"]:
        print("ok         ANTHROPIC_API_KEY is filled in")
    else:
        ready = False
        print("NOT READY  ANTHROPIC_API_KEY is empty. In your editor, paste the key I sent you "
              "after ANTHROPIC_API_KEY= in .env.")
    if lines["WIKIPEDIA_CONTACT"]:
        print("ok         WIKIPEDIA_CONTACT is filled in")
    else:
        ready = False
        print("NOT READY  WIKIPEDIA_CONTACT is empty. In your editor, put your Macalester email "
              "after WIKIPEDIA_CONTACT= in .env.")

    load_dotenv(ENV)  # so the two checks below use your key and your contact
    problem = wikipedia_problem()
    if problem is None:
        print("ok         Wikipedia answered a search")
    else:
        ready = False
        print(f"NOT READY  Wikipedia did not answer a search ({problem})")

    if lines["ANTHROPIC_API_KEY"]:
        problem = key_problem()
        if problem is None:
            print("ok         the Claude API accepted your key")
        else:
            ready = False
            print(f"NOT READY  {problem}")

    print("\nEverything is ready." if ready
          else "\nNot ready yet. Fix each line marked NOT READY, then run this again.")
    return 0 if ready else 1


if __name__ == "__main__":
    sys.exit(main())
