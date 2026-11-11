# COMP 440 HW3: Checking Claims Against Wikipedia

In this homework assignment you will study a small AI agent that checks claims against Wikipedia, and
measure the effectiveness of different methods. You will:

- Understand what makes a program an *agent*. You will study a language model that picks the next Wikipedia search query,
  reads the page that comes back, and decides when to stop.
- Gain hands-on experience with the loop around the model by writing it yourself: its tools, its
  instructions, its limit of 12 lookups, and the check that every sentence it quotes really appears in
  what it read.
- Compare the agent with two simpler methods on your claims, and measure how effective each one is.
- Check the agent's evidence yourself, and decide whether accuracy alone is a fair measure of it.

For extra credit, in Part 3, you find out why the agent fails on your claims, make one change, and see
where Wikipedia, which is written by its volunteer editors, is thin, out of date or wrong.

Everything is due 8:00am Tuesday, November 24.

## The claim checking task

The agent is designed to evaluate a claim, one sentence that is either true or false. Here is an
example claim you'll check in Part 0:

> The composer of "Persian Surgery Dervishes" was born on June 24, 1935.

The agent gives a *verdict*: *supported*, *refuted* or *doesn't say*. It also quotes the sentences from
Wikipedia that its verdict is based on, its *evidence*. No source comes with the claim: the agent searches
and reads Wikipedia as it is today.

The claims come from HoVer, a public dataset of claims that each need two, three or four Wikipedia
articles to check. Many claims do not name the page that holds the answer, so one fact has to be found before
you know which page to read next. You will study how the agent
breaks a claim into pieces, looks up each one, and synthesizes the results. 

## What you need before you start

You used all of these in earlier homeworks:

- Claude Code, installed and signed in. Run `claude update` first: the commands in this homework need a
  recent version.
- `uv`, the Python package manager. Check it with `uv --version`.
- git, and your GitHub account.
- A text editor, for your answers.
- Your API key, which I sent you by Slack direct message. The agent calls the Claude API directly, not
  through your Claude Code account, so it needs this key. Doing Parts 0 to 2 once costs about 35 cents
  on your key, and Part 3 about 20 cents more. That is charged to my account for the course, not to you.

## Getting started

1. Fork the repository on GitHub: open <https://github.com/shilad/comp440-hw3> and click **Fork**.
2. Clone your fork, with your GitHub username in place of `<your-username>`:

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

   The first time, it spends a minute or two installing what it needs. Then it opens the homework page
   in your browser and prints its address. Leave this terminal tab open while you work, because closing
   it stops the page. To start the page again later, run the same command in the folder.

5. On the homework page, open step 0a.

## How this homework works

This describes how the homework page is structured, but it is intended that you can follow along with it directly.
If you are curious, here are additional details.

- You talk with Claude to run programs and to ask for explanations. You type your answers in `WRITEUP.md`, in
  your editor.
- The homework page lists every step, 0a to 3c, and ticks each one when it is done. Part 3 is extra
  credit. For each step it shows a short summary and its tasks. Below the tasks, the step's instructions,
  from the pages in `instructions/`, open with a click, part by part: Words in this step, Actions,
  Interpreting output, Write-up, Troubleshooting and Hint (and in 1a, The six rules). Open Actions for
  the exact commands.
- Claude Code is your tutor and lab assistant for each step. For every step after the first, the homework
  page gives two choices, each with a **Copy** button: a prompt to paste into the Claude session you
  already have open, or a command to paste into a terminal tab in the homework's folder to start a new
  session. When you come back to a step, the page shows how to return to the same conversation.
- Claude does nothing until you ask. Claude Code sometimes asks your permission before it runs a command:
  read the command, and say yes if it is what you asked for.
- You type your answers yourself, in `WRITEUP.md`, in your editor. Claude will not write them, because
  you are graded on your own explanations and judgments. A blank line ends an answer, so to start a new
  paragraph put a line with just `>` between the two.
- Claude runs commands for you, explains the code, the tools, Wikipedia's API and the scores as often as
  you ask, and pastes a program's output into `WRITEUP.md` where a question asks for it. In step 1a it
  helps you write your loop, but it will not write the whole loop for you.
- The results viewer, **Results** at the top of the homework page, is where you read your runs: each
  run's accuracy and cost, each claim's verdicts from all three versions, the agent's trace one entry at
  a time, and two runs side by side.
