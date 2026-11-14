# COMP 440 HW3 Part 0: Set up and check one claim

In this part you get your copy of the homework running. Then you check one claim by feeding it to an
LLM, using a Wikipedia search, and using the agent. It should take about an hour.

Back to the [assignment page](../README.md).

## 0a. Get your copy running

In this step you get the homework running on your laptop, so the later steps can reach Wikipedia and the
Claude API.

**Words in this step:** *Claude* is this step's Claude Code session, your tutor. *`.env`* is the file
that holds your API key and your email; only you edit it.

**Actions:** First fork the repository, clone your fork and start the homework page, as the README's
Getting started section says. Then:

1. Open a new terminal tab in the homework's folder, `comp440-hw3`.
2. Run `cp .env.example .env`.
3. Open `.env` in your editor. Paste the API key I sent you by Slack right after `ANTHROPIC_API_KEY=`,
   type your Macalester email right after `WIKIPEDIA_CONTACT=`, and save.
4. In your editor, type your name after `Name:` at the top of `WRITEUP.md`, and save.
5. In that tab, start this step's Claude session with the command the homework page shows for 0a.
6. Ask Claude to run the set-up check. Fix each `NOT READY` line in your editor and ask again, until the
   last line reads "Everything is ready."

**Interpreting output:** Claude runs this command:

```
uv run python check_setup.py
```

It prints `ok` or `NOT READY` for each of five things: the `.env` file is there, the key is filled in,
the email is filled in, Wikipedia answered a search, and the Claude API accepted your key. A `NOT READY`
line says what to fix. The check never prints your key or email, and costs a small fraction of a cent.

**Write-up:** Write only your name, after `Name:` at the top of `WRITEUP.md`.

**Troubleshooting:**

- Claude says the model in the command is not available. Delete `--model claude-opus-5-5 --effort medium`
  from the command, and run the rest of it. Do the same with the command of every later step.
- The check still says `NOT READY` after you fixed `.env`. Check that you saved the file; if so, post the
  `NOT READY` line in `#comp440-f26` on Slack.
- The output starts with "ANTHROPIC_API_KEY is set and takes precedence...". That is a harmless notice
  from Anthropic's library, which a few laptops print before every run.
- Your editor's Open window does not show `.env`. Press Command-Shift-period to show hidden files, or open
  the whole `comp440-hw3` folder.
- You can't find the key I sent you. Ask me on Slack.

**Hint:** The email gives your runs their own allowance of Wikipedia requests; without it, you share one
with the whole class. `.env` is never committed and no Claude session reads it. Never put the key in the
chat, because your conversations are saved in `TRANSCRIPT.md` and pushed to GitHub, where anyone can read
them.

## 0b. Ask the model to assess a claim without tools

In this step you find out how well the model checks a single claim about Persian Surgery Dervishes from
memory alone, with no lookups. This is the no-tools baseline, the simplest of the three versions (no
tools, one search, the agent).

The claim you check in Part 0:

> The composer of "Persian Surgery Dervishes" was born on June 24, 1935.

**Words in this step:** *The model* is Claude Haiku, the small LLM that every version in this homework
calls with your key; it is not the Claude you are typing to. A *baseline* is a simpler method the agent is compared with. A *verdict* is one of *supported*,
*refuted* or *doesn't say*.

**Actions:**

1. Start this step with Claude: paste its prompt from the homework page into the Claude session you
   have open, or start a new session with its command (type `/exit` first if another session is
   open in that terminal).
2. Ask Claude to run the no-tools baseline on the claim, and read the output it pastes.
3. Type your answer to the question in `WRITEUP.md`, in your editor, under 0b.

**Interpreting output:** Claude runs this command:

```
uv run python check.py --method no-tools --out runs/part0 'The composer of "Persian Surgery Dervishes" was born on June 24, 1935.'
```

It prints the verdict, the model's explanation (its reason, from memory alone), and a line with the
lookups (none here) and the time. The result is saved as `runs/part0/no-tools-<number>.json`.

**Write-up:** Answer this question in `WRITEUP.md`, under 0b:

- What verdict did the model give (*supported*, *refuted* or *doesn't say*), and what reason did it give? Quote the lines of the output that show them.

**Troubleshooting:** If the run says the API key is missing or wrong, check in your editor that your key
comes right after `ANTHROPIC_API_KEY=` in `.env`. Never paste the key into the chat.

## 0c. Give it one search

In this step you find out whether including information captured from one Wikipedia search improves your
claim assessor.

The claim you check in Part 0:

> The composer of "Persian Surgery Dervishes" was born on June 24, 1935.

**Words in this step:** In *the one-search baseline*, the model writes one Wikipedia search, the program
reads the opening paragraphs of the top page found, and the model answers from that page alone. A *claim
assessor* is a program that gives a verdict on a claim; here, the model with one search.

**Actions:**

1. Start this step with Claude: paste its prompt from the homework page into the Claude session you
   have open, or start a new session with its command (type `/exit` first if another session is
   open in that terminal).
2. Ask Claude to run the one-search baseline on the claim, and read the output it pastes.
3. Click "Open these results" under 0c on the homework page to read the whole page it read.
4. Type your answers to the two questions in `WRITEUP.md`, in your editor, under 0c.

**Interpreting output:** Claude runs this command:

```
uv run python check.py --method one-search --out runs/part0 'The composer of "Persian Surgery Dervishes" was born on June 24, 1935.'
```

Line 1 is the search and a short version of its results; line 2 is the page it read, shortened. Then
come the verdict, the explanation, and the line of lookups and time. The verdict is based
only on the page in line 2. The result is saved as `runs/part0/one-search-<number>.json`.

**Write-up:** Answer these questions in `WRITEUP.md`, under 0c:

- Which Wikipedia page did it read? Quote the line of the output that shows it.
- Did that page settle the claim correctly? If not, why do you think the search led there?

**Troubleshooting:**

- The run warns that `WIKIPEDIA_CONTACT` is not set. Add `WIKIPEDIA_CONTACT=` and your Macalester email
  to `.env`, in your editor.
- "Open these results" isn't there. Open **Results** at the top of the homework page and, under "Part 0:
  Set up and check one claim", click the claim in the row whose Version is "one-search baseline".

## 0d. Run the agent and read its trace

In this step you find out how the agent gets from the claim to a verdict when it chooses its own lookups.

The claim you check in Part 0:

> The composer of "Persian Surgery Dervishes" was born on June 24, 1935.

**Words in this step:** *The agent* is the program in `agent.py` and its loop, in which the model picks
the next lookup, reads what comes back, and decides when to answer. A *lookup* is one call to `search`,
`read` or `wikidata`; `wikidata` asks Wikidata (wikidata.org) for one fact, such as a date of birth. A
*trace* is the agent's lookups for one claim, in order, with what each returned (not an error report). An
*entry* is one numbered line of a trace: a lookup or an answer. The *evidence* is the sentences quoted
from Wikipedia that a verdict is based on.

**Actions:**

1. Start this step with Claude: paste its prompt from the homework page into the Claude session you
   have open, or start a new session with its command (type `/exit` first if another session is
   open in that terminal).
2. Ask Claude to run the agent on the claim, and read the trace it pastes, one entry at a time.
3. Click "Open these results" under 0d and read "The agent's trace", with each lookup's full result.
4. Find out what Wikidata is: ask Claude, or look at wikidata.org.
5. Type your answers to the three questions in `WRITEUP.md`, in your editor, under 0d.

**Interpreting output:** Claude runs this command:

```
uv run python check.py --method agent --out runs/part0 'The composer of "Persian Surgery Dervishes" was born on June 24, 1935.'
```

The first line names the loop: `Agent loop: the reference loop (reference_loop.py)`, a loop I wrote (you
design your own in Part 1). Each numbered entry
is one tool call (`search`, `read`, `wikidata` or `answer`): what it asked for, then a short version of
what came back. Then come the verdict, the evidence, the explanation, and the line of lookups and
time. The entry numbers count answers too, but the Lookups count does not, so it can be smaller
than the last entry's number; when a question asks for a number, give the entry's. The result is saved as
`runs/part0/agent-<number>.json`.

An answer that was sent back (rejected) before a later one was accepted is the loop's evidence check: a
quoted sentence was not in anything the agent had read. Text in a search result does not count as read.

**Write-up:** Answer these questions in `WRITEUP.md`, under 0d:

- In one or two sentences, how did the agent get from the claim to its verdict? Point to the trace entries by their numbers.
- Which lookup would you have done differently, and how? If none, which one surprised you?
- Describe Wikidata briefly. Why may it be important to this task?

**Troubleshooting:**

- Wikipedia asks the program to slow down. It waits and tries again by itself. If the run stops with an
  error anyway, ask Claude to run the same command again.
- "Open these results" isn't there. Open **Results** at the top of the homework page and, under "Part 0:
  Set up and check one claim", click the claim in the row whose Version is "agent".

## What I look for

Part 0 is 15% of the homework. At a minimum I am looking for the following:

- Set up: 35% - Your repository runs, and the three outputs are in `runs/part0/`.
- Reading the outputs: 65% - Your answers to 0b, 0c and 0d say what each version did with this claim
  and point to the line of the output or trace that shows it.
