# COMP 440 HW3 Part 2: The agent against the baselines

Due 8:00am Tuesday, November 24. Back to the [assignment page](../README.md).

In this part you read the full run you started in 1e: how often each version matched the dataset's
label, what each one cost, and whether the agent's evidence holds up when you check it yourself. It
should take about 1 hour and 35 minutes.

## 2a. Compare accuracy

**What you're finding out:** How often each of the three versions matched the dataset's label on the
200 evaluation claims, and how that compares with your predictions from 1e.

**Words in this step:** *the three versions*: the no-tools baseline (the model, Claude Haiku, answers
from memory), the one-search baseline (one search, one page, then an answer) and the agent (the program
in `agent.py` and its loop, which picks its own lookups). *the dataset's label*: the label that HoVer, the public dataset these claims come from, gives
each claim: *supported* or *not supported*. A verdict of *refuted* or *doesn't say* counts as
*not supported*. *the number of articles*: how many
Wikipedia articles a claim needs (2, 3 or 4).

**What to do:**

1. Start this step's Claude session with the command the homework page shows for 2a, in a terminal tab in the
   homework's folder. If the last step's Claude is still open in that tab, type `/exit` first.
2. Check that the full run has finished (see "What you'll see").
3. Open **Results** at the top of the homework page, then "runs/part2", and read "Accuracy".
4. Ask Claude to paste the report into the empty block under 2a in `WRITEUP.md`.
5. Compare the report's first table with your predictions under 1e.
6. Answer the three questions.

**What you'll see:** A finished run ends with two tables in the tab where you started it, and saves them
as `runs/part2/report.txt`. If it stopped early, or its tables end with a line saying some runs stopped
with an error, run the same command again in a terminal tab in the homework's folder; it keeps every
claim it already finished:

```
uv run python evaluate.py data/eval.jsonl --out runs/part2
```

The first table gives, for each version, how many claims matched the dataset's label out of how many:
by number of articles, for all 200, and by the dataset's label. The "Accuracy" table in the results
viewer shows the same counts with percentages.

**What to write:** In `WRITEUP.md`, under 2a, fill in the block and answer:

- The report of your full run, from `runs/part2/report.txt`. Ask Claude to paste it into the empty block below.
- How do the results compare with your predictions? Where were you furthest off? Use the numbers from your run, by number of articles.
- Does the gap between the agent and the one-search baseline grow with the number of articles? If it does not, what might explain that?
- The no-tools baseline read nothing. How did it do, and what does that tell you about these claims?

**You're done when:** The homework page ticks 2a: `runs/part2/report.txt` exists, the block holds the
report, and the three answers have text after the `>`.

## 2b. Compare cost

**What you're finding out:** What the agent costs compared with the one-search baseline, and when that
extra cost is worth paying.

**Words in this step:** *lookup*: one call to `search`, `read` or `wikidata`; the loop allows at most 12
for one claim. *token*: the unit the API counts text in and charges by, about three quarters of a word.
*trace*: the agent's lookups for one claim, in order, with what each returned.

**What to do:**

1. Start this step's Claude session with the command the homework page shows for 2b, in a terminal tab in the
   homework's folder. If the last step's Claude is still open in that tab, type `/exit` first.
2. Read the report's second table, in the block under 2a in `WRITEUP.md`.
3. Open **Results** at the top of the homework page, then "runs/part2", and read "Cost".
4. Tick "Only claims where the agent used all 12 lookups" in the claims filters.
5. If any are listed, click one and read "The agent's trace".
6. Answer the three questions.

**What you'll see:** The second table gives, for each version, the average lookups, tokens, seconds and
dollars per claim. The results viewer's "Cost" section has the same "Average per claim" table, the
totals, and "The agent used all 12 lookups on N claims.", where "N claims" links to those claims.

**What to write:** In `WRITEUP.md`, under 2b:

- How much more does the agent cost per claim than the one-search baseline? Give the numbers.
- For which kinds of claims (for example by number of articles, or by what the claim asks) is that extra cost worth paying, and for which is it not?
- Did the agent ever use all 12 lookups? If so, pick one such claim and say what it was doing.

**You're done when:** The homework page ticks 2b: the three answers have text after the `>`.

## 2c. Check the evidence yourself

**What you're finding out:** Whether the agent's quoted evidence really supports its verdicts, and so
whether accuracy alone is a fair measure of the agent.

The loop already checks that every quoted sentence appears in something the agent read. A quote can be
real and still not support the verdict. For a verdict of *refuted*, the question is whether the quotes
show that the claim is false.

**Words in this step:** *verdict*: *supported*, *refuted* or *doesn't say*. *evidence*: the sentences
the agent quoted from Wikipedia. *the dataset's label*: the label that HoVer, the public dataset
these claims come from, gives each claim, *supported* or *not supported*.
*entry*: one numbered line of a trace, a lookup or an answer.

**What to do:**

1. Start this step's Claude session with the command the homework page shows for 2c, in a terminal tab in the
   homework's folder. If the last step's Claude is still open in that tab, type `/exit` first.
