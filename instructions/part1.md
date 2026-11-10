# COMP 440 HW3 Part 1: How the agent works

Due 8:00am Tuesday, November 24. Back to the [assignment page](../README.md).

In this part you look inside the agent. You read its loop, check a claim yourself with its four tools,
watch it work on 12 claims, write its instructions, and then start the full run on 200 claims while you
predict how it will do. It should take about 2 hours and 10 minutes, plus about 20 minutes for the
full run, which goes on by itself while you do other things.

## 1a. Read the loop

**What you're finding out:** What one turn of the agent's loop does, how the loop ends, and the two
rules the loop enforces that the model cannot override.

The agent is the program in `agent.py`: a loop in which the model (Claude Haiku, the small Claude model
that the agent and both baselines call) picks the next lookup, reads what comes back, and decides when
to answer. A lookup is one call to `search`, `read` or `wikidata`. Those three and `answer` are the
agent's four tools.

**What to do:**

1. Start this step's Claude session: in a terminal tab in the homework's folder, run the command the
   homework page shows for 1a. Claude is your Claude Code session, your tutor and lab assistant.
2. Open `agent.py` in your editor. It is about 210 lines.
3. Ask Claude to read `agent.py` with you a screenful at a time, from the top. Ask about any line you
   don't follow, as often as you like.
4. Find the function `run_agent()`, which is the loop, and follow one turn of it from start to end.
5. Find where the loop enforces each of its two rules, and note the line numbers. The rules: at most 12
   lookups per claim; and every sentence the agent quotes in its answer must appear in something it read
   in this check, or the answer is rejected.
6. Type your answers in `WRITEUP.md`, in your own words, with the line numbers each question asks for.

**What to write:** Under `## 1a. Read the loop` in `WRITEUP.md`, answer:

- What does the program send to the model on each turn of the loop? Give the line numbers.
- What does the program do when the model asks for a tool? Give the line numbers.
- What are the ways the loop can end? Give the line number of each.
- The loop allows at most 12 lookups per claim. What could go wrong without that limit? Give the line numbers where the loop enforces it.
- The loop rejects an answer when a quoted sentence is not in anything the agent read. What could go wrong without that check? Give the line numbers where the loop makes the check.

**You're done when:** The homework page ticks 1a. It does that when all five answers under 1a have text
after the `>`. This step makes no files.

**Hint:** The comments and messages in `agent.py` call the model "Claude" and call a lookup a "step".
In this homework, "Claude" means your Claude Code session, and the model is Claude Haiku.

**Hint:** In a trace you may see an answer that was sent back (rejected) before a later answer was
accepted. That is the evidence check you are reading here: a quoted sentence was not in anything the
agent had read, and text shown in a search result does not count as read.

## 1b. Be the agent

**What you're finding out:** What the agent's job is like, by doing it yourself with only its four
tools, before you watch it.

I'd like you to do this before you watch the agent do it. You'll read its traces much more closely once
you've made the same choices yourself.

The agent is the program in `agent.py`: a loop in which the model (Claude Haiku, the small Claude model
that the agent and both baselines call) picks the next lookup, reads what comes back, and decides when
to answer. Its four tools:

- `search`: searches Wikipedia and returns the top five page titles, each with a short snippet.
- `read`: returns one section of a Wikipedia page. With no section, it returns the page's opening
  paragraphs and the list of its sections.
- `wikidata`: returns one fact from Wikidata, Wikipedia's sister site, for an entity (such as a person
  or a place) and a property (such as "place of birth" or "population").
- `answer`: ends the check with a verdict and its evidence.

A lookup is one call to `search`, `read` or `wikidata`. A verdict is the answer to a claim: *supported*,
*refuted* or *doesn't say*. Evidence is the sentences quoted from Wikipedia that a verdict rests on.

You check two claims, each one sentence that is either true or false. Claim 1 is short, to learn the
tools:

> Mel Duncan holds a history degree from the private, coeducational liberal arts Macalester
> College located in Saint Paul, Minnesota, US.

Claim 2 is the one the questions are about:

