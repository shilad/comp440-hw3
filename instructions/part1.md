# COMP 440 HW3 Part 1: How the agent works

Due 8:00am Tuesday, November 24. Back to the [assignment page](../README.md).

In this part you look inside the agent. You read its loop, check two claims yourself with its four
tools, watch it work on 12 claims, write its instructions, and then start the full run on 200 claims
while you predict how it will do. It should take about 2 hours and 10 minutes, plus about 20 minutes for
the full run, which goes on by itself while you do other things.

## 1a. Read the loop

**What you're finding out:** What one turn of the agent's loop does, how the loop ends, and the two
rules the loop enforces that the model cannot override.

**Words in this step:** *the agent*: the program in `agent.py`, a loop in which the model (Claude Haiku,
the small Claude model that the agent and both baselines call) picks the next lookup, reads what comes
back, and decides when to answer. *lookup*: one call to `search`, `read` or `wikidata`; with `answer`,
these are the agent's four tools. In the code, a *tool_use block* is the part of the model's reply that
asks for a tool, and a *tool_result* is what the program sends back to the model.

**What to do:**

1. Start this step's Claude session with the command the homework page shows for 1a, in a terminal tab in the
   homework's folder. If the last step's Claude is still open in that tab, type `/exit` first.
2. Open `agent.py` in your editor. It is about 210 lines.
3. Ask Claude to read `agent.py` with you a screenful at a time, from the top.
4. Ask Claude about any line you don't follow, as often as you like.
5. Find `run_agent()`, which is the loop, and follow one turn of it from start to end.
6. Find the lines that enforce the rule of at most 12 lookups per claim.
7. Find the lines that reject an answer whose quoted sentence is not in anything the agent read.
8. Answer the five questions in `WRITEUP.md`, in your own words, with line numbers.

**What to write:** In `WRITEUP.md`, under 1a:

- What does the program send to the model on each turn of the loop? Give the line numbers.
- What does the program do when the model asks for a tool? Give the line numbers.
- What are the ways the loop can end? Give the line number of each.
- The loop allows at most 12 lookups per claim. What could go wrong without that limit? Give the line numbers where the loop enforces it.
- The loop rejects an answer when a quoted sentence is not in anything the agent read. What could go wrong without that check? Give the line numbers where the loop makes the check.

**You're done when:** The homework page ticks 1a: all five answers have text after the `>`.

**Hint:** The comments and messages in `agent.py` call the model "Claude" and call a lookup a "step".
In this homework, "Claude" means your Claude Code session, and the model is Claude Haiku. In a trace you
may see an answer that was sent back (rejected) before a later one was accepted. That is the loop's
evidence check, which you are reading here: a quoted sentence was not in anything the agent had read,
and text shown in a search result does not count as read.

## 1b. Be the agent

**What you're finding out:** What the agent's job is like, by doing it yourself with only its four
tools, before you watch it.

I'd like you to do this before you watch the agent do it. You'll read its traces much more closely once
you've made the same choices yourself.

Use **only** the agent's tools, not your browser: the point is to see only what the agent sees.
Claim 1 is for learning the tools:

> Mel Duncan holds a history degree from the private, coeducational liberal arts Macalester
> College located in Saint Paul, Minnesota, US.

Claim 2 is the one the questions are about. You have the agent's own limit for it: if you have made 12
lookups without settling it, stop and answer *doesn't say*, as the agent would have to.

> Vic & Anthony's Steakhouse is located at the American casino that was combined with the
> California Club. The casino is owned by Landry's, Inc.

**Words in this step:** *lookup*: one call to `search`, `read` or `wikidata`. *verdict*: *supported*,
*refuted* or *doesn't say*. *evidence*: the sentences quoted from Wikipedia that a verdict rests on.

**What to do:**

1. Start this step's Claude session with the command the homework page shows for 1b, in a terminal tab in the
   homework's folder. If the last step's Claude is still open in that tab, type `/exit` first.