2. Open **Results** at the top of the homework page, then "runs/part2".
3. Click "Clear the filters" under the claims filters.
4. Set "Verdict" in "The agent" box to "supported or refuted"; leave "Order" at "Order of the claims file".
5. Take rows 1 to 5.
6. Click row 1. Under "Quoted evidence", click "entry N" to read each quote highlighted.
7. Decide whether the quoted evidence supports the agent's verdict.
8. Click "open the live page" whenever you're unsure, to see today's page at that quote.
9. Fill in that claim's row of the table, then click "Next →" for row 2, and so on to row 5.
10. Answer the two questions.

**What you'll see:** The "Row" column counts the rows shown, in the order of the claims file, so rows 1
to 5 are fixed by the rule. I ask for the first five so that nobody, you or Claude, chooses which claims
get checked. A claim's page says, under "The agent", whether its verdict "matches the dataset's label":
that is the table's fourth column. To read more of a page as the agent read it, ask Claude to run one of these (`--no-log`
keeps them out of your record from 1b):

```
uv run python lookup.py --no-log read "<page title>"
uv run python lookup.py --no-log read "<page title>" "<section>"
```

**What to write:** In `WRITEUP.md`, under 2c, fill in the table and answer:

- The first five claims in your Part 2 run, in the order of the claims file, where the agent's verdict is *supported* or *refuted*.
- Of the five, how many matched the dataset's label, and for how many of those does the quoted evidence support the verdict?
- Is accuracy alone a good measure of this agent? Why or why not?

**You're done when:** The homework page ticks 2c: all five rows are filled, and both answers have text
after the `>`. That finishes Part 2, so the page commits your work as `Part 2 done` and pushes it to
your fork.

**Hint:** You type all the columns. Claude can show you each claim's first words and the agent's
verdict in the chat. Claude will not say whether the quoted evidence supports a verdict, because that
judgment is what this step is about.

## What I look for

Part 2 is 35% of the homework. At a minimum I am looking for the following:

- Accuracy and cost: 50% - Your answers to 2a and 2b use numbers from your run, by number of articles.
- Evidence check: 50% - Each of your five checks in 2c says whether the quote supports the verdict and
  why, and your answer weighs accuracy against how good the evidence is.

## Extra credit: find where Wikipedia has changed

This is extra credit, and it has no step on the homework page. Do it after Part 2, in any Claude
session you like (the homework page can take you back to 2c's), or with none.

**What you're finding out:** What it means to judge a system that reads today's Wikipedia against
labels made from the Wikipedia of 2017.

HoVer labeled its claims from Wikipedia as it was in 2017; the agent reads it as it is today. So some
of the agent's "wrong" answers may be right about today's Wikipedia.

**Words in this step:** *the dataset's label*: the label that HoVer, the public dataset these claims come from, gives
each claim: *supported* or *not supported*. A verdict of *refuted* or *doesn't say* counts as
*not supported*. *evidence*: the sentences the agent quoted from Wikipedia.
*the closest case*: the claim that came nearest, and what kept it from being clear.

**What to do:**

1. Open **Results** at the top of the homework page, then "runs/part2".
2. Click "Clear the filters" under the claims filters.
3. Set "Result" in "The agent" box to "does not match the dataset's label (any reason)".
4. Click these claims one at a time; "Next →" goes to the next one.
5. For each, decide whether its quoted evidence supports its verdict and today's page disagrees with the label.
6. For a claim you think qualifies, look at its page as it was at the end of 2017 (see the Hint).
7. Find at least two such claims.
8. Stop if you have read ten of the agent's wrong answers and found fewer than two.
9. In that case, use the closest case you found for each remaining row, and say it is not a clear case.
10. Type a heading `## Extra credit` at the end of `WRITEUP.md`, and under it the table and question below.

**What you'll see:** A claim's page shows "The dataset's label" at the top, and "The dataset lists these
articles for this claim:" and "Pages it read, live on Wikipedia today:" link to today's pages. The
results viewer cannot show older versions; Wikipedia's "View history" can. To read today's page as the
agent reads it, ask Claude to run this, or run it yourself in a terminal in the homework's folder:

```
uv run python lookup.py --no-log read "<page title>"
```

**What to write:** Under `## Extra credit` at the end of `WRITEUP.md`, copy this, then fill in the table
and type your answer after the `>`:

```
Two claims where the agent's quoted evidence supports its verdict and today's Wikipedia disagrees with the dataset's label. If you read ten of the agent's wrong answers and found fewer than two, fill each remaining row with the closest case you found, and say in that row that it is not a clear case.

| # | Claim (first few words) | The dataset's label | What today's Wikipedia says | What changed on the page, if you can tell |
|---|---|---|---|---|
| 1 | | | | |
| 2 | | | | |

What does this tell you about using a fixed dataset to judge a system that reads a live source?

>
```

**You're done when:** Both rows are filled and the question has an answer. The homework page does not
tick extra credit. It commits it with the rest of your work, as the Extra credit section of the README
says.

**Hint:** For a claim you think qualifies, open the Wikipedia page that holds the fact. Choose "View
history", open "Filter revisions", set "To date" to 31 December 2017 and press "Show revisions". The
first row is the page as it was at the end of 2017. This is for the table's last column; if you can't
tell what changed, say so there.
