# COMP 440 HW3 Part 1: How the agent works

Due 8:00am Tuesday, November 24. Back to the [assignment page](../README.md).

In this part you build and study the agent. You write its loop, check one claim yourself, watch it work
on your 12 development claims, write its instructions, and then start the full run on your 100
evaluation claims. It should take about 3 hours.

## 1a. Write the loop

In this step you write the agent loop yourself. The loop asks the model for lookups, runs the lookups it
chooses, sends back what they return, and stops.

**Words in this step:** *The agent* is the program in `agent.py` and its loop, in which the model
(Claude Haiku, the small Claude model that the agent and both baselines call) picks the next lookup,
reads what comes back, and decides when to answer. A *lookup* is one call to `search`, `read` or
`wikidata`. A *tool* is one of the four things the agent can call: `search`, `read`, `wikidata` and
`answer`. A *tool_use block* is the part of the model's reply that asks for a tool. A *tool_result* is
what your loop sends back to the model for one tool call. *The reference loop* is the loop in
`reference_loop.py`, which your copy uses until yours passes.

This is the one step where you write code. Everything around the loop is written for you; the loop is
yours. Four files are part of this step:

- `agent.py` is given. It holds the four tools, the evidence check (`answer_problem()`), `finish()`, and
  the exact sentences a loop sends. Read it first.
- `my_loop.py` is yours. It has the set-up lines already written, and a line that says where your loop
  goes.
- `reference_loop.py` is a loop I wrote. Your copy's agent uses it until your own loop passes the check,
  so nothing else in the homework waits on this step. Don't open it until your loop passes: reading it
  first shows you a finished loop before you have written your own. Claude cannot open it, so to talk
  about it with Claude, paste the lines you want into the chat.
- `check_loop.py` checks your loop against the six rules below, with a stand-in for the model and for
  Wikipedia. Run it as often as you like: it needs no key and no network, takes a few seconds, and costs
  nothing.

**Actions:**

1. Start this step's Claude session with the command the homework page shows for 1a, in a terminal tab in the
   homework's folder. If the last step's Claude is still open in that tab, type `/exit` first.
2. Open `agent.py` in your editor, and read it with Claude: the four tools, the evidence check and `finish()`.
3. Open `my_loop.py` in your editor.
4. Write the loop below the line that says where it goes, one rule at a time, and save. Remember, Claude
   can help you.
5. After each rule, ask Claude to run the check, or run `uv run python check_loop.py` yourself in a
   terminal in the homework's folder.
6. Fix the first `NOT YET` line, save, and run the check again.
7. When every rule passes, open `reference_loop.py` and compare it with your loop. Don't open it
   before then, because reading it first shows you a finished loop before you have written your own.
8. Answer the three questions in `WRITEUP.md`.

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
   send back `OUT_OF_STEPS`, and remember that you sent it. If the model asks for a lookup again on a later
   turn, stop with no verdict.
6. **Stop when the model stops.** If a reply has no tool call, remind the model with `REMINDER`; if the
   next reply has none either, stop with no verdict. The model is reminded each time it stops calling tools,
   but never twice in a row. If a reply's `stop_reason` is `"refusal"`, stop with no verdict.

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
  and is not run, however many it holds. Keep a variable that says whether `OUT_OF_STEPS` has been sent:
  that is how your loop knows, on a later turn, to stop.
- A trace entry is `{"tool": name, "input": input, "result": result}`. An accepted answer's result is
  `ACCEPTED`. A reminder is recorded as tool `"(reminder)"`, input `{}`, result `REMINDED`.
- The reminder goes to the model as a user turn whose content is the string itself,
  `{"role": "user", "content": REMINDER}`, not as a `tool_result`: the reply it follows has no tool call
  for a result to answer.
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

**Interpreting output:** Claude runs this command, or you run it yourself:

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
NOT YET    5. Enforce the limit: the model's third reply asked for a third search with the limit of 2 lookups reached, and your loop ran it: it had run 2 lookups before that one, and max_steps was 2; in another made-up check the model asked for one search in each of 6 replies, and your loop ran all 6 and never sent back OUT_OF_STEPS.
NOT YET    6. Stop when the model stops: the model's first reply had text and no tool call, and the next request your loop sent did not end with one user turn holding REMINDER ('Please finish by calling answer().').