2. Tell Claude you are starting on claim 1.
3. Decide on one lookup: which tool, and what to ask it.
4. Tell Claude that lookup, and read what comes back.
5. Note why you chose that lookup, for the table.
6. Repeat actions 3 to 5 until you have a verdict on claim 1.
7. Tell Claude you are moving on to claim 2, so it knows which claim each lookup was for.
8. Repeat actions 3 to 5 until you have a verdict on claim 2, or have made 12 lookups for it.
9. Ask Claude to paste your lookups into the table under 1b in `WRITEUP.md`.
10. Type your reason for each lookup in the "Why you chose it" column.
11. Answer the four questions under the table.

**What you'll see:** For each lookup, Claude runs one of these and pastes exactly what the agent would
see:

```
uv run python lookup.py search "<query>"
uv run python lookup.py read "<page title>"
uv run python lookup.py read "<page title>" "<section>"
uv run python lookup.py wikidata "<entity>" "<property>"
```

`search` returns the top five page titles, each with a short snippet. `read` returns one section of a
page, or with no section the opening paragraphs and the list of sections. `wikidata` returns one fact
from Wikidata (wikidata.org, a separate site from Wikipedia that stores single facts), for an entity (a
person, a place) and a property ("place of birth", "population"). Each lookup is added to `runs/part1/lookups.jsonl`, which Claude fills the table
from. Claude fills the Claim column from when you told it you moved on to claim 2: check it. Your
verdicts go in `WRITEUP.md`, so there is no `answer` call.

**What to write:** In `WRITEUP.md`, under 1b, fill in the table and answer:

- Your lookups for both claims, in order. Ask Claude to paste every column but the last from `runs/part1/lookups.jsonl`. Type every "Why you chose it" yourself.
- Your verdict on the first claim, and the sentence it rests on.
- Your verdict on the second claim, and the sentence or sentences it rests on. If you stopped at 12 lookups without settling it, your verdict is *doesn't say*: say where you got stuck.
- How many lookups did the second claim take? Which one was hardest to choose, and why?
- Did you have to back up and try something else? What happened?

**You're done when:** The homework page ticks 1b: `runs/part1/lookups.jsonl` exists, every numbered row
of the table has every cell filled, and the four answers have text after the `>`.

**If something goes wrong:**

- A lookup finds no page, or no such section: that is a result like any other, and the agent would have
  seen the same. Count it, and choose your next lookup from what it told you.
- A title with `&` or an apostrophe must be inside double quotes, as in
  `uv run python lookup.py read "<page title>"`, or the shell misreads it. Check Claude's command.

**Hint:** Claude will not suggest a lookup or say what a result means, but it will explain what a tool does or
how to read its output.

## 1c. Watch the agent work

**What you're finding out:** Whether the agent reaches the dataset's label on the 12 development claims,
and whether it gets there for a good reason.

**Words in this step:** *the development claims*: the 12 claims in `data/dev.jsonl`. *the number of
articles*: how many Wikipedia articles a claim needs (2, 3 or 4). *the dataset's label*: the label that HoVer, the public dataset these claims come from, gives
each claim: *supported* or *not supported*. A verdict of *refuted* or *doesn't say* counts as
*not supported*. *trace*: the
agent's lookups for one claim, in order, with what each returned. *entry*: one numbered line of a
trace, a lookup or an answer.

**What to do:**

1. Start this step's Claude session with the command the homework page shows for 1c, in a terminal tab in the
   homework's folder. If the last step's Claude is still open in that tab, type `/exit` first.
2. Ask Claude to run the agent on the 12 development claims.
3. Tell Claude what you expect, when it asks.
4. Read the two tables the run prints at the end.
5. Open **Results** at the top of the homework page, then "runs/part1/before".
6. Choose six claims: two each that need 2, 3 and 4 articles (see the Hint).
7. Make one of the six claim 2 from 1b, the claim about Vic & Anthony's Steakhouse.
8. Click each of the six and read "The agent's trace", one entry at a time.
9. Decide for each whether it got there for a good reason: does its quoted evidence really settle the claim?
10. Fill in one row of the table for each, and answer the question under it.

