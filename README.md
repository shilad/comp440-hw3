# COMP 440 HW3: Checking Claims Against Wikipedia

In this homework assignment you will study a small AI agent that checks claims against Wikipedia, and
measure what it adds over simpler methods. You will:

- Understand what makes a program an *agent*: a language model that picks the next thing to look up,
  reads what comes back, and decides when to stop.
- Gain hands-on experience with the loop around the model: its tools, its instructions, its limit of
  12 lookups, and the check that every sentence it quotes really appears in what it read.
- Compare the agent with two simpler methods, and measure where it helps, where it doesn't, and what
  it costs.
- Apply it to claims you write about a topic you know well, and find out where Wikipedia, which is
  written by its volunteer editors, is thin, out of date or wrong.

## The task

The agent is given a claim, one sentence that is either true or false, and nothing else. Here is the
claim you'll check in Part 0:

> [[SAMPLE_CLAIM]]

The agent has to give a *verdict*: *supported*, *refuted* or *doesn't say*. It also has to quote the
sentences from Wikipedia that its verdict rests on, its *evidence*. No source comes with the claim.
The agent finds its own evidence by searching and reading Wikipedia as it is today.

The claims in this homework come from HoVer, a public dataset of claims that each need two, three or
four Wikipedia articles to check. One search usually finds one of those articles at most. To check the
whole claim, the agent has to work out what the claim is made of, look up each piece, and put the
pieces together. That is what you'll study.

## What you need before you start

You used all of these in earlier homeworks:

- Claude Code, installed and signed in.
- `uv`, the Python package manager. Check it with `uv --version`.
- git, and your GitHub account.
- A text editor. You type every answer in it.
- Your API key. I sent you your own API key by Slack direct message. The agent calls the Claude API
  directly, not through your Claude Code account, so it needs this key.

## Getting started

1. Fork the repository on GitHub: open <https://github.com/shilad/comp440-hw3> and click **Fork**.
2. Clone your fork. Put your GitHub username in place of `<your-username>`:

   ```
   git clone https://github.com/<your-username>/comp440-hw3
   ```

3. Go into the folder:

   ```
   cd comp440-hw3
   ```

4. Start the homework page:

   ```
   uv run python -m workbench
   ```

   It opens the homework page in your browser and prints its address. Leave this terminal tab open
   while you work: closing it stops the page. To start the page again later, go into the folder and run
   the same command.

5. On the homework page, open step 0a and follow it from there.

## How this homework works

- The homework page lists every step, 0a to 3e, and ticks each one when it is done. For each step it
  shows what you're finding out and what counts as done. Under "If you're stuck" it shows the step's
  full instructions, from the pages in `instructions/`.
- Each step has its own Claude session: a Claude Code session that is your tutor and lab assistant for
  that step. The homework page shows the command that starts it, with a **Copy** button. Open a new
  terminal tab, go into the homework's folder, paste the command and press Enter. When you come back to
  a step later, the page shows the command that takes you back to the same conversation.
- Claude Code will sometimes ask your permission before it runs a command. Read the command. If it is
  what you asked for, say yes.
- You decide what happens. Claude does nothing until you ask, and each step's instructions say what to
  ask for. Before it runs anything whose result you'll judge, Claude will ask what you expect.
- You type your answers yourself, in `WRITEUP.md`, in your editor. Claude will not write them, because
  you are graded on your own explanations and judgments.
- Claude will run commands for you, explain the code, the tools, Wikipedia's API and the scores as often
  as you ask, and paste a program's output into `WRITEUP.md` where a question asks for it.
- The results viewer is where you read your runs. Open **Results** at the top of the homework page. It
  shows each run's accuracy and cost, each claim's verdicts from all three versions, the agent's lookups
  for a claim one at a time, and two runs side by side. Long results are much easier to read there than
  in the chat.
- Your work is saved when you finish each part. When every step of a part is ticked, the homework page
  saves your conversations with Claude in `TRANSCRIPT.md`, commits your work as `Part N done`, and
  pushes it to your fork. If you change an answer after that, it commits the change too. I read
  `TRANSCRIPT.md` when I grade, so start every Claude session in the homework's folder. Don't edit
  `TRANSCRIPT.md` yourself: the page writes it again before each commit.
- The two long runs, in steps 1e and 3d, take about [[EVAL_MINUTES]] and [[RERUN_MINUTES]] minutes. You
  start them yourself, in a terminal tab of their own, because a run started by Claude stops if you
  close that Claude session.

## The parts

| Part | What you do | Weight |
|---|---|---|
| [Part 0: Set up](instructions/part0.md) | Get your copy running, then check one claim three ways: the model alone, one search, and the agent | 10% |
| [Part 1: How the agent works](instructions/part1.md) | Read the agent's loop, check a claim yourself with its tools, watch it work, write its instructions, and start the full run while you predict how it will do | 25% |
| [Part 2: The agent against the baselines](instructions/part2.md) | Compare accuracy and cost by how many articles a claim needs, check the agent's evidence yourself, and find where Wikipedia has changed | 35% |
| [Part 3: Your own claims](instructions/part3.md) | Write claims about a topic you know, sort the agent's failures, make one change, and write up what you found | 30% |

