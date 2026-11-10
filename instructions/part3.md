# COMP 440 HW3 Part 3: Your own claims

Due 8:00am Thursday, November 19. Back to the [assignment page](../README.md).

In this part you'll test the agent on a topic you know better than most people, sort out why it
fails, make one change, and write up what you found.

## Step 1: Pick a topic and write your claims

- Pick a topic you know well, and that Wikipedia covers at least a little: your hometown, a band, a
  sport, a game, a field you've studied, Macalester. Something you could fact-check yourself
  without looking much up.
- Write **at least eight** claims about it. Include:
  - some that are true and some that are false;
  - at least two that need two or more Wikipedia articles to check;
  - at least two where you think Wikipedia doesn't say, or says something you think is wrong.
- For each claim, write your own verdict and the source you'd trust for it, in the table in
  `WRITEUP.md`. Claude copies the claims into `data/my-claims.jsonl` so the agent can run on them.
- Hint: false claims are most interesting when they are close to true. Change one fact (a year, a
  place, a name) rather than inventing something absurd.

## Step 2: Run the agent and the one-search baseline

- Claude runs both on your claims with
  `uv run python evaluate.py data/my-claims.jsonl --methods one-search,agent --out runs/part3/before`
  and saves the traces there.
- For which claims did they agree with you? Did anything surprise you?

## Step 3: Sort the failures

- For every claim where the agent's verdict differs from yours, read the trace and give it one
  label:
  - *wrong page*: it never found the page that settles the claim;
  - *stopped too early*: it answered before checking every piece;
  - *misread*: it read the right page and drew the wrong conclusion;
  - *wouldn't say "doesn't say"*: it forced a verdict Wikipedia doesn't support;
  - *Wikipedia is missing or wrong*: the agent did fine, and Wikipedia let it down;
  - or a label of your own, if none of these fit.
- Have Claude label the same traces without seeing your labels, then compare. Where did you
  disagree, and who do you think is right?
- Which failure was most common?

## Step 4: Make one change

- Make **one** change aimed at your most common failure. It can be to your instructions, to a
  tool (for example, what `search()` returns), or to the step limit.
- Claude reruns the agent on your claims and on the Part 2 evaluation sample, so you can see
  whether the change helped one and hurt the other:

  ```
  uv run python evaluate.py data/my-claims.jsonl --methods agent --out runs/part3/after
  uv run python evaluate.py data/eval.jsonl --methods agent --out runs/part3/after-eval
  ```

  Compare the first with `runs/part3/before`, and the second with the agent's row in `runs/part2`.
- Did it fix what you aimed at? What did it cost?

## Step 5: Write it up

- In the `Write-up` section of `WRITEUP.md`, answer in a few paragraphs:
  - What does the loop add over one search? Use your numbers from Part 2 and your claims from
    Part 3.
  - What does it cost, and when would you not use an agent for this?
  - What did your topic show you about Wikipedia as a source? Where it was thin or wrong, why
    might that be, given who writes it?
- Add a short account of how you used AI in this assignment, what you checked, and one decision
  you made yourself, as the syllabus asks.

## What to submit

Submit your repository URL through the [assignment submission form](https://forms.gle/mgKcnqzTGxNaGvteA),
choosing "HW3 Part 3" [TBD]. At a minimum I am looking for the following:

- Your claims, with your own verdicts and sources, in the table Claude sets up in `WRITEUP.md`.
- Your failure labels and Claude's, side by side.
- Your one change, and the runs before and after it in `runs/part3/` (`before`, `after` and
  `after-eval`).
- Your write-up and AI-use account.

## Grading

- Your claims: 20% - At least eight, with the mix above, each with your verdict and a source.
- Failure labels: 30% - Each label is backed by the line of the trace that shows it, and you explain
  where you and Claude disagreed.
- Your change: 20% - It targets your most common failure, and you report its effect on both your
  claims and the evaluation sample.
- Write-up: 30% - Your answers use your own numbers and examples, and the Wikipedia question goes
  beyond "it was missing" to why.

## Extra credit

Give the agent a fifth tool that reads one other well-known public site (for example, a
government statistics site or an encyclopedia other than Wikipedia [TBD: which sites are allowed]),
and rerun your claims. When do the two sources disagree, and how should the agent decide which to
believe?