- When every step of a part is ticked, the page saves your conversations with Claude in `TRANSCRIPT.md`,
  commits your work as `Part N done`, and pushes it to your fork. The commit holds everything git does
  not ignore: your answers, `instructions.md`, your claims, `runs/`, `TRANSCRIPT.md`, and `record/`, the
  page's record of each step. Later changes are committed too. I read `TRANSCRIPT.md` when I grade, so
  start every Claude session in the homework's folder. Don't edit `TRANSCRIPT.md`: the page writes it
  again before each commit.
- Two runs are long: the full run in step 1e takes about 10 minutes, and the run after your change in
  step 3b, which is extra credit, about 6 minutes. Start each in a terminal tab of its own, because a run
  started by Claude stops when that Claude session closes.

## The parts

| Part | What you do | Weight |
|---|---|---|
| [Part 0: Set up and check one claim](instructions/part0.md) | Get your copy running, then check one claim three ways: with an LLM alone, with one Wikipedia search, and with the agent | 15% |
| [Part 1: How the agent works](instructions/part1.md) | Write the agent's loop, check one claim yourself with its tools, watch it work, write its instructions, and start the full run while you predict how it will do | 35% |
| [Part 2: The agent against the baselines](instructions/part2.md) | Compare accuracy by how many articles a claim needs, and check the agent's evidence yourself | 50% |
| [Part 3 (extra credit): Why the agent fails, and one change](instructions/part3.md) | Sort the agent's failures on your claims, make one change, and write up what you found | Extra credit |

I expect this homework to take about 5 hours in all, in three sittings: about an hour for Part 0, about
3 hours for Part 1, and about an hour for Part 2. On top of that, the full run in
Part 1 takes about 10 minutes while you do other things. Part 3, which is extra credit, takes a little
over an hour more, and its run about 6 minutes.

## Words this homework uses

- A **claim** is one sentence that is either true or false.
- A **verdict** is the answer to a claim: *supported*, *refuted* or *doesn't say*.
- The **evidence** is the sentences quoted from Wikipedia that a verdict is based on.
- **The agent** is the program in `agent.py` and its loop: `my_loop.py` once yours passes the check in
  step 1a, and **the reference loop**, `reference_loop.py`, until then. In the loop, the model picks the
  next lookup, reads what comes back, and decides when to answer.
- A **tool** is one of the four things the agent can call: `search`, `read`, `wikidata` and `answer`. A
  **lookup** is a call to one of the first three. The loop allows at most 12 lookups for one claim.
- A **trace** is the agent's lookups for one claim, in order, with what each returned. An **entry** is
  one numbered line of a trace, a lookup or an answer.
- **The model** is Claude Haiku, the small LLM that the agent and both baselines call. **Claude** is your
  Claude Code session, your tutor; it is not the model.
- A **baseline** is a simpler method the agent is compared with: **the no-tools baseline** (the model
  answers from memory) or **the one-search baseline** (one search, one page, then an answer). With the
  agent, they are **the three versions**.
- **HoVer** is the public dataset the claims come from. **The dataset's label** is HoVer's *supported* or
  *not supported*; a verdict of *refuted* or *doesn't say* counts as *not supported*. **The number of
  articles** is how many Wikipedia articles a claim needs (2, 3 or 4).
- **Your claims** are the homework's claims, the same for every student: 12 **development claims** in
  `data/dev.jsonl` for trying things out in Part 1, and 100 **evaluation claims** in `data/eval.jsonl` for
  the full run and Parts 2 and 3.
- A **run** is one use of `evaluate.py`, saved in a folder under `runs/`.
- A **token** is the unit the Claude API counts text in and charges by, about three quarters of a word.

## Submitting

