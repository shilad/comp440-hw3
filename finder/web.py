"""The claim finder's screen, which the homework page serves under /claims.

The page in static/ does no searching itself: it asks these addresses, and they call finder.search.
The student's selection lives in the browser until they save it.

    GET  /claims/                 the screen
    GET  /claims/search?q=...&how=both&start=0
                                  50 results of a search from `start`, best first, with how many
                                  claims it found and how many contain any and all of its words
    POST /claims/save             saves the selected claims in data/dev.jsonl and data/eval.jsonl;
                                  the body is {"selected": [{"id", "query"}, ...]}
    GET  /claims/saved            what is saved already, from data/my-topic.json, as JSON

finder.search is imported only when a search or a save arrives, so the homework page starts
even while the claims are still loading or missing.
"""

from __future__ import annotations

import json
from pathlib import Path

STATIC = Path(__file__).parent / "static"
TYPES = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
         ".js": "text/javascript; charset=utf-8"}
WAYS = ("keyword", "meaning", "both")
PAGE = 50         # results sent at a time; the screen's "Show 50 more" asks for the next ones


def engine():
    """The search package, imported the first time a request needs it."""
    from finder import search  # noqa: PLC0415
    return search


def handle(method: str, path: str, query: dict, body: bytes, repo) -> tuple[int, str, bytes]:
    """(status, content type, body) for one request; path is what follows /claims."""
    repo = Path(repo)
    if method == "GET" and path in ("", "/"):
        return static("index.html")
    if method == "GET" and path.startswith("/static/"):
        return static(path[len("/static/"):])
    if method == "GET" and path == "/search":
        return answer(*search_page({k: v[0] for k, v in query.items()}))
    if method == "GET" and path == "/saved":
        return answer(saved(repo), 200)
    if method == "POST" and path == "/save":
        try:
            asked = json.loads(body or b"{}")
        except ValueError:
            asked = {}
        return answer(save_page(asked if isinstance(asked, dict) else {}, repo), 200)
    return answer({"error": "The claim finder has no such address."}, 404)


def static(name: str) -> tuple[int, str, bytes]:
    """One file of the screen, from static/."""
    f = (STATIC / name).resolve()
    if f.parent != STATIC.resolve() or f.suffix not in TYPES or not f.is_file():
        return 404, "text/plain; charset=utf-8", b"Not found."
    return 200, TYPES[f.suffix], f.read_bytes()


def answer(data: dict, status: int) -> tuple[int, str, bytes]:
    return status, "application/json", json.dumps(data).encode()


def search_page(params: dict) -> tuple[dict, int]:
    """The answer to /claims/search: one page of results, and the counts for the whole search."""
    query = " ".join(str(params.get("q") or "").split())
    how = params.get("how") if params.get("how") in WAYS else "both"
    try:
        start = max(0, int(params.get("start") or 0))
    except ValueError:
        start = 0
    if not query:
        return {"error": "Type a topic first."}, 400
    search = engine()
    results = search.search(query, how)
    return {"query": query, "how": how, "matches": search.keyword_counts(query),
            "total": len(results), "start": start, "results": results[start:start + PAGE]}, 200


def save_page(asked: dict, repo: Path) -> dict:
    """The answer to /claims/save: the selected claims looked up by id and saved, or the reason not."""
    selected = asked.get("selected")
    if not isinstance(selected, list) or not all(isinstance(s, dict) and s.get("id") for s in selected):
        return {"ok": False, "why": "The screen sent no claims to save. Reload the page and try again."}
    search = engine()
    by_id = search.claims_by_id()
    unknown = [s["id"] for s in selected if s["id"] not in by_id]
    if unknown:
        return {"ok": False, "why": f"The claim {unknown[0]} is no longer in the dataset. Remove it, select "
                                    "another claim, and save again."}
    try:
        search.save([by_id[s["id"]] for s in selected], [str(s.get("query") or "") for s in selected], folder=repo)
    except ValueError as refusal:
        return {"ok": False, "why": str(refusal)}
    return {"ok": True, **saved(repo)}


def saved(repo: Path) -> dict:
    """Whether the student has saved claims (data/my-topic.json, the note of the searches, exists),
    the searches that found them, how many are in data/dev.jsonl and data/eval.jsonl, and whether
    the agent has run on them, after which finder.search.save refuses to replace them."""
    note = repo / "data" / "my-topic.json"
    if not note.is_file():
        return {"saved": False}
    try:
        found = json.loads(note.read_text())
    except (OSError, ValueError):
        found = {}
    topics = found.get("topics", []) if isinstance(found, dict) else []
    return {"saved": True, "topics": [topic_text(t) for t in topics if topic_text(t)],
            "development": lines(repo / "data" / "dev.jsonl"), "evaluation": lines(repo / "data" / "eval.jsonl"),
            "run": engine().locked(repo)}


def topic_text(topic) -> str:
    """A topic from the note: its search text, whether the note holds the text or a small dict."""
    if isinstance(topic, dict):
        topic = topic.get("query") or topic.get("topic") or ""
    return str(topic)


def lines(f: Path) -> int:
    """How many claims a .jsonl file holds: its lines that are not empty."""
    return sum(1 for line in f.read_text().splitlines() if line.strip()) if f.is_file() else 0
