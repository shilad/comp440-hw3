"""The three lookup tools the agent can use: Wikipedia search, reading one
section of a Wikipedia page, and one fact from Wikidata.

Every request is cached in .cache/, so running the same claim twice doesn't
hit Wikipedia twice. Each function returns plain text, because that is what
the agent reads.
"""

import hashlib
import html
import json
import os
import re
import sys
from pathlib import Path

import time

import requests

WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"

# Wikipedia asks every program that calls its API to say who it is and how to
# reach whoever runs it, in the User-Agent. It allows a set number of requests
# a minute for each contact given there, counted by the contact. So you put
# your own email in .env as WIKIPEDIA_CONTACT, and your requests get an
# allowance of their own. Without it, every copy of this code gives the course
# site as its contact, and the whole class shares one allowance.
SHARED_USER_AGENT = ("COMP440-HW3/0.1 (https://shilad.github.io/comp440-website/; "
                     "Macalester College course assignment)")
_warned = False


def _headers():
    """The User-Agent for a request. It reads WIKIPEDIA_CONTACT each time, not
    when this file is imported, so it works whenever .env is loaded."""
    global _warned
    contact = os.environ.get("WIKIPEDIA_CONTACT", "").strip()
    if contact:
        return {"User-Agent": f"COMP440-HW3/0.1 ({contact}; Macalester College course assignment)"}
    if not _warned:  # once per run, not once per request
        _warned = True
        print("Warning: WIKIPEDIA_CONTACT is not set, so this copy shares Wikipedia's allowance "
              "of requests with the whole class, and your runs may slow down. To fix it, add "
              "the line WIKIPEDIA_CONTACT=<your Macalester email> to .env.", file=sys.stderr)
    return {"User-Agent": SHARED_USER_AGENT}


CACHE_DIR = Path(__file__).parent / ".cache"

# When Wikipedia says "too many requests", wait as long as it asks, but no more
# than MAX_PAUSE seconds at a time, and give up on a request after MAX_WAIT.
MAX_PAUSE = 60
MAX_WAIT = 300


class RateLimited(Exception):
    """Wikipedia kept saying "too many requests" for longer than MAX_WAIT."""


def _pause(response, tries):
    """Seconds to wait after a "too many requests" reply: what its Retry-After
    header asks for or, if it doesn't say, 2, 4, 8, ... seconds."""
    try:
        seconds = float(response.headers["Retry-After"])
    except (KeyError, ValueError):
        seconds = 2 ** tries
    return min(max(seconds, 1), MAX_PAUSE)


_said_waiting = 0.0  # when the notice below was last printed


def _say_waiting(seconds):
    """Say that the program is waiting because Wikipedia asked it to, at most
    once a minute, so that a run that has slowed down does not look stuck."""
    global _said_waiting
    if time.time() - _said_waiting < 60:
        return
    _said_waiting = time.time()
    notice = (f"Wikipedia asked this program to slow down, so it is waiting {seconds:.0f} seconds "
              "before it tries again. It does this by itself; you don't need to do anything.")
    if not os.environ.get("WIKIPEDIA_CONTACT", "").strip():
        notice += (" It happens much less once WIKIPEDIA_CONTACT is set in .env, because your "
                   "requests then get an allowance of their own.")
    print(notice, file=sys.stderr, flush=True)


def _get(url, params):
    """GET a JSON API with a disk cache."""
    params = {**params, "format": "json", "formatversion": "2"}
    key = hashlib.sha256((url + json.dumps(params, sort_keys=True)).encode()).hexdigest()
    path = CACHE_DIR / f"{key}.json"
    if path.exists():
        return json.loads(path.read_text())
    headers, tries, waited = _headers(), 0, 0
    while True:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        if response.status_code != 429:  # 429 means "too many requests"
            break
        tries += 1
        pause = _pause(response, tries)
        if waited + pause > MAX_WAIT:
            # An error, not an empty result, so that a rate limit never looks
            # to the agent like a page that doesn't exist.
            raise RateLimited(f"Wikipedia still says \"too many requests\" after {waited:.0f} "
                              "seconds of waiting. Wait a few minutes, then run again.")
        _say_waiting(pause)
        time.sleep(pause)
        waited += pause
    response.raise_for_status()
    data = response.json()
    CACHE_DIR.mkdir(exist_ok=True)
    path.write_text(json.dumps(data))
    return data


def _strip_html(text):
    """A search snippet as plain text: tags removed, and codes such as &amp; and
    &#039; turned back into the characters they stand for."""
    return html.unescape(re.sub(r"<[^>]+>", "", text))


# ---------- search ----------

