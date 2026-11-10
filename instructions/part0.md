# COMP 440 HW3 Part 0: Set up

Due 8:00am Tuesday, November 24. Back to the [assignment page](../README.md).

In this part you get your copy of the homework running, then check one claim three ways: with the model
alone, with one Wikipedia search, and with the agent. You'll see what each of the three does with the
same claim before you look inside any of them. It should take about 50 minutes.

## 0a. Get your copy running

**What you're finding out:** Nothing yet. This step gets the homework running on your laptop, so that
the later steps can reach Wikipedia and the Claude API.

**What to do:** Before this step, you should have forked the repository, cloned your fork and started
the homework page with `uv run python -m workbench`, as the Getting started section of the README
says. Then:

1. Open a new terminal tab and go into the homework's folder (the `comp440-hw3` folder you cloned).
2. Copy the command the homework page shows for 0a, paste it into that tab and press Enter. It starts
   this step's Claude session: Claude Code, as your tutor and lab assistant for this step.
3. Say yes when Claude Code asks whether you trust this folder.
4. Open `WRITEUP.md` in your editor, type your name after `Name:` at the top, on the same line, and
   save the file.
5. In your editor, create a new file named `.env` in the homework's folder, and copy everything in
   `.env.example` into it.
6. Paste the API key I sent you by Slack direct message right after `ANTHROPIC_API_KEY=` in `.env`.
7. Type your Macalester email right after `WIKIPEDIA_CONTACT=` in `.env`, and save the file.
8. Ask Claude to run the tests. Claude runs this command:

   ```
   uv run pytest -q
   ```

   The tests need no key and no network. They check that the code is installed and works.
9. Ask Claude to check that your `.env` file is there. Claude checks with `test -f .env` and never
   opens the file.

Why `.env`: the agent calls the Claude API directly, not through your Claude Code account, so it needs
your key. The email gives your runs their own allowance of Wikipedia requests, because Wikipedia counts
requests by the contact each program gives; without it, you share one allowance with the whole class.
`.env` is never committed, and no Claude session reads it. Never paste the key into the chat with
Claude: your conversations are saved in `TRANSCRIPT.md` and pushed to GitHub, where anyone can read
them.

**What to write:** Only your name, after `Name:` at the top of `WRITEUP.md`. There is nothing to write
under `## 0a. Get your copy running`.

**You're done when:** The homework page ticks 0a. It does that when the saved `WRITEUP.md` has your name
after `Name:` and the file `.env` exists. The first step that uses your key is 0b.

**If something goes wrong:**

- Claude says the model in the command is not available: delete `--model claude-opus-5-5 --effort medium`
  from the command, and run the rest of it.
- A test fails: ask Claude what the error means. If it can't fix it, post the error in `#comp440-f26`
  on Slack.
- You can't find the key I sent you: ask me on Slack.

## 0b. Ask the model with no tools

**What you're finding out:** How well the model checks a claim from memory alone, with no lookups.
This is the first baseline, the no-tools baseline.

The model is Claude Haiku, the small Claude model that every version in this homework calls. A
baseline is a simpler method that the agent, the program this homework studies, is compared with.

The claim for Part 0, which the homework page also shows beside this step's goal:

> [[SAMPLE_CLAIM]]

**What to do:**

1. Start this step's Claude session: in a terminal tab in the homework's folder, run the command the
   homework page shows for 0b. Claude is your Claude Code session, your tutor and lab assistant.
2. Ask Claude to run the no-tools baseline on the claim.
3. Tell Claude what verdict you expect, when it asks. A verdict is the answer to a claim: *supported*,
   *refuted* or *doesn't say*. Claude asks before it runs anything whose result you'll judge.
4. Read the output Claude pastes into the chat. Claude runs this command, with the claim in place of
   `<claim>`:

   ```
   uv run python check.py --method no-tools --out runs/part0 "<claim>"
   ```

   The output gives the verdict, the model's explanation, and a last line with the lookups, tokens,
   cost and time. Tokens are the unit the API counts text in and charges by, about three quarters of a
   word. This baseline makes no lookups. The result is saved as `runs/part0/no-tools-<number>.json`.

**What to write:** Under `## 0b. Ask the model with no tools` in `WRITEUP.md`, answer:

- What verdict did the model give, and what reason did it give? Quote the lines of the output that show them.
- How much would you trust this answer, and why?

**You're done when:** The homework page ticks 0b. It does that when a `runs/part0/no-tools-<number>.json`
file exists and both answers under 0b have text after the `>`.

**If something goes wrong:** If the run says the API key is missing or wrong, open `.env` in your
editor and check that your key comes right after `ANTHROPIC_API_KEY=`. Never paste the key into the
chat.

## 0c. Give it one search

**What you're finding out:** What one Wikipedia search adds, and whether that search lands on a page
that settles the claim.