Submit once, when Parts 0 to 2 are done, and Part 3 too if you do the extra credit, through the
[assignment submission form](https://forms.gle/mgKcnqzTGxNaGvteA): choose "Homework submission", then
"HW3", and give your repository's address. First check on GitHub that your fork shows the `Part 2 done`
commit, and `Part 3 done` if you did the extra credit, since I grade what is on GitHub.

In your repository I look for:

- `WRITEUP.md`, with every answer of Parts 0 to 2 filled in, and of Part 3 if you did the extra credit;
- your `instructions.md`;
- your loop, `my_loop.py`;
- your claims, `data/dev.jsonl` and `data/eval.jsonl`;
- your runs, in `runs/`;
- `TRANSCRIPT.md`, your conversations with Claude.

## If something goes wrong

- **The homework page will not start.** Check that you are in the `comp440-hw3` folder (`ls` shows
  `WRITEUP.md`), and run `uv run python -m workbench` again. If it says the page is already running, open
  the address it prints.
- **The port is in use.** The page tries the next port by itself and prints the address it found. Open
  that address.
- **Claude says the model in the command is not available.** Delete
  `--model claude-opus-5-5 --effort medium` from the command, and run the rest of it.
- **A run says the API key is missing or wrong.** Check in your editor that the key I sent you comes
  right after `ANTHROPIC_API_KEY=` in `.env`. Never paste the key into the chat: your conversations are
  saved in `TRANSCRIPT.md` and pushed to GitHub, where anyone can read them.
- **You want to check your set-up again.** Run `uv run python check_setup.py` in the homework's folder.
  It never prints your key.
- **A run's first line reads "ANTHROPIC_API_KEY is set and takes precedence...".** That is a harmless
  notice from Anthropic's library, which a few laptops print before every run.
- **A run warns that `WIKIPEDIA_CONTACT` is not set.** Add `WIKIPEDIA_CONTACT=` and your Macalester email
  to `.env`, in your editor. Without it, your runs share one Wikipedia allowance with the whole class and
  may slow down.
- **A run prints "Wikipedia asked this program to slow down, so it is waiting...".** The program waits
  and then continues by itself, and this happens much less once `WIKIPEDIA_CONTACT` is filled in. If a run
  stops anyway, start the same command again: it keeps every claim it already finished.
- **The homework page shows an update banner.** Press **Update**. The page saves your work first.
- **The page says your work is committed but not pushed.** Run `git push` in a terminal in the
  homework's folder.
- **A step will not tick.** Save `WRITEUP.md`, since the page reads the saved file. Check that every
  answer in that step's section has text right after its `>`, and that every numbered row of its tables
  has every cell filled. A step that runs a program also waits for the file the run saves, so check that
  the run has finished; step 1e is the one exception, and ticks once its run has started.

If you're still stuck, ask in `#comp440-f26` on Slack.

## Working together

This homework is individual. You are welcome to help classmates get set up and to talk through what
you're seeing, but don't share your `WRITEUP.md` answers, since the point is to form your own judgment.
Ask questions in `#comp440-f26` on Slack. Follow the class's
[AI-use norms](https://docs.google.com/document/d/1Eb6qxeS2wy-9TBzL8eGk9j75iYu_yEV4VoLQaywRz8E/edit).

## Resources

- [The HoVer paper](https://arxiv.org/abs/2011.03088) (Jiang et al., 2020) says where the claims come
  from, and how each was built to need two to four Wikipedia articles. The claims in `data/dev.jsonl`,
  `data/eval.jsonl` and the claim finder are [HoVer](https://hover-nlp.github.io/)'s, which its authors
  share under the [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) licence; they carry
  the same licence here.
- The word vectors of the claim finder's search by meaning, in `finder/data/word_vectors.json.gz` and
  `finder/data/claim_vectors.json.gz`, were made from
  [potion-base-8M](https://huggingface.co/minishlab/potion-base-8M), a set of word vectors from the
  model2vec project, which its authors share under the MIT licence. `finder/build_data.py` says how.
- The one-line descriptions of articles that the claim finder shows, in `finder/data/claims.json.gz`, are
  Wikipedia's short descriptions, fetched on November 10, 2026. Like the rest of Wikipedia, they are
  shared under the [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) licence, and they
  carry the same licence here.
- [Wikipedia's API documentation](https://www.mediawiki.org/wiki/API:Main_page) describes what the
  agent's tools use to search and read pages.

## Extra credit

Any of these earns extra credit, and you may do more than one.

**Why the agent fails, and one change.** Part 3 is extra credit: you sort the agent's failures on your
claims, make one change aimed at the most common one, and write up what you found. Its steps are on the
homework page, and its instructions are on [Part 3's page](instructions/part3.md).

**Find where Wikipedia has changed.** Find claims where the agent's quoted evidence supports its verdict
and today's Wikipedia disagrees with the dataset's label, which was made from the Wikipedia of 2017. The
instructions are at the end of [Part 2's page](instructions/part2.md), under "Extra credit: find where
Wikipedia has changed". Do it any time after Part 2.

**Give the agent a fifth tool.** Give the agent a fifth tool that reads one other well-known public site,
for example a government statistics site or an encyclopedia other than Wikipedia. Tell me which site
before you start. Do it after Part 2, and after Part 3 if you do it, because it changes the agent. Then
run the agent on your evaluation claims again. When do the two sources disagree, and how should the
agent decide which to believe?

Write what you found for the last two under a heading `## Extra credit` at the end of `WRITEUP.md`. Keep
the homework page running while you work on it: once Part 2 is done, the page commits and pushes any
further change about a minute after you save it, as `Part 2 updated`, or `Part 3 updated` if you did
Part 3. Check on GitHub that your fork shows it.
