# COMP 440 HW3 Part 3: Your own claims

Due 8:00am Tuesday, November 24. Back to the [assignment page](../README.md).

In this part you test the agent on a topic you know better than most people. You write your own claims,
run the agent on them, sort out why it fails, make one change, and write up what you found. It should
take about 2 hours and 20 minutes, including a second run on the 200 evaluation claims of about 10
minutes.

## 3a. Pick a topic and write your claims

**What you're finding out:** Nothing yet. You build your own set of test claims, on a topic you know
better than most people.

A claim is one sentence that is either true or false. A verdict is the answer to a claim: *supported*,
*refuted* or *doesn't say*. Your verdict is what is true as far as you know, from the source you would
trust, not what you think Wikipedia says. The agent, the program in `agent.py`, will check your claims
against Wikipedia in 3b.

**What to do:**

1. Start this step's Claude session: in a terminal tab in the homework's folder, run the command the
   homework page shows for 3a. Claude is your Claude Code session, your tutor and lab assistant.
2. Pick a topic you know well and that Wikipedia covers at least a little: your hometown, a band, a
   sport, a game, a field you've studied, Macalester. Something you could fact-check yourself without
   looking much up.
3. Type your topic, and why you know it well, under 3a in `WRITEUP.md`.
4. Write **at least eight** claims about it in the table under 3a. Include:
   - some that are true and some that are false;
   - at least two that need two or more Wikipedia articles to check;
   - at least two where you think Wikipedia doesn't say, or says something wrong.
5. For each claim, type your verdict and the source you would trust for it. Spell the verdict exactly
   `supported`, `refuted` or `doesn't say`, because the program compares the agent's verdict with yours
   word for word.
6. Ask Claude to copy your table into `data/my-claims.jsonl`, so the agent can run on your claims, with
   `mine-1` as the id of the claim in row 1, `mine-2` for row 2, and so on. Each line of the file looks
   like this:

   ```
   {"id": "mine-1", "claim": "...", "source": "mine", "label": "supported"}
   ```

7. Check that the file has one line for each claim in your table.

Claude will not suggest a topic or a claim, because they are yours, but it will tell you if your claims
are missing part of the mix in action 4.

**What to write:** Under `## 3a. Pick a topic and write your claims` in `WRITEUP.md`, answer and fill in
the table:

- Your topic, and why you know it well.
- Your claims, at least eight: some true and some false, at least two that need two or more Wikipedia articles, and at least two where you think Wikipedia doesn't say or says something wrong. Write each verdict as `supported`, `refuted` or `doesn't say`. For more claims, add rows numbered 9, 10 and so on.

**You're done when:** The homework page ticks 3a. It does that when `data/my-claims.jsonl` exists, the
topic answer has text after the `>`, and every numbered row of the table has every cell filled.

**Hint:** False claims are most interesting when they are close to true. Change one fact (a year, a
place, a name) rather than inventing something absurd.

## 3b. Run the agent on your claims

**What you're finding out:** Where the agent and the one-search baseline agree with your own verdicts
on your claims.

The agent is the program in `agent.py`: a loop in which the model (Claude Haiku, the small Claude model
that the agent and both baselines call) picks the next lookup, reads what comes back, and decides when
to answer. The one-search baseline is a simpler method it is compared with: one search, one page, then
an answer. Your claims are the ones in `data/my-claims.jsonl`, with your verdicts (*supported*,
*refuted* or *doesn't say*).

**What to do:**

1. Start this step's Claude session: in a terminal tab in the homework's folder, run the command the
   homework page shows for 3b. Claude is your Claude Code session, your tutor and lab assistant.
2. Ask Claude to run the one-search baseline and the agent on your claims. It takes about 3 minutes and
   costs a few cents on your key. Claude runs this command:

   ```
   uv run python evaluate.py data/my-claims.jsonl --methods one-search,agent --out runs/part3/before
   ```

3. Tell Claude what you expect, when it asks.
4. Read the two tables the run prints at the end. The first shows on how many of your claims each
   version's verdict matched yours. A verdict matches only when it is the same word as yours: your
   claims keep all three verdicts, so *refuted* and *doesn't say* are different answers here.
5. Open **Results** at the top of the homework page, then open the run `runs/part3/before`.
6. Open the claims where a version disagreed with you, and read what it did.
7. Answer the two questions.

**What to write:** Under `## 3b. Run the agent on your claims` in `WRITEUP.md`, answer:

