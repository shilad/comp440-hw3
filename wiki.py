"""The three lookup tools the agent can use: Wikipedia search, reading one
section of a Wikipedia page, and one fact from Wikidata.

Every request is cached in .cache/, so running the same claim twice doesn't
hit Wikipedia twice. Each function returns plain text, because that is what
the agent reads.
"""

import hashlib
import json
import re
from pathlib import Path

import time

import requests

WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"

# Wikipedia asks every program that calls its API to say who it is and how to
# reach whoever runs it. It lets a program that gives a web address or an email
# make far more requests a minute than one that doesn't.
HEADERS = {"User-Agent": "COMP440-HW3/0.1 (https://shilad.github.io/comp440-website/; "
                         "Macalester College course assignment)"}

CACHE_DIR = Path(__file__).parent / ".cache"


def _get(url, params):
    """GET a JSON API with a disk cache."""
    params = {**params, "format": "json", "formatversion": "2"}
    key = hashlib.sha256((url + json.dumps(params, sort_keys=True)).encode()).hexdigest()
    path = CACHE_DIR / f"{key}.json"
    if path.exists():
        return json.loads(path.read_text())
    for wait in (2, 4, 8, 16, None):
        response = requests.get(url, params=params, headers=HEADERS, timeout=30)
        if response.status_code != 429 or wait is None:
            break
        time.sleep(wait)  # Wikipedia asked us to slow down
    response.raise_for_status()
    data = response.json()
    CACHE_DIR.mkdir(exist_ok=True)
    path.write_text(json.dumps(data))
    return data


def _strip_html(text):
    return re.sub(r"<[^>]+>", "", text).replace("&quot;", '"').replace("&amp;", "&")


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
