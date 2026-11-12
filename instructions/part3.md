# COMP 440 HW3 Part 3 (extra credit): Why the agent fails, and one change

In this part you sort out why the agent fails on your evaluation claims, make one change aimed at the
most common failure, and write up what you found. It should take about an hour and 20 minutes.

Part 3 is extra credit: the homework is complete when Parts 0 to 2 are done. If you do Part 3, finish it
before you submit.

Back to the [assignment page](../README.md).

## 3a. Sort the failures

In this step you find out why the agent fails on your evaluation claims.

**Words in this step:** A *failure* is a claim where the agent's verdict, in your full run from 1e, does
not match the dataset's label.

**Actions:**

1. Start this step with Claude: paste its prompt from the homework page into the Claude session you
   have open, or start a new session with its command (type `/exit` first if another session is
   open in that terminal).
2. Open **Results** at the top of the homework page, then "runs/part2".
3. Click "Clear the filters", then set "Result" in "The agent" box to "does not match the dataset's label
   (any reason)"; leave "Order" at "Order of the claims file".
4. Click row 1 and read "The agent's trace", one entry at a time.
5. Give it one of these labels, without telling Claude, and decide whether the dataset's label is right:
   - *wrong page*: The agent never found the page that settles the claim.
   - *stopped too early*: The agent answered before checking every piece of the claim.
   - *misread*: The agent read the right page and drew the wrong conclusion.
   - *forced a verdict*: The agent answered *supported* or *refuted* when Wikipedia does not settle the claim.
   - *Wikipedia is missing or wrong*: The agent did what it should, and Wikipedia lacks the fact or has it wrong.
   - *the dataset's label is wrong*: The agent's verdict is right, and the dataset's label is not.
   - If none of these fits, give a label of your own.
6. Fill in its row of the table in `WRITEUP.md`, in your editor, under 3a. In the results viewer, click
   "Next →" and do the same for each row up to row 8.
7. Ask Claude to label the same claims. It gives its labels without seeing yours.
8. Ask Claude to add its labels to the "Claude's label" column, or type them in yourself, in your editor.
9. Type your answers to the two questions in `WRITEUP.md`, in your editor, under 3a.

**Interpreting output:** Claude labels from the traces alone, and may give *the dataset's label is
wrong* when the evidence the agent quoted goes against the label. It will not tell you which label to
give a trace, or say which of you is right.

**Write-up:** In `WRITEUP.md`, under 3a, fill in the table and answer:

- Fill in one row for each of the first eight failures in your full run from 1e, rows 1 to 8 of the claims table for runs/part2 with "Result" in "The agent" box set to "does not match the dataset's label (any reason)". If you have fewer than eight, fill a row for each and delete the rest. Type your labels before you ask Claude for its own. Then ask Claude to add its labels to the last column, or type them in yourself.
- Where did you and Claude disagree, and who do you think is right?
- Which kind of failure was most common? If no kind repeats, say which failure you will aim at in 3b, and why.

**Hint:** For "The entry of the trace that shows it", give the entry's number and a few words of what it
shows. For "Is the dataset's label right?", go by what you know: people made the dataset's labels from
the Wikipedia of 2017, and you may know a claim's subject better than they did.

## 3b. Make one change

In this step you make one change aimed at your most common failure. You find out whether it fixes that
failure on your evaluation claims.

**Words in this step:** A *token* is the unit the Claude API counts text in and charges by, about
three quarters of a word.

**Actions:**

1. Start this step with Claude: paste its prompt from the homework page into the Claude session you
   have open, or start a new session with its command (type `/exit` first if another session is
   open in that terminal).
2. First, make your loop count tokens, so that the run after your change shows what it cost. In
   `my_loop.py`, add `tokens = {"input": 0, "output": 0}` to the set-up lines. After each call to the
   model, add the reply's `.usage.input_tokens` to `tokens["input"]` and its `.usage.output_tokens` to
   `tokens["output"]`. Pass `tokens` to every `finish(...)` as its last argument. Do this in your
   editor, or describe it to Claude.
3. Ask Claude to run the check. Its last line, "Count the tokens (extra credit)", must say `ok`, like
   the six rules above it.
