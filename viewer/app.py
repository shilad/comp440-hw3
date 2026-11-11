"""The results viewer: pages where you read your own runs.

The homework page mounts handle() under /results. A request for /results/run?dir=runs/part2
reaches it as handle("GET", "/run", {"dir": ["runs/part2"]}, repo). Run it on its own with
`uv run python -m viewer`.

Pages: /  /run?dir=  /claim?dir=&id=  /check?file=  /compare?a=&b=  /open?path=
It only reads, only inside runs/ (and the claim files in data/), and shows what happened
without judging it.
"""

from __future__ import annotations

import html
import re
import sys
import time
import traceback
from pathlib import Path
from urllib.parse import quote, urlencode

from . import runs as R

# Every link starts with this. The homework page serves the viewer under /results; on its
# own (python -m viewer) it is "".
PREFIX = "/results"

STATIC = Path(__file__).parent / "static"
STATIC_TYPES = {".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8"}
HTML = "text/html; charset=utf-8"

# What one version of the agent is made of, said the same way everywhere: evaluate.py's
# fingerprint (agent_version) covers these files and the loop file in use.
AGENT_FILES = ('<code>instructions.md</code>, <code>agent.py</code>, <code>wiki.py</code> and the loop '
               '(<code>my_loop.py</code> or <code>reference_loop.py</code>)')

FOLD_AT = 700      # results longer than this many characters start folded
PEEK = 260         # characters shown while a result is folded

R.warm_up()        # load evaluate.py now, in the background, not on the first page


def e(text) -> str:
    return html.escape(str(text), quote=True)


def link(path: str, **params) -> str:
    pairs = [(k, v) for k, v in params.items() if v not in (None, "", [])]
    q = urlencode(pairs, doseq=True)
    return f"{PREFIX}{path}" + (f"?{q}" if q else "")


def a(href: str, text: str, cls: str = "", new_tab: bool = False) -> str:
    extra = f' class="{cls}"' if cls else ""
    if new_tab:
        extra += ' target="_blank" rel="noopener noreferrer"'
        text += '<span class="sr"> (opens in a new tab)</span>'
    return f'<a href="{e(href)}"{extra}>{text}</a>'


# ------------------------------------------------------------------ entry point

class Problem(Exception):
    def __init__(self, status: int, title: str, text: str):
        super().__init__(title)
        self.status, self.title, self.text = status, title, text


class Redirect(Exception):
    def __init__(self, to: str):
        super().__init__(to)
        self.to = to


def respond(method: str, path: str, query: dict, repo) -> tuple[int, str, bytes, dict]:
    """handle(), with headers: (status, content type, body, headers). A page that only sends
    the browser on (/open) comes back as a 303 with a Location header, so it never stays in
    the browser's history and Back works. The homework page uses this when it can."""
    try:
        return (*handle(method, path, query, repo, _raise=True), {})
    except Redirect as r:
        return 303, HTML, redirect(r.to).encode(), {"Location": r.to}


def handle(method: str, path: str, query: dict, repo, _raise: bool = False) -> tuple[int, str, bytes]:
    """(status, content type, body) for one request. A redirect comes back as a page that sends
    the browser on by itself (see respond() for a real one)."""
    repo = Path(repo)
    query = query or {}
    if method not in ("GET", "HEAD"):
        return 405, "text/plain; charset=utf-8", b"The results viewer only reads."
    path = path or "/"
    if path.startswith("/static/"):
        return static(path[len("/static/"):])
    routes = {"/": home, "/run": run_page, "/claim": claim_page, "/check": check_page,
              "/compare": compare_page, "/open": open_page}
    page = routes.get(path.rstrip("/") or "/")
    try:
        if page is None:
            raise Problem(404, "No such page", f"The results viewer has no page at {e(path)}.")
        body = page(repo, {k: (v[0] if isinstance(v, list) else v) for k, v in query.items()})
        return 200, HTML, body.encode("utf-8")
    except Redirect as r:
        if _raise:
            raise
        return 200, HTML, redirect(r.to).encode()
    except Problem as p:
        return p.status, HTML, shell(p.title, f"<h1>{e(p.title)}</h1><p>{p.text}</p>"
                                     f"<p>{a(link('/'), 'See every run you have')}</p>").encode()
    except R.BadPath:
        return 400, HTML, shell("Not inside runs/", "<h1>Not inside runs/</h1><p>The results "
                                "viewer only opens files and folders inside <code>runs/</code>.</p>"
                                f"<p>{a(link('/'), 'See every run you have')}</p>").encode()
    except Exception as error:  # noqa: BLE001  show something readable, and log the rest
        traceback.print_exc(file=sys.stderr)
        return 500, HTML, shell("Something went wrong", "<h1>Something went wrong</h1>"
                                "<p>The results viewer could not show this page: "
                                f"<code>{e(type(error).__name__)}: {e(error)}</code>. "
                                "The terminal that runs it has the details.</p>"
                                f"<p>{a(link('/'), 'See every run you have')}</p>").encode()


def static(name: str):
    target = (STATIC / name).resolve()
    if target.parent != STATIC.resolve() or target.suffix not in STATIC_TYPES or not target.is_file():
        return 404, "text/plain; charset=utf-8", b"Not found."
    return 200, STATIC_TYPES[target.suffix], target.read_bytes()


def shell(title: str, body: str, crumbs: list | None = None) -> str:
    trail = [a(link("/"), "Your runs")] + (crumbs or [])
    back = f'<a class="home" href="/">Back to the homework page</a>' if PREFIX else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)} · Results viewer</title>
<link rel="stylesheet" href="{e(link('/static/viewer.css'))}">
<script src="{e(link('/static/viewer.js'))}" defer></script>
</head>
<body>
<a class="skip" href="#main">Skip to the page's content</a>
<header class="top"><div class="wrap">
<div class="bar"><span class="label">COMP 440 HW3 · Results viewer</span>{back}</div>
<nav class="crumbs" aria-label="Where you are">{' <span aria-hidden="true">/</span> '.join(trail)}</nav>
</div></header>
<main id="main" class="wrap">
{body}
</main>
<footer class="foot"><div class="wrap">The results viewer reads what is saved in <code>runs/</code>
and never changes it. Reload the page to see new results.</div></footer>
</body>
</html>
"""


# ------------------------------------------------------------------ small pieces

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def when(t: float) -> str:
    if not t:
        return "unknown"
    lt = time.localtime(t)
    hour = lt.tm_hour % 12 or 12
    return f"{MONTHS[lt.tm_mon - 1]} {lt.tm_mday}, {hour}:{lt.tm_min:02d} {'am' if lt.tm_hour < 12 else 'pm'}"


def and_list(bits: list) -> str:
    """"a", "a and b", "a, b and c"."""
    return bits[0] if len(bits) == 1 else ", ".join(bits[:-1]) + " and " + bits[-1]


def plural(n: int, one: str, many: str | None = None) -> str:
    return f"{n:,} {one if n == 1 else (many or one + 's')}"


def pct(c: int, n: int) -> str:
    return f"{100 * c / n:.1f}%" if n else "no claims"


def frac(c: int, n: int) -> str:
    return f'{c:,} of {n:,} <span class="pct">({pct(c, n)})</span>' if n else "none yet"


def dollars(x: float, places: int = 4) -> str:
    return f"${x:.{places}f}"


def verdict_cell(row: dict | None, nn: str = "the dataset's label", long: bool = False) -> str:
    """A verdict with a mark for whether it matches the label, and the same in words: in full
    on a claim's page, "matches" or "does not match" in a table (whose legend says the rest)."""
    o = R.outcome(row)
    if o == "notrun":
        return '<span class="o notrun">not run yet</span>'
    ok = o == "correct"
    cls, mk = ("correct", "✓") if ok else ("wrong", "✗")
    if long:  # one sentence that reads by itself
        if o == "error":
            said = f"It stopped with an error, which does not match {nn}."
        elif row["verdict"] is None:
            said = f"It gave no verdict, which does not match {nn}."
        else:
            said = (f"The verdict is <em>{e(row['verdict'])}</em>, which "
                    f"{'matches' if ok else 'does not match'} {nn}.")
        return (f'<span class="o {cls} long"><span class="mk" aria-hidden="true">{mk}</span>'
                f'<span class="says">{said}</span></span>')
    text = "stopped with an error" if o == "error" else (row["verdict"] if row["verdict"] is not None
                                                            else "no verdict")
    words = "matches" if ok else "does not match"
    return (f'<span class="o {cls}"><span class="mk" aria-hidden="true">{mk}</span>'
            f'{e(text)}<span class="says">{words}</span></span>')


