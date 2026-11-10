# COMP 440 HW3 Part 2: The agent against the baselines

Due 8:00am Tuesday, November 24. Back to the [assignment page](../README.md).

In this part you read the full run you started in 1e: how often each version matched the dataset's
label, what each one cost, whether the agent's evidence holds up when you check it yourself, and where
Wikipedia has changed since the dataset was made. It should take about 1 hour and 35 minutes.

## 2a. Compare accuracy

**What you're finding out:** How often each of the three versions matched the dataset's label on the
200 evaluation claims, and how that compares with your predictions from 1e.

The run you started in 1e checked the 200 evaluation claims in `data/eval.jsonl` with the three
versions: the no-tools baseline (the model, Claude Haiku, answers from memory), the one-search baseline
(one search, one page, then an answer) and the agent (the program in `agent.py`, a loop in which the
model picks its own lookups). The dataset's label is HoVer's *supported* or *not supported*, and a
verdict of *refuted* or *doesn't say* counts as *not supported*. Each claim needs 2, 3 or 4 Wikipedia
articles to check: that is its number of articles.

**What to do:**

1. Start this step's Claude session: in a terminal tab in the homework's folder, run the command the
   homework page shows for 2a. Claude is your Claude Code session, your tutor and lab assistant.
2. Check that the full run has finished. The terminal tab where you started it ends with two tables,
   and the file `runs/part2/report.txt` exists. If the run stopped early, or its tables end with a line
   saying some runs stopped with an error, run the same command again in a terminal tab in the
   homework's folder. It keeps every claim it already finished and checks only the rest:

   ```
   uv run python evaluate.py data/eval.jsonl --out runs/part2
   ```

3. Open **Results** at the top of the homework page, then open the run `runs/part2`. Its page shows the
   report's two tables and every claim.
4. Ask Claude to paste the report into the empty block under 2a in `WRITEUP.md`.
5. Compare the report's first table with your predictions under 1e in `WRITEUP.md`. Each cell of that
   table is how many claims matched the dataset's label, out of how many, so divide to get a percentage.
6. Answer the three questions.

**What to write:** Under `## 2a. Compare accuracy` in `WRITEUP.md`, fill in the block and answer:

- The report of your full run, from `runs/part2/report.txt`. Ask Claude to paste it into the empty block below.
- How do the results compare with your predictions? Where were you furthest off? Use the numbers from your run, by number of articles.
- Does the gap between the agent and the one-search baseline grow with the number of articles? If it does not, what might explain that?
- The no-tools baseline read nothing. How did it do, and what does that tell you about these claims?

**You're done when:** The homework page ticks 2a. It does that when `runs/part2/report.txt` exists, the
block under 2a holds the report, and the three answers have text after the `>`.

## 2b. Compare cost

**What you're finding out:** What the agent costs compared with the one-search baseline, and when that
extra cost is worth paying.

The agent is the program in `agent.py`: a loop in which the model (Claude Haiku) picks the next lookup,
reads what comes back, and decides when to answer. A lookup is one call to `search`, `read` or
`wikidata`, and the loop allows at most 12 lookups for one claim. The one-search baseline is a simpler
method the agent is compared with: one search, one page, then an answer. Tokens are the unit the API
counts text in and charges by, about three quarters of a word.

**What to do:**

1. Start this step's Claude session: in a terminal tab in the homework's folder, run the command the
   homework page shows for 2b. Claude is your Claude Code session, your tutor and lab assistant.
2. Read the second table of the report from your full run, in the block under 2a in `WRITEUP.md`: the
   average lookups, tokens, seconds and cost in dollars per claim, for each version.
3. Open **Results** at the top of the homework page, then open the run `runs/part2`.
4. Use the claims table's filter for claims where the agent used all 12 lookups.
5. If there are any, open one and read its trace one lookup at a time. A trace is the list of the
   agent's lookups for one claim, in order, with what each returned.
6. Answer the three questions.

**What to write:** Under `## 2b. Compare cost` in `WRITEUP.md`, answer:

- How much more does the agent cost per claim than the one-search baseline? Give the numbers.
- For which kinds of claims is that extra cost worth paying, and for which is it not?
- Did the agent ever use all 12 lookups? If so, pick one such claim and say what it was doing.

**You're done when:** The homework page ticks 2b. It does that when the three answers have text after
the `>`. This step makes no files.

## 2c. Check the evidence yourself

**What you're finding out:** Whether the agent's evidence really supports its verdicts, and so whether
accuracy alone is a fair measure of the agent.

