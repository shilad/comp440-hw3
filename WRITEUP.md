# HW3 write-up

Name:

Answer each question under it, in your own words. Claude can fill in tables and numbers from your
runs, but the answers to the questions are yours. Each step's full instructions are on the
assignment page.

# Part 0: Set up

## Step 1: Get the repository and start Claude

Nothing to write here. `/setup` checks that everything works.

## Step 2: Ask the model on its own

What did it say? How much would you trust it, and why?

>

## Step 3: Run one search

Which page did it read? Was it the page that settles the claim? If not, why did the search land
there?

>

## Step 4: Run the agent and read its trace

How did the agent break the claim into pieces? Was there a step you would have done differently?

>

# Part 1: The loop and the tools

## Step 1: Read the loop

What does Claude get sent on each turn of the loop?

>

What happens when Claude asks for a tool?

>

What are the two ways the loop can stop?

>

## Step 2: Be the agent

The claim you checked:

>

Your calls, in order (Claude copies them from `runs/part1/lookups.jsonl`):

| # | Tool | What you asked for | Why |
|---|------|--------------------|-----|
| 1 | | | |

Your verdict and the evidence it rests on:

>

How many calls did you make? Which call was the hardest to choose, and why? Did you ever need to
back up?

>

## Step 3: Meet the guardrails

Why might the step limit and the evidence check matter? What could go wrong without them?

>

## Step 4: Predict

| Version | 2 articles | 3 articles | 4 articles | Why you think so |
|---------|------------|------------|------------|------------------|
| No tools | | | | |
| One search | | | | |
| Agent | | | | |

How many tool calls will the agent use per claim, and will that grow with the number of articles?

>

## Step 5: Watch the agent work

| Claim | Articles | Right verdict? | For the right reason? |
|-------|----------|----------------|-----------------------|
| | | | |

The trace you found most interesting, and what the agent did well or badly in it:

>

## Step 6: Write the agent's instructions

Your instructions are in `instructions.md`. What changed in the traces when Claude reran the six
claims? Was it the change you expected?

>

# Part 2: The agent against the baselines

## Step 1: Run all three versions on the evaluation sample

Nothing to write here. The runs are saved in `runs/part2/`.

## Step 2: Compare accuracy

The results table (Claude pastes it from the evaluation report):

```
```

How do the results compare with your predictions? Where were you most wrong?

>

Does the gap between the agent and the one-search baseline grow with the number of articles? If
not, what may be going on?

>

The no-tools baseline didn't read anything. How did it do, and what does that tell you about these
claims?

>

## Step 3: Compare cost

How much more does the agent cost than the one-search baseline? For which claims is that cost worth
paying, and for which isn't it?

>

Did the agent ever hit its step limit? What was it doing when it did?

>

## Step 4: Check the evidence by hand

| Claim | Verdict | Does the evidence support it? | Why or why not |
|-------|---------|-------------------------------|----------------|
| | | | |

How many of the agent's correct verdicts rest on evidence you'd accept? Is accuracy alone a good
measure of this agent?

>

## Step 5: Find where Wikipedia has changed

| Claim | Dataset's verdict | Today's Wikipedia says | What changed on the page |
|-------|-------------------|------------------------|--------------------------|
| | | | |

What does this tell you about using a fixed dataset to judge a system that reads a live source?

>

# Part 3: Your own claims

## Step 1: Pick a topic and write your claims

Your topic:

>

Your claims (Claude copies them into `data/my-claims.jsonl` so the agent can run on them):

| # | Claim | Your verdict | Source you'd trust |
|---|-------|--------------|--------------------|
| 1 | | | |

## Step 2: Run the agent and the one-search baseline

For which claims did they agree with you? Did anything surprise you?

>

## Step 3: Sort the failures

| Claim | Your label | The trace line that shows it | Claude's label |
|-------|------------|------------------------------|----------------|
| | | | |

Where did you and Claude disagree, and who do you think is right?

>

Which failure was most common?

>

## Step 4: Make one change

What you changed, and why:

>

The reruns are saved in `runs/part3/after/` (your claims) and `runs/part3/after-eval/` (the Part 2
evaluation sample).

Did it fix what you aimed at? What did it cost?

>

## Step 5: Write it up

### Write-up

What does the loop add over one search? Use your numbers from Part 2 and your claims from Part 3.

>

What does it cost, and when would you not use an agent for this?

>

What did your topic show you about Wikipedia as a source? Where it was thin or wrong, why might
that be, given who writes it?

>

### How I used AI

How you used AI in this assignment, what you checked, and one decision you made yourself.

>