def sources_of(items) -> set:
    return {it.get("source") for it in items}


def noun(items) -> str:
    """What a verdict is compared with, in the words students see."""
    sources = sources_of(items)
    if sources and sources <= {"mine"}:
        return "your verdict"
    if "mine" in sources:
        return "the label"
    return "the dataset's label"


def matched_means(items, lead: str = "A ✓ means") -> str:
    """Said once on a page, where a ✓ (or the word "Matched") first appears."""
    sources = sources_of(items)
    if sources and sources <= {"mine"}:
        return f"{lead} the verdict matched your verdict, the one in your claims file."
    text = f"{lead} the verdict matched the dataset's label"
    text += (", or, for your own claims, your verdict. " if "mine" in sources else ". ")
    return text + ("HoVer labels each claim only <em>supported</em> or <em>not supported</em>, so "
                   "<em>refuted</em> and <em>doesn't say</em> both count as <em>not supported</em>.")


def legend(items) -> str:
    nn = noun(items)
    return (f'<p class="legend small">In each version\'s column, a ✓ means the verdict matches {nn} and a ✗ '
            'means it does not. A missing verdict, or a claim that stopped with an error, does not match, as in '
            'evaluate.py.</p>')


def wiki_url(title: str, section: str | None = None) -> str:
    url = "https://en.wikipedia.org/wiki/" + quote(title.replace(" ", "_"), safe="()_,:'!-./")
    if section:
        url += "#" + quote(section.replace(" ", "_"), safe="()_,:'!-.")
    return url


def text_fragment(q: str) -> str:
    """#:~:text=... so the browser scrolls to the quote, if the live page still has it."""
    def enc(s):
        return quote(s, safe="").replace("-", "%2D")
    words = q.split()
    if len(words) <= 8:
        return "#:~:text=" + enc(" ".join(words))
    return "#:~:text=" + enc(" ".join(words[:4])) + "," + enc(" ".join(words[-4:]))


def page_link(page: dict, new_tab=True) -> str:
    if page["kind"] == "wikidata":
        return a(f"https://www.wikidata.org/wiki/{page['id']}",
                 f"Wikidata: {e(page['title'])} ({e(page['id'])})", new_tab=new_tab)
    text = e(page["title"]) + (f", section {e(page['section'])}" if page.get("section") else "")
    return a(wiki_url(page["title"], page.get("section")), text, new_tab=new_tab)


def args_text(inp: dict) -> str:
    parts = []
    for k, v in inp.items():
        if v is None or k == "evidence":
            continue
        parts.append(f'<span class="k">{e(k)}</span> <span class="v">{e(json_str(v))}</span>')
    return " · ".join(parts) if parts else '<span class="v">(nothing)</span>'


def json_str(v) -> str:
    if isinstance(v, str):
        return f"“{v}”"
    return str(v)


# ------------------------------------------------------------------ home

EMPTY_PART = {
    0: "Nothing yet. Steps 0c, 0d and 0e each save a check in <code>runs/part0/</code>.",
    1: ("Nothing yet. Step 1b saves your lookups in <code>runs/part1/lookups.jsonl</code>, and steps 1c "
        "and 1d save runs in <code>runs/part1/before/</code> and <code>runs/part1/after/</code>."),
    2: "Nothing yet. Step 1e starts the run that fills <code>runs/part2/</code>.",
    3: "Nothing yet. Step 3b saves a run in <code>runs/part3/after/</code>.",
}
PART_TITLES = {0: "Part 0: Set up and find your claims", 1: "Part 1: How the agent works",
               2: "Part 2: The agent against the baselines", 3: "Part 3: Why the agent fails, and one change"}


def home(repo: Path, q: dict) -> str:
    evals, checks, lookups = R.walk_runs(repo)
    out = ['<h1>Your runs</h1><p class="lede">Everything saved in <code>runs/</code>, part by part, in '
           'the order the homework makes it. Open a run or a check to read it.</p>']
    if not evals and not checks and not lookups:
        out.append('<p class="empty">No runs yet. Your first one appears here after step 0c.</p>')
        return shell("Your runs", "".join(out))
    runs = {}
    for rel in evals:
        path, rel = R.safe_path(repo, rel)
        run = R.get_run(repo, path, rel)
        if run is not None:
            runs[rel] = run
    if runs:
        out.append(f'<p class="small">{matched_means([it for r in runs.values() for it in r.items.values()] or [{}], "<em>Matched</em> means")}</p>')
    if len(runs) > 1:
        out.append(f'<p>{a(link("/compare"), "Compare two runs")}</p>')
    for part in (0, 1, 2, 3, None):
        ev = sorted((r for r in runs if R.part_of(r) == part), key=R.homework_order)
        ch = [r for r in checks if R.part_of(r) == part]
        lk = sorted((r for r in lookups if R.part_of(r) == part), key=R.homework_order)
        if part is None and not (ev or ch or lk):
            continue
        title = PART_TITLES.get(part, "Other runs")
        hid = f"part-{part}" if part is not None else "part-other"
        out.append(f'<section aria-labelledby="{hid}"><h2 id="{hid}">{e(title)}</h2>')
        if not (ev or ch or lk):
            hint = EMPTY_PART[part]
            if part == 3 and not R.in_homework(repo, "runs/part3/after"):
                hint = "Nothing yet."  # this homework's step list has no run in Part 3
            out.append(f'<p class="empty">{hint}</p></section>')
            continue
        out.append(checks_html(repo, ch))
        out.append(lookups_html(repo, lk))
        if ev:
            out.append(runs_table([runs[r] for r in ev]))
        out.append('</section>')
    return shell("Your runs", "".join(out))


def runs_table(runs: list) -> str:
    out = ['<div class="scroll"><table class="grid"><thead><tr><th scope="col">Run</th>'
           '<th scope="col">Made</th><th scope="col">Version</th><th scope="col">Claims done</th>'
           '<th scope="col">Matched</th></tr></thead><tbody>']
    for run in runs:
        total = run.total()
        span = max(len(run.methods), 1)
        status = "" if run.finished() else '<br><span class="tag">not finished</span>'
        head = (f'<th scope="rowgroup" rowspan="{span}">{a(link("/run", dir=run.rel), e(run.rel))}{status}'
                f'</th><td rowspan="{span}" class="nums">{when(run.started)}<br>'
                f'<span class="small">last saved {when(run.mtime)}</span></td>')
        if not run.methods:
            out.append(f'<tr class="first">{head}<td colspan="3" class="small">No results saved yet.</td></tr>')
            continue
        for k, m in enumerate(run.methods):
            st = R.stats(run, m)
            done = f"{st['n']:,} of {total:,}" if total else f"{st['n']:,}"
            out.append(f'<tr class="{"first" if k == 0 else ""}">{head if k == 0 else ""}'
                       f'<td>{e(R.method_name(m))}</td><td class="nums">{done}</td>'
                       f'<td class="nums">{frac(st["correct"], st["n"])}</td></tr>')
    out.append('</tbody></table></div>')
    return "".join(out)


def checks_html(repo: Path, checks: list) -> str:
    folders: dict[str, list] = {}
    for rel in checks:
        folders.setdefault(rel.rsplit("/", 1)[0], []).append(rel)
    out = []
    for folder in sorted(folders, key=R.homework_order):
        rows = []
        for rel in folders[folder]:
            path, rel = R.safe_path(repo, rel)
            row = R.CACHE.get(path, R.load_check)
            if row is not None:
                rows.append((R.check_time(path), rel, row))
        rows.sort(key=lambda x: x[0])  # the order they were made in
        out.append(f'<h3 id="{e(anchor(folder))}">Single checks in <code>{e(folder)}/</code></h3>'
                   '<div class="scroll"><table class="grid"><thead><tr><th scope="col">Saved</th>'
                   '<th scope="col">Version</th><th scope="col">Verdict</th><th scope="col">Claim</th>'
                   '</tr></thead><tbody>')
        for t, rel, row in rows:
            method = str(row.get("method") or Path(rel).name.rsplit("-", 1)[0])
            verdict = row["verdict"] if row["verdict"] is not None else "no verdict"
            out.append(f'<tr><td class="nums nowrap">{when(t)}</td><td class="nowrap">'
                       f'{e(R.method_name(method))}</td><td class="nowrap">{e(verdict)}</td>'
                       f'<td class="claimcell">{a(link("/check", file=rel), e(row.get("claim", rel)))}</td></tr>')
        out.append('</tbody></table></div>')
    return "".join(out)


