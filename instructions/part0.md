# COMP 440 HW3 Part 0: Set up

Due 8:00am Tuesday, November 24. Back to the [assignment page](../README.md).

In this part you get your copy of the homework running, then check one claim three ways: with the model
alone, with one Wikipedia search, and with the agent. You'll see what each does with the same claim
before you look inside any of them. It should take about 50 minutes.

## 0a. Get your copy running

**What this step is for:** Getting the homework running on your laptop, so the later steps can reach
Wikipedia and the Claude API.

**Words in this step:** *Claude*: your Claude Code session, your tutor and lab assistant; each step has
its own. *`.env`*: the file that holds your API key and your email; only you edit it.

**What to do:** First fork the repository, clone your fork and start the homework page, as the README's
Getting started section says. Then:

1. Open a new terminal tab and go into the homework's folder (the `comp440-hw3` folder you cloned).
2. In that tab, run `cp .env.example .env` to make your own `.env`.
3. Open `.env` in your editor and paste the API key I sent you by Slack right after `ANTHROPIC_API_KEY=`.
4. Type your Macalester email right after `WIKIPEDIA_CONTACT=`, and save `.env`.
5. Type your name after `Name:` at the top of `WRITEUP.md`, and save.
6. Copy the command the homework page shows for 0a, paste it into that tab and press Enter.
7. Say yes when Claude Code asks whether you trust this folder.
8. Ask Claude to run the set-up check.
9. Fix each line marked `NOT READY` in your editor, save, and ask Claude to run the check again.
10. Repeat action 9 until the check's last line reads "Everything is ready."

**What you'll see:** Claude runs this command:

```
uv run python check_setup.py
```

It prints one line each, marked `ok` or `NOT READY`, for five things: the `.env` file is there, the key
is filled in, the email is filled in, Wikipedia answered a search, and the Claude API accepted your key.
A `NOT READY` line says what to fix. The check never prints your key or email, and costs a small
fraction of a cent.

**What to write:** Only your name, after `Name:` at the top of `WRITEUP.md`.

**You're done when:** The check's last line reads "Everything is ready." and the homework page ticks 0a:
the saved `WRITEUP.md` has your name after `Name:`, and the check has passed (it then saves
`runs/part0/setup-check.txt`, which is how the page knows).

**If something goes wrong:**

- Claude says the model in the command is not available: delete `--model claude-opus-5-5 --effort medium`
  from the command, and run the rest of it.
- `NOT READY` again after you fixed `.env`: save the file and run the check again. If it still fails,
  post the `NOT READY` line in `#comp440-f26` on Slack.
- A first line reading "ANTHROPIC_API_KEY is set and takes precedence...": a harmless notice from
  Anthropic's library, which a few laptops print before every run.
- Your editor's Open window does not show `.env`: press Command-Shift-period in that window to show
  hidden files, or open the whole `comp440-hw3` folder in your editor.
- You can't find the key I sent you: ask me on Slack.

**Hint:** The agent calls the Claude API directly, not through your Claude Code account, so it needs
your key. The email gives your runs their own allowance of Wikipedia requests; without it, you share
one with the whole class. `.env` is never committed and no Claude session reads it. The key never goes
in the chat, because your conversations are saved in `TRANSCRIPT.md` and pushed to GitHub, where anyone
can read them.

## 0b. Ask the model with no tools

**What you're finding out:** How well the model checks a claim from memory alone, with no lookups.
This is the no-tools baseline, the simplest of the three versions (no tools, one search, the agent)
you will compare.

The claim you check in Part 0:

> The composer of "Persian Surgery Dervishes" was born on June 24, 1935.

**Words in this step:** *the model*: Claude Haiku, the small Claude model that every version in this
homework calls. *baseline*: a simpler method the agent is compared with. *verdict*: *supported*,
*refuted* or *doesn't say*. *token*: the unit the API counts text in and charges by, about three
quarters of a word.

**What to do:**

1. Start this step's Claude session with the command the homework page shows for 0b, in a terminal tab in the
   homework's folder. If the last step's Claude is still open in that tab, type `/exit` first.
2. Ask Claude to run the no-tools baseline on the claim.
3. Tell Claude what verdict you expect, when it asks. "Not sure" is a fine answer.
4. Read the output Claude pastes into the chat.
5. Answer the two questions in `WRITEUP.md`.

**What you'll see:** Claude runs this command:

```
uv run python check.py --method no-tools --out runs/part0 'The composer of "Persian Surgery Dervishes" was born on June 24, 1935.'
```

The output gives the verdict, the model's explanation, and a line with the lookups (none here),
tokens, cost and time. The result is saved as `runs/part0/no-tools-<number>.json`.

**What to write:** In `WRITEUP.md`, under 0b:

- What verdict did the model give, and what reason did it give? Quote the lines of the output that show them.
- How much would you trust this answer, and why?

**You're done when:** The homework page ticks 0b: a `runs/part0/no-tools-<number>.json` file exists,
and both answers have text after the `>`.

**If something goes wrong:** If the run says the API key is missing or wrong, check in your editor that
your key comes right after `ANTHROPIC_API_KEY=` in `.env`. Never paste the key into the chat.

## 0c. Give it one search

**What you're finding out:** What one Wikipedia search adds, and whether it lands on a page that
settles the claim.

The claim you check in Part 0:

> The composer of "Persian Surgery Dervishes" was born on June 24, 1935.

