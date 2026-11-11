# The homework page

A local web page for a homework. It lists the steps, ticks the ones that are complete by reading
`WRITEUP.md` and the student's files, and gives each step its own Claude Code session, which the
student starts in a terminal with the command the page shows. Python's standard library only; it
serves this computer only.

## Starting it

In the homework's folder:

```bash
uv run python -m workbench              # opens http://localhost:8450 in the browser
uv run python -m workbench --no-open    # without opening the browser
uv run python -m workbench --port 8460  # look for a free port from 8460
```

It serves the repository it sits in, with that repository's `steps.toml`. If port 8450 is taken
it uses the next free one and prints it (other course tools use 8440). If the page is already
running for this folder, it says where and opens that instead of starting a second one. It needs
Python 3.11 or later; `.python-version` asks `uv` for 3.12.

## What it does by itself

- **Ticks steps.** A step is complete when every slot it names in `WRITEUP.md` is filled and every
  file it names exists, read fresh every time, however the file got there (a run in the
  student's own terminal counts). Steps open in order. A checkpoint with a file or answers of its
  own is ticked only by them. One without (a prediction, say) is ticked by Claude through the
  `page` skill, or by a later checkpoint being reached. One with `tick = false` (reading a trace
  in the results viewer, say: only the student can see it done) shows with no tick, the server
  refuses a tick on it, and nothing waits on it: completion comes from slots and files alone, and
  a step with neither is marked done as a whole. The step being complete ticks nothing.
- **Commits each part.** When every step of Part N is complete, the page writes `TRANSCRIPT.md`
  and `record/`, then commits `Part N done`: everything in the repository that isn't git-ignored
  (`git add -A`), so `instructions.md`, the student's claims, every result under `runs/` and any
  change to the starter code go in. `.gitignore` keeps out `.env`, `.cache/` (Wikipedia's
  answers), `.venv/`, `.workbench/`, `__pycache__/`, `.pytest_cache/`, `.DS_Store` and
  `.claude/settings.local.json`.
- **Commits later changes.** If an answer of a committed part changes, one of its step files is
  added or changed, or one of its steps' conversations grows, the page commits `Part N updated`
  once the files have been still for 30 seconds and those conversations for 2 minutes, so a
  commit never cuts a conversation off and a student who is still typing gets one commit, not
  many. An answer in a required part that isn't committed yet waits for that part's own commit.
  Once every required part is committed, any other change (extra credit at the end of
  `WRITEUP.md`, work on an extra-credit part not yet done, a change to the code) is committed the
  same way, as an update of the latest committed part (`Part 2 updated`, or `Part 3 updated` once
  Part 3 is done); `uv.lock` alone is not a change.
- **Pushes.** With `push = true` in `steps.toml`, every commit the page makes is pushed to
  `origin` (`git push origin HEAD`). A push never asks for a login and never blocks anything. If
  it fails, the commit stays on the laptop, the page says in one sentence that the work is
  committed but not pushed and how to push by hand (`git push`), and it tries again every five
  minutes. It also pushes, at start, commits from before a restart that never reached `origin`.
- **Never commits `uv.lock`.** A student's own `uv` may rewrite it; it is uv's file, not their work.
- **Never commits a key.** A staged file that holds something like `sk-ant-...`, or a file named
  in `never_read`, is left out of the commit (the rest is committed), and the page names the file
  and says to remove the key from it. Once the key is gone, the next commit takes the file.
- **Offers updates.** See below.

## The conversations: TRANSCRIPT.md

Before each commit the page writes every Claude conversation of the homework into `TRANSCRIPT.md`:
each step's session under a heading naming the step (`# 0b. Ask the model with no tools`), in step
order, then any session started in this folder some other way. A step's session id is kept in
`.workbench/state.json`; resuming the session adds to the same conversation. A conversation that
is in the file but no longer on the laptop is kept as it was. `uv run python -m workbench.transcript`
writes the file by hand.

Each conversation uses the format of HW2's `dump_transcript.py`, which the grading tools read
(the `transcript-session` and `end-session` markers, the `## Session` line, the line counting the
student's turns, `**User:**` and `**Claude:**`, one line per tool call starting `- 🔧`). It
differs in four ways: each tool call is followed by the first 12 lines of what it returned, in a
fenced block; a shell call shows its command (up to 200 characters) rather than its description;
parts of one turn are separated by a blank line; and Claude Code's own notes around a slash
command's output are left out. Anything that looks like an API key becomes `[key removed]`.

## What the page showed: record/

Also before each commit, one JSON file per started step in `record/`: which checkpoints were
reached, the student's answers and who last wrote each one (the student, or Claude in which
step's session), what they predicted, asked and ran and what came back, with times, and what
Claude told the page.

## Updates from the class repository

The steps file's `upstream` is the class repository (the environment variable
`WORKBENCH_UPSTREAM` overrides it, for trying the page out without GitHub). At start the page
makes sure a remote named `upstream` points there; it never changes `origin`. If `origin` is the
class repository itself, the student cloned without forking: the page says so, with the command
that points `origin` at their fork, and doesn't push.

At start and about every 30 minutes the page fetches `upstream` quietly (20-second limit; any
failure is silent). When the class repository's `main` has commits the student's branch lacks,
the page lists their subjects with an **Update** button. The button:

1. commits the student's changes as `Save work before update`, so nothing they typed can be lost
   and git never refuses for want of a clean folder;
   (a rewritten `uv.lock` is put back as committed instead);
2. runs `git merge --no-edit upstream/main`;
3. if the merge fails (a real conflict, or an untracked file in the way), runs `git merge --abort`
   where needed, so every file is as it was, and says: the update could not be applied
   automatically, nothing in your files was changed, post in #comp440-f26 on Slack.

After an update the page reads `steps.toml` and the brief's pages again without a restart (it
does this whenever they change). If anything under `workbench/`, `viewer/` or `finder/` changed, it
asks the student to restart the page: Ctrl-C in its terminal, then start it again.