The agent is the program in `agent.py`: a loop in which the model (Claude Haiku) picks the next lookup,
reads what comes back, and decides when to answer. Its verdict is *supported*, *refuted* or
*doesn't say*, and its evidence is the sentences it quoted from Wikipedia. The loop already checks that
every quoted sentence appears in something the agent read. A quote can be real and still not support
the verdict. The dataset's label is HoVer's *supported* or *not supported*, and a verdict of *refuted*
or *doesn't say* counts as *not supported*.

**What to do:**

1. Start this step's Claude session: in a terminal tab in the homework's folder, run the command the
   homework page shows for 2c. Claude is your Claude Code session, your tutor and lab assistant.
2. Open **Results** at the top of the homework page, then open the run `runs/part2`.
3. Clear the claims table's filters, so that it shows every claim, in the order of the claims file.
4. Going down the table, take the first ten claims where the agent's verdict is *supported* or
   *refuted*. Skip any where it said *doesn't say* or gave no verdict. I ask for the first ten so that
   nobody, you or Claude, chooses which claims get checked.
5. Open the first claim. Read each sentence the agent quoted where it is highlighted in what the agent
   read, and decide whether it supports the agent's verdict.
6. Open the live Wikipedia page from the claim's page whenever you're unsure.
7. Fill in that claim's row of the table, then do the same for the other nine. You can ask Claude to
   fill in the first three columns (the number, the claim's first few words and the agent's verdict);
   the last two are yours.
8. Answer the two questions.

Claude can read more of a page for you with one of these commands, but it will not say whether a quote
supports a verdict, because that judgment is what this step is about. `--no-log` keeps these lookups
out of your record from 1b:

```
uv run python lookup.py --no-log read "<page title>"
uv run python lookup.py --no-log read "<page title>" "<section>"
```

**What to write:** Under `## 2c. Check the evidence yourself` in `WRITEUP.md`, fill in the table and
answer:

- The first ten claims in your Part 2 run, in the order of the claims file, where the agent's verdict is *supported* or *refuted*.
- Of the ten, how many matched the dataset's label, and how many of those rest on evidence you accept?
- Is accuracy alone a good measure of this agent? Why or why not?

**You're done when:** The homework page ticks 2c. It does that when all ten rows of the table have every
cell filled and both answers have text after the `>`. This step makes no files.

## 2d. Find where Wikipedia has changed

**What you're finding out:** What it means to judge a system that reads today's Wikipedia against
labels made from the Wikipedia of 2017.

HoVer, the public dataset the claims come from, labeled each claim *supported* or *not supported* from
Wikipedia as it was in 2017. The agent, the program in `agent.py`, reads Wikipedia as it is today. So
some of the agent's "wrong" answers may be right about today's Wikipedia. A verdict of *refuted* or
*doesn't say* counts as *not supported*, and the agent's evidence is the sentences it quoted from
Wikipedia.

**What to do:**

1. Start this step's Claude session: in a terminal tab in the homework's folder, run the command the
   homework page shows for 2d. Claude is your Claude Code session, your tutor and lab assistant.
2. Open **Results** at the top of the homework page, then open the run `runs/part2`.
3. Filter the claims table to the claims where the agent's result is wrong: its verdict did not match
   the dataset's label.
4. Open these claims one at a time. For each, decide whether the agent's evidence is sound and today's
   Wikipedia page disagrees with the dataset's label.
5. To see an older version of a page, open the page on Wikipedia, choose "View history", and pick a
   version from 2017. To see today's version as the agent reads it, ask Claude to read it for you with
   `uv run python lookup.py --no-log read "<page title>"`.
6. Find at least two such claims, and fill in a row of the table for each.
7. Stop if you have read ten of the agent's wrong answers and found fewer than two. Use a row of the
   table for the closest case you found, and say so in that row.
8. Answer the question under the table.

**What to write:** Under `## 2d. Find where Wikipedia has changed` in `WRITEUP.md`, fill in the table
and answer:

- Two claims where the agent's evidence is sound and today's Wikipedia disagrees with the dataset's label. If you read ten of the agent's wrong answers and found fewer than two, use a row for the closest case you found, and say so in it.
- What does this tell you about using a fixed dataset to judge a system that reads a live source?

**You're done when:** The homework page ticks 2d. It does that when both rows of the table have every
cell filled and the answer has text after the `>`. With 2d ticked, every step of Part 2 is done, so the
page commits your work as `Part 2 done` and pushes it to your fork.

## What I look for

Part 2 is 35% of the homework. At a minimum I am looking for the following:

- Accuracy and cost: 35% - Your answers to 2a and 2b use numbers from your run, by number of articles.
- Evidence check: 35% - Each of your ten checks in 2c says whether the quote supports the verdict and
  why, and your answer weighs accuracy against how good the evidence is.
- Changed pages: 30% - Each claim you found in 2d shows the dataset's label, what today's page says,
  and what that means for the score.
