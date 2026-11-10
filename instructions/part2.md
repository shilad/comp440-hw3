# COMP 440 HW3 Part 2: The agent against the baselines

Due 8:00am Tuesday, November 24. Back to the [assignment page](../README.md).

In this part you read the full run you started in 1e: how often each version matched the dataset's
label, what each one cost, whether the agent's evidence holds up when you check it yourself, and where
Wikipedia has changed since the dataset was made. It should take about 1 hour and 35 minutes.

## 2a. Compare accuracy

**What you're finding out:** How often each of the three versions matched the dataset's label on the
200 evaluation claims, and how that compares with your predictions from 1e.

**Words in this step:** *the three versions*: the no-tools baseline (the model, Claude Haiku, answers
from memory), the one-search baseline (one search, one page, then an answer) and the agent (the program
in `agent.py`, which picks its own lookups). *the evaluation claims*: the 200 claims in
`data/eval.jsonl`. *the dataset's label*: HoVer's *supported* or *not supported*; a verdict of *refuted*
or *doesn't say* counts as *not supported*. *the number of articles*: how many Wikipedia articles a
claim needs (2, 3 or 4).

**What to do:**

1. Start this step's Claude session with the command the homework page shows for 2a.
2. Check that the full run has finished (see "What you'll see").
3. Open **Results** at the top of the homework page, then open the run `runs/part2`.
4. Ask Claude to paste the report into the empty block under 2a in `WRITEUP.md`.
5. Compare the report's first table with your predictions under 1e in `WRITEUP.md`.
6. Answer the three questions.

**What you'll see:** A finished run ends with two tables in the terminal tab where you started it, and
saves them as `runs/part2/report.txt`. If the run stopped early, or its tables end with a line saying
some runs stopped with an error, run the same command again in a terminal tab in the homework's folder.
It keeps every claim it already finished and checks only the rest:

```
uv run python evaluate.py data/eval.jsonl --out runs/part2
```

The report's first table gives, for each version, how many claims matched the dataset's label, out of
how many: by number of articles, for all 200, and by the dataset's label. Divide to get a percentage.
The run's page in the results viewer shows the same two tables and every claim.

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

**Words in this step:** *the agent*: the program in `agent.py`, a loop in which the model (Claude Haiku)
picks the next lookup, reads what comes back, and decides when to answer. *lookup*: one call to
`search`, `read` or `wikidata`; the loop allows at most 12 for one claim. *the one-search baseline*: one
search, one page, then an answer. *token*: the unit the API counts text in and charges by, about three
quarters of a word. *trace*: the agent's lookups for one claim, in order, with what each returned.

**What to do:**

1. Start this step's Claude session with the command the homework page shows for 2b.
2. Read the report's second table, in the block under 2a in `WRITEUP.md`.
3. Open **Results** at the top of the homework page, then open the run `runs/part2`.
4. Tick the claims table's box for claims where the agent used all 12 lookups.
5. If any are listed, open one and read its trace one lookup at a time.
6. Answer the three questions.

**What you'll see:** The report's second table gives, for each version, the average lookups, tokens,
seconds and cost in dollars per claim.

**What to write:** Under `## 2b. Compare cost` in `WRITEUP.md`, answer:

- How much more does the agent cost per claim than the one-search baseline? Give the numbers.
- For which kinds of claims is that extra cost worth paying, and for which is it not?
- Did the agent ever use all 12 lookups? If so, pick one such claim and say what it was doing.

**You're done when:** The homework page ticks 2b. It does that when the three answers have text after
the `>`. This step makes no files.

## 2c. Check the evidence yourself

**What you're finding out:** Whether the agent's evidence really supports its verdicts, and so whether
accuracy alone is a fair measure of the agent.

The loop already checks that every quoted sentence appears in something the agent read. A quote can be
real and still not support the verdict.

**Words in this step:** *verdict*: *supported*, *refuted* or *doesn't say*. *evidence*: the sentences
the agent quoted from Wikipedia. *the dataset's label*: HoVer's *supported* or *not supported*; a
verdict of *refuted* or *doesn't say* counts as *not supported*.

**What to do:**

1. Start this step's Claude session with the command the homework page shows for 2c.
2. Open **Results** at the top of the homework page, then open the run `runs/part2`.
3. Clear the claims table's filters.
4. In the agent's Verdict list, choose "supported or refuted".
5. Take the first ten rows, in the order the table shows them.
6. Open the first claim and read each quoted sentence where it is highlighted in what the agent read.
7. Decide whether the quotes support the agent's verdict.
8. Use the claim page's "open the live page" link whenever you're unsure.
9. Fill in that claim's row of the table, then do the same for the other nine.
10. Answer the two questions.

**What you'll see:** The table keeps the order of the claims file, so the first ten rows are fixed by the
rule, not chosen. I ask for the first ten so that nobody, you or Claude, chooses which claims get
checked. If you want to read more of a page as the agent read it, ask Claude to run one of these. The
`--no-log` keeps them out of your record from 1b:

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

**Hint:** You can ask Claude to fill in the first three columns (the number, the claim's first few words
and the agent's verdict); the last two are yours. Claude will not say whether a quote supports a
verdict, because that judgment is what this step is about.

## 2d. Find where Wikipedia has changed

**What you're finding out:** What it means to judge a system that reads today's Wikipedia against
labels made from the Wikipedia of 2017.

HoVer, the public dataset the claims come from, labeled each claim *supported* or *not supported* from
Wikipedia as it was in 2017. The agent reads Wikipedia as it is today. So some of the agent's "wrong"
answers may be right about today's Wikipedia.

**Words in this step:** *the agent*: the program in `agent.py`, which checks claims with its own
lookups. *the dataset's label*: HoVer's *supported* or *not supported*; a verdict of *refuted* or
*doesn't say* counts as *not supported*. *evidence*: the sentences the agent quoted from Wikipedia.

**What to do:**

1. Start this step's Claude session with the command the homework page shows for 2d.
2. Open **Results** at the top of the homework page, then open the run `runs/part2`.
3. In the claims table's filters, set the agent's Result to "did not match (any reason)".
4. Open these claims one at a time.
5. For each, decide whether the agent's evidence is sound and today's page disagrees with the label.
6. Look at the page as it was in 2017: on Wikipedia, choose "View history" and pick a 2017 version.
7. Find at least two such claims, and fill in a row of the table for each.
8. Stop if you have read ten of the agent's wrong answers and found fewer than two.
9. In that case, use a row of the table for the closest case you found, and say so in that row.
10. Answer the question under the table.

**What you'll see:** With the Result filter set, the table shows only the claims where the agent's
verdict did not match the dataset's label. To read today's version of a page as the agent reads it, ask
Claude to run:

```
uv run python lookup.py --no-log read "<page title>"
```

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
