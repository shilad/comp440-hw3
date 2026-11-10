# COMP 440 HW3: Checking Claims Against Wikipedia

In this homework assignment you will study a small AI agent that checks claims against Wikipedia, and
measure what it adds over simpler methods. You will:

- Understand what makes a program an *agent*: a language model that picks the next thing to look up,
  reads what comes back, and decides when to stop.
- Gain hands-on experience with the loop around the model by writing it yourself: its tools, its
  instructions, its limit of 12 lookups, and the check that every sentence it quotes really appears in
  what it read.
- Compare the agent with two simpler methods, and measure where it helps, where it doesn't, and what
  it costs.
- Run it on the dataset's claims about a few topics you know well, and find out where Wikipedia,
  which is written by its volunteer editors, is thin, out of date or wrong.

## The task

The agent is given a claim, one sentence that is either true or false, and nothing else. Here is the
claim you'll check in Part 0:

> The composer of "Persian Surgery Dervishes" was born on June 24, 1935.

I chose it because it is short and about a recording few people know, so it is a fair test of what
the model remembers.

The agent has to give a *verdict*: *supported*, *refuted* or *doesn't say*. It also has to quote the
sentences from Wikipedia that its verdict rests on, its *evidence*. No source comes with the claim.
The agent finds its own evidence by searching and reading Wikipedia as it is today.

The claims in this homework come from HoVer, a public dataset of claims that each need two, three or
four Wikipedia articles to check. Many HoVer claims do not name the page that holds the answer, so one
fact has to be found before you know which page to read next. Whether one search is enough, and when,
is one of the things you'll measure. The agent works out what a claim is made of, looks up each piece,
and puts the pieces together, and how it does that is what you'll study.

You study it on HoVer's claims about a few topics you know better than most people. In step 0b you pick
the topics and select 112 claims about them, and every run after that uses them. I ask for topics you
know because then you can judge the agent's answers, and the dataset's labels, for yourself.

## What you need before you start

You used all of these in earlier homeworks:

- Claude Code, installed and signed in. Update it first, with `claude update` in a terminal: the
  commands in this homework need a recent version.
- `uv`, the Python package manager. Check it with `uv --version`.
- git, and your GitHub account.
- A text editor. You type every answer in it.
- Your API key. I sent you your own API key by Slack direct message. The agent calls the Claude API
  directly, not through your Claude Code account, so it needs this key. Doing the whole homework once
  costs about 65 cents on your key. That is charged to my account for the course, not to you.

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

   The first time, it spends a minute or two installing what it needs. Then it opens the homework
   page in your browser and prints its address. Leave this terminal tab open
   while you work: closing it stops the page. To start the page again later, go into the folder and run
   the same command.

5. On the homework page, open step 0a and follow it from there.

## How this homework works

- The homework page lists every step, 0a to 3c, and ticks each one when it is done. For each step it
  shows what the step is for and its tasks. Under "If you're stuck" it shows the step's
  full instructions, from the pages in `instructions/`. Open it for every step, stuck or not: it has
  the exact commands and what I am looking for. Step 0a, the set-up step, shows them in full.
- Each step has its own Claude session: a Claude Code session that is your tutor and lab assistant for
  that step. The homework page shows the command that starts it, with a **Copy** button. Open a new
  terminal tab, go into the homework's folder, paste the command and press Enter. When you finish a
  step, type `/exit` to close its session; you can use the same tab for the next step. When you come
  back to a step later, the page shows the command that takes you back to the same conversation.
- Claude Code will sometimes ask your permission before it runs a command. Read the command. If it is
  what you asked for, say yes.
- You decide what happens. Claude does nothing until you ask, and each step's instructions say what to
  ask for. Before it runs anything whose result you'll judge, Claude will ask what you expect.
- You type your answers yourself, in `WRITEUP.md`, in your editor. Claude will not write them, because
  you are graded on your own explanations and judgments. Keep each answer free of blank lines: a blank
  line ends the answer, so to start a new paragraph put a line with just `>` between the two.
- Claude will run commands for you, explain the code, the tools, Wikipedia's API and the scores as often
  as you ask, and paste a program's output into `WRITEUP.md` where a question asks for it.
- The results viewer is where you read your runs. Open **Results** at the top of the homework page; it
  opens in a new tab. It shows each run's accuracy and cost, each claim's verdicts from all three
  versions, the agent's trace for a claim one entry at a time, and two runs side by side. Long results
  are easier to read there.
