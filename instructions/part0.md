# COMP 440 HW3 Part 0: Set up

Due 8:00am Tuesday, November 24. Back to the [assignment page](../README.md).

In this part you get your copy of the homework running, then check one claim three ways: with the model
alone, with one Wikipedia search, and with the agent. You'll see what each of the three does with the
same claim before you look inside any of them. It should take about 50 minutes.

## 0a. Get your copy running

**What you're finding out:** Nothing yet. This step gets the homework running on your laptop, so that
the later steps can reach Wikipedia and the Claude API.

**Words in this step:** *Claude*: your Claude Code session, your tutor and lab assistant. Each step has
its own. *`.env`*: the file that holds your API key and your email. Only you edit it.

**What to do:** Before this step, fork the repository, clone your fork and start the homework page, as
the Getting started section of the README says. Then:

1. Open a new terminal tab and go into the homework's folder (the `comp440-hw3` folder you cloned).
2. Copy the command the homework page shows for 0a, paste it into that tab and press Enter.
3. Say yes when Claude Code asks whether you trust this folder.
4. Type your name after `Name:` at the top of `WRITEUP.md`, in your editor, and save.
5. In your editor, create a file named `.env` in the homework's folder and copy `.env.example` into it.
6. Paste the API key I sent you by Slack right after `ANTHROPIC_API_KEY=`. Never paste it into the chat.
7. Type your Macalester email right after `WIKIPEDIA_CONTACT=`, and save `.env`.
8. Ask Claude to run the set-up check.
9. Fix each line marked `NOT READY` in your editor, save, and ask Claude to run the check again.
10. Repeat action 9 until the check's last line reads "Everything is ready."

**What you'll see:** Claude runs this command:

```
uv run python check_setup.py
```

It prints one line for each of five things, each marked `ok` or `NOT READY`: the `.env` file is there,
the key is filled in, the email is filled in, Wikipedia answered a search, and the Claude API accepted
your key. A `NOT READY` line says what to fix. The check never prints your key or your email, and it
costs a small fraction of a cent.

**What to write:** Only your name, after `Name:` at the top of `WRITEUP.md`. There is nothing to write
under `## 0a. Get your copy running`.

**You're done when:** The set-up check's last line reads "Everything is ready." and the homework page
ticks 0a, which it does when the saved `WRITEUP.md` has your name after `Name:` and `.env` exists.

**If something goes wrong:**

- Claude says the model in the command is not available: delete `--model claude-opus-5-5 --effort medium`
  from the command, and run the rest of it.
- The check still says `NOT READY` after you fixed `.env`: make sure you saved the file, then ask Claude
  to run the check again. If it still fails, post the `NOT READY` line in `#comp440-f26` on Slack.
- The output starts with a line reading "ANTHROPIC_API_KEY is set and takes precedence...": that is a
  notice from Anthropic's library, which a few laptops print before every run. It is harmless.
- You can't find the key I sent you: ask me on Slack.

**Hint:** Why `.env`: the agent calls the Claude API directly, not through your Claude Code account, so
it needs your key. The email gives your runs their own allowance of Wikipedia requests, because
Wikipedia counts requests by the contact each program gives; without it, you share one allowance with
the whole class. `.env` is never committed, and no Claude session reads it. The key never goes in the
chat, because your conversations are saved in `TRANSCRIPT.md` and pushed to GitHub, where anyone can
read them.

## 0b. Ask the model with no tools

**What you're finding out:** How well the model checks a claim from memory alone, with no lookups.
This is the first baseline, the no-tools baseline.

The claim for Part 0, which the homework page also shows beside this step's goal:

> The composer of "Persian Surgery Dervishes" was born on June 24, 1935.

**Words in this step:** *the model*: Claude Haiku, the small Claude model that every version in this
homework calls. *baseline*: a simpler method the agent is compared with. *verdict*: the answer to a
claim, *supported*, *refuted* or *doesn't say*. *token*: the unit the API counts text in and charges by,
about three quarters of a word.

**What to do:**

1. Start this step's Claude session with the command the homework page shows for 0b.
2. Ask Claude to run the no-tools baseline on the claim.
3. Tell Claude what verdict you expect, when it asks.
4. Read the output Claude pastes into the chat.
5. Answer the two questions in `WRITEUP.md`.

**What you'll see:** Claude runs this command:

```
uv run python check.py --method no-tools --out runs/part0 'The composer of "Persian Surgery Dervishes" was born on June 24, 1935.'
```

The output gives the verdict, the model's explanation, and a last line with the lookups (none for this
baseline), tokens, cost and time. The result is saved as `runs/part0/no-tools-<number>.json`.

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