## The results viewer

Pages under `/results` belong to the results viewer in `viewer/`, if it is there:
`viewer.app.handle(method, path, query, repo)` returns `(status, content type, body)`, where
`path` is what follows `/results` (`/results/run` arrives as `/run`; `/results` itself redirects
to `/results/`, which arrives as `/`), `query` is a dict of lists and `repo` a `pathlib.Path`.
When the viewer also has `respond(...)`, which adds a headers dict, the page uses it, so
`/results/open` is a real redirect. Without `viewer/`, `/results` says in one sentence that the
viewer isn't installed. A step whose `files` exist under `runs/` links to
`/results/open?path=<the newest such file of its first files entry that has one>`; there is no
link for files elsewhere (`.env`, `data/my-claims.jsonl`). A step with `hide_results = true` (1e,
which asks the student not to look at the full run's results yet) gets no such link, and its
record lists no files under `runs/`; the "Results" link in the header stays.

## The claim finder

Addresses under `/claims` belong to the claim finder in `finder/`, mounted the same way. Since
Nov 11 no step uses it and the header has no link to it; the routes stay until the instructor
decides whether to delete `finder/`. `finder.web.handle(method, path, query, body, repo)`
returns `(status, content type, body)`, with `body` the bytes of a POST. `/claims` redirects to
`/claims/`. `finder/web.py` lists its addresses; it imports `finder.search` only when a search or
a save arrives, so the page starts without it. Without `finder/`, `/claims` says in one sentence
that the claim finder isn't installed.

## A step's Claude session

The page writes two files per step into the git-ignored `.workbench/` folder, and the step's
command uses them:

```bash
claude -n "0b Ask the model with no tools" --session-id <id> --model claude-opus-5-5 --effort medium \
    --setting-sources user --settings .workbench/0b.json \
    --append-system-prompt-file .workbench/0b.md --plugin-dir .workbench/plugin "Start step 0b."
```

- `0b.md` is the step's prompt: the tutor rules, then this step's text, brief, checkpoints and slots.
- `0b.json` holds the calls the step may make without asking, and the hook (`guard.py`, run by the
  page's own Python) that refuses commits, pushes and anything touching `.env`.
- `--setting-sources user` keeps this repository's `CLAUDE.md` and `.claude/` out, so the prompt
  is the whole brief. `CLAUDE.md` is for a student who starts plain `claude` here: it sends them
  to the page. It is written from `steps.toml` by `uv run python -m workbench.claude_md`; a test
  fails when the two are out of step.
- `--plugin-dir` loads the `page` skill: Claude posts a status line, the student's prediction,
  and the checkpoints it ticks, by running `.workbench/page.py`, which finds the server's port in
  `.workbench/server.json`.
- **Going on in the same session.** Every step after the first also shows a prompt to paste into
  the Claude session the student already has open: `Start step 0c. Read .workbench/0c.md and
  follow it from now on, in place of your instructions for any other step.` The session then
  serves 0c; the tutor rules say so. It keeps the settings it was started with, so every step's
  settings allow every step's `Bash(...)` rules (other rules, such as `Edit(instructions.md)`,
  stay with their own step); the hook is the same file for every step. What is lost: a command
  another step needs no longer asks first (an `evaluate.py` run in Part 0, say), so only the
  briefs keep each step to its own commands.
- **Each step's record follows the step, not the session.** The page reads every conversation
  it started (the session ids in `.workbench/state.json`) and cuts each one at every message that
  starts with "Start step <label>.": a stretch serves that step until the next such message;
  anything before the first serves the step the session was started for. A step's record, its
  state line and its saved `record/` file come from its stretches, wherever they are, and the hook
  log's lines are matched to a stretch by session id and time. A step whose latest stretch is
  followed by another step's says that the session went on to that step. Its terminal command is
  then `claude --resume <that session> ... "Start step <label>. Read ..."`, which reopens the
  conversation and moves it back onto the step; before the step has any stretch, it is the new
  session command. `TRANSCRIPT.md` writes each conversation once, under the step it was started
  for, and gives each other step it served one line saying where. A session the page did not start
  (plain `claude`) is not read for the record.
- Every step's Tasks list begins with how to start the step with Claude (`start_task` in the steps
  file, which a step may reword or leave out); the page ticks it once Claude has started on the
  step. A `stop_task` would end the list, with no tick; HW3 leaves it empty, and the new-session
  box says to type `/exit` first if another session is open in that terminal. Above a step's
  first write-up question the list shows `answers_task`, one sentence on where the answers are
  typed, and an unanswered question then says only "Not written yet."