> Vic & Anthony's Steakhouse is located at the American casino that was combined with the
> California Club. The casino is owned by Landry's, Inc.

For claim 2 you have the agent's own limit: at most 12 lookups. If you have made 12 lookups without
settling it, stop and answer *doesn't say*, as the agent would have to.

**What to do:**

1. Start this step's Claude session: in a terminal tab in the homework's folder, run the command the
   homework page shows for 1b. Claude is your Claude Code session, your tutor and lab assistant.
2. Tell Claude you are starting on claim 1.
3. Decide on one lookup: which tool, and what to ask it.
4. Tell Claude that lookup. Claude runs exactly that, with one of these commands, and pastes what came
   back, which is exactly what the agent would see:

   ```
   uv run python lookup.py search "<query>"
   uv run python lookup.py read "<page title>"
   uv run python lookup.py read "<page title>" "<section>"
   uv run python lookup.py wikidata "<entity>" "<property>"
   ```

   Each lookup is added to `runs/part1/lookups.jsonl`, so your lookups are counted the way the agent's
   are.
5. Note why you chose that lookup. You'll type the reasons into the table.
6. Repeat actions 3 to 5 until you have a verdict on claim 1.
7. Tell Claude you are moving on to claim 2, so that it knows which claim each lookup was for.
8. Repeat actions 3 to 5 for claim 2, until you have a verdict or have made 12 lookups for it.
9. Ask Claude to paste your lookups into the table under 1b in `WRITEUP.md`. Claude fills in every
   column but the last, from `runs/part1/lookups.jsonl`.
10. Type your reason for each lookup in the "Why you chose it" column.
11. Answer the four questions under the table.

Use **only** these tools, not your browser: the point is to see only what the agent sees. Your verdicts
go in `WRITEUP.md`, so there is no `answer` call. Claude will not suggest a lookup or say what a result
means, since making those choices is the point of this step.

**What to write:** Under `## 1b. Be the agent` in `WRITEUP.md`, fill in the table and answer:

- Your lookups for both claims, in order. Ask Claude to paste every column but the last from `runs/part1/lookups.jsonl`. Type every "Why you chose it" yourself.
- Your verdict on the first claim, and the sentence it rests on.
- Your verdict on the second claim, and the sentence or sentences it rests on. If you stopped at 12 lookups without settling it, your verdict is *doesn't say*: say where you got stuck.
- How many lookups did the second claim take? Which one was hardest to choose, and why?
- Did you have to back up and try something else? What happened?

**You're done when:** The homework page ticks 1b. It does that when `runs/part1/lookups.jsonl` exists
(it does after your first lookup), every numbered row of the table has every cell filled, and the four
answers have text after the `>`.

**If something goes wrong:**

- A lookup finds no page, or no such section: that is a result like any other, and the agent would
  have seen the same thing. Count it, and choose your next lookup from what it told you.
- A page title with `&` or an apostrophe in it must be inside double quotes in the command, as in
  `uv run python lookup.py read "<page title>"`, or the shell misreads it. If a lookup fails in a way
  you don't expect, check that Claude's command has the title in double quotes.

## 1c. Watch the agent work

**What you're finding out:** Whether the agent reaches the dataset's label on the 12 development claims,
and whether it gets there for a good reason.

The agent is the program in `agent.py`: a loop in which the model (Claude Haiku) picks the next lookup,
reads what comes back, and decides when to answer. The development claims are the 12 claims in
`data/dev.jsonl`. They come from HoVer, a public dataset of claims that each need 2, 3 or 4 Wikipedia
articles to check: that is a claim's number of articles. The dataset's label is HoVer's *supported* or
*not supported*, and a verdict of *refuted* or *doesn't say* counts as *not supported*.

**What to do:**

1. Start this step's Claude session: in a terminal tab in the homework's folder, run the command the
   homework page shows for 1c. Claude is your Claude Code session, your tutor and lab assistant.
2. Ask Claude to run the agent on the 12 development claims. It takes about a minute and costs about 2
   cents on your key. Claude runs this command:

   ```
   uv run python evaluate.py data/dev.jsonl --methods agent --out runs/part1/before
   ```

   The folder is called `before` because in 1d you write the agent's instructions and run the same
   claims again, into `runs/part1/after`.
