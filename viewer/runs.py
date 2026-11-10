"""Reading what is saved in runs/: evaluation folders, single checks, by-hand lookups.

Everything here only reads. A file is parsed once and parsed again only when its size or
modification time changes, so a 200-claim run with full traces is read from disk once.

Paths that come from a request go through safe_path(), which accepts only paths inside the
repository's runs/ folder. The one other place read is the claim files in data/*.jsonl, a fixed
set, because evaluate.py does not save a claim's label or number of articles in its rows.
"""

from __future__ import annotations

import contextlib
import fnmatch
import io
import json
import os
import re
import sys
import threading
import time
from pathlib import Path

METHOD_ORDER = ["no-tools", "one-search", "agent"]
NAMES = {"no-tools": "no-tools baseline", "one-search": "one-search baseline", "agent": "agent"}
VERDICTS = ["supported", "refuted", "doesn't say"]
DEFAULT_MAX_STEPS = 12
OUT_OF_STEPS = re.compile(r"You have used all (\d+) steps")


def method_name(method: str) -> str:
    return NAMES.get(method, method)


def method_key(method: str):
    return (METHOD_ORDER.index(method) if method in METHOD_ORDER else len(METHOD_ORDER), method)


# ------------------------------------------------------------------ the rules, from evaluate.py

class Rules:
    """is_correct() and group_of() from the repository's own evaluate.py, so the numbers here
    are the numbers it prints. If evaluate.py (or agent.py, which it imports) cannot be loaded,
    for example while agent.py is half edited, the copies below are used and `problem` says why."""

    def __init__(self):
        self.lock = threading.Lock()
        self.module = None
        self.problem = None
        self.tried = 0.0

    def get(self):
        with self.lock:
            if self.module is None and time.time() - self.tried > 5:
                self.tried = time.time()
                self.module, self.problem = _import_evaluate()
            return self.module

    def is_correct(self, item, verdict):
        mod = self.get()
        if mod is not None:
            try:
                return bool(mod.is_correct(item, verdict))
            except Exception:  # noqa: BLE001  a student's change to evaluate.py; fall back
                pass
        return _is_correct(item, verdict)

    def group_of(self, item):
        mod = self.get()
        if mod is not None:
            try:
                return mod.group_of(item)
            except Exception:  # noqa: BLE001
                pass
        return _group_of(item)

    def max_steps(self):
        mod = self.get()
        try:
            return int(mod.agent.MAX_STEPS)
        except Exception:  # noqa: BLE001
            return DEFAULT_MAX_STEPS

    def report_text(self, items, results_by_method):
        """What evaluate.py's report() prints for these results, or None."""
        mod = self.get()
        if mod is None:
            return None
        out = io.StringIO()
        try:
            with contextlib.redirect_stdout(out):
                mod.report(items, results_by_method)
        except Exception:  # noqa: BLE001
            return None
        return out.getvalue().strip("\n")


def _import_evaluate():
    """Import evaluate.py from the repository this package sits in, without letting it load
    .env: the viewer has no use for the API key, and importing evaluate.py would otherwise put
    it in this process's environment (the homework page's, when the viewer is mounted there)."""
    root = str(Path(__file__).resolve().parent.parent)
    if root not in sys.path:
        sys.path.insert(0, root)
    try:
        import dotenv
    except Exception:  # noqa: BLE001
        dotenv = None
    real = dotenv.load_dotenv if dotenv else None
    try:
        if dotenv:
            dotenv.load_dotenv = lambda *args, **kwargs: False
        import evaluate
        return evaluate, None
    except BaseException as error:  # noqa: BLE001  a syntax error in agent.py, a missing package
        return None, f"{type(error).__name__}: {error}"
    finally:
        if dotenv:
            dotenv.load_dotenv = real


FEVER = {"SUPPORTS": "supported", "REFUTES": "refuted", "NOT ENOUGH INFO": "doesn't say"}


def _is_correct(item, verdict):  # a copy of evaluate.is_correct, used only if it cannot load
    if verdict is None:
        return False
    if item["source"] == "hover":
        return (verdict == "supported") == (item["label"] == "SUPPORTED")
    if item["source"] == "fever":
        return verdict == FEVER[item["label"]]
    return verdict == item["label"]