4. Decide on **one** change aimed at your most common failure from 3a (see the Hint).
5. Make the change in your editor, or tell Claude exactly what to change.
6. Start the run yourself, in another terminal tab in the homework's folder:
   `uv run python evaluate.py data/eval.jsonl --methods agent --out runs/part3/after`.
7. Leave that tab open, your laptop awake and your change alone until the run ends with two tables.
8. Open **Results** at the top of the homework page, click "Compare two runs", then "Step 3b:
   runs/part2 with runs/part3/after".
9. Read "Accuracy". Then, under "Claims that changed", set "Change" to "does not match in A, matches in
   B", and then to "matches in A, does not match in B".
10. Type your answers to the three questions in `WRITEUP.md`, in your editor, under 3b.

**Interpreting output:** Once the check's last line says `ok`, `check.py`, `evaluate.py` and the results
viewer show tokens and cost for every run, the baselines' in `runs/part2` too; the agent's results saved
before that say "not counted". The run takes about 6 minutes and costs about 21 cents on your key. In the
comparison, A is your full run, `runs/part2`, and B is this run, `runs/part3/after`. The model does not
give the same answer every time, so a difference of a few claims between the two runs can be chance.

**Write-up:** Answer these questions in `WRITEUP.md`, under 3b:

- What did you change, and why did you expect it to help?
- How many of your evaluation claims did the agent match before the change and after it? Which of your eight failures from 3a now match?
- Quote one claim the agent matched before the change and not after it, if there is one, and say what you think happened. If there is none, say so.

**Troubleshooting:**

- The check has no line "Count the tokens (extra credit)": your loop passes no count to `finish()` yet.
  Pass `tokens` as the last argument of every `finish(...)`.
- That line says `NOT YET`: the count your loop passed to `finish()` is not what the model's replies
  used, and its sentence says where. Until it says `ok`, no agent run starts.
- The run stops partway. Run the same command again; it keeps every claim it already finished.
- The run says its folder has saved results from an earlier version of your agent: you changed
  `instructions.md`, `agent.py`, `wiki.py` or your loop since it started. To start over with the agent
  as it is now, for the same time and cost again, run
  `uv run python evaluate.py data/eval.jsonl --methods agent --out runs/part3/after --fresh`.

**Hint:** The change can be to `instructions.md`, to a tool (for example, what `search` returns, in
`wiki.py`), or to the limit of 12 lookups (in `agent.py`). Apart from the token count, leave your loop,
`my_loop.py`, as it passed the check: once a line of the check says `NOT YET`, no agent run starts until
your loop passes again. Claude will not propose a change, because the choice is yours.

## 3c. Write it up

In this step you say what you learned, in your own words.

**Actions:**

1. Start this step with Claude: paste its prompt from the homework page into the Claude session you
   have open, or start a new session with its command (type `/exit` first if another session is
   open in that terminal).
2. Ask Claude to show you any of your numbers or results.
3. Type your answers to the three questions in `WRITEUP.md`, in your editor, under 3c.

**Write-up:** Answer these questions in `WRITEUP.md`, under 3c:

- What does the agent's loop add over one search, what does it cost, and when would you not use an agent for a job like this? Use your numbers from Part 2 and Part 3.
- What did your claims show you about Wikipedia as a source? Where it was thin or wrong, why might that be, given who writes it?
- Your numbers rest on 100 claims. Which of your conclusions would you trust on another 100 claims, which might be chance, and what would you measure to find out?

**Hint:** The agent's cost per claim is under "Cost" for `runs/part3/after` in the results viewer, and
the one-search baseline's is under "Cost" for `runs/part2`. Keep each answer free of blank lines, since
a blank line ends it. To start a new paragraph,
put a line with just `>` between the two. Claude will not write or suggest a sentence, because the
write-up is yours. The page does not submit your homework: submit it yourself, as the README's
Submitting section says.

## What I look for

Part 3 is extra credit. At a minimum I am looking for the following:

- Failure labels: 35% - Each label in 3a is backed by the entry of the trace that shows it, you say
  whether the dataset's label is right, and you explain where you and Claude disagreed.
- Your change: 30% - Your 3b change targets your most common failure, and you report its effect on
  your evaluation claims and on your eight failures.
- Write-up: 35% - Your 3c answers use your own numbers and examples, the Wikipedia answer goes beyond
  "it was missing" to why, and you say which of your conclusions might be chance.
