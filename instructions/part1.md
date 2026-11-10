# COMP 440 HW3 Part 1: The loop and the tools

Due 8:00am Thursday, November 19. Back to the [assignment page](../README.md).

In this part you'll learn how the agent works from the inside, try its tools yourself, predict how
it will do, and write its instructions.

## Step 1: Read the loop

- Open `agent.py` with Claude. It is about 180 lines. Have Claude walk you through it from top
  to bottom.
- Answer three questions in your own words:
  - What does Claude get sent on each turn of the loop?
  - What happens when Claude asks for a tool?
  - What are the two ways the loop can stop?
- Hint: the part that makes this an agent is small. Look for the line where the program decides
  what to do next based on what the model sent back.

## Step 2: Be the agent

- The agent has four tools:
  - `search(query)`: searches Wikipedia and returns the top titles with a short snippet of each.
  - `read(title, section)`: returns one section of a page. Called with no section, it returns the
    page's opening paragraphs and its list of sections.
  - `wikidata(entity, property)`: returns one structured fact from Wikidata, Wikipedia's sister
    site, such as a birth date or a population.
  - `answer(verdict, evidence)`: ends the run with *supported*, *refuted* or *doesn't say*, and the
    sentences the verdict rests on.
- Claude gives you a three-article claim from the sample. Check it yourself using **only** these
  four tools: tell Claude which tool to call and with what, one call at a time, and Claude runs it
  with `uv run python lookup.py`, which shows you exactly what the agent would see and logs each
  call to `runs/part1/lookups.jsonl`.
- Count your calls. Which call was the hardest to choose, and why? Did you ever need to back up?
- I'd like you to do this before you watch the agent do it. You'll read its traces much more
  closely once you've made the same choices yourself.

## Step 3: Meet the guardrails

- The loop does two things the model doesn't control:
  - It allows at most 12 tool calls per claim. After that, the agent must answer.
  - It checks every quoted sentence in `answer()` against the pages the agent actually read in this
    run. If a quote isn't there, the loop rejects the answer and tells the agent why.
- Why might each of these matter? What could go wrong without them?

## Step 4: Predict

- Before running anything at scale, predict the accuracy of each of the three versions (no tools,
  one search, agent) on claims that need two, three and four articles. A guess is fine. Claude
  writes your predictions into a table in `WRITEUP.md`.
- Also predict roughly how many tool calls the agent will use per claim, and whether that number
  will grow with the number of articles.
- Give a sentence of reasoning for each version.

## Step 5: Watch the agent work

- Claude runs the agent on **six** claims from `data/dev.jsonl`, two each needing two, three and
  four articles.
- Read the traces with Claude. For each one: did it get the right verdict, and did it get there
  for the right reason?
- Pick the trace you found most interesting and say what the agent did well or badly in it.

## Step 6: Write the agent's instructions

- The agent's instructions are in `instructions.md`. It starts nearly empty: it
  says what the four tools are and nothing about how to use them.
- Write your own instructions. At a minimum they should say:
  - how to break a claim into the pieces that have to be checked;
  - when to use `wikidata()` instead of reading a page;
  - when the agent has enough evidence to stop;
  - when to answer *doesn't say*.
- Claude reruns the same six claims with your instructions. What changed in the traces? Was it the
  change you expected?
- You can do this however you want, but I recommend writing short, direct rules and changing one
  thing at a time. It is hard to tell what helped when you change everything at once.

## What to submit

Submit your repository URL through the [assignment submission form](https://forms.gle/mgKcnqzTGxNaGvteA),
choosing "HW3 Part 1" [TBD]. At a minimum I am looking for the following:

- Your answers to every question in Steps 1 to 6 in `WRITEUP.md`, including your predictions table.
- Your own `instructions.md`.
- The traces from Steps 5 and 6 in `runs/part1/`.

## Grading

- The loop: 25% - Your answers to Step 1 and Step 3 say what the loop does in your own words and
  point to the lines of `agent.py` that do it.
- Being the agent: 20% - Your Step 2 record shows each call you chose and why, and names the
  hardest choice.
- Predictions: 15% - Each prediction has a reason. They are graded on the reasoning, not on whether
  they turn out right.
- Instructions: 40% - Your `instructions.md` covers the four points above, and your Step 6 answer
  compares the traces before and after with specific examples.
