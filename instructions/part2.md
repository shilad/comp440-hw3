# COMP 440 HW3 Part 2: The agent against the baselines

In this part you read the full run you started in 1e: how often each version matched the dataset's
label, and whether the agent's evidence supports its verdicts when you check it yourself. It should take
about an hour.

Back to the [assignment page](../README.md).

## 2a. Compare accuracy

In this step you find out how often each of the three versions matched the dataset's label on your 100
evaluation claims. You compare those numbers with your predictions from 1e.

**Words in this step:** *The three versions* are the no-tools baseline, the one-search baseline and the
agent. *The dataset's label* is *supported* or *not supported*; a verdict of *refuted* or *doesn't say*
counts as *not supported*. *The number of articles* is how many Wikipedia articles a claim needs (2, 3
or 4).

**Actions:**

1. Start this step's Claude session (type `/exit` first if another one is open).
2. Check that the full run has finished: it ends with two tables in the tab where you started it.
3. Open **Results** at the top of the homework page, then "runs/part2", and read "Accuracy".
4. Ask Claude to paste the report into the empty block under 2a in `WRITEUP.md`.
5. Type your answers to the three questions in `WRITEUP.md`, in your editor, under 2a.

**Interpreting output:** The report's first table gives, for each version, how many claims matched the
dataset's label out of how many: by number of articles, for all 100, and by the dataset's label. The
"Accuracy" table in the results viewer shows the same counts with percentages. Counts and percentages
are both fine in your answers.

**Write-up:** In `WRITEUP.md`, under 2a, fill in the block and answer:

- Ask Claude to paste the report of your full run, from `runs/part2/report.txt`, into the empty block below.
- How do the results compare with your predictions? Where were you furthest off? Use the numbers from your run, by number of articles.
- Does the gap between the agent and the one-search baseline grow with the number of articles? If it does not, what might explain that?
- The no-tools baseline read nothing. How did it do, and what does that tell you about these claims?

**Troubleshooting:**

- The run stopped early, or its tables end with a line saying some runs stopped with an error. Run
  `uv run python evaluate.py data/eval.jsonl --out runs/part2` again. It keeps every claim it already
  finished.

## 2b. Check the evidence yourself

In this step you find out whether the agent's quoted evidence really supports its verdicts.

**Words in this step:** The *evidence* is the sentences the agent quoted from Wikipedia.

**Actions:**

1. Start this step's Claude session (type `/exit` first if another one is open).
2. Open **Results** at the top of the homework page, then "runs/part2".
3. Click "Clear the filters" under the claims filters.
4. Set "Verdict" in "The agent" box to "supported or refuted"; leave "Order" at "Order of the claims file".
5. Click row 1. Under "Quoted evidence", click each "entry N" to read that quote highlighted in the trace.
6. Decide whether the quoted evidence supports the agent's verdict. If you are unsure, click "open the
   live page" to see today's page at that quote.
7. Fill in its row of the table in `WRITEUP.md`, in your editor, under 2b. In the results viewer, click
   "Next →" and do the same for each row up to row 5.
8. Type your answers to the two questions in `WRITEUP.md`, in your editor, under 2b.

**Interpreting output:** Under "The agent", a claim's page says whether its verdict "matches the
dataset's label": that is the table's fourth column. To read more of a page as the agent read it, ask
Claude to run one of these. `--no-log` keeps them out of `runs/part1/lookups.jsonl`, your 1b record.

```
uv run python lookup.py --no-log read "<page title>"
uv run python lookup.py --no-log read "<page title>" "<section>"
```

**Write-up:** In `WRITEUP.md`, under 2b, fill in the table and answer:

- Fill in one row for each of the first five claims in your Part 2 run, in the order of the claims file, where the agent's verdict is *supported* or *refuted*.
- Of the five, how many matched the dataset's label, and for how many of those does the quoted evidence support the verdict?
- Is accuracy alone a good measure of this agent? Why or why not?

**Hint:** The loop has already checked that each quote appears in something the agent read. A quote can
be real and still not support the verdict. For a verdict of *refuted*, ask whether the quotes show that
the claim is false.

Some claims are worded oddly, because people made them by rewriting other claims. Take each as written,
and if you cannot tell what it asserts, say so in its row.

You type every column. Claude can show you each claim's first words and verdict, but will not say
whether the quoted evidence supports it.

When 2b is ticked, the page commits and pushes your work as `Part 2 done`. Submit it yourself, as the
README's Submitting section says (after Part 3, if you do the extra credit).

## What I look for

Part 2 is 50% of the homework. At a minimum I am looking for the following:

- Accuracy: 50% - Your answers to 2a use numbers from your run, by number of articles.
- Evidence check: 50% - Each of your five checks in 2b says whether the quote supports the verdict and
  why, and your answer weighs accuracy against how good the evidence is.

## Extra credit: find where Wikipedia has changed

This is extra credit, with no step on the homework page. Do it after Part 2, in any Claude session or
with none.

HoVer labeled its claims from Wikipedia as it was in 2017; the agent reads today's Wikipedia. So some
answers that are wrong by the dataset's label may be right about today's Wikipedia.

**Words in this step:** *The closest case* is the wrong answer that came nearest to qualifying.

**Actions:**

1. Open **Results** at the top of the homework page, then "runs/part2".
2. Click "Clear the filters", then set "Result" in "The agent" box to "does not match the dataset's
   label (any reason)".
3. Click the first claim, and "Next →" for each one after it.
4. For each, decide whether its quoted evidence supports its verdict and today's page disagrees with the
   dataset's label.
5. For a claim that qualifies, find its page as it was at the end of 2017 (see the Hint).
6. Stop when you have two such claims, or when you have read ten of the agent's wrong answers. Fill any
   remaining row with the closest case you found, and say in it what kept it from being clear.

**Interpreting output:** A claim's page shows "The dataset's label" at the top. Its links to Wikipedia
open the pages as they are today. To read today's page as the agent reads it, run this (or ask Claude
to):

```
uv run python lookup.py --no-log read "<page title>"
```

**Write-up:** Type a heading `## Extra credit` at the end of `WRITEUP.md`. Under it, copy this, then
fill in the table and type your answer after the `>`:

```
Two claims where the agent's quoted evidence supports its verdict and today's Wikipedia disagrees with the dataset's label. If you read ten of the agent's wrong answers and found fewer than two, fill each remaining row with the closest case you found, and say in that row that it is not a clear case.

| # | Claim (first few words) | The dataset's label | What today's Wikipedia says | What changed on the page, if you can tell |
|---|---|---|---|---|
| 1 | | | | |
| 2 | | | | |

What does this tell you about using a fixed dataset to judge a system that reads a live source?

>
```

**Hint:** To see a page as it was at the end of 2017, open it on Wikipedia, choose "View history", open
"Filter revisions", set "To date" to 31 December 2017 and press "Show revisions". The first row is the
page at the end of 2017.

The homework page does not tick extra credit, but commits it with the rest of your work, as the README's
Extra credit section says.