def _group_of(item):  # a copy of evaluate.group_of
    if item["source"] == "hover":
        return f"HoVer, {item['hops']} articles"
    if item["source"] == "fever":
        return "FEVER"
    return "Your claims"


RULES = Rules()


def warm_up():
    """Load evaluate.py in the background, so the first page does not wait for it."""
    threading.Thread(target=RULES.get, daemon=True).start()


# ------------------------------------------------------------------ paths

class BadPath(Exception):
    """A path that is not inside runs/."""


def _parts(rel) -> list[str]:
    if not isinstance(rel, str) or not rel.strip() or "\x00" in rel:
        raise BadPath("no path given")
    rel = rel.strip().replace("\\", "/")
    if rel.startswith("/") or rel.startswith("~") or re.match(r"^[A-Za-z]:", rel):
        raise BadPath("an absolute path")
    parts = [p for p in rel.split("/") if p not in ("", ".")]
    if ".." in parts:
        raise BadPath("a path with ..")
    if not parts or parts[0] != "runs":
        raise BadPath("a path outside runs/")
    return parts


def safe_path(repo: Path, rel) -> tuple[Path, str]:
    """(the real path, the tidy relative path) for a path inside repo/runs. Raises BadPath for
    anything else: absolute paths, paths with .., paths outside runs/, and symbolic links that
    lead out of runs/."""
    parts = _parts(rel)
    try:
        runs = (repo / "runs").resolve()
        target = repo.joinpath(*parts).resolve()
    except (OSError, RuntimeError, ValueError) as error:
        raise BadPath(str(error)) from None
    if target != runs and runs not in target.parents:
        raise BadPath("a path outside runs/")
    return target, "/".join(parts)


def safe_glob(repo: Path, pattern) -> list[tuple[Path, str]]:
    """Matches for a pattern such as runs/part0/agent-*.json, newest first, all inside runs/."""
    parts = _parts(pattern)
    runs = repo / "runs"
    if not runs.is_dir():
        return []
    found = []
    for path in runs.glob("/".join(parts[1:]) or "."):
        rel = path.relative_to(repo).as_posix()
        try:
            real, tidy = safe_path(repo, rel)
        except BadPath:
            continue
        if fnmatch.fnmatch(tidy, "/".join(parts)):
            try:
                found.append((real.stat().st_mtime, real, tidy))
            except OSError:
                continue
    found.sort(key=lambda x: -x[0])
    return [(real, tidy) for _, real, tidy in found]


# ------------------------------------------------------------------ cached file reading

class FileCache:
    def __init__(self):
        self.lock = threading.Lock()
        self.entries: dict = {}

    def get(self, path: Path, loader):
        try:
            st = path.stat()
        except OSError:
            return None
        sig = (st.st_mtime_ns, st.st_size)
        key = (str(path), loader.__name__)
        with self.lock:
            hit = self.entries.get(key)
            if hit and hit[0] == sig:
                return hit[1]
        try:
            value = loader(path)
        except OSError:
            return None
        with self.lock:
            self.entries[key] = (sig, value)
        return value


CACHE = FileCache()


def _lines(path: Path):
    """(parsed dicts, number of lines that could not be read). A run that is still going may
    have half a line at the end."""
    rows, bad = [], 0
    text = path.read_bytes().decode("utf-8", "replace")
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            bad += 1
            continue
        if isinstance(row, dict):
            rows.append(row)
        else:
            bad += 1
    return rows, bad


def load_results(path: Path):
    """One method's file in an evaluation folder: {id: tidy row} (a later line for the same id
    replaces an earlier one, as evaluate.py does) and the count of unreadable lines."""
    rows, bad = _lines(path)
    out: dict = {}
    for row in rows:
        if "id" in row:
            out[str(row["id"])] = tidy(row)
    return out, bad


def load_claims(path: Path):
    rows, _ = _lines(path)
    return [r for r in rows if "id" in r and "claim" in r]