- The claim finder is where you select your claims, in step 0b. Open **Find claims** at the top of the
  homework page. You search the dataset's claims one topic at a time, select the ones you want, and save
  112 of them: 12 in `data/dev.jsonl` and 100 in `data/eval.jsonl`. Every run in the homework uses them,
  so each student's homework runs on claims about their own topics.
- Your work is saved when you finish each part. When every step of a part is ticked, the homework page
  saves your conversations with Claude in `TRANSCRIPT.md`, commits your work as `Part N done`, and
  pushes it to your fork. The commit holds everything in the repository that git does not ignore: your
  answers, `instructions.md`, your claims, everything under `runs/`, `TRANSCRIPT.md`, and `record/`, the
  page's own record of each step. If you change
  an answer after that, it commits the change too. I read `TRANSCRIPT.md` when I grade, so start every Claude session in the homework's folder. Don't edit
  `TRANSCRIPT.md` yourself: the page writes it again before each commit.
- Two runs are long: the full run in step 1e takes about 10 minutes, and the run after your change in
  step 3b about 8 minutes. You start each of them yourself, in a terminal tab of its own, because a run
  started by Claude stops if you close that Claude session.

## The parts

| Part | What you do | Weight |
|---|---|---|
| [Part 0: Set up and find your claims](instructions/part0.md) | Get your copy running, select the dataset's claims about a few topics you know, then check one claim three ways: the model alone, one search, and the agent | 10% |
| [Part 1: How the agent works](instructions/part1.md) | Write the agent's loop, check two claims yourself with its tools, watch it work, write its instructions, and start the full run while you predict how it will do | 25% |
| [Part 2: The agent against the baselines](instructions/part2.md) | Compare accuracy and cost by how many articles a claim needs, and check the agent's evidence yourself | 35% |
| [Part 3: Why the agent fails, and one change](instructions/part3.md) | Sort the agent's failures on your claims, make one change, and write up what you found | 30% |

Everything is due 8:00am Tuesday, November 24.

I expect this homework to take about 6 hours and 40 minutes in all, in four sittings: about 1 hour and
35 minutes for Part 0, about 3 hours and 5 minutes for Part 1, about 50 minutes for Part 2, and about 1
hour and 10 minutes for Part 3. On top of that, the full run in Part 1 takes about 10 minutes and the
run after your change in Part 3 about 8 minutes, while you do other things.

## Words this homework uses

- A **claim** is one sentence that is either true or false.
- A **verdict** is the answer to a claim, always one of *supported*, *refuted* or *doesn't say*.
- The **evidence** is the sentences quoted from Wikipedia that a verdict rests on.
- **The agent** is the program in `agent.py` and the loop that drives it: `my_loop.py` once yours
  passes, `reference_loop.py` until then. In the loop, the model picks the next lookup, reads what comes
  back, and decides when to answer.
- **The reference loop** is the loop in `reference_loop.py`, which your copy uses until your own loop
  passes the check in step 1a.
- A **lookup** is one call to `search`, `read` or `wikidata`.
- A **tool** is one of the four things the agent can call: `search`, `read`, `wikidata` and `answer`.
- A **trace** is the list of the agent's lookups for one claim, in order, with what each returned.
- An **entry** is one numbered line of a trace, a lookup or an answer. The numbers count every entry; a
  "Lookups" count counts only `search`, `read` and `wikidata`.
- A **baseline** is a simpler method the agent is compared with. There are two: **the no-tools
  baseline** (the model answers from memory) and **the one-search baseline** (one search, one page, then
  an answer).
- **The three versions** are the no-tools baseline, the one-search baseline and the agent.
- **The model** is Claude Haiku, the small Claude model that the agent and both baselines call.
- **Claude** is your Claude Code session, your tutor and lab assistant. It is not the model.
- **The number of articles** is how many Wikipedia articles a claim needs (2, 3 or 4), from the dataset.
- **HoVer** is the public dataset the claims come from. It labels each claim *supported* or *not
  supported*.
- **The dataset's label** is HoVer's *supported* or *not supported*. A verdict of *refuted* or *doesn't
  say* counts as *not supported*.
- **The claim finder** is the screen where you search the dataset's claims for your topics in step 0b.
  You open it with **Find claims** at the top of the homework page.