def lookups_html(repo: Path, lookups: list) -> str:
    out = []
    for rel in lookups:
        path, rel = R.safe_path(repo, rel)
        rows, bad = R.CACHE.get(path, R.load_lookups) or ([], 0)
        out.append(f'<h3 id="{e(anchor(rel))}">Your lookups by hand, in <code>{e(rel)}</code>, '
                   f'{plural(len(rows), "lookup")}</h3>')
        if rows:
            out.append('<ol class="lookups">')
            for row in rows:
                inp = row.get("input") if isinstance(row.get("input"), dict) else {}
                out.append(f'<li><span class="tool">{e(row.get("tool"))}</span> {args_text(inp)}</li>')
            out.append('</ol>')
        if bad:
            out.append(f'<p class="small">{plural(bad, "line")} in this file could not be read.</p>')
    return "".join(out)


def anchor(rel: str) -> str:
    return "f-" + re.sub(r"[^A-Za-z0-9]+", "-", rel).strip("-")


# ------------------------------------------------------------------ one evaluation run

def load_run(repo: Path, rel) -> R.Run:
    path, rel = R.safe_path(repo, rel)
    if not path.exists():
        raise Problem(404, "Nothing saved there yet", f"Nothing is saved at <code>{e(rel)}</code> yet. "
                      + part_hint(rel, repo))
    run = R.get_run(repo, path, rel) if path.is_dir() else None
    if run is None:
        raise Problem(404, "Not an evaluation run", f"<code>{e(rel)}</code> holds no evaluation "
                      "results: no file of results from evaluate.py.")
    return run


def part_hint(rel: str, repo: Path) -> str:
    """Which step makes what is at `rel`, from the homework's step list."""
    parts = rel.split("/")
    for n in range(len(parts), 1, -1):
        hint = R.where_from(repo, "/".join(parts[:n]))
        if hint:
            return hint
    return ""


FILTER_KEYS = ("q", "articles", "label", "used_all", "sort")
SORTS = {"": "Order of the claims file", "cost-high": "Cost, highest first",
         "cost-low": "Cost, lowest first", "lookups-high": "Most lookups first",
         "lookups-low": "Fewest lookups first"}
VERDICT_CHOICES = {"": "any verdict", "supported-or-refuted": "supported or refuted",
                   "supported": "supported", "refuted": "refuted", "doesn't say": "doesn't say",
                   "none": "no verdict"}


def outcomes(items) -> dict:
    return {"": "any result", "matched": f"matches {noun(items)}",
            "unmatched": f"does not match {noun(items)} (any reason)",
            "none": "gave no verdict", "error": "stopped with an error", "notrun": "not run yet"}


def focus(run: R.Run) -> str | None:
    """The method whose calls and cost the claims table shows: the agent, if it is there."""
    if "agent" in run.methods:
        return "agent"
    return run.methods[-1] if run.methods else None


def filters_of(q: dict, run: R.Run) -> dict:
    f = {k: str(q.get(k, "")).strip() for k in FILTER_KEYS}
    for m in run.methods:
        f["r_" + m] = str(q.get("r_" + m, "")).strip()
        f["v_" + m] = str(q.get("v_" + m, "")).strip()
    if f["sort"] not in SORTS:
        f["sort"] = ""
    return {k: v for k, v in f.items() if v}


def matches(run: R.Run, i: str, f: dict, max_steps: int) -> bool:
    item = run.items[i]
    if f.get("q"):
        text = R.norm_claim(item["claim"])
        if not all(w in text for w in f["q"].lower().split()):
            return False
    if f.get("articles") and (R.hops_text(item) or "none") != f["articles"]:
        return False
    if f.get("label") and R.label_text(item) != f["label"]:
        return False
    for m in run.methods:
        row = run.rows[m].get(i)
        want = f.get("r_" + m)
        if want:
            o = R.outcome(row)
            if want == "matched":
                if o != "correct":
                    return False
            elif want == "unmatched":
                if o not in ("wrong", "none", "error"):
                    return False
            elif o != want:
                return False
        v = f.get("v_" + m)
        if v:
            if row is None or row["failed"]:
                return False
            if v == "none":
                if row["verdict"] is not None:
                    return False
            elif v == "supported-or-refuted":
                if row["verdict"] not in ("supported", "refuted"):
                    return False
            elif row["verdict"] != v:
                return False
    if f.get("used_all"):
        if "agent" not in run.rows or not R.used_all_steps(run.rows["agent"].get(i), max_steps):
            return False
    return True


def filtered(run: R.Run, f: dict) -> list[str]:
    ids = [i for i in run.ids if matches(run, i, f, run.limit)]
    m = focus(run)
    sort = f.get("sort", "")
    if sort and m:
        field = "cost_usd" if sort.startswith("cost") else "steps"  # "steps" is agent.py's word for lookups
        have = [i for i in ids if i in run.rows[m]]
        missing = [i for i in ids if i not in run.rows[m]]
        have.sort(key=lambda i: run.rows[m][i][field], reverse=sort.endswith("high"))
        ids = have + missing
    return ids


def run_page(repo: Path, q: dict) -> str:
    run = load_run(repo, q.get("dir"))
    f = filters_of(q, run)
    out = [f'<h1><code>{e(run.rel)}</code></h1>']
    out.append(run_facts(run))
    if not run.methods:
        out.append('<p class="empty">No results saved yet. If the run has just started, reload in a minute.</p>')
        return shell(run.rel, "".join(out), [e(run.rel)])
    out.append(accuracy_section(run))
    out.append(cost_section(run))
    out.append(claims_section(run, f))
    return shell(run.rel, "".join(out), [e(run.rel)])


def run_facts(run: R.Run) -> str:
    out = ['<div class="facts">']
    total = run.total()
    made = f"The run was made on {when(run.started)} and last saved on {when(run.mtime)}."
    if run.file:
        out.append(f'<p>The claims come from <code>{e(run.file[0])}</code>, which holds '
                   f'{plural(run.file[1], "claim")}. {made}</p>')
    else:
        out.append(f'<p>{plural(len(run.ids), "claim")}. {made}</p>')
    missing = sum(1 for i in run.ids if "source" not in run.items[i])
    if missing:
        out.append(f'<p class="note">{plural(missing, "claim")} {"is" if missing == 1 else "are"} in no '
                   'claims file, so the label and the number of articles are not known.</p>')
    if run.methods:
        parts = [f"the {e(R.method_name(m))} has {len(run.rows[m]):,}" + (f" of {total:,}" if total else "")
                 + " results" for m in run.methods]
        out.append(f'<p>So far {and_list(parts)}.</p>')
    if not run.finished():
        line = ("<strong>This run has not finished.</strong> Its folder has no <code>report.txt</code> yet, "
                "and evaluate.py saves that only when every claim has a result. ")
        if run.recently_changed():
            line += "Its files changed in the last two minutes, so it is probably still going: reload to see more."
        else:
            line += ("It may still be going, or it may have stopped early. To finish it, run the same command "
                     "again: it picks up where it stopped and runs only the claims that have no result.")
        out.append(f'<p class="note">{line}</p>')
    for m in run.methods:
        if run.bad.get(m):
            out.append(f'<p class="note">{plural(run.bad[m], "line")} in <code>{e(m)}.jsonl</code> could '
                       'not be read. If the run is still going, it may be writing that line now.</p>')
    if len(run.limits) > 1:
        out.append('<p class="note">The agent\'s results here were made under different limits of lookups per '
                   'claim: ' + " and ".join(str(n) for n in run.limits) + '.</p>')
    if len(run.versions) > 1:
        out.append(f'<p class="note">The agent\'s results here were made by {len(run.versions)} different versions '
                   f'of the agent: different {AGENT_FILES}.</p>')
    relabelled = len(run.relabelled)
    if relabelled:
        out.append(f'<p class="note">For {plural(relabelled, "result")}, the label in the claims file has '
                   'changed since the run, so today it would count the other way. This page uses what the run '
                   'saved, as evaluate.py does.</p>')
    if R.RULES.problem and R.RULES.module is None:
        out.append(f'<p class="note">evaluate.py could not be loaded (<code>{e(R.RULES.problem)}</code>), '
                   'so this page uses its own copy of evaluate.py\'s rules for grouping claims.</p>')
    if run.methods:
        out.append(f'<p>{a("#claims", "Go to the claims")} · '
                   f'{a(link("/compare", a=run.rel), "Compare this run with another")}</p>')
    out.append('</div>')
    return "".join(out)


