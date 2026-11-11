# COMP 440 HW3 Part 3 (extra credit): Why the agent fails, and one change

Due 8:00am Tuesday, November 24. Back to the [assignment page](../README.md).

In this part you sort out why the agent fails on your evaluation claims, make one change aimed at the
most common failure, and write up what you found. It should take a little over an hour.

Part 3 is extra credit: the homework is complete when Parts 0 to 2 are done. If you do Part 3, finish it
before you submit. The run after your change takes about 6 minutes more, and it goes on by itself while
you do other things.

## 3a. Sort the failures

In this step you find out why the agent fails on your evaluation claims.

**Words in this step:** A *failure* is one of your evaluation claims where the agent's verdict does not
match the dataset's label, in the full run you started in step 1e. A *trace* is the agent's lookups for one claim, in order, with what each returned. An *entry* is
one numbered line of a trace, a lookup or an answer.

The labels:

- *wrong page*: The agent never found the page that settles the claim.
- *stopped too early*: The agent answered before checking every piece of the claim.
- *misread*: The agent read the right page and drew the wrong conclusion.
- *forced a verdict*: The agent answered *supported* or *refuted* when Wikipedia does not settle the claim.
- *Wikipedia is missing or wrong*: The agent did what it should, and Wikipedia lacks the fact or has it wrong.
- *the dataset's label is wrong*: The agent's verdict is right, and the dataset's label is not.
- If none of these fits, give a label of your own.

**Actions:** You label first, and Claude labels without seeing yours, so that neither set of labels
can steer the other.

1. Start this step's Claude session with the command the homework page shows for 3a, in a terminal tab in the
   homework's folder. If the last step's Claude is still open in that tab, type `/exit` first.
2. Open **Results** at the top of the homework page, then "runs/part2".
3. Click "Clear the filters" under the claims filters.
4. Set "Result" in "The agent" box to "does not match the dataset's label (any reason)"; leave "Order" at
   "Order of the claims file".
5. Take rows 1 to 8. If there are fewer than eight rows, take them all.
6. Click row 1 and read "The agent's trace", one entry at a time.
7. Give it one label from the list above, without telling Claude, and decide whether the dataset's label
   is right.
8. Fill in that claim's row of the table under 3a, then click "Next →" for row 2, and so on to row 8.
9. Ask Claude to label the same claims.
10. Ask Claude to add its labels to the last column, "Claude's label", or type them in yourself.
11. Answer the two questions.

**Output:** The "Row" column counts the rows shown, in the order of your claims file, so rows 1 to 8 are
fixed by the rule. I ask for the first eight so that nobody, you or Claude, chooses which failures get
sorted. Claude finds the same eight in the run's saved files. For "The entry of the trace that shows
it", give the entry's number and a few words of what it shows. For "Is the dataset's label right?",
answer yes, no or can't tell, from what you know about your topics. Claude gives its labels in the chat
without opening `WRITEUP.md`, so it has not seen yours. It labels from the traces alone, and it may give
*the dataset's label is wrong* when the evidence the agent quoted goes against the label. It will not
say which of you is right, and it will not fill in your column about the dataset's label: that is your
judgment, from what you know about your topics.

**Write-up:** In `WRITEUP.md`, under 3a, fill in the table and answer:

- Fill in one row for each of the first eight failures in your full run from 1e, rows 1 to 8 of the claims table for runs/part2 with "Result" in "The agent" box set to "does not match the dataset's label (any reason)". If you have fewer than eight, fill a row for each and delete the rest. Type your labels before you ask Claude for its own. Then ask Claude to add its labels to the last column, or type them in yourself.
- Where did you and Claude disagree, and who do you think is right?
- Which kind of failure was most common? If no kind repeats, say which failure you will aim at in 3b, and why.

**Completion:** The homework page ticks 3a: every numbered row of the table is filled, Claude's
labels included, and both answers have text after the `>`.

**Hint:** The dataset's labels were made by people, from the Wikipedia of 2017, and you may know your
topics better than they did. A label that looks wrong to you is not a mistake in your run: say so in
that row. Claude will not tell you which label to give a trace, because reading the traces is what this
step is about. You ask for its own labels after you have typed yours, so that you can compare the two
readings.

## 3b. Make one change

In this step you make one change aimed at your most common failure. You find out whether it fixes that
failure on your evaluation claims.

**Actions:**

1. Start this step's Claude session with the command the homework page shows for 3b, in a terminal tab in the
   homework's folder. If the last step's Claude is still open in that tab, type `/exit` first.