def load_check(path: Path):
    try:
        row = json.loads(path.read_bytes().decode("utf-8", "replace"))
    except json.JSONDecodeError:
        return None
    if not isinstance(row, dict) or "verdict" not in row or "trace" not in row:
        return None
    return tidy(row)


def load_lookups(path: Path):
    rows, bad = _lines(path)
    return [r for r in rows if "tool" in r], bad


def _num(x, kind=float):
    try:
        return kind(x)
    except (TypeError, ValueError):
        return kind(0)


def tidy(row: dict) -> dict:
    """A saved result with every field the pages use in a known shape. Older files sometimes
    hold one quote as a plain string, or leave fields out."""
    evidence = row.get("evidence") or []
    if isinstance(evidence, str):
        evidence = [evidence]
    evidence = [str(q) for q in evidence if str(q).strip()]
    tokens = row.get("tokens") if isinstance(row.get("tokens"), dict) else {}
    trace = row.get("trace") if isinstance(row.get("trace"), list) else []
    calls = []
    for step in trace:
        if not isinstance(step, dict):
            continue
        inp = step.get("input") if isinstance(step.get("input"), dict) else {}
        result = step.get("result")
        calls.append({"tool": str(step.get("tool", "?")), "input": inp,
                      "result": result if isinstance(result, str) else json.dumps(result)})
    verdict = row.get("verdict")
    out = dict(row)
    out.update(
        verdict=verdict if isinstance(verdict, str) else None,
        evidence=evidence,
        explanation=str(row.get("explanation") or ""),
        trace=calls,
        steps=_num(row.get("steps"), int),
        tokens={"input": _num(tokens.get("input"), int), "output": _num(tokens.get("output"), int)},
        cost_usd=_num(row.get("cost_usd")),
        seconds=_num(row.get("seconds")),
        failed="error" in row,
    )
    return out


def made_time(path: Path) -> float:
    """When a file was made: its birth time where the system keeps one (macOS does), otherwise
    its last change."""
    try:
        st = path.stat()
    except OSError:
        return 0.0
    return getattr(st, "st_birthtime", None) or st.st_mtime


def file_time(path: Path) -> float:
    try:
        st = path.stat()
    except OSError:
        return 0.0
    return st.st_mtime


# ------------------------------------------------------------------ the claim files in data/

class Claims:
    """Every claim in data/*.jsonl, by id and by claim text."""

    def __init__(self, repo: Path):
        self.files: dict[str, list] = {}
        self.by_id: dict[str, tuple] = {}
        self.by_text: dict[str, tuple] = {}
        data = repo / "data"
        if not data.is_dir():
            return
        for path in sorted(data.glob("*.jsonl")):
            items = CACHE.get(path, load_claims) or []
            name = f"data/{path.name}"
            self.files[name] = items
            for pos, item in enumerate(items):
                self.by_id.setdefault(str(item["id"]), (item, name, pos))
                self.by_text.setdefault(norm_claim(item["claim"]), (item, name, pos))

    def best_file(self, ids) -> tuple[str, int] | None:
        """The smallest claim file that holds every one of these ids: (name, size)."""
        ids = set(ids)
        fits = [(len(items), name) for name, items in self.files.items()
                if ids and ids <= {str(i["id"]) for i in items}]
        return (min(fits)[1], min(fits)[0]) if fits else None


def norm_claim(text) -> str:
    return " ".join(str(text).split()).lower()


# ------------------------------------------------------------------ what one claim's label means

def label_text(item: dict) -> str:
    """The label as the pages show it: supported / not supported for HoVer."""
    label, source = item.get("label"), item.get("source")
    if label is None:
        return "not known"
    if source == "hover":
        return "supported" if label == "SUPPORTED" else "not supported"
    if source == "fever":
        return FEVER.get(label, str(label))
    return str(label)


def hops_text(item: dict) -> str:
    hops = item.get("hops")
    return str(hops) if hops not in (None, "") else ""