def accuracy_section(run: R.Run) -> str:
    items = list(run.items.values())
    out = ['<section aria-labelledby="h-acc"><h2 id="h-acc">Accuracy</h2>',
           f'<p class="small">{matched_means(items)}</p>']
    sts = {m: R.stats(run, m) for m in run.methods}
    out.append(accuracy_table(run.methods, sts, R.group_names(run),
                              f"How many verdicts matched {noun(items)}, by the number of articles a claim needs"))
    if len({sts[m]["n"] for m in run.methods}) > 1:
        out.append('<p class="note">The versions do not all have results for the same claims yet. Each '
                   'column counts only the claims that version has finished.</p>')
    text = R.report_text(run)
    if text:
        out.append('<details class="report"><summary>The same numbers as evaluate.py prints them</summary>'
                   f'<pre>{e(text)}</pre></details>')
    bad = []
    for m in run.methods:
        st = sts[m]
        if st["failed"] or st["no_verdict"]:
            bits = []
            if st["no_verdict"]:
                bits.append(a(link("/run", dir=run.rel, **{"r_" + m: "none"}) + "#claims",
                              plural(st["no_verdict"], "claim") + " with no verdict"))
            if st["failed"]:
                bits.append(a(link("/run", dir=run.rel, **{"r_" + m: "error"}) + "#claims",
                              plural(st["failed"], "claim") + " that stopped with an error"))
            bad.append(f'<li>The {e(R.method_name(m))} has {" and ".join(bits)}.</li>')
    out.append('<h3>Claims with no verdict, or that stopped with an error</h3>')
    if bad:
        out.append('<p class="small">They count as not matching above. A verdict is missing when the program '
                   'could not get one from the model: for example the model declined, the agent used all its '
                   'lookups, or its answer was sent back three times. Each claim\'s page shows the text that '
                   'was saved with it.</p><ul>' + "".join(bad) + '</ul>')
    else:
        out.append('<p class="small">None: every saved result has a verdict.</p>')
    out.append('</section>')
    return "".join(out)


def accuracy_table(methods: list, sts: dict, groups: list, caption: str, b_sts: dict | None = None) -> str:
    """evaluate.py's first table: one row per group, "All", then the same count by the dataset's
    label. With b_sts, two columns (A and B) and their difference, for one version."""
    rows = [(g, "group") for g in groups] + [("All", "all")]
    label_names = [name for _, name in R.LABEL_ROWS]
    if any(sts[m]["labels"] for m in methods):
        rows += [(name, "label") for name in label_names]

    def count(st, g, kind):
        if kind == "all":
            return st["correct"], st["n"]
        return tuple((st["labels"] if kind == "label" else st["groups"]).get(g, (0, 0)))

    if b_sts is None:
        head = "".join(f'<th scope="col">The {e(R.method_name(m))}</th>' for m in methods)
    else:
        head = '<th scope="col">A</th><th scope="col">B</th><th scope="col">B minus A</th>'
    out = [f'<div class="scroll"><table class="grid nums"><caption>{caption}</caption><thead><tr>'
           f'<th scope="col">Claims</th>{head}</tr></thead><tbody>']
    first_label = True
    for g, kind in rows:
        cls = ""
        if kind == "all":
            cls = ' class="all"'
        elif kind == "label" and first_label:
            cls, first_label = ' class="first"', False
        name = "All claims" if kind == "all" else g
        out.append(f'<tr{cls}><th scope="row">{e(name)}</th>')
        if b_sts is None:
            for m in methods:
                c, n = count(sts[m], g, kind)
                out.append(f'<td>{frac(c, n)}</td>')
        else:
            m = methods[0]
            ca, n = count(sts[m], g, kind)
            cb, _ = count(b_sts[m], g, kind)
            out.append(f'<td>{frac(ca, n)}</td><td>{frac(cb, n)}</td><td>{diff_points(ca, cb, n)}</td>')
        out.append('</tr>')
    out.append('</tbody></table></div>')
    return "".join(out)


def cost_section(run: R.Run) -> str:
    sts = {m: R.stats(run, m) for m in run.methods}
    out = ['<section aria-labelledby="h-cost"><h2 id="h-cost">Cost</h2>',
           '<div class="scroll"><table class="grid nums"><caption>Average per claim</caption><thead><tr>'
           '<th scope="col">Version</th><th scope="col">Claims</th><th scope="col">Lookups</th>'
           '<th scope="col">Tokens</th><th scope="col">Seconds</th><th scope="col">Dollars</th>'
           '</tr></thead><tbody>']
    for m in run.methods:
        st = sts[m]
        out.append(f'<tr><th scope="row">{e(R.method_name(m))}</th><td>{st["n"]:,}</td>'
                   f'<td>{st["steps"]:.1f}</td><td>{st["tokens"]:,.0f}</td><td>{st["seconds"]:.1f}</td>'
                   f'<td>{dollars(st["cost"])}</td></tr>')
    out.append('</tbody></table></div>')
    out.append('<div class="scroll"><table class="grid nums"><caption>Totals for the claims saved so far'
               '</caption><thead><tr><th scope="col">Version</th><th scope="col">Lookups</th>'
               '<th scope="col">Tokens in</th><th scope="col">Tokens out</th>'
               '<th scope="col">Seconds, added up</th><th scope="col">Dollars</th></tr></thead><tbody>')
    for m in run.methods:
        st = sts[m]
        out.append(f'<tr><th scope="row">{e(R.method_name(m))}</th><td>{st["total_steps"]:,}</td>'
                   f'<td>{st["total_in"]:,}</td><td>{st["total_out"]:,}</td>'
                   f'<td>{st["total_seconds"]:,.1f}</td><td>{dollars(st["total_cost"])}</td></tr>')
    if len(run.methods) > 1:
        out.append(f'<tr class="all"><th scope="row">All versions</th>'
                   f'<td>{sum(s["total_steps"] for s in sts.values()):,}</td>'
                   f'<td>{sum(s["total_in"] for s in sts.values()):,}</td>'
                   f'<td>{sum(s["total_out"] for s in sts.values()):,}</td>'
                   f'<td>{sum(s["total_seconds"] for s in sts.values()):,.1f}</td>'
                   f'<td>{dollars(sum(s["total_cost"] for s in sts.values()))}</td></tr>')
    out.append('</tbody></table></div>')
    out.append('<p class="small">A lookup is one call to <code>search</code>, <code>read</code> or '
               '<code>wikidata</code>; the final answer is not counted. Tokens are input and output '
               'together. Seconds are each claim\'s own time, added up; claims run a few at a time, so '
               'the whole run took less time than that. Dollars are worked out from the tokens at the '
               'prices in <code>agent.py</code>.</p>')
    if "agent" in sts:
        n = sts["agent"]["all_steps"]
        out.append(f'<p class="small">The agent used all {run.limit} lookups on '
                   f'{a(link("/run", dir=run.rel, used_all="1") + "#claims", plural(n, "claim"))}.</p>')
    out.append('</section>')
    return "".join(out)


def select(name: str, label: str, choices: dict, value: str) -> str:
    opts = "".join(f'<option value="{e(k)}"{" selected" if k == value else ""}>{e(v)}</option>'
                   for k, v in choices.items())
    return (f'<label class="field"><span>{label}</span>'
            f'<select name="{e(name)}" data-auto>{opts}</select></label>')