def search(query, limit=5):
    """Search Wikipedia. Returns the top titles, each with a short snippet."""
    data = _get(WIKIPEDIA_API, {
        "action": "query", "list": "search", "srsearch": query, "srlimit": limit,
    })
    hits = data.get("query", {}).get("search", [])
    if not hits:
        return f"No Wikipedia pages matched {query!r}."
    lines = [f"{i}. {h['title']}: {_strip_html(h.get('snippet', ''))}" for i, h in enumerate(hits, 1)]
    return "\n".join(lines)


# ---------- read ----------

def page_text(title):
    """The plain text of a page and the title it resolved to (after redirects).
    Returns (None, title) if there is no such page."""
    data = _get(WIKIPEDIA_API, {
        "action": "query", "prop": "extracts", "explaintext": 1,
        "redirects": 1, "titles": title,
    })
    pages = data.get("query", {}).get("pages", [])
    if not pages or pages[0].get("missing") or "extract" not in pages[0]:
        return None, title
    return pages[0]["extract"], pages[0]["title"]


def split_sections(text):
    """Split a page's plain text into (heading, body) pairs. The first pair is
    the opening paragraphs, with the heading "Introduction"."""
    parts = re.split(r"^(={2,6})\s*(.+?)\s*\1\s*$", text, flags=re.M)
    sections = [("Introduction", parts[0].strip())]
    for i in range(1, len(parts) - 2, 3):
        sections.append((parts[i + 1].strip(), parts[i + 2].strip()))
    return [(h, b) for h, b in sections if b]


def read(title, section=None):
    """Read one section of a Wikipedia page. With no section, returns the
    opening paragraphs and the list of the page's sections."""
    text, resolved = page_text(title)
    if text is None:
        return f"There is no Wikipedia page titled {title!r}. Try search() first."
    sections = split_sections(text)
    if section is None:
        intro = sections[0][1] if sections else ""
        names = ", ".join(h for h, _ in sections[1:]) or "(none)"
        return f"Page: {resolved}\n\n{intro}\n\nSections: {names}"
    for heading, body in sections:
        if heading.lower() == section.lower():
            return f"Page: {resolved}, section: {heading}\n\n{body}"
    names = ", ".join(h for h, _ in sections)
    return f"{resolved} has no section called {section!r}. Its sections are: {names}"


# ---------- wikidata ----------

def _wikidata_id(name, kind):
    data = _get(WIKIDATA_API, {
        "action": "wbsearchentities", "search": name, "language": "en",
        "type": kind, "limit": 1,
    })
    hits = data.get("search", [])
    return (hits[0]["id"], hits[0].get("label", name)) if hits else (None, name)


def _labels(ids):
    if not ids:
        return {}
    data = _get(WIKIDATA_API, {
        "action": "wbgetentities", "ids": "|".join(ids), "props": "labels", "languages": "en",
    })
    return {i: e.get("labels", {}).get("en", {}).get("value", i)
            for i, e in data.get("entities", {}).items()}


def _format_value(snak, labels):
    value = snak.get("datavalue", {}).get("value")
    kind = snak.get("datatype")
    if value is None:
        return "(no value)"
    if kind == "wikibase-item":
        return labels.get(value["id"], value["id"])
    if kind == "time":
        return value["time"].lstrip("+").split("T")[0]
    if kind == "quantity":
        return value["amount"].lstrip("+")
    if kind == "monolingualtext":
        return value["text"]
    return str(value)


def wikidata(entity, prop):
    """Look up one property of one entity on Wikidata, for example
    wikidata("Robert Zemeckis", "place of birth")."""
    entity_id, entity_label = _wikidata_id(entity, "item")
    if entity_id is None:
        return f"Wikidata has no item matching {entity!r}."
    prop_id, prop_label = _wikidata_id(prop, "property")
    if prop_id is None:
        return f"Wikidata has no property matching {prop!r}."
    data = _get(WIKIDATA_API, {
        "action": "wbgetentities", "ids": entity_id, "props": "claims",
    })
    claims = data.get("entities", {}).get(entity_id, {}).get("claims", {}).get(prop_id, [])
    if not claims:
        return f"Wikidata has no {prop_label} for {entity_label} ({entity_id})."
    snaks = [c["mainsnak"] for c in claims]
    items = [s["datavalue"]["value"]["id"] for s in snaks
             if s.get("datatype") == "wikibase-item" and "datavalue" in s]
    labels = _labels(items)
    values = "; ".join(_format_value(s, labels) for s in snaks)
    return f"Wikidata: {entity_label} ({entity_id}), {prop_label}: {values}"
