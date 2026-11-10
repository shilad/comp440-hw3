# COMP 440 HW3 Part 1: How the agent works

Due 8:00am Tuesday, November 24. Back to the [assignment page](../README.md).

In this part you build and study the agent. You write its loop, check two claims yourself with its
four tools, watch it work on 12 claims, write its instructions, and then start the full run on 200
claims while you predict how it will do. It should take about 3 hours and 5 minutes, plus about 20
minutes for the full run, which goes on by itself while you do other things.

## 1a. Write the loop

**What you're finding out:** What an agent is made of, by writing its loop yourself: ask the model, run
the lookups it chooses, send back what they return, and stop.

This is the one step where you write code. Everything around the loop is written for you; the loop is
yours. Four files are part of this step:

- `agent.py` is given. It holds the four tools, the evidence check (`answer_problem()`), `finish()`, and
  the exact sentences a loop sends. Read it first.
- `my_loop.py` is yours. It has the set-up lines already written, and a line that says where your loop
  goes.
- `reference_loop.py` is a loop I wrote. Your copy's agent uses it until your own loop passes the check,
  so nothing else in the homework waits on this step. Don't open it until your loop passes: reading it
  first gives the exercise away. Claude cannot open it at all.
- `check_loop.py` checks your loop against the six rules below, with a stand-in for the model and for
  Wikipedia. Run it as often as you like: it needs no key and no network, takes a few seconds, and costs
  nothing.

**Words in this step:** *the agent*: the program in `agent.py` and its loop, in which the model (Claude
Haiku, the small Claude model that the agent and both baselines call) picks the next lookup, reads what
comes back, and decides when to answer. *lookup*: one call to `search`, `read` or `wikidata`. *tool*: one
of the four things the agent can call: `search`, `read`, `wikidata` and `answer`. *tool_use block*: the
part of the model's reply that asks for a tool. *tool_result*: what your loop sends back to the model for
one tool call. *the reference loop*: the loop in `reference_loop.py`, which your copy uses until yours
passes.

**What to do:**

1. Start this step's Claude session with the command the homework page shows for 1a, in a terminal tab in the
   homework's folder. If the last step's Claude is still open in that tab, type `/exit` first.
2. Open `agent.py` in your editor, and read it with Claude: the four tools, the evidence check and `finish()`.
3. Open `my_loop.py` in your editor.
4. Write the loop below the line that says where it goes, one rule at a time, and save.
5. After each rule, ask Claude to run the check, or run it yourself in a terminal in the homework's folder.
6. Fix the first `NOT YET` line, save, and run the check again.
7. When every rule passes, open `reference_loop.py` and compare it with your loop.
8. Answer the four questions in `WRITEUP.md`.

**The six rules:**

1. **Ask the model.** Each turn, send the model the system text, the tools and the whole conversation so
   far. Add the tokens the reply used to `tokens`, and add the reply to the conversation as the assistant's
   turn.
2. **Run its lookups.** For each lookup the reply asks for, call `lookup(name, input)`, add 1 to `steps`,
   and add an entry to `trace`. Keep what `read` and `wikidata` return in `read_so_far`; do not keep what
   `search` returns.
3. **Send the results back.** After the reply's tool calls are handled, add one user turn to the
   conversation that holds a result for every call, each marked with the id of the call it answers.
4. **Check the answer.** When the reply calls `answer`, check it with `answer_problem()`. If there is no
   problem, stop and return `finish(...)` with the answer's verdict, evidence and explanation. If there is
   a problem, send back `REJECTED` followed by the problem, and after `MAX_REJECTED` rejected answers stop
   with no verdict.
5. **Enforce the limit.** Once `steps` has reached `max_steps`, do not run another lookup. The first time,
   send back `OUT_OF_STEPS`. If the model asks for a lookup again on a later turn, stop with no verdict.
6. **Stop when the model stops.** If a reply has no tool call, remind the model once with `REMINDER`; if
   the next reply has none either, stop with no verdict. If a reply's `stop_reason` is `"refusal"`, stop
   with no verdict.

**What the code gives you** (the details the rules and the check rely on):

- The call is `client.messages.create(model=MODEL, max_tokens=16000, system=system, tools=TOOLS,
  messages=messages)`.
- The reply has `.content` (a list of blocks), `.stop_reason` and `.usage` (`.input_tokens`,
  `.output_tokens`). A tool call is a block with `.type == "tool_use"`, `.name`, `.input` and `.id`.
  It is an object, not a dictionary, so read its parts with a dot, as in `call.name`. One reply can
  hold several tool calls, and every one of them needs a result.