- **Your claims** are the 112 claims you select and save with the claim finder in step 0b, all about
  your topics.
- **Your development claims** are 12 of your claims, in `data/dev.jsonl`, a small set for trying things
  out in Part 1.
- **Your evaluation claims** are the other 100 of your claims, in `data/eval.jsonl`, which the full run
  in step 1e checks and Parts 2 and 3 study.
- A **run** is one use of `evaluate.py`, saved in a folder under `runs/`.
- **The limit of 12 lookups** is the most lookups the loop allows for one claim.
- An **API** is the way one program asks another for something over the network. The agent's program
  uses the Claude API to call the model, and Wikipedia's API to search and read pages.
- A **token** is the unit the Claude API counts text in and charges by, about three quarters of a word.

## Submitting

Submit once, when all four parts are done, through the
[assignment submission form](https://forms.gle/mgKcnqzTGxNaGvteA). Choose "Homework submission",
then "HW3", and give your
repository's address. Before you submit, check on GitHub that your fork shows the `Part 3 done`
commit, since I grade what is on GitHub.

In your repository I look for:

- `WRITEUP.md`, with every answer filled in;
- your `instructions.md`;
- your loop, `my_loop.py`;
- your claims, `data/dev.jsonl`, `data/eval.jsonl` and `data/my-topic.json`;
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
- **You want to check your set-up again.** Run `uv run python check_setup.py` in the homework's
  folder, as in step 0a. It never prints your key.
- **A run's first line reads "ANTHROPIC_API_KEY is set and takes precedence...".** That is a notice
  from Anthropic's library, which a few laptops print before every run. It is harmless.
- **A run warns that `WIKIPEDIA_CONTACT` is not set.** Add a line to `.env`, in your editor:
  `WIKIPEDIA_CONTACT=` followed by your Macalester email. Without it, your runs share one Wikipedia
  allowance with the whole class and may slow down.
- **A run prints "Wikipedia asked this program to slow down, so it is waiting...".** The program waits
  and carries on by itself. It happens much less once you have filled in `WIKIPEDIA_CONTACT` in `.env`. If a
  run stops anyway, start the same command again: it keeps every claim it already finished and checks
  only the rest.
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

- [The HoVer paper](https://arxiv.org/abs/2011.03088) (Jiang et al., 2020) says where the claims come
  from, and how each was built to need two to four Wikipedia articles. The claims in `data/dev.jsonl`,
  `data/eval.jsonl` and the claim finder are [HoVer](https://hover-nlp.github.io/)'s, which its authors
  share under the [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) licence; they carry
  the same licence here.
- The word vectors that the claim finder's search by meaning uses, in `finder/data/word_vectors.json.gz`
  and `finder/data/claim_vectors.json.gz`, were made from
  [potion-base-8M](https://huggingface.co/minishlab/potion-base-8M), a set of word vectors from the
  model2vec project, which its authors share under the MIT licence. `finder/build_data.py` says how.
- The one-line descriptions of the articles that the claim finder shows with each claim, in
  `finder/data/claims.json.gz`, are Wikipedia's short descriptions, fetched on November 10, 2026. Like
  the rest of Wikipedia, they are shared under the
  [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) licence, and they carry the same
  licence here.
- [Wikipedia's API documentation](https://www.mediawiki.org/wiki/API:Main_page) describes what the
  agent's tools use to search and read pages.

## Extra credit

Either of these earns extra credit, and you may do both.

**Find where Wikipedia has changed.** Find claims where the agent's quoted evidence supports its
verdict and today's Wikipedia disagrees with the dataset's label, which was made from the Wikipedia of
2017. The instructions are at the end of [Part 2's page](instructions/part2.md), under "Extra credit:
find where Wikipedia has changed". Do it any time after Part 2.

**Give the agent a fifth tool.** Give the agent a fifth tool that reads one other well-known public
site, for example a government statistics site or an encyclopedia other than Wikipedia. Tell me which
site before you start. Do it only after Part 3 is done, because it changes the agent. Then run the agent
on your evaluation claims again. When do the two sources disagree, and how should the agent decide which to
believe?

Write what you found under a heading `## Extra credit` at the end of `WRITEUP.md`. Keep the homework
page running while you work on it: once Part 3 is done, the page commits and pushes any further change
about a minute after you save it, as `Part 3 updated`. Check on GitHub that your fork shows it.