def claims_section(run: R.Run, f: dict) -> str:
    ids = filtered(run, f)
    m_focus = focus(run)
    items = list(run.items.values())
    label_name = "Your verdict" if noun(items) == "your verdict" else "The dataset's label"
    numbers = sorted({R.hops_text(run.items[i]) or "none" for i in run.ids})
    labels = sorted({R.label_text(run.items[i]) for i in run.ids})
    out = ['<section aria-labelledby="claims"><h2 id="claims" tabindex="-1">Claims</h2>',
           f'<form class="filters" method="get" action="{e(link("/run"))}#claims" role="search" '
           'aria-label="Filter the claims">',
           f'<input type="hidden" name="dir" value="{e(run.rel)}">',
           '<div class="row">',
           f'<label class="field grow"><span>Claim contains</span><input type="search" name="q" '
           f'value="{e(f.get("q", ""))}" placeholder="words in the claim"></label>',
           select("articles", "The number of articles", {"": "any number",
                  **{h: (h if h != "none" else "not given") for h in numbers}}, f.get("articles", "")),
           select("label", label_name, {"": "any", **{x: x for x in labels}}, f.get("label", "")),
           select("sort", "Order", SORTS if m_focus else {"": SORTS[""]}, f.get("sort", "")),
           '</div><div class="row">']
    for m in run.methods:
        out.append(f'<fieldset class="method"><legend>The {e(R.method_name(m))}</legend>'
                   + select("r_" + m, "Result", outcomes(items), f.get("r_" + m, ""))
                   + select("v_" + m, "Verdict", VERDICT_CHOICES, f.get("v_" + m, "")) + '</fieldset>')
    if "agent" in run.methods:
        checked = " checked" if f.get("used_all") else ""
        out.append(f'<label class="check"><input type="checkbox" name="used_all" value="1" data-auto{checked}> '
                   f'Only claims where the agent used all {run.limit} lookups</label>')
    out.append('</div><div class="row actions"><button type="submit">Show these claims</button> '
               f'{a(link("/run", dir=run.rel) + "#claims", "Clear the filters")}</div></form>')
    out.append(f'<p class="count" role="status" aria-live="polite">Showing <strong>{len(ids):,}</strong> '
               f'of {plural(len(run.ids), "claim")}.</p>')
    nn = noun(items)
    out.append(legend(items))
    if not ids:
        out.append('<p class="empty">No claims match these filters.</p></section>')
        return "".join(out)
    sort_note = f" (the {e(R.method_name(m_focus))})" if m_focus else ""
    out.append('<div class="scroll"><table class="grid claims"><thead><tr>'
               '<th scope="col" class="num">Row</th><th scope="col">Claim</th>'
               f'<th scope="col">{label_name}</th><th scope="col" class="num">Number of articles</th>')
    out += [f'<th scope="col">The {e(R.method_name(m))}</th>' for m in run.methods]
    if m_focus:
        out.append(f'<th scope="col" class="num">Lookups{sort_note}</th>'
                   f'<th scope="col" class="num">Cost{sort_note}</th>')
    out.append('</tr></thead><tbody>')
    for n, i in enumerate(ids, 1):
        item = run.items[i]
        href = link("/claim", dir=run.rel, id=i, **f)
        out.append(f'<tr id="row-{e(i)}"><td class="num" title="Line {run.position[i] + 1} of the claims file">{n}</td>'
                   f'<td class="claimcell">{a(href, e(item["claim"]))}</td>'
                   f'<td class="nowrap">{e(R.label_text(item))}</td><td class="num">{e(R.hops_text(item))}</td>')
        for m in run.methods:
            out.append(f'<td class="nowrap">{verdict_cell(run.rows[m].get(i), nn)}</td>')
        if m_focus:
            row = run.rows[m_focus].get(i)
            out.append(f'<td class="num">{row["steps"] if row else ""}</td>'
                       f'<td class="num">{dollars(row["cost_usd"]) if row else ""}</td>')
        out.append('</tr>')
    out.append('</tbody></table></div></section>')
    return "".join(out)


# ------------------------------------------------------------------ one claim

def claim_page(repo: Path, q: dict) -> str:
    run = load_run(repo, q.get("dir"))
    i = str(q.get("id", ""))
    if i not in run.items:
        raise Problem(404, "No such claim", f"<code>{e(run.rel)}</code> has no claim with the id "
                      f"<code>{e(i)}</code>.")
    f = filters_of(q, run)
    ids = filtered(run, f)
    item = run.items[i]
    nav = ""
    back = link("/run", dir=run.rel, **f) + f"#row-{i}"
    if i in ids:
        k = ids.index(i)
        prev = link("/claim", dir=run.rel, id=ids[k - 1], **f) if k > 0 else None
        nxt = link("/claim", dir=run.rel, id=ids[k + 1], **f) if k + 1 < len(ids) else None
        where = f"Claim {k + 1} of {len(ids):,}" + (" that match your filters" if f else "")
        nav = pager(prev, nxt, where, back)
    else:
        nav = pager(None, None, "This claim is not among the ones your filters show", back)
    full = q.get("full") == "1"
    out = [nav, claim_head(item, run.items[i].get("source") is not None,
                           [("", run.rows["agent"].get(i))] if "agent" in run.rows else [])]
    out.append(f'<p class="small">{matched_means([item])}</p>')
    cols = []
    for m in run.methods:
        row = run.rows[m].get(i)
        note = ""
        if (m, i) in run.relabelled:
            note = ('<p class="note">The label in <code>data/</code> has changed since this run. The run '
                    f'saved this result as {"matching" if row["correct"] else "not matching"}.</p>')
        cols.append(result_card(m, row, note, anchor_for=m, nn=noun([item])))
    out.append(f'<div class="cards n{len(cols)}">{"".join(cols)}</div>')
    for m in reversed(run.methods):  # the agent first: its trace is the long one
        row = run.rows[m].get(i)
        if row and row["trace"]:
            out.append(trace_section(m, row, full, toggle=link("/claim", dir=run.rel, id=i, **f,
                                                                full="" if full else "1")))
    out.append(nav)
    return shell(item["claim"][:60], "".join(out), [a(link("/run", dir=run.rel, **f) + "#claims", e(run.rel)),
                                                     "One claim"])


def pager(prev, nxt, where, back) -> str:
    p = a(prev, "← Previous", "pg", ) if prev else '<span class="pg off">← Previous</span>'
    n = a(nxt, "Next →", "pg") if nxt else '<span class="pg off">Next →</span>'
    p = p.replace("<a ", '<a rel="prev" ', 1) if prev else p
    n = n.replace("<a ", '<a rel="next" ', 1) if nxt else n
    keys = '<br><span class="hint">The left and right arrow keys move too.</span>' if (prev or nxt) else ""
    return (f'<nav class="pager" aria-label="Claims">{p}<span class="where">{e(where)} · '
            f'{a(back, "back to the table")}{keys}</span>{n}</nav>')


def claim_head(item: dict, known: bool, reads: list | None = None) -> str:
    """The claim, its label and the number of articles, and the articles the dataset lists for it,
    marked with whether the agent read each one. `reads` is [(name of the run, the agent's row)]."""
    out = [f'<h1 class="claim">{e(item["claim"])}</h1><div class="facts">']
    if known:
        if item.get("source") == "mine":
            said = f'Your verdict is <strong>{e(R.label_text(item))}</strong>. This is one of your own claims.'
        else:
            said = f"The dataset's label is <strong>{e(R.label_text(item))}</strong>"
            said += (f", and the claim needs {e(R.hops_text(item))} articles." if R.hops_text(item) else ".")
        out.append(f"<p>{said}</p>")
        if isinstance(item.get("articles"), list) and item["articles"]:
            out.append(articles_html(item, reads or []))
    else:
        out.append('<p class="note">This claim is in no claims file, so its label is not known.</p>')
    out.append(f'<p class="small">Id: <code>{e(item.get("id", ""))}</code></p></div>')
    return "".join(out)


def articles_html(item: dict, reads: list) -> str:
    out = ['<p class="small arts-head">The dataset lists these articles for this claim:</p><ul class="arts">']
    marks = [(name, row, dict(R.articles_read(item, row))) for name, row in reads if row is not None]
    for title in (R.article_title(t) for t in item["articles"]):
        bits = []
        for name, row, seen in marks:
            n = seen.get(title)
            who = f"the agent in {name}" if name else "the agent"
            if n:
                anchor_id = f"#call-{(name.lower() + '-') if name else ''}agent-{n}"
                bits.append(f'<span class="o">{who} read it in {a(anchor_id, f"entry {n}")}</span>')
            else:
                bits.append(f'<span class="o notread">{who} did not read it</span>')
        said = (": " + "; ".join(bits) + ".") if bits else ""
        out.append(f'<li>{a(wiki_url(str(title)), e(title), new_tab=True)}{said}</li>')
    out.append('</ul>')
    return "".join(out)