- On how many of your claims did each version agree with you?
- What surprised you?

**You're done when:** The homework page ticks 3b. It does that when `runs/part3/before/report.txt`
exists (the run saves it when it finishes) and both answers have text after the `>`.

## 3c. Sort the failures

**What you're finding out:** Why the agent fails on your claims, and whether Claude reads the same
failures the same way you do.

The agent is the program in `agent.py`: a loop in which the model (Claude Haiku) picks the next lookup,
reads what comes back, and decides when to answer. A failure here is a claim where the agent's verdict
differs from yours. A trace is the list of the agent's lookups for one claim, in order, with what each
returned. Claude is your Claude Code session, your tutor and lab assistant.

The labels:

- *wrong page*: it never found the page that settles the claim;
- *stopped too early*: it answered before checking every piece of the claim;
- *misread*: it read the right page and drew the wrong conclusion;
- *wouldn't say "doesn't say"*: it forced a verdict that Wikipedia does not support;
- *Wikipedia is missing or wrong*: the agent did fine, and Wikipedia let it down;
- a label of your own, if none of these fits.

**What to do:** Do these in this order. You label first, and Claude labels without seeing yours, so
that neither set of labels can steer the other.

1. Start this step's Claude session: in a terminal tab in the homework's folder, run the command the
   homework page shows for 3c.
2. Open **Results** at the top of the homework page, open the run `runs/part3/before`, and in the
   claims table's filters set the agent's Result to "did not match (any reason)". The table then shows
   the claims where the agent's verdict differs from yours.
3. Open each of those claims and read its trace one lookup at a time.
4. Give each one label from the list above. For each, fill in a row of the table under 3c: the claim's
   number from your 3a table, your label, and the line of the trace that shows it (the lookup's number
   and a few words of what it shows). Use the empty row for the first claim and add a row for each of
   the others. Don't tell Claude your labels.
5. Ask Claude to label the same claims. Claude reads their traces and gives its labels in the chat,
   without opening `WRITEUP.md`, so it has not seen yours.
6. Ask Claude to add its labels to the last column of the table, "Claude's label", or type them in
   yourself. Claude will not say which of you is right.
7. Answer the two questions.

If the agent disagreed with you on fewer than three claims, there isn't enough to sort. Go back to your
3a table and add harder claims, ask Claude to add them to `data/my-claims.jsonl`, and ask Claude to run
3b's command again. Add new claims rather than rewording old ones: a run keeps its saved result for each
claim number, so a reworded claim would not be checked again. The command checks only the new claims:

```
uv run python evaluate.py data/my-claims.jsonl --methods one-search,agent --out runs/part3/before
```

Then start again from action 2.

**What to write:** Under `## 3c. Sort the failures` in `WRITEUP.md`, fill in the table and answer:

- One row for each claim where the agent's verdict differs from yours: the claim's number from your 3a table, your label, and the line of the trace that shows it. Type your labels before you ask Claude for its own. Then ask Claude to add its labels to the last column, or type them in yourself.
- Where did you and Claude disagree, and who do you think is right?
- Which kind of failure was most common?

**You're done when:** The homework page ticks 3c. It does that when every row of the table has every
cell filled, Claude's labels included, and both answers have text after the `>`.

## 3d. Make one change

**What you're finding out:** Whether one change aimed at your most common failure fixes it, and what
it does on the 200 evaluation claims.

The agent is the program in `agent.py`: a loop in which the model (Claude Haiku) picks the next lookup,
reads what comes back, and decides when to answer. A lookup is one call to `search`, `read` or
`wikidata`. The evaluation claims are the 200 claims in `data/eval.jsonl`, the ones your full run in 1e
checked, saved in `runs/part2`.

**What to do:**

1. Start this step's Claude session: in a terminal tab in the homework's folder, run the command the
   homework page shows for 3d. Claude is your Claude Code session, your tutor and lab assistant.
2. Decide on **one** change aimed at your most common failure from 3c. It can be to `instructions.md`,
   to a tool (for example, what `search` returns, in `wiki.py`), or to the limit of 12 lookups (in
   `agent.py`).
3. Make the change in your editor, or tell Claude exactly what to change. Claude makes exactly the
   change you describe and shows you what changed. It will not propose a change, because choosing it is
   the point of this step.