def outcome(row: dict | None) -> str:
    """notrun / error / none / correct / wrong."""
    if row is None:
        return "notrun"
    if row["failed"]:
        return "error"
    if row["verdict"] is None:
        return "none"
    return "correct" if row.get("correct") else "wrong"


def used_all_steps(row: dict, max_steps: int) -> bool:
    if row is None:
        return False
    if any(OUT_OF_STEPS.search(c["result"]) for c in row["trace"]):
        return True
    return row["steps"] >= max_steps


# ------------------------------------------------------------------ an evaluation folder

class Run:
    """One evaluation folder: one results file per method."""

    def __init__(self, repo: Path, path: Path, rel: str, claims: Claims):
        self.path, self.rel = path, rel
        self.rows: dict[str, dict] = {}
        self.bad: dict[str, int] = {}
        self.mtime = 0.0
        self.started = float("inf")
        for f in result_files(path, (repo / "runs").resolve()):
            loaded = CACHE.get(f, load_results)
            if loaded is None:
                continue
            method = f.stem
            # Copies, so that filling in "correct" below never changes the cached rows.
            self.rows[method] = {i: dict(r) for i, r in loaded[0].items()}
            self.bad[method] = loaded[1]
            self.mtime = max(self.mtime, file_time(f))
            self.started = min(self.started, made_time(f))
        self.started = self.started if self.rows else 0.0
        self.methods = sorted(self.rows, key=method_key)
        seen: dict[str, None] = {}
        for m in self.methods:
            for i in self.rows[m]:
                seen.setdefault(i, None)
        known = [i for i in seen if i in claims.by_id]
        # Claims in the order of their claim file, as evaluate.py lists them; others after.
        known.sort(key=lambda i: (claims.by_id[i][1], claims.by_id[i][2]))
        self.ids = known + [i for i in seen if i not in claims.by_id]
        self.items: dict[str, dict] = {}
        self.relabelled: dict[tuple, bool] = {}
        for i in self.ids:
            item = dict(claims.by_id[i][0]) if i in claims.by_id else {"id": i}
            for m in self.methods:
                row = self.rows[m].get(i)
                if row:
                    for key in ("label", "source", "hops"):
                        if key in row and row[key] is not None:
                            item.setdefault(key, row[key])
                    if not item.get("claim") and row.get("claim"):
                        item["claim"] = row["claim"]
            item.setdefault("claim", "(the claim text was not saved)")
            self.items[i] = item
        for m in self.methods:
            for i, row in self.rows[m].items():
                item = self.items[i]
                if "correct" not in row or not isinstance(row["correct"], bool):
                    row["correct"] = (RULES.is_correct(item, row["verdict"])
                                      if "label" in item and "source" in item else False)
                elif "label" in item and "source" in item and not row["failed"]:
                    try:
                        now = RULES.is_correct(item, row["verdict"])
                    except Exception:  # noqa: BLE001
                        now = row["correct"]
                    if now != row["correct"]:
                        self.relabelled[(m, i)] = True
        self.file = claims.best_file(self.ids)
        self.position = {i: n for n, i in enumerate(self.ids)}

    def group(self, i: str) -> str:
        item = self.items[i]
        if "source" not in item:
            return "Claims not in data/"
        try:
            return RULES.group_of(item)
        except (KeyError, TypeError):
            return "Claims not in data/"

    def total(self) -> int | None:
        return self.file[1] if self.file else None

    def finished(self) -> bool:
        total = self.total() or len(self.ids)
        return all(len(self.rows[m]) >= total for m in self.methods)

    def recently_changed(self, seconds=120) -> bool:
        return time.time() - self.mtime < seconds


def inside(path: Path, root_real: Path) -> bool:
    try:
        real = path.resolve()
    except (OSError, RuntimeError):
        return False
    return real == root_real or root_real in real.parents