3. Tell Claude what you expect, when it asks.
4. Read the two tables the run prints at the end. The first shows how many claims matched the dataset's
   label, by number of articles and by the dataset's label. The second shows the average lookups, tokens, seconds and cost per
   claim. Tokens are the unit the API counts text in and charges by, about three quarters of a word.
5. Open **Results** at the top of the homework page, then open the run `runs/part1/before`.
6. Choose six claims to read closely: two that need 2 articles, two that need 3, and two that need 4.
   For each number of articles, choose one the agent got right and one it got wrong, where there is
   one. One of the six must be claim 2 from 1b, the claim about Vic & Anthony's Steakhouse, so that
   you can set the agent's lookups beside your own. The claims table can be filtered by the number of
   articles a claim needs and by the agent's result (whether it matched the label).
7. Open each of the six claims and read its trace one lookup at a time. A trace is the list of the
   agent's lookups for one claim, in order, with what each returned. Each sentence the agent quoted is
   highlighted where it appears in what the agent read.
8. Decide, for each of the six, whether the agent got there for a good reason: does its evidence, the
   sentences it quoted from Wikipedia, settle the claim?
9. Fill in one row of the table for each claim, and answer the question under it.

**What to write:** Under `## 1c. Watch the agent work` in `WRITEUP.md`, fill in the table and answer:

- The six traces you read closely: two claims each that need 2, 3 and 4 articles. For each number of articles, one the agent got right and one it got wrong, where there is one.
- Which trace did you find most interesting, and what did the agent do well or badly in it?

**You're done when:** The homework page ticks 1c. It does that when `runs/part1/before/report.txt`
exists (the run saves it when it finishes), all six rows of the table have every cell filled, and the
answer has text after the `>`.

**If something goes wrong:** If the run stops partway, ask Claude to run the same command again. It
keeps every claim it already finished and checks only the rest.

## 1d. Write the agent's instructions

**What you're finding out:** How much the agent's behavior depends on its instructions.

The agent is the program in `agent.py`: a loop in which the model (Claude Haiku) picks the next lookup,
reads what comes back, and decides when to answer. Its instructions are in `instructions.md`: the
program sends them to the model on every turn of the loop. The file starts with three sentences that
name the job and the four tools (`search`, `read`, `wikidata` and `answer`) and say nothing about how to
use them. The development claims are the 12 claims in `data/dev.jsonl`.

**What to do:**

1. Start this step's Claude session: in a terminal tab in the homework's folder, run the command the
   homework page shows for 1d. Claude is your Claude Code session, your tutor and lab assistant.
2. Open `instructions.md` in your editor.
3. Write your own instructions in it, and save the file. At a minimum they must say:
   - how to break a claim into the pieces that have to be checked;
   - when to use `wikidata` instead of reading a page;
   - when the agent has enough evidence to stop;
   - when to answer *doesn't say*.

   You can do this however you want, but I recommend writing short, direct rules and changing one
   thing at a time. It is hard to tell what helped when you change everything at once. Claude will not
   write or suggest text for `instructions.md`, because what the agent is told is your decision.
4. Ask Claude to run the agent on the 12 development claims again, with your instructions. It takes
   about a minute and costs about 2 cents, or more if your instructions make the agent do more. Claude
   runs this command:

   ```
   uv run python evaluate.py data/dev.jsonl --methods agent --out runs/part1/after
   ```

5. Open **Results** at the top of the homework page, choose "Compare two runs", and compare
   `runs/part1/before` with `runs/part1/after`.
6. Read the claims whose verdict changed, with their traces before and after side by side. Then open a
   few claims whose verdict stayed the same, in each run, to see whether their lookups changed. A trace
   is the list of the agent's lookups for one claim, in order, with what each returned. The model does
   not give the same answer every time, so 12 claims are too few to prove a change helped. Read the
   traces, not only the score.