def result_card(method: str, row: dict | None, note: str = "", anchor_for: str = "",
                title: str | None = None, mark: bool = True, nn: str = "the dataset's label") -> str:
    title = f'<h2 class="card-title">{title or "The " + e(R.method_name(method))}</h2>'
    if row is None:
        return f'<article class="card">{title}<p class="empty">No result for this claim yet.</p></article>'
    shown = verdict_cell(row, nn, long=True) if mark else f'<span class="o">{e(row["verdict"] or "no verdict")}</span>'
    if not mark:
        shown = (f'<span class="o">The verdict is <em>{e(row["verdict"])}</em>.</span>' if row["verdict"] is not None
                 else '<span class="o">It gave no verdict.</span>')
    out = [f'<article class="card">{title}<p class="verdict-line">{shown}</p>', note]
    if row["explanation"]:
        out.append(f'<h3 class="label">Explanation</h3><p class="expl">{e(row["explanation"])}</p>')
    places = R.quote_places(row)
    out.append('<h3 class="label">Quoted evidence</h3>')
    if not places:
        out.append('<p class="small">None.</p>')
    else:
        if any(h for place in places for h in place["hits"]):
            out.append('<p class="small hint">An <em>open the live page</em> link opens today\'s Wikipedia '
                       'page in a new tab. Your browser jumps to the quote if the page still has it.</p>')
        out.append('<ol class="quotes">')
        for n, place in enumerate(places, 1):
            out.append(f'<li><blockquote id="q-{e(anchor_for)}-{n}">{e(place["quote"])}</blockquote>'
                       f'<p class="small">{quote_where(row, place, n, anchor_for)}</p></li>')
        out.append('</ol>')
    t = row["tokens"]
    out.append(f'<p class="numbers-line">It made {plural(row["steps"], "lookup")}, used {t["input"]:,} tokens in '
               f'and {t["output"]:,} tokens out, cost {dollars(row["cost_usd"])} and took '
               f'{row["seconds"]:.1f} seconds.</p>')
    if row["trace"]:
        out.append(f'<p class="small">{a("#trace-" + anchor_for, "Its trace, one entry at a time")}</p>')
    out.append('</article>')
    return "".join(out)


def quote_where(row: dict, place: dict, n: int, who: str) -> str:
    if not place["hits"]:
        if place["across"]:
            return ("This quote is not in any one text the agent read: it runs from the end of one "
                    "result into the start of the next.")
        return "This quote appears in nothing the agent read in this check."
    bits = []
    for hit in place["hits"]:
        call = row["trace"][hit["call"]]
        # A trace's numbered lines are entries (a lookup or an answer); "Lookups" counts only lookups.
        where = a(f"#call-{who}-{hit['call'] + 1}", f"entry {hit['call'] + 1}") + f" of the trace ({e(call['tool'])})"
        page = R.page_of(call)
        extra = ""
        if page and page["kind"] == "wikipedia":
            extra = " · " + a(wiki_url(page["title"]) + text_fragment(place["quote"]),
                              "open the live page", new_tab=True)
        elif page:
            extra = " · " + page_link(page)
        if call["tool"] == "search":
            where += " (a search result's short snippet)"
        bits.append(f"Found in {where}, highlighted below{extra}.")
    return " ".join(bits)


def trace_section(method: str, row: dict, full: bool, toggle: str, heading: str = "h2",
                  title: str | None = None) -> str:
    trace = row["trace"]
    places = R.quote_places(row)
    marks: dict[int, list] = {}
    for n, place in enumerate(places, 1):
        for hit in place["hits"]:
            for span in hit["spans"]:
                marks.setdefault(hit["call"], []).append((span[0], span[1], n))
    pages, seen = [], set()
    for n, call in enumerate(trace):
        page = R.page_of(call)
        if page:
            key = (page["kind"], page["title"], page.get("section"))
            if key not in seen:
                seen.add(key)
                pages.append((n, page))
    title = title or f"The {e(R.method_name(method))}'s trace"
    out = [f'<section class="trace" aria-labelledby="trace-{e(method)}">'
           f'<{heading} id="trace-{e(method)}" tabindex="-1">{title}</{heading}>',
           f'<p>{trace_counts(trace)}</p>']
    if pages:
        out.append('<p class="small">It read these pages, and each link opens the page as it is on Wikipedia today: '
                   + ", ".join(page_link(p) for _, p in pages) + '</p>')
    out.append(f'<p class="small tools-row"><button type="button" class="linkbtn" data-open-all>Open every '
               f'result</button> <button type="button" class="linkbtn" data-close-all>Fold every result</button> '
               f'{a(toggle, "Show this page with every result folded" if full else "Show this page with every result open")}</p>')
    out.append('<ol class="calls">')
    for n, call in enumerate(trace):
        out.append(call_html(call, n, method, marks.get(n, []), full))
    out.append('</ol></section>')
    return "".join(out)


def trace_counts(trace: list) -> str:
    """What the entries were: lookups, lookups refused after the limit, answers, reminders."""
    refused = [R.OUT_OF_STEPS.search(c["result"]) for c in trace]
    refused = [m for m in refused if m]
    answers = sum(1 for c in trace if c["tool"] == "answer")
    reminders = sum(1 for c in trace if c["tool"] == "(reminder)")
    lookups = len(trace) - len(refused) - answers - reminders
    bits = [plural(lookups, "lookup") + " (<code>search</code>, <code>read</code> or <code>wikidata</code>)"]
    if refused:
        bits.append(plural(len(refused), "lookup") + " refused because the agent had already used all "
                    f"{refused[0].group(1)} lookups")
    if answers:
        bits.append(plural(answers, "answer"))
    if reminders:
        bits.append(plural(reminders, "reminder") + " from the loop to call answer()")
    return f'This trace has {plural(len(trace), "entry", "entries")}: ' + and_list(bits) + "."


def call_html(call: dict, n: int, who: str, marks: list, full: bool) -> str:
    tool = call["tool"]
    head = f'<span class="no">{n + 1}.</span> <span class="tool">{e(tool)}</span>'
    body = []
    if tool == "answer":
        inp = call["input"]
        ev = inp.get("evidence") or []
        if isinstance(ev, str):
            ev = [ev]
        body.append(f'<p>Verdict: <strong>{e(inp.get("verdict", "(none)"))}</strong></p>')
        if ev:
            body.append('<p class="small">Evidence:</p><ol class="ev">'
                        + "".join(f"<li>{e(x)}</li>" for x in ev) + '</ol>')
        if inp.get("explanation"):
            body.append(f'<p class="small">Explanation: {e(inp["explanation"])}</p>')
        body.append(f'<p class="came">Came back: <span class="result-inline">{e(call["result"])}</span></p>')
    else:
        head += f' <span class="args">{args_text(call["input"])}</span>'
        page = R.page_of(call)
        if page:
            head += f' <span class="pagelink">{page_link(page)}</span>'
        body.append(result_html(call["result"], marks, full))
    return f'<li class="call" id="call-{e(who)}-{n + 1}"><div class="call-head">{head}</div>{"".join(body)}</li>'


def highlighted(text: str, marks: list) -> str:
    """The text with each quote's place wrapped in <mark>."""
    if not marks:
        return e(text)
    cuts = sorted({0, len(text)} | {s for s, _, _ in marks} | {t for _, t, _ in marks})
    out = []
    for s, t in zip(cuts, cuts[1:]):
        nums = sorted({n for ms, mt, n in marks if ms <= s and t <= mt})
        piece = e(text[s:t])
        if nums:
            label = ",".join(str(x) for x in nums)
            out.append(f'<mark data-q="{label}" title="Quote {label}">{piece}</mark>')
        else:
            out.append(piece)
    return "".join(out)


def result_html(text: str, marks: list, full: bool) -> str:
    size = len(text)
    lines = text.count("\n") + 1
    if size <= FOLD_AT and lines <= 10:
        return f'<pre class="result">{highlighted(text, marks)}</pre>'
    opened = " open" if (full or marks) else ""
    peek = e("\n".join(text[:PEEK].rstrip().splitlines()[:5]))
    note = f'{size:,} characters' + (", with a quote highlighted" if marks else "")
    return (f'<details class="result"{opened}><summary><span class="peek">{peek}…</span> '
            f'<span class="more">Show the whole result ({note})</span>'
            f'<span class="less">Fold this result ({note})</span></summary>'
            f'<pre class="result">{highlighted(text, marks)}</pre></details>')


# ------------------------------------------------------------------ one single check

def check_page(repo: Path, q: dict) -> str:
    path, rel = R.safe_path(repo, q.get("file"))
    if not path.is_file():
        raise Problem(404, "Nothing saved there", f"There is no file at <code>{e(rel)}</code>. "
                      + part_hint(rel, repo))
    row = R.CACHE.get(path, R.load_check)
    if row is None:
        raise Problem(404, "Not a single check", f"<code>{e(rel)}</code> is not a result saved by check.py.")
    row = dict(row)
    method = str(row.get("method") or path.name.rsplit("-", 1)[0])
    claims = R.Claims(repo)
    found = claims.by_text.get(R.norm_claim(row.get("claim", "")))
    full = q.get("full") == "1"
    out = [f'<p class="small">check.py saved this check in <code>{e(rel)}</code> on {when(R.check_time(path))}.</p>']
    if found:
        item, name, _ = found
        item = dict(item)
        row["correct"] = R.RULES.is_correct(item, row["verdict"]) if not row["failed"] else False
        out.append(claim_head(item, True, [("", row)] if method == "agent" else []))
        out.append(f'<p class="small">This claim is in <code>{e(name)}</code>, which gives the label above. '
                   f'{matched_means([item])}</p>')
        card = result_card(method, row, anchor_for=method, nn=noun([item]))
    else:
        out.append(f'<h1 class="claim">{e(row.get("claim", ""))}</h1>')
        out.append('<p class="small">This claim is in no file in <code>data/</code>, so there is no label '
                   'to compare the verdict with.</p>')
        card = result_card(method, row, anchor_for=method, mark=False)
    out.append(f'<div class="cards n1">{card}</div>')
    if row["trace"]:
        out.append(trace_section(method, row, full, toggle=link("/check", file=rel, full="" if full else "1")))
    folder = rel.rsplit("/", 1)[0]
    return shell(row.get("claim", rel)[:60], "".join(out),
                 [a(link("/") + "#" + anchor(folder), e(folder)), e(path.name)])