> The composer of "Persian Surgery Dervishes" was born on June 24, 1935.

**Words in this step:** *the one-search baseline*: a simpler method the agent is compared with. The
model (Claude Haiku) writes one Wikipedia search, the program reads the opening paragraphs of the top
page it finds, and the model answers from that page alone. *verdict*: *supported*, *refuted* or
*doesn't say*.

**What to do:**

1. Start this step's Claude session with the command the homework page shows for 0c.
2. Ask Claude to run the one-search baseline on the claim.
3. Tell Claude which Wikipedia page you would want it to read, when it asks.
4. Read the output Claude pastes into the chat.
5. Open the check in the results viewer to read the whole page it read (see "What you'll see").
6. Answer the two questions in `WRITEUP.md`.

**What you'll see:** Claude runs this command:

```
uv run python check.py --method one-search --out runs/part0 'The composer of "Persian Surgery Dervishes" was born on June 24, 1935.'
```

The line numbered 1 is the search: what it searched for, and under it a short version of the results.
The line numbered 2 is the page it read, and under it a short version of that page. Then come the
verdict, the model's explanation, and a line with the lookups, tokens, cost and time. The result is
saved as `runs/part0/one-search-<number>.json`. To read the whole page it read, click "Open these
results" under 0c on the homework page. Or open **Results** at the top of the homework page (it opens in
a new tab) and, under "Part 0: Set up", in "Single checks in runs/part0/", click the claim in the row
whose Version is "one-search baseline". A long result is folded: click "+ Show the whole result".

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

The claim for Part 0, which the homework page also shows beside this step's goal:

> The composer of "Persian Surgery Dervishes" was born on June 24, 1935.

**Words in this step:** *the agent*: the program in `agent.py`, a loop in which the model (Claude Haiku)
picks the next lookup, reads what comes back, and decides when to answer. *lookup*: one call to
`search`, `read` or `wikidata`. *trace*: the agent's lookups for one claim, in order, with what each
returned. *evidence*: the sentences quoted from Wikipedia that a verdict rests on.

**What to do:**

1. Start this step's Claude session with the command the homework page shows for 0d.
2. Ask Claude to run the agent on the claim.
3. Tell Claude what you expect the agent to do, when it asks.
4. Read the trace Claude pastes into the chat, one lookup at a time.
5. Open the check in the results viewer and read the trace again, with each lookup's full result.
6. Answer the two questions in `WRITEUP.md`.

**What you'll see:** Claude runs this command:

```
uv run python check.py --method agent --out runs/part0 'The composer of "Persian Surgery Dervishes" was born on June 24, 1935.'
```

Each numbered line is one call to one of the agent's four tools (`search`, `read`, `wikidata` and
`answer`): the tool, what it asked for, and under it a short version of what came back. The last
numbered line is usually its call to `answer`. Then come the verdict, the evidence, the explanation and
a line with the lookups, tokens, cost and time. The result is saved as `runs/part0/agent-<number>.json`.
To open it in the results viewer, click "Open these results" under 0d on the homework page. Or open
**Results** at the top of the homework page (it opens in a new tab) and, under "Part 0: Set up", in
"Single checks in runs/part0/", click the claim in the row whose Version is "agent". Below "The agent"
box, "The agent's trace" shows one lookup at a time with each lookup's full result: click "+ Show the
whole result" to open a long one, or "Open every result" to open them all.

A trace sometimes shows an answer that was sent back (rejected) before a later answer was accepted.
That is the loop's check on evidence doing its job: a quoted sentence was not in anything the agent had
read, and text shown in a search result does not count as read.

**What to write:** Under `## 0d. Run the agent and read its trace` in `WRITEUP.md`, answer:

- In one or two sentences, how did the agent get from the claim to its verdict? Point to the lookups by their numbers in the trace.
- Which lookup would you have done differently, and how? If none, which one surprised you?

**You're done when:** The homework page ticks 0d. It does that when a `runs/part0/agent-<number>.json`
file exists and both answers under 0d have text after the `>`. With 0d ticked, every step of Part 0 is
done, so the page commits your work as `Part 0 done` and pushes it to your fork.

**If something goes wrong:** If Wikipedia asks the program to slow down, it waits and tries again by
itself. If the run stops with an error anyway, ask Claude to run the same command again.

## What I look for

Part 0 is 10% of the homework. At a minimum I am looking for the following:

- Set up: 40% - Your repository runs, and the three outputs are in `runs/part0/`.
- Reading the outputs: 60% - Your answers to 0b, 0c and 0d say what each version did with this claim
  and point to the line of the output or trace that shows it.
