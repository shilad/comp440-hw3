# COMP 440 HW3 Part 2: The agent against the baselines

Due 8:00am Thursday, November 19. Back to the [assignment page](../README.md).

In this part you'll run all three versions on the same claims, measure what the agent adds and
what it costs, and check whether its evidence holds up.

## Step 1: Run all three versions on the evaluation sample

- Claude runs `uv run python evaluate.py data/eval.jsonl --out runs/part2`. It runs the no-tools baseline, the
  one-search baseline and your agent (with your instructions from Part 1) on the evaluation
  sample, `data/eval.jsonl`: 200 HoVer claims, about a third each needing two, three and four
  articles, half of them supported.
- This takes a while, about [TBD] minutes, and it costs real API money, so run it once and read
  the results from the saved file. Claude saves every run to `runs/part2/`.
- While it runs, look back at your predictions from Part 1 Step 4.

## Step 2: Compare accuracy

- Claude prints how often each version gave the dataset's verdict, overall and by the number of
  articles a claim needs:

  ```
  [TBD: expected output, from a real run]
  ```

- HoVer labels each claim only *supported* or *not supported*, so *refuted* and *doesn't say*
  both count as *not supported*.
- How do the results compare with your predictions? Where were you most wrong?
- Does the gap between the agent and the one-search baseline grow with the number of articles? If
  not, what may be going on?
- The no-tools baseline didn't read anything. How did it do, and what does that tell you about
  these claims?

## Step 3: Compare cost

- Claude prints, for each version, the average number of tool calls, tokens and seconds per claim.
- How much more does the agent cost than the one-search baseline? For which claims is that cost
  worth paying, and for which isn't it?
- Did the agent ever hit its step limit? What was it doing when it did?

## Step 4: Check the evidence by hand

- Claude picks **ten** claims where the agent answered *supported* or *refuted*. For each one,
  open the quoted sentences on the real Wikipedia page.
- Does each quote actually say what the agent says it does? A quote can be real and still not
  support the verdict.
- How many of the agent's correct verdicts rest on evidence you'd accept? Is accuracy alone a
  good measure of this agent?

## Step 5: Find where Wikipedia has changed

- The datasets were built from Wikipedia as it stood around 2017. Some of the agent's "wrong"
  answers may be right about today's Wikipedia.
- Find **at least two** claims where today's Wikipedia disagrees with the dataset's verdict. For
  each, say what changed on the page, if you can tell.
- Hint: Claude can show you an older version of a page using its revision history.
- What does this tell you about using a fixed dataset to judge a system that reads a live source?

## What to submit

Submit your repository URL through the [assignment submission form](https://forms.gle/mgKcnqzTGxNaGvteA),
choosing "HW3 Part 2" [TBD]. At a minimum I am looking for the following:

- Your answers to every question in Steps 1 to 5 in `WRITEUP.md`.
- The saved runs in `runs/part2/`.
- Your evidence checks from Step 4 and your changed claims from Step 5, in the tables Claude sets
  up in `WRITEUP.md`.

## Grading

- Accuracy and cost: 35% - Your answers to Steps 2 and 3 compare the versions with numbers from
  your run, by number of articles, and say where the agent's extra cost is and isn't worth it.
- Evidence check: 35% - Each of your ten checks says whether the quote supports the verdict and
  why, and your answer weighs accuracy against how good the evidence is.
- Changed pages: 30% - Each claim you found shows the dataset's verdict, what today's page says,
  and what that means for the score.