4. Ask Claude to run the agent on your claims again, with the change. Claude runs this command:

   ```
   uv run python evaluate.py data/my-claims.jsonl --methods agent --out runs/part3/after
   ```

5. If you adjust your change after seeing these results, ask Claude to run the same command with
   `--fresh` at the end. Without `--fresh`, a run never checks a claim again once its result is saved,
   and `--fresh` replaces this folder's saved results with a new run:

   ```
   uv run python evaluate.py data/my-claims.jsonl --methods agent --out runs/part3/after --fresh
   ```

   Settle on your change before the next action, because the long run uses the agent as it is then.
6. Open a new terminal tab and go into the homework's folder (the `comp440-hw3` folder you cloned).
7. Start the agent on the 200 evaluation claims again yourself, in that tab:

   ```
   uv run python evaluate.py data/eval.jsonl --methods agent --out runs/part3/after-eval
   ```

   It takes about 10 minutes and costs about 35 cents on your key. Start it in your
   own tab, because a run started by Claude stops if you close that Claude session. Leave the tab open,
   your laptop awake and `instructions.md` alone until it ends with two tables, since the agent reads
   `instructions.md` again for every claim.
8. Open **Results** at the top of the homework page, choose "Compare two runs", and compare
   `runs/part3/before` with `runs/part3/after`.
9. When the long run has finished, compare `runs/part2` with `runs/part3/after-eval` the same way.
10. Answer the three questions.

**What to write:** Under `## 3d. Make one change` in `WRITEUP.md`, answer:

- What did you change, and why did you expect it to help?
- Did it fix the failure you aimed at? Give the numbers before and after on your claims.
- What did the change do on the 200 evaluation claims? Was it worth it?

**You're done when:** The homework page ticks 3d. It does that when `runs/part3/after/report.txt` and
`runs/part3/after-eval/report.txt` exist (each run saves its report when it finishes) and the three
answers have text after the `>`.

**If something goes wrong:**

- A run stops partway: run the same command again. It keeps every claim it already finished and checks
  only the rest.
- One of this step's two runs stops at once and says its folder has saved results from an earlier
  version of your agent: you changed `instructions.md`, `agent.py` or `wiki.py` after that run started.
  To start that run over with the agent as it is now, add `--fresh` to the end of the same
  command.

## 3e. Write it up

**What you're finding out:** This is where you say what you learned.

The agent is the program in `agent.py`: a loop in which the model (Claude Haiku) picks the next lookup,
reads what comes back, and decides when to answer. The one-search baseline is a simpler method it is
compared with: one search, one page, then an answer.

**What to do:**

1. Start this step's Claude session: in a terminal tab in the homework's folder, run the command the
   homework page shows for 3e. Claude is your Claude Code session, your tutor and lab assistant.
2. Answer the three questions under `### Write-up` in 3e, using your own numbers and examples.
3. Answer the question under `### How I used AI`.
4. Ask Claude to show you any of your own numbers or results you want to use. Claude will not write or
   suggest a sentence, because the write-up is yours.

Each answer can be as long as you need. Keep each one in a single block with no blank line inside it,
since a blank line ends the answer. To start a new paragraph, put a line with just `>` between the two.

**What to write:** Under `## 3e. Write it up` in `WRITEUP.md`, answer, under `### Write-up`:

- What does the agent's loop add over one search? Use your numbers from Part 2 and your claims from Part 3.
- What does the agent cost, and when would you not use an agent for a job like this?
- What did your topic show you about Wikipedia as a source? Where it was thin or wrong, why might that be, given who writes it?

and under `### How I used AI`:

- How did you use AI in this homework, what did you check yourself, and what is one decision you made on your own?

**You're done when:** The homework page ticks 3e. It does that when all four answers have text after the
`>`. With 3e ticked, every step of Part 3 is done, so the page commits your work as `Part 3 done` and
pushes it to your fork. Then submit, as the Submitting section of the README says.

## What I look for

Part 3 is 30% of the homework. At a minimum I am looking for the following:

- Your claims: 20% - At least eight in 3a, with the mix asked for, each with your verdict and a source.
- Failure labels: 30% - Each label in 3c is backed by the line of the trace that shows it, and you
  explain where you and Claude disagreed.
- Your change: 20% - Your 3d change targets your most common failure, and you report its effect on both
  your claims and the 200 evaluation claims.
- Write-up: 30% - Your 3e answers use your own numbers and examples, and the Wikipedia answer goes
  beyond "it was missing" to why.