# ------------------------------------------------------------------ two runs side by side

CHANGE_KINDS = {"": "every change", "now-matched": "does not match in A, matches in B",
                "now-unmatched": "matches in A, does not match in B",
                "both-matched": "verdict changed, matches in both",
                "both-unmatched": "verdict changed, does not match in both"}


def change_kind(ra: dict, rb: dict) -> str | None:
    ca, cb = bool(ra["correct"]), bool(rb["correct"])
    va = "error" if ra["failed"] else ra["verdict"]
    vb = "error" if rb["failed"] else rb["verdict"]
    if ca != cb:
        return "now-matched" if cb else "now-unmatched"
    if va != vb:
        return "both-matched" if ca else "both-unmatched"
    return None


def compare_page(repo: Path, q: dict) -> str:
    evals, _, _ = R.walk_runs(repo)
    evals = sorted(evals, key=R.homework_order)
    ra, rb = q.get("a", ""), q.get("b", "")
    A = load_run(repo, ra) if ra else None
    B = load_run(repo, rb) if rb else None
    if A and B and q.get("id") is not None:
        return compare_claim(A, B, q)
    out = ['<h1>Compare two runs</h1>', picker(evals, A.rel if A else "", B.rel if B else "")]
    if not evals:
        out.append('<p class="empty">No runs yet. The first one you can compare is made in step 1c.</p>')
        return shell("Compare two runs", "".join(out), ["Compare two runs"])
    if not (A and B):
        out.append(suggested(evals, repo))
        return shell("Compare two runs", "".join(out), ["Compare two runs"])
    shared = [m for m in A.methods if m in B.methods]
    only_a = [m for m in A.methods if m not in B.methods]
    only_b = [m for m in B.methods if m not in A.methods]
    out.append(f'<p>A is {a(link("/run", dir=A.rel), "<code>" + e(A.rel) + "</code>")}, made {when(A.started)}. '
               f'B is {a(link("/run", dir=B.rel), "<code>" + e(B.rel) + "</code>")}, made {when(B.started)}. '
               f'{a(link("/compare", a=B.rel, b=A.rel), "Swap A and B")}</p>')
    if A.rel == B.rel:
        out.append('<p class="note">A and B are the same run.</p>')
    for run in (A, B):
        if not run.finished():
            out.append(f'<p class="note"><code>{e(run.rel)}</code> has not finished: its folder has no '
                       '<code>report.txt</code> yet.</p>')
    if "agent" in shared and A.versions_complete and B.versions_complete and \
            len(set(A.versions) | set(B.versions)) == 1:
        out.append(f'<p class="note">A and B used the same version of the agent: the same {AGENT_FILES}.</p>')
    if "agent" in shared and A.limit != B.limit:
        out.append(f'<p class="note">A was made with a limit of {A.limit} lookups per claim, and B with a limit '
                   f'of {B.limit}.</p>')
    for side, ms in (("A", only_a), ("B", only_b)):
        if ms:
            out.append(f'<p class="small">Only run {side} has these versions, so this page does not compare them: '
                       + ", ".join(f"the {e(R.method_name(m))}" for m in ms) + '.</p>')
    if not shared:
        out.append('<p class="empty">These two runs have no version in common, so there is nothing to compare.</p>')
        return shell("Compare two runs", "".join(out), ["Compare two runs"])
    common = {m: [i for i in A.ids if i in A.rows[m] and i in B.rows[m]] for m in shared}
    items = [A.items[i] for m in shared for i in common[m]]
    out.append(f'<p class="small">{matched_means(items)}</p>')
    for m in shared:
        na, nb, nc = len(A.rows[m]), len(B.rows[m]), len(common[m])
        if not (na == nb == nc):
            out.append(f'<p class="note">For the {e(R.method_name(m))}, A has {plural(na, "claim")} and B has '
                       f'{plural(nb, "claim")}. This page compares the {plural(nc, "claim")} both have.</p>')
        else:
            out.append(f'<p class="small">The {e(R.method_name(m))}: both runs have the same '
                       f'{plural(nc, "claim")}.</p>')
    # accuracy
    out.append('<section aria-labelledby="h-cacc"><h2 id="h-cacc">Accuracy</h2>')
    for m in shared:
        sa, sb = R.stats(A, m, common[m]), R.stats(B, m, common[m])
        out.append(accuracy_table([m], {m: sa}, R.group_names(A, common[m]),
                                  f"The {e(R.method_name(m))}: how many verdicts matched {noun(items)}, "
                                  "by the number of articles a claim needs", {m: sb}))
    out.append('</section>')
    # cost
    out.append('<section aria-labelledby="h-ccost"><h2 id="h-ccost">Cost per claim</h2>'
               '<div class="scroll"><table class="grid nums"><caption>Averages over the claims both runs have'
               '</caption><thead><tr><th scope="col">Version</th><th scope="col">Per claim</th><th scope="col">A</th>'
               '<th scope="col">B</th><th scope="col">B minus A</th></tr></thead><tbody>')
    for m in shared:
        sa, sb = R.stats(A, m, common[m]), R.stats(B, m, common[m])
        rows = [("Lookups", "steps", "{:.1f}", 1), ("Tokens", "tokens", "{:,.0f}", 0),
                ("Seconds", "seconds", "{:.1f}", 1), ("Dollars", "cost", "${:.4f}", 4)]
        for k, (label, key, fmt, places) in enumerate(rows):
            head = f'<th scope="rowgroup" rowspan="4">The {e(R.method_name(m))}</th>' if k == 0 else ""
            # The difference of the two numbers as shown, so that the row adds up on the page.
            d = round(round(sb[key], places) - round(sa[key], places), places)
            sign = "+" if d > 0 else ("−" if d < 0 else "")
            dtext = sign + fmt.format(abs(d)) if d else "no change"
            out.append(f'<tr class="{"first" if k == 0 else ""}">{head}<td>{label}</td><td>{fmt.format(sa[key])}</td>'
                       f'<td>{fmt.format(sb[key])}</td><td>{dtext}</td></tr>')
    out.append('</tbody></table></div></section>')
    # changes
    kind_f = q.get("kind", "") if q.get("kind", "") in CHANGE_KINDS else ""
    meth_f = q.get("m", "") if q.get("m", "") in shared else ""
    changes = change_list(A, B, shared, common)
    counts = {k: sum(1 for c in changes if c[2] == k) for k in CHANGE_KINDS if k}
    shown = [c for c in changes if (not kind_f or c[2] == kind_f) and (not meth_f or c[1] == meth_f)]
    out.append('<section aria-labelledby="h-changes"><h2 id="h-changes" tabindex="-1">Claims that changed</h2>')
    out.append(f'<p>A claim is listed when its verdict, or whether it matched {noun(items)}, differs between '
               'A and B.</p><ul class="kinds">' + "".join(
                   f'<li>{a(link("/compare", a=A.rel, b=B.rel, kind=k, m=meth_f) + "#h-changes", CHANGE_KINDS[k])}: '
                   f'{n:,}</li>' for k, n in counts.items()) + '</ul>')
    out.append(f'<form class="filters" method="get" action="{e(link("/compare"))}#h-changes"><div class="row">'
               f'<input type="hidden" name="a" value="{e(A.rel)}"><input type="hidden" name="b" value="{e(B.rel)}">'
               + select("kind", "Change", CHANGE_KINDS, kind_f)
               + (select("m", "Version", {"": "every version", **{m: R.method_name(m) for m in shared}}, meth_f)
                  if len(shared) > 1 else "")
               + '</div><div class="row actions"><button type="submit">Show these claims</button></div></form>')
    out.append(f'<p class="count" role="status">Showing <strong>{len(shown):,}</strong> of '
               f'{plural(len(changes), "change")}.</p>')
    if not shown:
        out.append('<p class="empty">No claims changed in this way.</p>' if changes else
                   '<p class="empty">No claim changed: every shared claim has the same verdict in A and B.</p>')
    else:
        out.append(legend(items))
        out.append('<div class="scroll"><table class="grid claims"><thead><tr><th scope="col" class="num">Row</th>'
                   '<th scope="col">Claim</th><th scope="col">Label</th><th scope="col" class="num">Number of articles</th>'
                   '<th scope="col">Version</th><th scope="col">A</th><th scope="col">B</th>'
                   '<th scope="col">Both traces</th></tr></thead><tbody>')
        for n, (i, m, kind) in enumerate(shown, 1):
            item = A.items[i]
            href = link("/compare", a=A.rel, b=B.rel, id=i, m=m, kind=kind_f, mf=meth_f)
            out.append(f'<tr><td class="num">{n}</td><td class="claimcell">{a(href, e(item["claim"]))}</td>'
                       f'<td class="nowrap">{e(R.label_text(item))}</td>'
                       f'<td class="num">{e(R.hops_text(item))}</td><td class="nowrap">{e(R.method_name(m))}</td>'
                       f'<td class="nowrap">{verdict_cell(A.rows[m][i], noun([item]))}</td>'
                       f'<td class="nowrap">{verdict_cell(B.rows[m][i], noun([item]))}</td>'
                       f'<td class="nowrap">{a(href, "Open A and B")}</td></tr>')
        out.append('</tbody></table></div>')
    out.append('</section>')
    return shell("Compare two runs", "".join(out), ["Compare two runs"])