Everything is due 8:00am Tuesday, November 24.

[[HOURS_LINE]]

## Words this homework uses

- **claim**: one sentence that is either true or false.
- **verdict**: the answer to a claim, always one of *supported*, *refuted* or *doesn't say*.
- **evidence**: the sentences quoted from Wikipedia that a verdict rests on.
- **the agent**: the program in `agent.py`, a loop in which the model picks the next lookup, reads what
  comes back, and decides when to answer.
- **lookup**: one call to `search`, `read` or `wikidata`.
- **tool**: one of the four things the agent can call: `search`, `read`, `wikidata` and `answer`.
- **trace**: the list of the agent's lookups for one claim, in order, with what each returned.
- **baseline**: a simpler method the agent is compared with. There are two: **the no-tools baseline**
  (the model answers from memory) and **the one-search baseline** (one search, one page, then an
  answer).
- **the three versions**: the no-tools baseline, the one-search baseline and the agent.
- **the model**: Claude Haiku, the small Claude model that the agent and both baselines call.
- **Claude**: your Claude Code session, your tutor and lab assistant. It is not the model.
- **the number of articles**: how many Wikipedia articles a claim needs (2, 3 or 4), from the dataset.
- **HoVer**: the public dataset the claims come from. It labels each claim *supported* or
  *not supported*.
- **the dataset's label**: HoVer's *supported* or *not supported*. A verdict of *refuted* or
  *doesn't say* counts as *not supported*.
- **the development claims**: the 12 claims in `data/dev.jsonl`.
- **the evaluation claims**: the 200 claims in `data/eval.jsonl`.
- **a run**: one use of `evaluate.py`, saved in a folder under `runs/`.
- **the limit of 12 lookups**: the most lookups the loop allows for one claim.
- **token**: the unit the API counts text in and charges by, about three quarters of a word.

## Submitting

Submit once, when all four parts are done, through the
[assignment submission form](https://forms.gle/mgKcnqzTGxNaGvteA). Choose "HW3" and give your
repository's address. Before you submit, check on GitHub that your fork shows the `Part 3 done`
commit, since I grade what is on GitHub.

In your repository I look for:

- `WRITEUP.md`, with every answer filled in;
- your `instructions.md`;
- your runs, in `runs/`;
- `TRANSCRIPT.md`, your conversations with Claude.

## If something goes wrong

- **The homework page will not start.** Check that you are in the `comp440-hw3` folder you cloned
  (`ls` shows `WRITEUP.md`), and run `uv run python -m workbench` again. If it says the page is already
  running, open the address it prints.
- **The port is in use.** The page tries the next port by itself and prints the address it found. Open
  that address.
- **Claude says the model in the command is not available.** Delete
  `--model claude-opus-5-5 --effort medium` from the command, and run the rest of it.
- **A run says the API key is missing or wrong.** Open `.env` in your editor and check that the key I
  sent you comes right after `ANTHROPIC_API_KEY=`. Never paste the key into the chat with Claude:
  your conversations are saved in `TRANSCRIPT.md` and pushed to GitHub, where anyone can read them.
- **A run warns that `WIKIPEDIA_CONTACT` is not set.** Add a line to `.env`, in your editor:
  `WIKIPEDIA_CONTACT=` followed by your Macalester email. Without it, your runs share one Wikipedia
  allowance with the whole class and may slow down.
- **Wikipedia refuses requests for a while.** The program waits and tries again by itself. If a run
  stops anyway, start the same command again: it keeps every claim it already finished and checks only
  the rest.
- **The homework page shows an update banner.** Press **Update**. The page saves your work first.
- **The page says your work is committed but not pushed.** Run `git push` in a terminal in the
  homework's folder.
- **A step will not tick.** Save `WRITEUP.md`, since the page reads the saved file. Then check that
  every answer in that step's section has text right after its `>`, and that every numbered row of its
  tables has every cell filled.

If you're still stuck, ask in `#comp440-f26` on Slack.

## Working together

This homework is individual. You are welcome to help classmates get set up and to talk through what
you're seeing. I ask that you not share your `WRITEUP.md` answers, though, since the point is to form
your own judgment. Ask questions in `#comp440-f26` on Slack. Follow the class's
[AI-use norms](https://docs.google.com/document/d/1Eb6qxeS2wy-9TBzL8eGk9j75iYu_yEV4VoLQaywRz8E/edit).

## Resources

- [The HoVer paper](https://arxiv.org/abs/2011.03088) (Jiang et al., 2020): where the claims come from,
  and how each was built to need two to four Wikipedia articles.
- [Wikipedia's API documentation](https://www.mediawiki.org/wiki/API:Main_page): what the agent's tools
  use to search and read pages.

## Extra credit

Give the agent a fifth tool that reads one other well-known public site, for example a government
statistics site or an encyclopedia other than Wikipedia. Tell me which site before you start. Do it
only after Part 3 is done, because it changes the agent. Then run the agent on your own claims again.
When do the two sources disagree, and how should the agent decide which to believe?

Write what you found under a heading `## Extra credit` at the end of `WRITEUP.md`. The homework page
does not commit extra credit, so commit and push it yourself, in a terminal in the homework's folder:

```
git add -A
git commit -m "Extra credit"
git push
```