- A turn of the conversation is a dictionary with a `"role"` (`"user"` or `"assistant"`) and a
  `"content"`, like the first one in `my_loop.py`. The content can be a string or a list. For the
  assistant's turn, the content is the reply's `.content`, just as it came back.
- A result sent back is `{"type": "tool_result", "tool_use_id": call.id, "content": result}`.
  Every tool call gets one in the next user turn, whatever happened to it: what a lookup returned,
  `REJECTED` followed by the problem for an answer that is sent back, or `OUT_OF_STEPS` for a lookup
  refused at the limit.
- In rule 5, "the first time" is the first reply that asks for a lookup when `steps` has already
  reached `max_steps`. Each lookup in that reply gets `OUT_OF_STEPS.format(n=max_steps)` as its result
  and is not run.
- A trace entry is `{"tool": name, "input": input, "result": result}`. An accepted answer's result is
  `ACCEPTED`. A reminder is recorded as tool `"(reminder)"`, input `{}`, result `REMINDED`.
- Every tool call gets one entry in `trace`, with the result it was given: what a lookup returned,
  `ACCEPTED`, `REJECTED` followed by the problem, or `OUT_OF_STEPS`. The results viewer numbers these
  entries, so a loop that records only lookups shows wrong traces. The one exception is a lookup the
  model asks for after `OUT_OF_STEPS` has been sent: the loop stops there, and that lookup needs no
  entry.
- The answer is cleaned first: `answer = clean_answer(call.input)`.
- `finish(claim, verdict, evidence, explanation, trace, tokens, steps)` makes what the loop returns.
  "Stop with no verdict" means `return finish(claim, None, [], why, trace, tokens, steps)`, where `why` is
  `REJECTED_TOO_OFTEN.format(n=rejected)`, `RAN_OUT`, `NO_ANSWER` or `DECLINED`. Stopping always means
  `return`: a `break` leaves only the innermost loop.
- `REJECTED`, `OUT_OF_STEPS`, `REMINDER` and the other sentences are in `agent.py`. `OUT_OF_STEPS` and
  `REJECTED_TOO_OFTEN` have a `{n}` to fill in with `.format(n=...)`.

**What you'll see:** Claude runs this command, or you run it yourself:

```
uv run python check_loop.py
```

It prints one line for each rule, `ok` or `NOT YET`. A `NOT YET` line says what the stand-in model did
and what your loop did or failed to do; it does not say how to fix it. Until you start, all six lines say
"the loop is not written yet". A run partway through looks like this:

```
ok         1. Ask the model
ok         2. Run its lookups
ok         3. Send the results back
NOT YET    4. Check the answer: the model's second reply gave an answer that quotes the page it had read, and your loop called lookup() for it.
NOT YET    5. Enforce the limit: the model's third reply asked for a third search with the limit of 2 lookups reached, and your loop ran it.
NOT YET    6. Stop when the model stops: the model's first reply had text and no tool call, and the next request your loop sent did not end with one user turn holding REMINDER ('Please finish by calling answer().').

Not yet. Fix the first NOT YET line, then run this again.
```

To look inside your loop, add `print(...)` lines to it. After its six lines, the check shows what your
loop printed during the made-up check behind the first `NOT YET` line.

When every rule passes, it ends with "Every rule passes. From now on your copy's agent runs on your loop
(my_loop.py)." and saves `runs/part1/loop-check.txt`. From then on, `check.py` and `evaluate.py` start
their output with `Agent loop: yours (my_loop.py)`.

**What to write:** In `WRITEUP.md`, under 1a:

- What does your loop send to the model on each turn? Give the line numbers in `my_loop.py`.
- What are the ways your loop can end? Give the line number of each.
- Which rule took you longest to get right, and what was wrong with your first try?
- Now open `reference_loop.py` and compare it with your loop. Name one difference, and say whether it changes what the agent does. (If you used `--use-reference`, say how far your own loop got and what stopped you.)

**You're done when:** The homework page ticks 1a: the check has passed (it then saves
`runs/part1/loop-check.txt`), or you have chosen the reference loop as below, and the four answers have
text after the `>`.

**If something goes wrong:**

- The check reports an error in your code: its line names the error and the line of `my_loop.py`. Ask
  Claude what the error means.