**What you'll see:** Claude runs this command. It takes about a minute and costs about 2 cents:

```
uv run python evaluate.py data/dev.jsonl --methods agent --out runs/part1/before
```

The first table shows how many claims matched the dataset's label, by number of articles and by the
dataset's label; the second, the average lookups, tokens, seconds and cost per claim. The run is saved
in `runs/part1/before`, "before" the instructions you write in 1d. On a claim's page, each quote under
"Quoted evidence" says "Found in entry N of the trace (read), highlighted below": click "entry N" to see
it.

**What to write:** In `WRITEUP.md`, under 1c, fill in the table and answer:

- The six traces you read closely: two claims each that need 2, 3 and 4 articles. For each number of articles, one the agent got right and one it got wrong, where there is one. One of the six must be claim 2 from 1b.
- Which trace did you find most interesting, and what did the agent do well or badly in it?

**You're done when:** The homework page ticks 1c: `runs/part1/before/report.txt` exists (the run saves
it when it finishes), all six rows are filled, and the answer has text after the `>`.

**If something goes wrong:** If the run stops partway, ask Claude to run the same command again. It
keeps every claim it already finished.

**Hint:** For each number of articles, choose one claim the agent got right and one it got wrong. If
the agent got both right, or both wrong, for a number of articles, use both. In "Claims", set "The number of articles" to "2" (then "3", then "4"), and set "Result" in
"The agent" box to "matches the dataset's label" or "does not match the dataset's label (any reason)".
"Next →" goes to the next claim in the filtered list. To find claim 2 from 1b, type a few of its words
in "Claim contains" and press Enter.

## 1d. Write the agent's instructions

**What you're finding out:** How much the agent's behavior depends on its instructions.

**Words in this step:** *`instructions.md`*: the agent's instructions, which the program sends to the
model (Claude Haiku) on every turn of the loop. It starts with three sentences that name the job, the
four tools and how to finish, and say nothing about how to look things up. *trace*: the agent's lookups for one claim, in order,
with what each returned.

**What to do:**

1. Start this step's Claude session with the command the homework page shows for 1d, in a terminal tab in the
   homework's folder. If the last step's Claude is still open in that tab, type `/exit` first.
2. Write your own instructions in `instructions.md`, in your editor, covering at least the four points
   below, and save.
3. Ask Claude to run the agent on the 12 development claims again.
4. Open **Results** at the top of the homework page and click "Compare two runs".
5. Click "Step 1d: runs/part1/before with runs/part1/after" and read "Accuracy".
6. Under "Claims that changed", click "Open A and B" to read a claim's two traces side by side.
7. Open a few claims whose verdict stayed the same, in each run, to see whether their lookups changed.
8. Each time you change `instructions.md` again, ask Claude to run the same command with `--fresh`.
9. Answer the two questions in `WRITEUP.md`.

At a minimum your instructions must say:

- how to break a claim into the pieces that have to be checked;
- when to use `wikidata` instead of reading a page;
- when the agent has enough evidence to stop;
- when to answer *doesn't say*.

Add to the three sentences already in `instructions.md`, or rewrite them, but keep what they say about
finishing with `answer` and the three verdict words.

**What you'll see:** For the first run with your instructions, Claude runs this command. It takes about
a minute and costs about 2 cents, or more if your instructions make the agent do more:

```
uv run python evaluate.py data/dev.jsonl --methods agent --out runs/part1/after
```

A run never checks a claim again once its result is saved, so after each later change Claude runs the
same command with `--fresh`, which replaces the folder's saved results with a new run:

```
uv run python evaluate.py data/dev.jsonl --methods agent --out runs/part1/after --fresh
```

**What to write:** In `WRITEUP.md`, under 1d:

- What changed in the agent's traces after you wrote your instructions? Give one claim as an example.
- Was that the change you expected? If not, what do you think happened?