- `top_note`, one sentence on what happens where (talking with Claude, typing in `WRITEUP.md`),
  shows near the top of the page, under the learning goals.
- The page says nothing under the command about a model that is not available. Step 0a's
  Troubleshooting and the README's "If something goes wrong" do: delete
  `--model claude-opus-5-5 --effort medium` from the command and run the rest of it.

## The steps file

`steps.toml` at the top of the repository. Top-level keys the page reads: `title`, `writeup`,
`tutor`, `model`, `effort`, `commit_parts` (default true), `push` (default false), `upstream`,
`allow`, `never_read`, `overview`, `sample_claim` (any text, quotes included), `start_task`,
`stop_task`, `answers_task`, `top_note`. A checkpoint table may carry `tick = false`. A step's `minutes`
shows in its header as "about 25 minutes". A `files` entry is only ever checked for existence, so
`files = [".env"]` is safe; the page never opens, shows or links to a `never_read` file. Then `[[part]]` tables (`number`, `title`,
`due`, and `extra_credit = true` for a part that isn't required) and `[[step]]` tables. A step's
id is its name on the page (`"0b"`); its section in `WRITEUP.md` starts with that name
(`## 0b. Ask the model to assess a claim without tools`), and `slots = ["0b.*"]` takes every
question, table and pasted block in that section. A key the page doesn't know is ignored, with a
note in the terminal.

A step's `summary` (a sentence or two on what the step is) shows under its title, open or closed,
and opens its Claude session's prompt. A step has no `goal` any more; one in an older steps file
is ignored, with a note. Every step opens the same way: any text of its instruction section that
comes before the first bold label (the repeated summary left out), then Tasks (its checkpoints and
write-up questions, numbered for a step with `setup = true`), then every labeled part of the
section (Words in this step, Actions, Write-up, Hint, and any other label) folded, each opened with
a click. A task's or a question's text may hold `code` spans and
`[links](address)`: an address that starts with `https://`, `http://` or one `/` (a page of the
homework page itself, such as `/claims/`) becomes a link that opens in a new tab, and any other
shows as its words. A part with `extra_credit = true` shows as "Part 3 (extra credit)"; the count
at the top counts only the required steps and says which part is extra credit. Its steps still open
in order and its "Part 3 done" commit is made as for any part.

## Files

| File | What it is |
|---|---|
| `server.py` | The web server, the commits and pushes, the update button, the results mount |
| `steps.py` | Reads `steps.toml` and the `WRITEUP.md` slots; which steps are complete or locked |
| `sessions.py` | Each step's prompt, settings and command; what its session did; the record |
| `transcript.py` | Writes `TRANSCRIPT.md` |
| `updates.py` | The `upstream` remote, the fetch, the merge |
| `claude_md.py` | Writes `CLAUDE.md` from `steps.toml` |
| `labels.py` | A plain label for each tool call ("Ran check.py") |
| `guard.py`, `page.py`, `plugin/` | Copied into `.workbench/`: the hook, and the `page` skill and its script |
| `static/` | The page: HTML, CSS and JavaScript, no build step |

The tests are in `tests/test_workbench.py` (`uv run --frozen pytest -q`): no network, no Claude.