Not yet. Fix the first NOT YET line, then run this again.
```

To look inside your loop, add `print(...)` lines to it. After its six lines, the check shows what your
loop printed during the made-up check behind the first `NOT YET` line.

When every rule passes, it ends with "Every rule passes. From now on your copy's agent runs on your loop
(my_loop.py)." and saves `runs/part1/loop-check.txt`. From then on, `check.py` and `evaluate.py` start
their output with `Agent loop: yours (my_loop.py)`.

**Write-up:** Answer these questions in `WRITEUP.md`, under 1a:

- What does your loop send to the model on each turn? Give the line numbers in `my_loop.py`.
- What are the ways your loop can end? Give the line number of each.
- Now open `reference_loop.py` and compare it with your loop. Describe one difference in implementation and the resulting effects on agent behavior.

**Completion:** The homework page ticks 1a: the check has passed (it then saves
`runs/part1/loop-check.txt`), or you have chosen the reference loop as below, and the three answers have
text after the `>`.

**Troubleshooting:**

- The check reports an error in your code. Its line names the error and the line of `my_loop.py`. Ask
  Claude what the error means.
- The check says your loop did not stop. It stops a loop that runs for more than a few seconds. Read
  that rule again, and ask Claude what the line means.
- You can't finish your loop and want to move on. That is a real option. Ask Claude to run
  `uv run python check_loop.py --use-reference`, or run it yourself. Your copy keeps using the reference
  loop, and the rest of the homework works exactly as before. You lose the points for the loop itself
  (the first line of "What I look for" below), not the rest of the homework. You can come back to your
  loop at any time: once it passes the check, your copy switches to it. To answer 1a's questions, open
  `reference_loop.py`. Answer the first two about it, with its line numbers, and for the third, say how
  far your own loop got and what stopped you.
- You changed `my_loop.py` after it passed. Run the check again. If it no longer passes, your copy goes
  back to the reference loop until it does.

**Hint:** Write rules 1 to 3 first, then run the check. Claude can help you write the loop: it explains
the API, the tools and Python, reads `my_loop.py` with you, and says what is wrong and why when the
check fails. When you are stuck, it suggests how to fix one part, with a few lines of example code. It
will not write the whole loop for you, because the point is that you write one and know what each part
does. Don't open `reference_loop.py` before your loop passes. Claude cannot open it, but you can paste
lines of it into the chat to talk about them. The code
calls a lookup a "step": `MAX_STEPS` is the limit of 12 lookups, and `OUT_OF_STEPS` tells the model it
has used all its steps.

## 1b. Be the agent

In this step you check one claim yourself, using only the agent's four tools.

The claim you check in this step:

> Vic & Anthony's Steakhouse is located at the American casino that was combined with the
> California Club. The casino is owned by Landry's, Inc.

**Words in this step:** A *lookup* is one call to `search`, `read` or `wikidata`. A *verdict* is one of
*supported*, *refuted* or *doesn't say*. The *evidence* is the sentences quoted from Wikipedia that a
verdict is based on.

**Actions:**

1. Start this step's Claude session with the command the homework page shows for 1b, in a terminal tab in the
   homework's folder. If the last step's Claude is still open in that tab, type `/exit` first.
2. Decide on one lookup: which tool, and what to ask it. Use **only** the agent's tools, not your
   browser, because the point is to see only what the agent sees.
3. Tell Claude that lookup, and read what comes back.
4. Note why you chose that lookup, for the table.
5. Repeat actions 2 to 4 until you have a verdict. You have the agent's own limit: if you have made 12
   lookups without answering the claim, stop and answer *doesn't say*, as the agent would have to.
6. Ask Claude to paste your lookups into the table under 1b in `WRITEUP.md`.
7. Type your reason for each lookup in the "Why you chose it" column.
8. Answer the question under the table.

**Interpreting output:** For each lookup, Claude runs one of these and pastes exactly what the agent would
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
person, a place) and a property ("place of birth", "population"). Each lookup is added to
`runs/part1/lookups.jsonl`, which Claude fills the table from. Your verdict goes in `WRITEUP.md`, so
there is no `answer` call.

**Write-up:** In `WRITEUP.md`, under 1b, fill in the table and answer:

- List your lookups, in order. Ask Claude to paste every column but the last from `runs/part1/lookups.jsonl`. Type "Why you chose it" yourself.
- What is your verdict on the claim, and which sentence or sentences are most important?

**Completion:** The homework page ticks 1b: `runs/part1/lookups.jsonl` exists, every numbered row
of the table has every cell filled, and the answer has text after the `>`.

**Troubleshooting:**

- A lookup finds no page, or no such section. That is a result like any other, and the agent would have
  seen the same. Count it, and choose your next lookup from what it told you.
- A title with `&` or an apostrophe must be inside double quotes, as in
  `uv run python lookup.py read "<page title>"`, or the shell misreads it. Check Claude's command.

**Hint:** Claude will not suggest a lookup or say what a result means, because choosing the lookups is
the agent's job you are doing here. It will explain what a tool does or how to read its output. I ask
you to do this before you watch the agent, because you'll read its traces much more closely once you've
made the same choices yourself.

## 1c. Watch the agent work

In this step you find out whether the agent matches the dataset's label on your 12 development claims.

**Words in this step:** *Your development claims* are the 12 of your claims from step 0b that are in
`data/dev.jsonl`. *The number of articles* is how many Wikipedia articles a claim needs (2, 3 or 4).
*The dataset's label* is the label that HoVer, the public dataset these claims come from, gives each
claim: *supported* or *not supported*. A verdict of *refuted* or *doesn't say* counts as *not
supported*. A *trace* is the agent's lookups for one claim, in order, with what each returned. An
*entry* is one numbered line of a trace, a lookup or an answer.

**Actions:**

1. Start this step's Claude session with the command the homework page shows for 1c, in a terminal tab in the
   homework's folder. If the last step's Claude is still open in that tab, type `/exit` first.
2. Ask Claude to run the agent on your 12 development claims.
3. Read the two tables the run prints at the end.
4. Open **Results** at the top of the homework page, then "runs/part1/before".
5. Choose three claims: one each that needs 2, 3 and 4 Wikipedia articles, where your development claims
   have one (see the Hint).
6. Click each of the three and read "The agent's trace", one entry at a time.
7. Decide for each whether it got there for a good reason: does its quoted evidence really answer the
   claim?
8. Fill in one row of the table for each, and answer the question under it.

**Interpreting output:** Claude runs this command. It takes about a minute and costs about 2 cents:

```
uv run python evaluate.py data/dev.jsonl --methods agent --out runs/part1/before
```

The first table shows how many claims matched the dataset's label, by number of articles and by the
dataset's label; the second, the average lookups, tokens, seconds and cost per claim. The run is saved
in `runs/part1/before`, "before" the instructions you write in 1d. On a claim's page, each quote under
"Quoted evidence" says "Found in entry N of the trace (read), highlighted below": click "entry N" to see
it.

**Write-up:** In `WRITEUP.md`, under 1c, fill in the table and answer:

- List the three traces you read closely. At least one should be a claim the agent got wrong (if it had errors).
- Which trace did you find most interesting, and what did the agent do well or badly in it?

**Completion:** The homework page ticks 1c: `runs/part1/before/report.txt` exists (the run saves
it when it finishes), all three rows are filled, and the answer has text after the `>`.

**Troubleshooting:** If the run stops partway, ask Claude to run the same command again. It
keeps every claim it already finished.

**Hint:** Your claims were selected for your topics, not for their number of articles, so a number may
be missing from your 12. Then choose another claim instead. In "Claims", set "The number of articles" to
"2" (then "3", then "4"), and set "Result" in "The agent" box to "matches the dataset's label" or "does
not match the dataset's label (any reason)". "Next →" goes to the next claim in the filtered list. The
dataset's labels were made by people, from the Wikipedia of 2017, so one may look wrong to you. If it
does, say so in that row: it is not a mistake in your run.

## 1d. Write the agent's instructions

In this step you write the agent's instructions, and see how its traces change.

**Words in this step:** *`instructions.md`* holds the agent's instructions, which the program sends to
the model (Claude Haiku) on every turn of the loop. It starts with three sentences that name the job,
the four tools and how to finish, and say nothing about how to look things up. A *trace* is the agent's
lookups for one claim, in order, with what each returned.

**Actions:**

1. Start this step's Claude session with the command the homework page shows for 1d, in a terminal tab in the
   homework's folder. If the last step's Claude is still open in that tab, type `/exit` first.
2. Write your own instructions in `instructions.md`, in your editor, and save. Add to the three
   sentences already there, or rewrite them, but keep what they say about finishing with `answer` and
   the three verdict words. At a minimum your instructions must say:
   - how to break a claim into the pieces that have to be checked;
   - when to use `wikidata` instead of reading a page;
   - when the agent has enough evidence to stop;
   - when to answer *doesn't say*.
3. Ask Claude to run the agent on your 12 development claims again.
4. Open **Results** at the top of the homework page and click "Compare two runs".
5. Click "Step 1d: runs/part1/before with runs/part1/after" and read "Accuracy".
6. Under "Claims that changed", click "Open A and B" to read a claim's two traces side by side.
7. Answer the question in `WRITEUP.md`.

**Interpreting output:** For the run with your instructions, Claude runs this command. It takes about a
minute and costs about 2 cents, or more if your instructions make the agent do more:

```
uv run python evaluate.py data/dev.jsonl --methods agent --out runs/part1/after
```

It ends with the same two tables as the run in 1c, and "Compare two runs" in the results viewer sets
the two runs side by side.

**Write-up:** Answer this question in `WRITEUP.md`, under 1d:

- What changed in the agent's traces after you wrote your instructions? Give one claim as an example.

**Completion:** The homework page ticks 1d: `runs/part1/after/report.txt` exists, and the answer has
text after the `>`.

**Troubleshooting:**

- The comparison says "A and B used the same version of the agent". Your change to `instructions.md`
  was not in the second run. Save the file, then ask Claude to run the command with `--fresh`.
- You changed `instructions.md` after the run. A run never checks a claim again once its result is
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

In this step you start the run on your 100 evaluation claims.

**Words in this step:** *The three versions* are the no-tools baseline (the model answers from memory),
the one-search baseline (one search, one page, then an answer) and the agent. A version gets a claim
right when its verdict matches *the dataset's label*: the label that HoVer, the public dataset these
claims come from, gives each claim, *supported* or *not supported*. A verdict of *refuted* or *doesn't
say* counts as *not supported*. *Your evaluation claims* are the 100 of your claims from step 0b that
are in `data/eval.jsonl`.

**Actions:**

1. Start this step's Claude session with the command the homework page shows for 1e, in a terminal tab in the
   homework's folder. If the last step's Claude is still open in that tab, type `/exit` first.
2. Open another terminal tab and go into the homework's folder (the `comp440-hw3` folder you cloned).
3. Start the full run yourself in that tab, with this command:
   `uv run python evaluate.py data/eval.jsonl --out runs/part2`.
4. Leave that tab open and your laptop awake until the run ends with two tables.
5. While it runs, fill in the predictions table under 1e in `WRITEUP.md`, and answer the question under
   it.
6. Don't look at the run's results before your predictions are saved. The run shows its results only
   when it ends, as two tables; the progress lines before that only count claims.

**Interpreting output:** The full run takes about 10 minutes and costs about 28 cents on your key, which is charged to my account for the
course, not to you. It runs the no-tools baseline on all 100 of your evaluation claims, then the
one-search baseline, then the agent with your `instructions.md` from 1d. It prints a
progress line every ten claims, ends with two tables, and is saved in `runs/part2`. You read the two
tables in 2a.

**Write-up:** In `WRITEUP.md`, under 1e, fill in the table and answer:

- Predict the share of claims each version will get right (its verdict matches the dataset's label), as a percentage. A guess is fine; the reasons are what I grade.
- How many lookups will the agent make per claim, on average? Will that grow with the number of articles? Why?

**Completion:** The homework page ticks 1e: the run has started (`runs/part2/no-tools.jsonl`
exists), every cell of the table's three rows is filled, and the answer has text after the `>`. The run
need not have finished. That finishes Part 1, so the page commits your work as `Part 1 done` and pushes
it to your fork. Once the run has ended, this is a good place to stop for the day.

**Troubleshooting:**

- The run stops (you closed the tab, your laptop slept, or Wikipedia refused requests for too long). Run
  the same command again in a terminal tab in the homework's folder. It keeps every claim it already
  finished.
- It stops and says the saved results came from an earlier version of your agent. You changed
  `instructions.md` after the run started. Put it back as it was and run the command again.

**Hint:** Start the run in your own tab, because a run started by Claude stops if you close that Claude
session. Leave `instructions.md` alone while it runs, because the agent reads it again for every claim.
Claude will not suggest a number for your predictions, because they are yours.

## What I look for

Part 1 is 35% of the homework. At a minimum I am looking for the following:

- Your loop: 30% - `my_loop.py` passes the check, the conversation shows you wrote it, and your answers
  to 1a point to its lines.
- Being the agent: 20% - Your 1b record shows each lookup and why you chose it, and your verdict names
  the sentences that are most important.
- Predictions: 15% - Each prediction in 1e has a reason. They are graded on the reasoning, not on being
  right.
- Instructions: 35% - Your `instructions.md` covers the four points in 1d, your 1c table says for each
  trace whether the agent got there for a good reason, and your 1d answer compares the traces before and
  after with a specific example.