**You're done when:** The homework page ticks 1d: `runs/part1/after/report.txt` exists, and both
answers have text after the `>`.

**If something goes wrong:** If the comparison says "A and B used the same version of the agent", your
change to `instructions.md` was not in the second run. Save the file, then ask Claude to run the
command with `--fresh`.

**Hint:** You can do this however you want, but I recommend writing short, direct rules and changing
one thing at a time. It is hard to tell what helped when you change everything at once. The model does
not give the same answer every time, so 12 claims are too few to prove a change helped: read the
traces, not only the score. Claude will not write or suggest text for `instructions.md`, because what
the agent is told is your decision.

## 1e. Start the full run, and predict

**What this step is for:** Starting the run on the 200 evaluation claims, and writing down your
predictions before you see any results.

**Words in this step:** *the three versions*: the no-tools baseline (the model answers from memory), the
one-search baseline (one search, one page, then an answer) and the agent. A version gets a claim right
when its verdict matches *the dataset's label*: the label that HoVer, the public dataset these claims
come from, gives each claim, *supported* or *not supported*. A verdict of *refuted* or *doesn't say*
counts as *not supported*.

**What to do:**

1. Start this step's Claude session with the command the homework page shows for 1e, in a terminal tab in the
   homework's folder. If the last step's Claude is still open in that tab, type `/exit` first.
2. Open another terminal tab and go into the homework's folder (the `comp440-hw3` folder you cloned).
3. Start the full run yourself in that tab, with the command under "What you'll see".
4. Leave that tab open, your laptop awake and `instructions.md` alone until the run ends.
5. Don't read any results until your predictions are saved. The run shows its results only when it ends,
   as two tables; the progress lines before that only count claims. If it ends first, don't look at its tab.
6. Fill in the predictions table under 1e in `WRITEUP.md`.
7. Answer the question under the table.

**What you'll see:** You run this command yourself:

```
uv run python evaluate.py data/eval.jsonl --out runs/part2
```

It takes about 20 minutes and costs about 50 cents on your key, which is charged to my account for the
course, not to you. It runs the no-tools baseline on all 200
claims, then the one-search baseline, then the agent with your `instructions.md` from 1d. It prints a
progress line every ten claims, ends with two tables, and is saved in `runs/part2`.

**What to write:** In `WRITEUP.md`, under 1e, fill in the table and answer:

- Your predictions: the share of claims each version will get right (its verdict matches the dataset's label), as a percentage. A guess is fine; the reasons are what I grade.
- How many lookups will the agent make per claim, on average? Will that grow with the number of articles? Why?

**You're done when:** The homework page ticks 1e: the run has started (`runs/part2/no-tools.jsonl`
exists), every cell of the table's three rows is filled, and the answer has text after the `>`. The run
need not have finished. That finishes Part 1, so the page commits your work as `Part 1 done` and pushes
it to your fork. Once the run has ended, this is a good place to stop for the day.

**If something goes wrong:**

- The run stops (you closed the tab, your laptop slept, or Wikipedia refused requests for too long): run
  the same command again in a terminal tab in the homework's folder. It keeps every claim it already
  finished.
- It stops and says the saved results came from an earlier version of your agent: you changed
  `instructions.md` after the run started. Put it back as it was and run the command again.

**Hint:** Start the run in your own tab, because a run started by Claude stops if you close that Claude
session. Leave `instructions.md` alone while it runs, because the agent reads it again for every claim.
Claude will not suggest a number for your predictions, because they are yours.

## What I look for

Part 1 is 25% of the homework. At a minimum I am looking for the following:

- The loop: 25% - Your answers to 1a say what the loop does in your own words and point to the lines of
  `agent.py`.
- Being the agent: 20% - Your 1b record shows each lookup and why you chose it, and names the hardest
  choice.
- Predictions: 15% - Each prediction in 1e has a reason. They are graded on the reasoning, not on being
  right.
- Instructions: 40% - Your `instructions.md` covers the four points in 1d, and your 1c table and 1d
  answers compare the traces before and after with a specific example.
