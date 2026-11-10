# COMP 440 HW3 Part 3: Your own claims

Due 8:00am Tuesday, November 24. Back to the [assignment page](../README.md).

In this part you test the agent on a topic you know better than most people. You write your own claims,
run the agent on them, sort out why it fails, make one change, and write up what you found. It should
take about 2 hours and 10 minutes, including a second run on the 200 evaluation claims of about 10
minutes.

## 3a. Pick a topic and write your claims

**What this step is for:** Building your own set of test claims, on a topic you know better than most
people.

**Words in this step:** *claim*: one sentence that is either true or false. *your verdict*:
*supported* if the claim is true and *refuted* if it is false, according to the source you trust, not
what you think Wikipedia says.

**What to do:**

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

**What you'll see:** Each line of `data/my-claims.jsonl` looks like this, with the claim's row number in
its id and your verdict, `supported` or `refuted`, as its label. The program compares the agent's
verdict with yours word for word, so the spelling matters.

```
{"id": "mine-1", "claim": "...", "source": "mine", "label": "supported"}
```

**What to write:** In `WRITEUP.md`, under 3a, answer and fill in the table:

- Your topic, and why you know it well.
- Your claims, at least eight: some true and some false, at least two that need two or more Wikipedia articles, and at least two where you think Wikipedia doesn't say or says something wrong. Write each verdict as `supported` if the claim is true or `refuted` if it is false, according to the source you trust. For more claims, add rows numbered 9, 10 and so on.

**You're done when:** The homework page ticks 3a: `data/my-claims.jsonl` exists, the topic answer has
text after the `>`, and every numbered row of the table is filled.

**Hint:** False claims are most interesting when they are close to true. Change one fact (a year, a
place, a name) rather than inventing something absurd. Claude will not suggest a topic or a claim, but
it will tell you if your claims are missing part of the mix.

## 3b. Run the agent on your claims

**What you're finding out:** Where the agent and the one-search baseline agree with your own verdicts
on your claims.

**Words in this step:** *the agent*: the program in `agent.py`, a loop in which the model (Claude Haiku,
the small Claude model that the agent and both baselines call) picks the next lookup, reads what comes
back, and decides when to answer. *the one-search baseline*: one search, one page, then an answer.

**What to do:**

1. Start this step's Claude session with the command the homework page shows for 3b, in a terminal tab in the
   homework's folder. If the last step's Claude is still open in that tab, type `/exit` first.
2. Ask Claude to run the one-search baseline and the agent on your claims.
3. Tell Claude what you expect, when it asks.
4. Read the two tables the run prints at the end.
5. Open **Results** at the top of the homework page, then "runs/part3/before".
6. Click the claims where a version disagreed with you, and read what it did.
7. Answer the two questions.

**What you'll see:** Claude runs this command. It takes about 3 minutes and costs a few cents:

```
uv run python evaluate.py data/my-claims.jsonl --methods one-search,agent --out runs/part3/before
```

The first table shows on how many of your claims each version's verdict matched yours. A verdict
matches only when it is the same word as yours, so when a version answers *doesn't say* it does not
match, whichever verdict you gave. The run is saved in `runs/part3/before`.

**What to write:** In `WRITEUP.md`, under 3b:

- On how many of your claims did each version agree with you?
- What surprised you?

**You're done when:** The homework page ticks 3b: `runs/part3/before/report.txt` exists, and both
answers have text after the `>`.

## 3c. Sort the failures

**What you're finding out:** Why the agent fails on your claims, and whether Claude reads the same
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

**What to do:** In this order: you label first, and Claude labels without seeing yours, so that neither
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

**What you'll see:** The filter leaves only your failures in the table. For "the line of the trace that
shows it", give the entry's number and a few words of what it shows. Claude gives its labels in the
chat without opening `WRITEUP.md`, so it has not seen yours. It will not say which of you is right.

**What to write:** In `WRITEUP.md`, under 3c, fill in the table and answer:

- One row for each claim where the agent's verdict differs from yours: the claim's number from your 3a table, your label, and the line of the trace that shows it. Type your labels before you ask Claude for its own. Then ask Claude to add its labels to the last column, or type them in yourself.
- Where did you and Claude disagree, and who do you think is right?
- Which kind of failure was most common?

**You're done when:** The homework page ticks 3c: every row of the table is filled, Claude's labels
included, and both answers have text after the `>`.

**If something goes wrong:** If the agent disagreed with you on fewer than three claims, there isn't
enough to sort. Add harder claims to your 3a table. Go back to 3a's Claude session (the homework page
shows the command that returns to it) and ask Claude to add them to `data/my-claims.jsonl`. Then go back
to 3b's session and ask Claude to run 3b's command again, update your answers under 3b, and start this
step again from action 2. Add new claims rather than rewording old ones: a run keeps its saved result
for each claim number, so a reworded claim would not be checked again. The command checks only the new
claims:

```
uv run python evaluate.py data/my-claims.jsonl --methods one-search,agent --out runs/part3/before
```

## 3d. Make one change

