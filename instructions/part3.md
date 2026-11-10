# COMP 440 HW3 Part 3: Your own claims

Due 8:00am Tuesday, November 24. Back to the [assignment page](../README.md).

In this part you test the agent on a topic you know better than most people. You write your own claims,
run the agent on them, sort out why it fails, make one change, and write up what you found. It should
take about 1 hour and 50 minutes.

## 3a. Pick a topic and write your claims

In this step you build your own set of test claims, on a topic you know better than most people.

**Words in this step:** *claim*: one sentence that is either true or false. *your verdict*:
*supported* if the claim is true and *refuted* if it is false, according to the source you trust, not
what you think Wikipedia says.

**Actions:**

1. Start this step's Claude session with the command the homework page shows for 3a, in a terminal tab in the
   homework's folder. If the last step's Claude is still open in that tab, type `/exit` first.
2. Pick a topic you know well and that Wikipedia covers at least a little.
3. Use your browser to read what Wikipedia says on your topic. That is allowed in this step.
4. Type your topic, and why you know it well, under 3a in `WRITEUP.md`.
5. Write **at least eight** claims about it in the table under 3a, with the mix listed below.
6. Type your verdict for each: `supported` if it is true, `refuted` if it is false, spelled exactly so.
7. Type the source you would trust for each: a link, a book, or how you know it first-hand.
8. Ask Claude to copy your table into `data/my-claims.jsonl`, with ids `mine-1`, `mine-2` and so on.
9. Open `data/my-claims.jsonl` and check that it has one line for each claim in your table.

Topics that work: your hometown, a band, a sport, a game, a field you've studied, Macalester. Something
you could fact-check yourself without looking much up. Your claims must include:

- some that are true and some that are false;
- at least two that need two or more Wikipedia articles to check, like the HoVer claims: one fact has
  to be found before you know which page holds the next;
- at least two where you think Wikipedia doesn't say, or says something wrong.

For those claims too, your verdict is what is true. Finding out what the agent does when Wikipedia
lacks the fact, or has it wrong, is the point.

**Output:** Each line of `data/my-claims.jsonl` looks like this, with the claim's row number in
its id and your verdict, `supported` or `refuted`, as its label. The program compares the agent's
verdict with yours word for word, so the spelling matters.

```
{"id": "mine-1", "claim": "...", "source": "mine", "label": "supported"}
```

**Write-up:** In `WRITEUP.md`, under 3a, answer and fill in the table:

- Your topic, and why you know it well.
- Your claims, at least eight: some true and some false, at least two that need two or more Wikipedia articles, and at least two where you think Wikipedia doesn't say or says something wrong. Write each verdict as `supported` if the claim is true or `refuted` if it is false, according to the source you trust. For more claims, add rows numbered 9, 10 and so on.

**Completion:** The homework page ticks 3a: `data/my-claims.jsonl` exists, the topic answer has
text after the `>`, and every numbered row of the table is filled.

**Hint:** False claims are most interesting when they are close to true. Change one fact (a year, a
place, a name) rather than inventing something absurd. Claude will not suggest a topic or a claim, but
it will tell you if your claims are missing part of the mix.

## 3b. Run the agent on your claims

In this step you find out where the agent and the one-search baseline agree with your own verdicts on
your claims.

**Words in this step:** *the agent*: the program in `agent.py` and its loop, in which the model (Claude Haiku,
the small Claude model that the agent and both baselines call) picks the next lookup, reads what comes
back, and decides when to answer. *the one-search baseline*: one search, one page, then an answer.

**Actions:**

1. Start this step's Claude session with the command the homework page shows for 3b, in a terminal tab in the
   homework's folder. If the last step's Claude is still open in that tab, type `/exit` first.
2. Ask Claude to run the one-search baseline and the agent on your claims.
3. Tell Claude what you expect, when it asks.
4. Read the two tables the run prints at the end.
5. Open **Results** at the top of the homework page, then "runs/part3/before".
6. Click the claims where a version disagreed with you, and read what it did.
7. Answer the two questions.