**Words in this step:** *the one-search baseline*: the model (Claude Haiku) writes one Wikipedia search,
the program reads the opening paragraphs of the top page found, and the model answers from that page
alone. *verdict*: *supported*, *refuted* or *doesn't say*.

**What to do:**

1. Start this step's Claude session with the command the homework page shows for 0c, in a terminal tab in the
   homework's folder. If the last step's Claude is still open in that tab, type `/exit` first.
2. Ask Claude to run the one-search baseline on the claim.
3. Tell Claude which page you would want it to read, when it asks. If you don't know its title,
   describe the page, or say you're not sure.
4. Read the output Claude pastes into the chat.
5. Click "Open these results" under 0c on the homework page to read the whole page it read.
6. Answer the two questions in `WRITEUP.md`.

**What you'll see:** Claude runs this command:

```
uv run python check.py --method one-search --out runs/part0 'The composer of "Persian Surgery Dervishes" was born on June 24, 1935.'
```

The line numbered 1 is the search and a short version of its results; the line numbered 2 is the page
it read and a short version of that page. Then come the verdict, the explanation, and a line with the lookups, tokens, cost and
time. The result is saved as `runs/part0/one-search-<number>.json`. In the results viewer, a long result
is folded: click "+ Show the whole result".

**What to write:** In `WRITEUP.md`, under 0c:

- Which Wikipedia page did it read? Quote the line of the output that shows it.
- Did that page settle the claim? If not, why do you think the search led there?

**You're done when:** The homework page ticks 0c: a `runs/part0/one-search-<number>.json` file exists,
and both answers have text after the `>`.

**If something goes wrong:**

- The run warns that `WIKIPEDIA_CONTACT` is not set: add `WIKIPEDIA_CONTACT=` and your Macalester email
  to `.env`, in your editor.
- "Open these results" isn't there: open **Results** at the top of the homework page and, under "Part 0:
  Set up", click the claim in the row whose Version is "one-search baseline".

## 0d. Run the agent and read its trace

**What you're finding out:** How the agent gets from the claim to a verdict when it chooses its own
lookups.

The claim you check in Part 0:

> The composer of "Persian Surgery Dervishes" was born on June 24, 1935.

**Words in this step:** *the agent*: the program in `agent.py` and its loop, in which the model (Claude
Haiku) picks the next lookup, reads what comes back, and decides when to answer. The model is a small
Claude model that the program calls with your key; it is not the Claude you are typing to. In Part 0 the
agent runs on the reference loop, a loop I wrote; you write your own in Part 1. *lookup*: one call to
`search`, `read` or `wikidata`. `wikidata` asks Wikidata for one fact; Wikidata (wikidata.org) is a
separate site from Wikipedia that stores single facts, such as a person's date of birth. *trace*: the
record of the agent's lookups for one claim, in order, with what each returned; it is not an error
report. *entry*: one numbered line of a trace, a lookup or an answer. *evidence*: the sentences quoted
from Wikipedia that a verdict rests on.

**What to do:**

1. Start this step's Claude session with the command the homework page shows for 0d, in a terminal tab in the
   homework's folder. If the last step's Claude is still open in that tab, type `/exit` first.
2. Ask Claude to run the agent on the claim.
3. Tell Claude what you expect the agent to do, when it asks.
4. Read the trace Claude pastes into the chat, one entry at a time.
5. Click "Open these results" under 0d and read "The agent's trace", with each lookup's full result.
6. Answer the two questions in `WRITEUP.md`.

**What you'll see:** Claude runs this command:

```
uv run python check.py --method agent --out runs/part0 'The composer of "Persian Surgery Dervishes" was born on June 24, 1935.'
```

The first line says which loop the agent ran on: `Agent loop: the reference loop (reference_loop.py)`.
Each numbered entry is one call to one of the agent's four tools (`search`, `read`, `wikidata`,
`answer`): what it asked for, then a short version of what came back. The last is usually `answer`. Then
come the verdict, the evidence, the explanation, and the line of lookups, tokens, cost and time. The
numbers count every entry in the trace, answers included. The Lookups count on the last line counts
only `search`, `read` and `wikidata`, so it can be smaller than the last number. When a question asks
for a number, give the number on that entry's line. The
result is saved as `runs/part0/agent-<number>.json`. In the results viewer, "Open every result" unfolds
every lookup.

A trace sometimes shows an answer that was sent back (rejected) before a later one was accepted. That
is the loop's evidence check: a quoted sentence was not in anything the agent had read, and text shown
in a search result does not count as read.

**What to write:** In `WRITEUP.md`, under 0d:

- In one or two sentences, how did the agent get from the claim to its verdict? Point to the entries by their numbers in the trace.
- Which lookup would you have done differently, and how? If none, which one surprised you?

**You're done when:** The homework page ticks 0d: a `runs/part0/agent-<number>.json` file exists, and
both answers have text after the `>`. That finishes Part 0, so the page commits your work as
`Part 0 done` and pushes it to your fork.

**If something goes wrong:**

- Wikipedia asks the program to slow down: it waits and tries again by itself. If the run stops with an
  error anyway, ask Claude to run the same command again.
- "Open these results" isn't there: open **Results** at the top of the homework page and, under "Part 0:
  Set up", click the claim in the row whose Version is "agent".

## What I look for

Part 0 is 10% of the homework. At a minimum I am looking for the following:

- Set up: 40% - Your repository runs, and the three outputs are in `runs/part0/`.
- Reading the outputs: 60% - Your answers to 0b, 0c and 0d say what each version did with this claim
  and point to the line of the output or trace that shows it.