def result_files(folder: Path, root_real: Path) -> list[Path]:
    """The .jsonl files in a folder that hold evaluation results (rows with an id and a
    verdict), not lookups or claims. A symbolic link that leads out of runs/ is skipped."""
    out = []
    try:
        entries = sorted(folder.iterdir())
    except OSError:
        return out
    for f in entries:
        if f.suffix != ".jsonl" or not f.is_file() or f.name == "lookups.jsonl":
            continue
        if not inside(f, root_real):
            continue
        loaded = CACHE.get(f, load_results)
        if loaded is None:
            continue
        rows, _ = loaded
        if rows and all("verdict" in r for r in list(rows.values())[:3]):
            out.append(f)
        elif not rows and f.stem in METHOD_ORDER:  # an empty file a run has just made
            out.append(f)
    return out


def is_run(folder: Path, root_real: Path) -> bool:
    return folder.is_dir() and bool(result_files(folder, root_real))


_RUNS: dict = {}
_RUNS_LOCK = threading.Lock()


def get_run(repo: Path, path: Path, rel: str) -> Run | None:
    """The Run for an evaluation folder, built again only when one of its files, or a claim
    file in data/, has changed."""
    root_real = (repo / "runs").resolve()
    files = result_files(path, root_real)
    if not files:
        return None
    data = sorted((repo / "data").glob("*.jsonl")) if (repo / "data").is_dir() else []
    sig = []
    for f in files + data:
        try:
            st = f.stat()
        except OSError:
            continue
        sig.append((str(f), st.st_mtime_ns, st.st_size))
    key = (str(repo), rel)
    with _RUNS_LOCK:
        hit = _RUNS.get(key)
        if hit and hit[0] == sig:
            return hit[1]
    run = Run(repo, path, rel, Claims(repo))
    with _RUNS_LOCK:
        _RUNS[key] = (sig, run)
    return run


# ------------------------------------------------------------------ statistics

def stats(run: Run, method: str, ids=None) -> dict:
    """Accuracy and cost for one method, over `ids` (default: every claim it has a result for).
    The formulas are evaluate.py's report()."""
    rows_by_id = run.rows[method]
    ids = [i for i in (run.ids if ids is None else ids) if i in rows_by_id]
    rows = [rows_by_id[i] for i in ids]
    n = len(rows)
    groups: dict[str, list] = {}
    for i in ids:
        g = groups.setdefault(run.group(i), [0, 0])
        g[0] += bool(rows_by_id[i]["correct"])
        g[1] += 1
    d = n or 1
    failed = sum(r["failed"] for r in rows)
    max_steps = RULES.max_steps()
    return {
        "n": n,
        "correct": sum(bool(r["correct"]) for r in rows),
        "groups": groups,
        "steps": sum(r["steps"] for r in rows) / d,
        "tokens": sum(r["tokens"]["input"] + r["tokens"]["output"] for r in rows) / d,
        "seconds": sum(r["seconds"] for r in rows) / d,
        "cost": sum(r["cost_usd"] for r in rows) / d,
        "total_in": sum(r["tokens"]["input"] for r in rows),
        "total_out": sum(r["tokens"]["output"] for r in rows),
        "total_seconds": sum(r["seconds"] for r in rows),
        "total_cost": sum(r["cost_usd"] for r in rows),
        "total_steps": sum(r["steps"] for r in rows),
        "failed": failed,
        "no_verdict": sum(r["verdict"] is None for r in rows) - failed,
        "all_steps": sum(used_all_steps(r, max_steps) for r in rows) if method == "agent" else None,
    }


def group_names(run: Run, ids=None) -> list[str]:
    return sorted({run.group(i) for i in (run.ids if ids is None else ids)})


def report_text(run: Run) -> str | None:
    """evaluate.py's own printed report, when every method has a result for the same claims
    and every claim is in data/ (otherwise its report() cannot be called the way it calls it)."""
    if not run.methods or any(set(run.rows[m]) != set(run.ids) for m in run.methods):
        return None
    if any("source" not in run.items[i] for i in run.ids):
        return None
    items = [run.items[i] for i in run.ids]
    results = {m: [run.rows[m][i] for i in run.ids] for m in run.methods}
    return RULES.report_text(items, results)


# ------------------------------------------------------------------ finding everything in runs/

