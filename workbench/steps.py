"""The assignment: its steps, its write-up slots, and which steps are complete.

An assignment is the `steps.toml` file at the top of the homework's repository. Completion is never
stored: it is read from the student's repository every time, so editing WRITEUP.md by hand, in
any editor, counts the same as Claude writing it. A step is complete when every slot it names is
filled and every file it names exists. A step with neither is complete when Claude marks it done.
"""

from __future__ import annotations

import dataclasses
import re
import subprocess
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

MARKER = "XXXX"
PART = re.compile(r"^## Part (\d+)")
QUOTE_PART = re.compile(r"^#{1,2} Part (\d+)\b")
HEADING = re.compile(r"^### (.+?)\s*$")
BOLD = re.compile(r"^\*\*(.+?):\*\*\s*(.*)$")


@dataclass
class Step:
    id: str
    part: int
    title: str
    body: str = ""            # what the student reads, in Markdown
    brief: str = ""           # what this step's Claude session is told
    slots: list[str] = field(default_factory=list)   # WRITEUP.md slot labels this step fills
    files: list[str] = field(default_factory=list)   # files that must exist (a * matches as in a glob)
    allow: list[str] = field(default_factory=list)   # tool calls that run without asking
    after: list[str] | None = None                   # step ids that must be complete first
    minutes: int | None = None
    page: str | None = None      # or take the body from a Markdown page...
    section: str | None = None   # ...the part under this "## " heading
    summary: str = ""            # a sentence, shown while the step is closed
    goal: str = ""               # what the student is finding out, shown when it is open
    setup: bool = False          # a setup step: its text and checkpoints show as plain steps
    claim: bool = False          # show the assignment's sample claim beside the goal
    # A command the student runs in a terminal tab of their own (a long run), shown in a second
    # box under the Claude command: a table with `command` and `note`.
    run_yourself: dict | None = None
    # What counts: the step's checkpoints, in order, worded as outcomes, not moves. Each is a
    # string, or a table with `text` and the `files` or `slots` that tick it by themselves; one with
    # neither is ticked by Claude, through the page skill, or by any later checkpoint being ticked.
    checkpoints: list = field(default_factory=list)


@dataclass
class Checkpoint:
    text: str
    files: list[str] = field(default_factory=list)
    slots: list[str] = field(default_factory=list)


def run_yourself(s: Step) -> dict | None:
    """The step's own-terminal command as {"command", "note"}, or None."""
    r = s.run_yourself
    if isinstance(r, str):
        r = {"command": r}
    if not isinstance(r, dict) or not str(r.get("command") or "").strip():
        return None
    return {"command": str(r["command"]).strip(), "note": str(r.get("note") or "").strip()}


def checkpoints(s: Step) -> list[Checkpoint]:
    return [Checkpoint(text=c) if isinstance(c, str) else Checkpoint(**c) for c in s.checkpoints]


@dataclass
class Assignment:
    title: str
    writeup: str
    tutor: str
    steps: list[Step]
    parts: dict[int, dict]
    model: str | None = None
    effort: str | None = None
    commit_parts: bool = True
    push: bool = False
    upstream: str | None = None      # the class repository, whose main branch carries updates
    allow: list[str] = field(default_factory=list)
    never_read: list[str] = field(default_factory=list)
    overview: str | None = None
    sample_claim: str = ""
    source: Path | None = None

    def step(self, step_id: str) -> Step:
        """A step by its id ("0.2") or its label ("0b")."""
        for s in self.steps:
            if step_id in (s.id, self.label(s)):
                return s
        raise KeyError(step_id)

    def label(self, s: Step) -> str:
        """What the page calls a step: its part's number and its letter within the part, as 3a.
        A step whose id is already such a name ("0b") keeps it, so the page, the files and the
        write-up's headings always agree."""
        if LABEL.fullmatch(s.id):
            return s.id
        same = [x.id for x in self.steps if x.part == s.part]
        return f"{s.part}{chr(ord('a') + same.index(s.id))}"


LABEL = re.compile(r"\d+[a-z]")
STEP_KEYS = {f.name for f in dataclasses.fields(Step)}


def load(path: Path) -> Assignment:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    parts = {p["number"]: p for p in data.get("part", [])}
    steps = []
    for s in data.get("step", []):
        unknown = sorted(set(s) - STEP_KEYS)
        if unknown:   # a key this version doesn't know is left out, never a reason to stop
            print(f"Note: {path.name}, step {s.get('id')}: ignoring {', '.join(unknown)}")
        steps.append(Step(**{k: v for k, v in s.items() if k in STEP_KEYS}))
    ids = [s.id for s in steps]
    if len(set(ids)) != len(ids):
        raise ValueError(f"{path}: two steps share an id")
    return Assignment(
        title=data["title"],
        writeup=data.get("writeup", "WRITEUP.md"),
        tutor=data.get("tutor", ""),
        steps=steps,
        parts=parts,
        model=data.get("model") or None,
        effort=data.get("effort") or None,
        commit_parts=data.get("commit_parts", True),
        push=data.get("push", False),
        upstream=data.get("upstream") or None,
        allow=data.get("allow", []),
        never_read=data.get("never_read", []),
        overview=data.get("overview") or None,
        sample_claim=data.get("sample_claim", ""),
        source=path,
    )