**Output:** Claude runs this command. It takes about 3 minutes and costs a few cents:

```
uv run python evaluate.py data/my-claims.jsonl --methods one-search,agent --out runs/part3/before
```

The first table shows on how many of your claims each version's verdict matched yours. A verdict
matches only when it is the same word as yours, so when a version answers *doesn't say* it does not
match, whichever verdict you gave. The run is saved in `runs/part3/before`.

**Write-up:** Answer these questions in `WRITEUP.md`, under 3b:

- On how many of your claims did each version agree with you?
- What surprised you?

**Completion:** The homework page ticks 3b: `runs/part3/before/report.txt` exists, and both
answers have text after the `>`.

## 3c. Sort the failures

In this step you find out why the agent fails on your claims. You also see whether Claude reads the same
failures the same way you do.

**Words in this step:** *failure*: a claim where the agent's verdict differs from yours. *trace*: the
agent's lookups for one claim, in order, with what each returned. *entry*: one numbered line of a
trace, a lookup or an answer.

The labels:

- *wrong page*: it never found the page that settles the claim;
- *stopped too early*: it answered before checking every piece of the claim;
- *misread*: it read the right page and drew the wrong conclusion;
- *forced a verdict*: it answered *supported* or *refuted* when Wikipedia does not settle the claim;
- *Wikipedia is missing or wrong*: the agent did what it should, and Wikipedia lacks the fact or has it
  wrong;
- a label of your own, if none of these fits.

**Actions:** Follow this order: you label first, and Claude labels without seeing yours, so that neither
set of labels can steer the other.

1. Start this step's Claude session with the command the homework page shows for 3c, in a terminal tab in the
   homework's folder. If the last step's Claude is still open in that tab, type `/exit` first.
2. Open **Results** at the top of the homework page, then "runs/part3/before".
3. Set "Result" in "The agent" box to "does not match your verdict (any reason)".
4. Click each of those claims and read "The agent's trace", one entry at a time.
5. Give each one label from the list above, without telling Claude.
6. Copy the empty row of the table under 3c once for each failure, and fill in each row.
7. Ask Claude to label the same claims.
8. Ask Claude to add its labels to the last column, "Claude's label", or type them in yourself.
9. Answer the two questions.

**Output:** The filter leaves only your failures in the table. For "the line of the trace that
shows it", give the entry's number and a few words of what it shows. Claude gives its labels in the
chat without opening `WRITEUP.md`, so it has not seen yours. It will not say which of you is right.

**Write-up:** In `WRITEUP.md`, under 3c, fill in the table and answer:

- One row for each claim where the agent's verdict differs from yours: the claim's number from your 3a table, your label, and the line of the trace that shows it. Type your labels before you ask Claude for its own. Then ask Claude to add its labels to the last column, or type them in yourself.
- Where did you and Claude disagree, and who do you think is right?
- Which kind of failure was most common? If no kind repeats, say which failure you will aim at in 3d, and why.

**Completion:** The homework page ticks 3c: every row of the table is filled, Claude's labels
included, and both answers have text after the `>`.

**Troubleshooting:** Two failures are enough to go on. If the agent disagreed with you on fewer
than two claims, there isn't enough to sort, and you need harder claims. You can do all of this in this
step's session:

1. Type two or three new claims as new rows at the end of your 3a table in `WRITEUP.md`, each with your
   verdict and your source. Add new claims rather than rewording old ones: a run keeps its saved result
   for each claim number, so a reworded claim would not be checked again.
2. Paste the same new claims into the chat, each with your verdict, and ask Claude to add them to
   `data/my-claims.jsonl` and to run 3b's command again (it is below). It checks only the new claims.
3. Update your answers under 3b if its numbers changed, then go on from action 2 above.

```
uv run python evaluate.py data/my-claims.jsonl --methods one-search,agent --out runs/part3/before
```

## 3d. Make one change

In this step you make one change aimed at your most common failure. You find out whether it fixes that
failure on your own claims.

**Actions:**