- The check says your loop did not stop: it stops a loop that runs for more than a few seconds. Read
  that rule again, and ask Claude what the line means.
- You can't finish your loop and want to move on. That is a real option. Ask Claude to run
  `uv run python check_loop.py --use-reference`, or run it yourself. Your copy keeps using the reference
  loop, and the rest of the homework works exactly as before. You lose the points for the loop itself
  (the first line of "What I look for" below), not the rest of the homework. You can come back to your
  loop at any time: once it passes the check, your copy switches to it.
- You changed `my_loop.py` after it passed: run the check again. If it no longer passes, your copy goes
  back to the reference loop until it does.

**Hint:** Write rules 1 to 3 first, then run the check. Claude explains the API, Python and what a
`NOT YET` line means as often as you ask, and will not write or correct your code: the loop is yours.
Don't open `reference_loop.py` before your loop passes, and Claude cannot open it at all. The code calls
a lookup a "step": `MAX_STEPS` is the limit of 12 lookups, and `OUT_OF_STEPS` tells the model it has used
all its steps.

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
6. Choose three claims: one each that needs 2, 3 and 4 articles (see the Hint).
7. Make the one that needs 3 claim 2 from 1b, the claim about Vic & Anthony's Steakhouse.
8. Click each of the three and read "The agent's trace", one entry at a time.
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

- The three traces you read closely: one claim each that needs 2, 3 and 4 articles, with claim 2 from 1b as the one that needs 3. At least one is a claim the agent got wrong, where there is one.
- Which trace did you find most interesting, and what did the agent do well or badly in it?

**You're done when:** The homework page ticks 1c: `runs/part1/before/report.txt` exists (the run saves
it when it finishes), all three rows are filled, and the answer has text after the `>`.

**If something goes wrong:** If the run stops partway, ask Claude to run the same command again. It
keeps every claim it already finished.

**Hint:** Choose the claims that need 2 and 4 articles so that at least one of your three is a claim the
agent got wrong, where there is one. In "Claims", set "The number of articles" to "2" (then "3", then "4"), and set "Result" in
"The agent" box to "matches the dataset's label" or "does not match the dataset's label (any reason)".
"Next →" goes to the next claim in the filtered list. To find claim 2 from 1b, type a few of its words
in "Claim contains" and press Enter. The dataset's labels were made by people, from the Wikipedia of
2017, so one may look wrong to you. If it does, say so in that row: it is not a mistake in your run.

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
8. Answer the two questions in `WRITEUP.md`.

At a minimum your instructions must say:

- how to break a claim into the pieces that have to be checked;
- when to use `wikidata` instead of reading a page;
- when the agent has enough evidence to stop;
- when to answer *doesn't say*.

Add to the three sentences already in `instructions.md`, or rewrite them, but keep what they say about
finishing with `answer` and the three verdict words.

**What you'll see:** For the run with your instructions, Claude runs this command. It takes about a
minute and costs about 2 cents, or more if your instructions make the agent do more:

```
uv run python evaluate.py data/dev.jsonl --methods agent --out runs/part1/after
```

**What to write:** In `WRITEUP.md`, under 1d:

- What changed in the agent's traces after you wrote your instructions? Give one claim as an example.
- Was that the change you expected? If not, what do you think happened?

**You're done when:** The homework page ticks 1d: `runs/part1/after/report.txt` exists, and both
answers have text after the `>`.

**If something goes wrong:**

- The comparison says "A and B used the same version of the agent": your change to `instructions.md`
  was not in the second run. Save the file, then ask Claude to run the command with `--fresh`.
- You changed `instructions.md` after the run: a run never checks a claim again once its result is
  saved, so ask Claude to run the same command with `--fresh` at the end, which replaces this folder's
  saved results with a new run:

  ```
  uv run python evaluate.py data/dev.jsonl --methods agent --out runs/part1/after --fresh
  ```

**Hint:** You can do this however you want, but I recommend writing short, direct rules. The model does
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

- Your loop: 30% - `my_loop.py` passes the check, the conversation shows it is your own work, and your
  answers to 1a point to its lines.
- Being the agent: 20% - Your 1b record shows each lookup and why you chose it, and names the hardest
  choice.
- Predictions: 15% - Each prediction in 1e has a reason. They are graded on the reasoning, not on being
  right.
- Instructions: 35% - Your `instructions.md` covers the four points in 1d, and your 1c table and 1d
  answers compare the traces before and after with a specific example.