def intro(text: str | None) -> str:
    """The first paragraph of a page that isn't its title, a quote or its due date: what a part or
    the whole assignment is about, in the brief's own words."""
    for para in (text or "").split("\n\n"):
        para = " ".join(para.split())
        if para and not para.startswith(("#", ">", "Due ", "```", "|", "- ")):
            return para
    return ""


def present(repo: Path, pattern: str) -> list[Path]:
    """The files a step's `files` entry names: one path, or every match of a glob."""
    if any(ch in pattern for ch in "*?["):
        return sorted(repo.glob(pattern))
    return [repo / pattern] if (repo / pattern).exists() else []


def page(a: Assignment, repo: Path, name: str) -> str | None:
    """A Markdown page of the brief, from the repository."""
    f = repo / name
    return f.read_text(encoding="utf-8") if f.is_file() else None


def body(s: Step, a: Assignment, repo: Path) -> str:
    """What the student reads for a step: its own text, or a section of a page."""
    if s.body or not s.page:
        return s.body
    text = page(a, repo, s.page)
    if text is None:
        return f"(The page {s.page} isn't in this repository yet.)"
    if not s.section:
        return text
    out, inside = [], False
    for line in text.splitlines():
        if line.startswith("## "):
            if inside:
                break
            inside = line[3:].strip() == s.section
            continue
        if inside:
            out.append(line)
    return "\n".join(out).strip() or f"(No section \"{s.section}\" in {s.page}.)"


# ---------------------------------------------------------------------------------------------
# WRITEUP.md slots. Two layouts, both used by the course's templates.
#
# Heading layout (HW1, the retrieval activity): a "### Label" heading under "## Part N", whose
# answer is the text up to the next heading, and "**Label:** answer" lines. Blank while it reads
# XXXX.
#
# Quote layout (HW3): "# Part N: Title", then one "## " section per step, whose heading starts
# with the step's name ("## 0b. Ask the model on its own"; older copies say "## Step 2: ...").
# Each question is a paragraph followed by a line that starts with ">"; the answer is what follows
# the ">". A Markdown table is a slot too, filled when every row that isn't empty has every cell
# filled, and so is a fenced block that a paragraph asks Claude to paste into. A slot's key is
# "Part N / <section heading> / <the question>", so `slots = ["0b.*"]` takes every slot of the
# section whose heading starts with "0b.". A file with any ">" line is read in this layout.

QUOTE = re.compile(r"^>\s?(.*)$")
PLAIN = re.compile(r"^(Name|Date):\s*(.*)$")


def read_slots(text: str) -> dict[str, str]:
    """Every slot, keyed "Part N / Label" (or just "Label" above the parts), to its answer."""
    lines = text.splitlines()
    if layout(text) == "quote":
        return read_quote_slots(lines)
    found: dict[str, str] = {}
    part = None
    for i, line in enumerate(lines):
        m = PART.match(line)
        if m:
            part = int(m.group(1))
            continue
        m = HEADING.match(line)
        if m:
            below = []
            for nxt in lines[i + 1:]:
                if nxt.lstrip().startswith("#"):
                    break
                below.append(nxt)
            found[key(part, m.group(1))] = "\n".join(below).strip()
            continue
        m = BOLD.match(line) or PLAIN.match(line)
        if m:
            found[key(part, m.group(1))] = m.group(2).strip()
    return found


def layout(text: str) -> str:
    """"quote" for HW3's layout, "heading" for the older one."""
    return "quote" if any(QUOTE.match(line) for line in text.splitlines()) else "heading"


def cells(row: str) -> list[str]:
    return [c.strip() for c in row.strip().strip("|").split("|")]


