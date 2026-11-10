"""Tell the workbench page what this step's Claude Code session is doing.

    python3 .workbench/page.py STEP status "Walking through run_agent()"
    python3 .workbench/page.py STEP expected "supported"   what the student expects the run to show
    python3 .workbench/page.py STEP done N      tick checkpoint N of the step
    python3 .workbench/page.py STEP done        the whole step, for one with nothing to write

The `page` skill tells Claude when to use it. It posts to the workbench server running on this
laptop, whose port the server leaves in server.json beside this file. Standard library only,
because it runs under the student's own `python3`; the server copies it into .workbench/.
"""

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROUTES = {"status": "status", "expected": "expected", "done": "mark"}


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] not in ROUTES:
        print(__doc__.strip().split("\n\n")[0])
        return 2
    step, verb, rest = argv[0], argv[1], argv[2:]
    if verb in ("status", "expected"):
        if not rest:
            print(f'Give it as one quoted argument: {verb} "' + ("Running the agent on your claim" if verb == "status" else "supported") + '"')
            return 2
        body = {"text": " ".join(rest)}
    elif rest:
        if not rest[0].isdigit():
            print("Give the checkpoint's number from your instructions: done 2")
            return 2
        body = {"checkpoint": int(rest[0]), "by": "claude"}
    else:
        body = {"done": True, "by": "claude"}
    # Straight to this laptop: a proxy set for the web must not carry it.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        port = json.loads((HERE / "server.json").read_text(encoding="utf-8"))["port"]
        req = urllib.request.Request(f"http://127.0.0.1:{port}/api/step/{step}/{ROUTES[verb]}",
                                     data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        with opener.open(req, timeout=5) as r:
            reply = json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as err:
        try:
            reply = json.loads(err.read() or b"{}")
        except ValueError:
            reply = {"error": f"The page answered {err.code}."}
    except (OSError, ValueError, KeyError):
        print("The workbench page isn't running, so nothing was sent. Carry on without it.")
        return 1
    if reply.get("error"):
        print(reply["error"])
        return 1
    print(reply.get("said") or "Sent.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