**What you're finding out:** Whether one change aimed at your most common failure fixes it, and what
it does on the 200 evaluation claims.

**Words in this step:** *the evaluation claims*: the 200 claims in `data/eval.jsonl`, which your full
run in 1e checked and saved in `runs/part2`.

**What to do:**

1. Start this step's Claude session with the command the homework page shows for 3d, in a terminal tab in the
   homework's folder. If the last step's Claude is still open in that tab, type `/exit` first.
2. Decide on **one** change aimed at your most common failure from 3c (see the Hint).
3. Make the change in your editor, or tell Claude exactly what to change.
4. Ask Claude to run the agent on your claims again, with the change.
5. If you adjust your change after seeing the results, ask Claude to run that again with `--fresh`.
6. Settle on your change before the next action, because the long run uses the agent as it is then.
7. Open a new terminal tab and go into the homework's folder (the `comp440-hw3` folder you cloned).
8. Start the agent on the 200 evaluation claims yourself, in that tab.
9. Leave that tab open, your laptop awake and `instructions.md` alone until the run ends.
10. Open **Results** at the top of the homework page, click "Compare two runs", then "Step 3d:
    runs/part3/before with runs/part3/after".
11. When the long run has finished, go back to "Compare two runs" and click "Step 3d: runs/part2 with
    runs/part3/after-eval".
12. Answer the three questions.

**What you'll see:** Claude makes exactly the change you describe and shows you what changed. For your
claims, Claude runs the first command below; after you adjust your change, the second, whose `--fresh`
replaces the folder's saved results, since a run never checks a saved claim again:

```
uv run python evaluate.py data/my-claims.jsonl --methods agent --out runs/part3/after
uv run python evaluate.py data/my-claims.jsonl --methods agent --out runs/part3/after --fresh
```

In your own tab you run this. It takes about 10 minutes, costs about 35 cents and ends with two tables:

```
uv run python evaluate.py data/eval.jsonl --methods agent --out runs/part3/after-eval
```

**What to write:** In `WRITEUP.md`, under 3d:

- What did you change, and why did you expect it to help?
- Did it fix the failure you aimed at? Give how many of your claims the agent matched before and after, and say whether the claims you gave that label now match.
- What did the change do on the 200 evaluation claims? Was it worth it?

**You're done when:** The homework page ticks 3d: `runs/part3/after/report.txt` and
`runs/part3/after-eval/report.txt` exist, and the three answers have text after the `>`.

**If something goes wrong:**

- A run stops partway: run the same command again. It keeps every claim it already finished.
- One of this step's two runs stops at once and says its folder has saved results from an earlier
  version of your agent: you changed `instructions.md`, `agent.py` or `wiki.py` after that run started.
  Add `--fresh` to the end of the same command to start that run over with the agent as it is now.

**Hint:** The change can be to `instructions.md`, to a tool (for example, what `search` returns, in
`wiki.py`), or to the limit of 12 lookups (in `agent.py`). Claude will not propose a change, because
choosing it is the point of this step. Start the long run in your own tab, because a run started by
Claude stops if you close that Claude session; leave `instructions.md` alone while it runs, because the
agent reads it again for every claim.

## 3e. Write it up

**What this step is for:** Saying what you learned, in your own words.

**What to do:**

1. Start this step's Claude session with the command the homework page shows for 3e, in a terminal tab in the
   homework's folder. If the last step's Claude is still open in that tab, type `/exit` first.
2. Answer the three questions under `### Write-up` in 3e, using your own numbers and examples.
3. Answer the question under `### How I used AI`.
4. Ask Claude to show you any of your own numbers or results you want to use.

**What to write:** In `WRITEUP.md`, under 3e, answer under `### Write-up`:

- What does the agent's loop add over one search? Use your numbers from Part 2 and your claims from Part 3.
- What does the agent cost, and when would you not use an agent for a job like this?
- What did your topic show you about Wikipedia as a source? Where it was thin or wrong, why might that be, given who writes it?

and under `### How I used AI`:

- How did you use AI in this homework, what did you check yourself, and what is one decision you made on your own?

**You're done when:** The homework page ticks 3e: all four answers have text after the `>`. That
finishes Part 3, so the page commits your work as `Part 3 done` and pushes it to your fork. Then submit,
as the Submitting section of the README says.

**Hint:** An answer can be as long as you need, but keep it in one block with no blank line inside it,
since a blank line ends the answer. To start a new paragraph, put a line with just `>` between the two.
Claude will not write or suggest a sentence, because the write-up is yours.

## What I look for

Part 3 is 30% of the homework. At a minimum I am looking for the following:

- Your claims: 20% - At least eight in 3a, with the mix asked for, each with your verdict and a source.
- Failure labels: 30% - Each label in 3c is backed by the line of the trace that shows it, and you
  explain where you and Claude disagreed.
- Your change: 20% - Your 3d change targets your most common failure, and you report its effect on both
  your claims and the 200 evaluation claims.
- Write-up: 30% - Your 3e answers use your own numbers and examples, and the Wikipedia answer goes
  beyond "it was missing" to why.