2. Decide on **one** change aimed at your most common failure from 3a (see the Hint).
3. Make the change in your editor, or tell Claude exactly what to change.
4. Start the run yourself in another terminal tab in the homework's folder, with the first command under
   "Output".
5. Leave that tab open, your laptop awake and your change alone until the run ends with two tables.
6. Open **Results** at the top of the homework page, click "Compare two runs", then "Step 3b:
   runs/part2 with runs/part3/after".
7. Read "Accuracy". Then, under "Claims that changed", set "Change" to "does not match in A, matches in
   B", and then to "matches in A, does not match in B".
8. Answer the three questions.

**Output:** Claude makes exactly the change you describe and shows you what changed. You run
the first command below yourself, on your 100 evaluation claims, the same claims as your full run in 1e.
It takes about 6 minutes and costs about 21 cents on your key. If you adjust your change after seeing
the results, run the second, whose `--fresh` replaces the folder's saved results, since a run never
checks a saved claim again. It costs the same again:

```
uv run python evaluate.py data/eval.jsonl --methods agent --out runs/part3/after
uv run python evaluate.py data/eval.jsonl --methods agent --out runs/part3/after --fresh
```

The comparison sets the agent in your full run, `runs/part2`, beside the agent in this run,
`runs/part3/after`.

The model does not give the same answer every time, so a difference of a few claims between the two
runs can be chance.

**Write-up:** Answer these questions in `WRITEUP.md`, under 3b:

- What did you change, and why did you expect it to help?
- How many of your evaluation claims did the agent match before the change and after it? Which of your eight failures from 3a now match?
- Quote one claim the agent matched before the change and not after it, if there is one, and say what you think happened. If there is none, say so.

**Completion:** The homework page ticks 3b: `runs/part3/after/report.txt` exists, and the three
answers have text after the `>`.

**Troubleshooting:**

- The run stops partway. Run the same command again. It keeps every claim it already finished.
- The run stops at once and says its folder has saved results from an earlier version of your agent.
  You changed `instructions.md`, `agent.py`, `wiki.py` or your loop after the run started. Add `--fresh`
  to the end of the same command to start the run over with the agent as it is now.

**Hint:** The change can be to `instructions.md`, to a tool (for example, what `search` returns, in
`wiki.py`), or to the limit of 12 lookups (in `agent.py`). Leave your loop, `my_loop.py`, as it passed
the check: a loop that breaks one of the six rules is put back on the reference loop the next time the
check runs. Claude will not propose a change, because choosing it is the point of this step. Leave
`instructions.md` alone while a run is going, because the agent reads it again for every claim.

## 3c. Write it up

In this step you say what you learned, in your own words.

**Actions:**

1. Start this step's Claude session with the command the homework page shows for 3c, in a terminal tab in the
   homework's folder. If the last step's Claude is still open in that tab, type `/exit` first.
2. Ask Claude to show you any of your own numbers or results you want to use.
3. Answer the three questions in `WRITEUP.md`, using your own numbers and examples.

**Write-up:** Answer these questions in `WRITEUP.md`, under 3c:

- What does the agent's loop add over one search, what does it cost, and when would you not use an agent for a job like this? Use your numbers from Part 2 and Part 3.
- What did your topics show you about Wikipedia as a source? Where it was thin or wrong, why might that be, given who writes it?
- Your numbers rest on 100 claims about the topics you chose. Which of your conclusions would you trust on another 100 claims, which might be chance, and what would you measure to find out?

**Completion:** The homework page ticks 3c: all three answers have text after the `>`. That
finishes Part 3, so the page commits your work as `Part 3 done` and pushes it to your fork. The page does
not hand your homework in: submit it yourself, as the Submitting section of the README says.

**Hint:** An answer can be as long as you need, but keep it in one block with no blank line inside it,
since a blank line ends the answer. To start a new paragraph, put a line with just `>` between the two.
Claude will not write or suggest a sentence, because the write-up is yours.

## What I look for

Part 3 is extra credit. At a minimum I am looking for the following:

- Failure labels: 35% - Each label in 3a is backed by the entry of the trace that shows it, you say
  whether the dataset's label is right, and you explain where you and Claude disagreed.
- Your change: 30% - Your 3b change targets your most common failure, and you report its effect on
  your evaluation claims and on your eight failures.
- Write-up: 35% - Your 3c answers use your own numbers and examples, the Wikipedia answer goes beyond
  "it was missing" to why, and you say which of your conclusions might be chance.