def walk_runs(repo: Path):
    """(evaluation folders, single-check files, lookup files) under runs/, as relative paths."""
    runs = repo / "runs"
    evals, checks, lookups = [], [], []
    if not runs.is_dir():
        return evals, checks, lookups
    root_real = runs.resolve()
    for folder, dirs, files in os.walk(runs, followlinks=False):
        dirs[:] = sorted(d for d in dirs if not d.startswith("."))
        here = Path(folder)
        if not inside(here, root_real):
            continue
        rel = here.relative_to(repo).as_posix()
        if is_run(here, root_real):
            evals.append(rel)
        for name in sorted(files):
            p = here / name
            if not inside(p, root_real):
                continue
            if name == "lookups.jsonl":
                lookups.append(f"{rel}/{name}")
            elif name.endswith(".json") and CACHE.get(p, load_check) is not None:
                checks.append(f"{rel}/{name}")
    return evals, checks, lookups


def check_time(path: Path) -> float:
    """check.py names its files <method>-<seconds since 1970>.json."""
    m = re.search(r"-(\d{9,11})\.json$", path.name)
    return float(m.group(1)) if m else file_time(path)


# ------------------------------------------------------------------ where a quote appears

_SWAP = {"’": "'", "“": '"', "”": '"'}


def normalize(text: str) -> str:
    """agent.py's normalize(): the same text the agent's evidence check compares."""
    for a, b in _SWAP.items():
        text = text.replace(a, b)
    return re.sub(r"\s+", " ", text).strip().lower()


def _norm_with_map(text: str):
    out, where = [], []
    for i, ch in enumerate(text):
        ch = _SWAP.get(ch, ch)
        if ch.isspace():
            if out and out[-1] != " ":
                out.append(" ")
                where.append(i)
            continue
        for c in ch.lower():
            out.append(c)
            where.append(i)
    while out and out[-1] == " ":
        out.pop()
        where.pop()
    return "".join(out), where


def find_spans(text: str, quote: str) -> list[tuple[int, int]]:
    """Where `quote` appears in `text`, compared the way agent.py compares (case, curly quotes
    and runs of spaces ignored), as (start, end) positions in the original text."""
    q = normalize(quote)
    if not q:
        return []
    flat, where = _norm_with_map(text)
    spans, start = [], 0
    while True:
        k = flat.find(q, start)
        if k < 0:
            break
        spans.append((where[k], where[k + len(q) - 1] + 1))
        start = k + 1
    return spans


def quote_places(row: dict) -> list[dict]:
    """For each evidence quote: the trace entries whose result contains it, with positions."""
    places = []
    texts = [(n, c) for n, c in enumerate(row["trace"]) if c["tool"] not in ("answer", "(reminder)")]
    for q in row["evidence"]:
        hits = []
        for n, call in texts:
            spans = find_spans(call["result"], q)
            if spans:
                hits.append({"call": n, "tool": call["tool"], "spans": spans})
        across = False
        if not hits:
            joined = normalize(" ".join(c["result"] for _, c in texts if c["tool"] != "search"))
            across = bool(normalize(q)) and normalize(q) in joined
        places.append({"quote": q, "hits": hits, "across": across})
    return places


# ------------------------------------------------------------------ what a trace entry read

PAGE = re.compile(r"^Page: (.+?)(?:, section: (.+))?$", re.M)
NO_SECTION = re.compile(r"^(.+?) has no section called ")
WIKIDATA = re.compile(r"^Wikidata: .*?\((Q\d+)\)")


def page_of(call: dict) -> dict | None:
    """For a read() or wikidata() entry: the page it read, as {title, section, kind, id}."""
    result = call["result"]
    if call["tool"] == "read":
        first = result.split("\n", 1)[0]
        m = PAGE.match(first)
        if m:
            return {"kind": "wikipedia", "title": m.group(1), "section": m.group(2)}
        m = NO_SECTION.match(first)
        if m:
            return {"kind": "wikipedia", "title": m.group(1), "section": None}
        return None
    if call["tool"] == "wikidata":
        m = WIKIDATA.match(result)
        if m:
            return {"kind": "wikidata", "id": m.group(1),
                    "title": str(call["input"].get("entity", m.group(1)))}
    return None