7. Each time you change `instructions.md` again and want to see the effect, ask Claude to run the same
   command with `--fresh` at the end. Without `--fresh`, a run never checks a claim again once its
   result is saved, and `--fresh` replaces this folder's saved results with a new run:

   ```
   uv run python evaluate.py data/dev.jsonl --methods agent --out runs/part1/after --fresh
   ```

   Then compare the two runs again.

**What to write:** Under `## 1d. Write the agent's instructions` in `WRITEUP.md`, answer:

- What changed in the agent's traces after you wrote your instructions? Give one claim as an example.
- Was that the change you expected? If not, what do you think happened?

**You're done when:** The homework page ticks 1d. It does that when `runs/part1/after/report.txt`
exists (the run saves it when it finishes) and both answers have text after the `>`.

## 1e. Start the full run, and predict

**What you're finding out:** Nothing yet. You start the run on the 200 evaluation claims and write down
your predictions before you see any results.

The run checks the 200 evaluation claims in `data/eval.jsonl` with all three versions: the no-tools
baseline (the model, Claude Haiku, answers from memory), the one-search baseline (one search, one page,
then an answer) and the agent (the program in `agent.py`, which picks its own lookups). The agent uses
your `instructions.md` from 1d. A version gets a claim right when its verdict matches the dataset's
label: HoVer's *supported* or *not supported*, where a verdict of *refuted* or *doesn't say* counts as
*not supported*. Each claim needs 2, 3 or 4 Wikipedia articles to check: that is its number of
articles.

**What to do:**

1. Start this step's Claude session: in a terminal tab in the homework's folder, run the command the
   homework page shows for 1e. Claude is your Claude Code session, your tutor and lab assistant.
2. Open another new terminal tab, and go into the homework's folder (the `comp440-hw3` folder you
   cloned).
3. Start the full run yourself, in that tab:

   ```
   uv run python evaluate.py data/eval.jsonl --out runs/part2
   ```

   It takes about 20 minutes and costs about 50 cents on your key. It runs the
   no-tools baseline on all 200 claims, then the one-search baseline, then the agent, and prints a
   progress line every ten claims. Start it in your own tab, because a run started by Claude stops if
   you close that Claude session.
4. Leave that tab open, and your laptop awake, until the run ends with two tables.
5. Leave `instructions.md` alone until the run has finished, since the agent reads it again for every
   claim.
6. Don't look at the run's results, in the terminal or in the results viewer, until your predictions
   are typed and saved.
7. Fill in the predictions table under 1e in `WRITEUP.md`: for each version and each number of
   articles, the share of claims you think it will get right, as a percentage. A guess is fine; the
   reasons are what I grade. Claude will not suggest a number, because the predictions are yours.
8. Answer the question under the table.

**What to write:** Under `## 1e. Start the full run, and predict` in `WRITEUP.md`, fill in the table
and answer:

- Your predictions: the share of claims each version will get right (its verdict matches the dataset's label), as a percentage. A guess is fine; the reasons are what I grade.
- How many lookups will the agent make per claim, on average? Will that grow with the number of articles? Why?

**You're done when:** The homework page ticks 1e. It does that when the run has started (the file
`runs/part2/no-tools.jsonl` exists), every cell of the table's three rows is filled, and the answer has
text after the `>`. The run doesn't need to have finished. With 1e ticked, every step of Part 1 is done,
so the page commits your work as `Part 1 done` and pushes it to your fork. Once the run has ended, this
is a good place to stop for the day.

**If something goes wrong:** If the run stops, because you closed the tab, your laptop slept or
Wikipedia refused requests for too long, run the same command again in a terminal tab in the homework's
folder. It keeps every claim it already finished and checks only the rest.

## What I look for

Part 1 is 25% of the homework. At a minimum I am looking for the following:

- The loop: 25% - Your answers to 1a say what the loop does in your own words and point to the lines of
  `agent.py`.
- Being the agent: 20% - Your 1b record shows each lookup and why you chose it, and names the hardest
  choice.
- Predictions: 15% - Each prediction in 1e has a reason. They are graded on the reasoning, not on being
  right.
- Instructions: 40% - Your `instructions.md` covers the four points in 1d, and your 1d answers compare
  the traces before and after with a specific example.