def read_quote_slots(lines: list[str]) -> dict[str, str]:
    found: dict[str, str] = {}
    part, section, sub = None, None, None
    para: list[str] = []          # the paragraph just above, which asks the question
    last = None                   # the ">" answer just above, which a paragraph may continue
    i = 0

    def put(label: str, answer: str) -> str:
        trail = [x for x in (section, sub) if x]
        base = " / ".join(trail + [label])
        k, n = key(part, base), 2
        while k in found:
            k, n = key(part, f"{base} ({n})"), n + 1
        found[k] = answer
        return k

    def rest_of_answer() -> None:
        """A paragraph after an answer and a blank line, followed by another paragraph or a
        heading (not by a ">" line, a table or a block), is more of that answer: a student who
        leaves a blank line inside an answer keeps the second paragraph. Only an answer that has
        something in it takes more, so text in the template can never fill a blank answer."""
        text = "\n".join(x for x in para if x).strip()
        if last and found.get(last) and text:
            found[last] += "\n\n" + text

    while i < len(lines):
        line = lines[i]
        m = QUOTE_PART.match(line)
        if m:
            rest_of_answer()
            part, section, sub, para, last = int(m.group(1)), None, None, [], None
            i += 1
            continue
        if line.startswith("## "):
            rest_of_answer()
            section, sub, para, last = line[3:].strip(), None, [], None
            i += 1
            continue
        if line.startswith("### "):
            rest_of_answer()
            sub, para, last = line[4:].strip(), [], None
            i += 1
            continue
        m = PLAIN.match(line) if part is None else None
        if m:
            found[m.group(1)] = m.group(2).strip()
            i += 1
            continue
        if QUOTE.match(line):
            block = []
            while i < len(lines) and QUOTE.match(lines[i]):
                block.append(QUOTE.match(lines[i]).group(1))
                i += 1
            # Markdown's lazy continuation: lines typed straight under a ">" line belong to it.
            while i < len(lines) and lines[i].strip() and not lines[i].startswith(("#", "|", "```")):
                block.append(lines[i])
                i += 1
            last = put(question(para) or "Answer", "\n".join(block).strip())
            para = []
            continue
        if line.lstrip().startswith("|"):
            rows = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                rows.append(cells(lines[i]))
                i += 1
            head, body_rows = rows[0], [r for r in rows[2:] if any(r)]
            done = bool(body_rows) and all(all(c for c in r) for r in body_rows)
            label = question(para) or "Table: " + ", ".join(c for c in head if c and c != "#")
            put(label, "\n".join(" | ".join(r) for r in body_rows) if done else "")
            para, last = [], None
            continue
        if line.startswith("```"):
            inner = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                inner.append(lines[i])
                i += 1
            i += 1
            put(question(para) or "Pasted output", "\n".join(inner).strip())
            para, last = [], None
            continue
        if line.strip():
            if para and para[-1] == "":
                rest_of_answer()   # a new paragraph replaces the one above, which may be more answer
                para = []
            para.append(line.strip())
        elif para and para[-1] != "":
            para.append("")
        i += 1
    rest_of_answer()
    return found


def question(para: list[str]) -> str:
    """The question a slot answers: the last paragraph above it, on one line."""
    return re.sub(r"\s+", " ", " ".join(x for x in para if x)).strip()


def key(part: int | None, label: str) -> str:
    return label if part is None else f"Part {part} / {label}"


def slot_key(step: Step, label: str) -> str:
    """A step names its slots by label alone; a label with a slash is already a full key."""
    if " / " in label or label in ("Name", "Date"):
        return label
    return key(step.part, label)


def step_keys(step: Step, slots: dict[str, str]) -> list[str]:
    """The slot keys a step fills. A label ending in * takes every slot of the step's part that
    starts with it, so `slots = ["0b.*"]` keeps working when a question is reworded."""
    keys: list[str] = []
    for label in step.slots:
        if label.endswith("*"):
            prefix = slot_key(step, label[:-1])
            keys += [k for k in slots if k.startswith(prefix)]
        else:
            keys.append(slot_key(step, label))
    return keys


def filled(answer: str | None) -> bool:
    return bool(answer) and MARKER not in answer


# ---------------------------------------------------------------------------------------------
# Status of every step, read fresh from the repository.

def status(a: Assignment, repo: Path, marked: set[str]) -> list[dict]:
    wp = repo / a.writeup
    slots = read_slots(wp.read_text(encoding="utf-8")) if wp.exists() else {}
    out, done = [], set()
    for i, s in enumerate(a.steps):
        need_slots = step_keys(s, slots)
        slot_state = {k: filled(slots.get(k)) for k in need_slots}
        missing_files = [f for f in s.files if not present(repo, f)]
        if need_slots or s.files:
            complete = all(slot_state.values()) and not missing_files
        else:
            complete = s.id in marked
        before = s.after if s.after is not None else ([a.steps[i - 1].id] if i else [])
        waiting_on = [b for b in before if b not in done]
        if complete:
            done.add(s.id)
        out.append({
            "id": s.id,
            "part": s.part,
            "title": s.title,
            "complete": complete,
            "locked": bool(waiting_on) and not complete,
            "waiting_on": waiting_on,
            "slots": [{"key": k, "filled": v, "answer": slots.get(k, "")} for k, v in slot_state.items()],
            "missing_files": missing_files,
            "manual": not (need_slots or s.files),
        })
    return out


def part_done_commits(repo: Path) -> set[int]:
    """Parts whose "Part N done" commit exists. The whole subject must match."""
    try:
        log = subprocess.run(["git", "log", "--format=%s"], cwd=repo, capture_output=True,
                             text=True, timeout=10).stdout
    except (OSError, subprocess.TimeoutExpired):
        return set()
    return {int(m.group(1)) for line in log.splitlines()
            if (m := re.fullmatch(r"Part (\d+) done", line.strip()))}