1. Start this step's Claude session with the command the homework page shows for 3d, in a terminal tab in the
   homework's folder. If the last step's Claude is still open in that tab, type `/exit` first.
2. Decide on **one** change aimed at your most common failure from 3c (see the Hint).
3. Make the change in your editor, or tell Claude exactly what to change.
4. Ask Claude to run the agent on your claims again, with the change.
5. If you adjust your change after seeing the results, ask Claude to run that again with `--fresh`.
6. Open **Results** at the top of the homework page, click "Compare two runs", then "Step 3d:
   runs/part3/before with runs/part3/after".
7. Answer the two questions.

**Output:** Claude makes exactly the change you describe and shows you what changed. For your
claims, Claude runs the first command below; after you adjust your change, the second, whose `--fresh`
replaces the folder's saved results, since a run never checks a saved claim again:

```
uv run python evaluate.py data/my-claims.jsonl --methods agent --out runs/part3/after
uv run python evaluate.py data/my-claims.jsonl --methods agent --out runs/part3/after --fresh
```

**Write-up:** Answer these questions in `WRITEUP.md`, under 3d:

- What did you change, and why did you expect it to help?
- Did it fix the failure you aimed at? Give how many of your claims the agent matched before and after, and say whether the claims you gave that label now match.

**Completion:** The homework page ticks 3d: `runs/part3/after/report.txt` exists, and the two
answers have text after the `>`.

**Troubleshooting:**

- The run stops partway: run the same command again. It keeps every claim it already finished.
- The run stops at once and says its folder has saved results from an earlier version of your agent:
  you changed `instructions.md`, `agent.py`, `wiki.py` or your loop after the run started. Add `--fresh`
  to the end of the same command to start the run over with the agent as it is now.

**Hint:** The change can be to `instructions.md`, to a tool (for example, what `search` returns, in
`wiki.py`), or to the limit of 12 lookups (in `agent.py`). Leave your loop, `my_loop.py`, as it passed
the check: a loop that breaks one of the six rules is put back on the reference loop the next time the
check runs. Claude will not propose a change, because choosing it is the point of this step. Leave `instructions.md` alone while a run is going, because the
agent reads it again for every claim.

## 3e. Write it up

In this step you say what you learned, in your own words.

**Actions:**

1. Start this step's Claude session with the command the homework page shows for 3e, in a terminal tab in the
   homework's folder. If the last step's Claude is still open in that tab, type `/exit` first.
2. Answer the two questions under `### Write-up` in 3e, using your own numbers and examples.
3. Answer the question under `### How I used AI`.
4. Ask Claude to show you any of your own numbers or results you want to use.

**Write-up:** In `WRITEUP.md`, under 3e, answer under `### Write-up`:

- What does the agent's loop add over one search, what does it cost, and when would you not use an agent for a job like this? Use your numbers from Part 2 and your claims from Part 3.
- What did your topic show you about Wikipedia as a source? Where it was thin or wrong, why might that be, given who writes it?

and under `### How I used AI`:

- How did you use AI in this homework, what did you check yourself, and what is one decision you made on your own?

**Completion:** The homework page ticks 3e: all three answers have text after the `>`. That
finishes Part 3, so the page commits your work as `Part 3 done` and pushes it to your fork. The page does
not hand your homework in: submit it yourself, as the Submitting section of the README says.

**Hint:** An answer can be as long as you need, but keep it in one block with no blank line inside it,
since a blank line ends the answer. To start a new paragraph, put a line with just `>` between the two.
Claude will not write or suggest a sentence, because the write-up is yours.

## What I look for

Part 3 is 30% of the homework. At a minimum I am looking for the following:

- Your claims: 20% - At least eight in 3a, with the mix asked for, each with your verdict and a source.
- Failure labels: 30% - Each label in 3c is backed by the line of the trace that shows it, and you
  explain where you and Claude disagreed.
- Your change: 20% - Your 3d change targets your most common failure, and you report its effect on
  your claims.
- Write-up: 30% - Your 3e answers use your own numbers and examples, and the Wikipedia answer goes
  beyond "it was missing" to why.