def suggested(evals: list, repo: Path) -> str:
    """The comparisons the homework asks for, as links when both runs exist."""
    have = set(evals)
    out = ['<p>Pick two runs above. Run A is the one you count from. The homework asks for these '
           'comparisons:</p><ul class="kinds">']
    for ra, rb, step in R.comparisons(repo):
        text = f"Step {step}: <code>{e(ra)}</code> with <code>{e(rb)}</code>"
        if ra in have and rb in have:
            out.append(f'<li>{a(link("/compare", a=ra, b=rb), text)}</li>')
        else:
            missing = " and ".join(f"<code>{e(r)}</code>" for r in (ra, rb) if r not in have)
            out.append(f'<li>{text} <span class="small">({missing} not made yet)</span></li>')
    out.append('</ul>')
    return "".join(out)


def change_list(A, B, shared, common) -> list[tuple]:
    out = []
    for m in shared:
        for i in common[m]:
            kind = change_kind(A.rows[m][i], B.rows[m][i])
            if kind:
                out.append((i, m, kind))
    order = {i: n for n, i in enumerate(A.ids)}
    out.sort(key=lambda c: (order.get(c[0], 0), R.method_key(c[1])))
    return out


def diff_points(ca: int, cb: int, n: int) -> str:
    if not n:
        return ""
    d = 100 * (cb - ca) / n
    if cb == ca:
        return "no change"
    sign = "+" if d > 0 else "−"
    return f"{sign}{abs(d):.1f} points ({sign}{plural(abs(cb - ca), 'claim')})"


def picker(evals: list, ra: str, rb: str) -> str:
    def options(chosen):
        opts = ['<option value="">Pick a run</option>']
        opts += [f'<option value="{e(r)}"{" selected" if r == chosen else ""}>{e(r)}</option>' for r in evals]
        return "".join(opts)
    if not evals:
        return ""
    return (f'<form class="filters" method="get" action="{e(link("/compare"))}"><div class="row">'
            f'<label class="field"><span>Run A</span><select name="a">{options(ra)}</select></label>'
            f'<label class="field"><span>Run B</span><select name="b">{options(rb)}</select></label>'
            '</div><div class="row actions"><button type="submit">Compare</button></div></form>')


def compare_claim(A: R.Run, B: R.Run, q: dict) -> str:
    i = str(q.get("id"))
    m = q.get("m") or ""
    if i not in A.items or i not in B.items:
        raise Problem(404, "No such claim", "That claim is not in both runs.")
    shared = [x for x in A.methods if x in B.methods]
    if m not in shared:
        m = "agent" if "agent" in shared else (shared[0] if shared else "")
    if not m:
        raise Problem(404, "Nothing to compare", "These two runs have no method in common.")
    common = {x: [k for k in A.ids if k in A.rows[x] and k in B.rows[x]] for x in shared}
    kind_f, meth_f = q.get("kind", ""), q.get("mf", "")
    changes = [c for c in change_list(A, B, shared, common)
               if (not kind_f or c[2] == kind_f) and (not meth_f or c[1] == meth_f)]
    back = link("/compare", a=A.rel, b=B.rel, kind=kind_f, m=meth_f) + "#h-changes"
    keys = [(c[0], c[1]) for c in changes]
    if (i, m) in keys:
        k = keys.index((i, m))
        go = lambda c: link("/compare", a=A.rel, b=B.rel, id=c[0], m=c[1], kind=kind_f, mf=meth_f)  # noqa: E731
        prev = go(changes[k - 1]) if k > 0 else None
        nxt = go(changes[k + 1]) if k + 1 < len(changes) else None
        nav = pager(prev, nxt, f"Change {k + 1} of {len(changes):,}", back)
    else:
        nav = pager(None, None, "This claim did not change", back)
    item = A.items[i]
    full = q.get("full") == "1"
    reads = [(side, run.rows["agent"].get(i)) for side, run in (("A", A), ("B", B))] if m == "agent" else []
    out = [nav, claim_head(item, "source" in item, reads), f'<p class="small">{matched_means([item])}</p>']
    out.append(f'<p>The {e(R.method_name(m))} in A (<code>{e(A.rel)}</code>) and in B (<code>{e(B.rel)}</code>).</p>')
    cols = []
    for side, run in (("A", A), ("B", B)):
        row = run.rows[m].get(i)
        who = f"{side.lower()}-{m}"
        card = result_card(m, row, anchor_for=who, title=f"{side}: <code>{e(run.rel)}</code>",
                           nn=noun([item]))
        trace = ""
        if row and row["trace"]:
            trace = trace_section(who, row, full, heading="h3", title=f"{side}'s trace", toggle=link(
                "/compare", a=A.rel, b=B.rel, id=i, m=m, kind=kind_f, mf=meth_f, full="" if full else "1"))
        cols.append(f'<div class="side">{card}{trace}</div>')
    out.append(f'<div class="sides">{"".join(cols)}</div>')
    out.append(nav)
    return shell("Compare one claim", "".join(out),
                 [a(link("/compare", a=A.rel, b=B.rel), "Compare two runs"), "One claim"])


# ------------------------------------------------------------------ /open?path=

def open_page(repo: Path, q: dict) -> str:
    raw = q.get("path", "")
    if not raw or raw.strip().rstrip("/") == "runs":
        return go(link("/"))
    if any(ch in raw for ch in "*?["):
        hits = R.safe_glob(repo, raw)
        if not hits:
            return nothing_yet(raw, repo)
        path, rel = hits[0]
    else:
        path, rel = R.safe_path(repo, raw)
    if not path.exists():
        return nothing_yet(rel, repo)
    root_real = (repo / "runs").resolve()
    if path.is_dir():
        if path == root_real:
            return go(link("/"))
        if R.is_run(path, root_real):
            return go(link("/run", dir=rel))
        return go(link("/") + "#" + anchor(rel))
    if path.name == "lookups.jsonl":
        return go(link("/") + "#" + anchor(rel))
    if path.suffix == ".json" and R.CACHE.get(path, R.load_check) is not None:
        return go(link("/check", file=rel))
    if R.is_run(path.parent, root_real):  # a results file, report.txt or run.json
        return go(link("/run", dir=rel.rsplit("/", 1)[0]))
    part = R.part_of(rel)
    return go(link("/") + (f"#part-{part}" if part is not None else ""))


def go(to: str):
    raise Redirect(to)


def redirect(to: str) -> str:
    """A page that sends the browser on: by script with location.replace (so Back skips it),
    and by a refresh after one second if scripts are off."""
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f'<meta http-equiv="refresh" content="1; url={e(to)}"><title>Opening the results</title></head>'
            f'<body><p><a id="go" href="{e(to)}">Open the results</a></p>'
            f'<script src="{e(link("/static/go.js"))}"></script></body></html>')


def nothing_yet(rel: str, repo: Path) -> str:
    return shell("Nothing saved yet", f'<h1>Nothing saved yet</h1><p>Nothing is saved at <code>{e(rel)}</code> '
                 f'yet. {part_hint(rel, repo)}</p>')