The claim for Part 0, which the homework page also shows beside this step's goal:

> [[SAMPLE_CLAIM]]

**What to do:**

1. Start this step's Claude session: in a terminal tab in the homework's folder, run the command the
   homework page shows for 0c. Claude is your Claude Code session, your tutor and lab assistant.
2. Ask Claude to run the one-search baseline on the claim. The one-search baseline is a simpler method
   the agent is compared with. The model (Claude Haiku, the small Claude model that every version in
   this homework calls) writes one Wikipedia search. The program reads the opening paragraphs of the
   top page that search finds, and the model answers from that page alone.
3. Tell Claude which Wikipedia page you would want it to read for this claim, when it asks. Claude asks
   before it runs anything.
4. Read the output Claude pastes into the chat. Claude runs this command, with the claim in place of
   `<claim>`:

   ```
   uv run python check.py --method one-search --out runs/part0 "<claim>"
   ```

   The line numbered 1 is the search: what it searched for, and under it a short version of the
   results. The line numbered 2 is the page it read, and under it a short version of what came back.
   Then come the verdict (*supported*, *refuted* or *doesn't say*), the model's explanation, and a line
   with the lookups, tokens, cost and time. The result is saved as `runs/part0/one-search-<number>.json`.
5. Ask Claude to show you the whole page text it read, from that file, if the short version isn't
   enough to decide whether the page settles the claim.

**What to write:** Under `## 0c. Give it one search` in `WRITEUP.md`, answer:

- Which Wikipedia page did it read? Quote the line of the output that shows it.
- Did that page settle the claim? If not, why do you think the search led there?

**You're done when:** The homework page ticks 0c. It does that when a
`runs/part0/one-search-<number>.json` file exists and both answers under 0c have text after the `>`.

**If something goes wrong:**

- The run says the API key is missing or wrong: open `.env` in your editor and check that your key
  comes right after `ANTHROPIC_API_KEY=`. Never paste the key into the chat.
- The run warns that `WIKIPEDIA_CONTACT` is not set: add a line to `.env`, in your editor:
  `WIKIPEDIA_CONTACT=` followed by your Macalester email.

## 0d. Run the agent and read its trace

**What you're finding out:** How the agent gets from the claim to a verdict when it chooses its own
lookups.

The agent is the program in `agent.py`: a loop in which the model (Claude Haiku, the small Claude model
that every version in this homework calls) picks the next lookup, reads what comes back, and decides
when to answer. A lookup is one call to `search`, `read` or `wikidata`.

The claim for Part 0, which the homework page also shows beside this step's goal:

> [[SAMPLE_CLAIM]]

**What to do:**

1. Start this step's Claude session: in a terminal tab in the homework's folder, run the command the
   homework page shows for 0d. Claude is your Claude Code session, your tutor and lab assistant.
2. Ask Claude to run the agent on the claim.
3. Tell Claude what you expect the agent to do, when it asks.
4. Read the trace Claude pastes into the chat, one lookup at a time. The trace is the list of the
   agent's lookups for one claim, in order, with what each returned. Claude runs this command, with the
   claim in place of `<claim>`:

   ```
   uv run python check.py --method agent --out runs/part0 "<claim>"
   ```

   Each numbered line is one call to one of the agent's four tools (`search`, `read`, `wikidata` and
   `answer`): the tool, what it asked for, and under it a short version of what came back. The last
   numbered line is usually the agent's call to `answer`. Then come the verdict (*supported*,
   *refuted* or *doesn't say*), its evidence (the sentences it quoted from Wikipedia), its explanation,
   and a line with the lookups, tokens, cost and time. The result is saved as
   `runs/part0/agent-<number>.json`.
5. Open **Results** at the top of the homework page, open your Part 0 run, then open the claim. The
   results viewer shows the agent's trace one lookup at a time, with each lookup's full result.

**What to write:** Under `## 0d. Run the agent and read its trace` in `WRITEUP.md`, answer:

- In one or two sentences, how did the agent get from the claim to its verdict? Point to the lookups by their numbers in the trace.
- Which lookup would you have done differently, and how? If none, which one surprised you?

**You're done when:** The homework page ticks 0d. It does that when a `runs/part0/agent-<number>.json`
file exists and both answers under 0d have text after the `>`. With 0d ticked, every step of Part 0 is
done, so the page commits your work as `Part 0 done` and pushes it to your fork.

**If something goes wrong:** If Wikipedia refuses requests for a while, the program waits and tries
again by itself. If the run stops with an error anyway, ask Claude to run the same command again.

## What I look for

Part 0 is 10% of the homework. At a minimum I am looking for the following:

- Set up: 40% - Your repository runs, and the three outputs are in `runs/part0/`.
- Reading the outputs: 60% - Your answers to 0b, 0c and 0d say what each version did with this claim
  and point to the line of the output or trace that shows it.
