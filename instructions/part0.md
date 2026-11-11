# COMP 440 HW3 Part 0: Set up and find your claims

Due 8:00am Tuesday, November 24. Back to the [assignment page](../README.md).

In this part you get your copy of the homework running, and create a dataset of claims about a few
topics you are interested in. Then you check one claim by feeding it to an LLM, using a Wikipedia search,
and using the agent. It should take about 1 hour and 40 minutes.

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
4. Type your name after `Name:` at the top of `WRITEUP.md`, and save.
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
  from the command, and run the rest of it.
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

## 0b. Pick your topics and find your claims

In this step you pick a few topics you are interested in, and select 112 of the dataset's claims about
them in the claim finder. You will use 12 claims for development and 100 for evaluation.

**Words in this step:** The *claim finder* (**Find claims** at the top of the homework page) searches
about 11,700 claims from HoVer, the public dataset this homework uses. A search *by keyword* finds the
claims that contain your words. A search *by meaning* finds claims whose words are close in meaning to
yours, using word vectors (lists of numbers that are close for words used in similar ways). A search by
*both* combines the two rankings. *Retrieval* is finding the items in a collection that best match a
request; `finder/search.py` holds the claim finder's retrieval code.

**Actions:**

1. Start this step's Claude session (type `/exit` first if another one is open).
2. Pick two to four topics you are interested in.
3. Open **Find claims** at the top of the homework page, and search your first topic in a few words. Try
   the three ways of searching, and other words for the topic.
4. Press **Select all 50 shown** above the list, then **Remove** on each claim that is not on your
   topic. You can also **Select** one claim at a time.
5. Press **Show 50 more** for more claims on the topic. When the claims stop being about your topic,
   search the next one.
6. When the line at the top says you have selected 112 of 112 claims, press **Save these as my claims**.
7. Read the retrieval code, lines 1 to 165 of `finder/search.py`, and answer the two questions.

**Interpreting output:** The claim finder shows the claims for your search, best first, 50 at a time.
Each shows the dataset's label, the number of articles it needs, those articles' titles with
Wikipedia's one-line description of each, and its rank by keyword and by meaning (1 is best). Above the
list, a count says how many claims contain all your words. For a topic of one or two words, a count
under about 200 means the list may stop being about the topic further down, and the screen says so. **Select all 50
shown** selects every claim shown that you have not selected yet; its number says how many, and it never
takes you past 112. **Show my selection** lists your selection.

**Save these as my claims** works only when you have exactly 112 claims, at least 30 labeled
*supported* and at least 30 *not supported*, and the agent has not yet run on them. The labels rule is so
that an agent that always gives the same answer cannot score well; about six in ten claims are
*supported*, so more of your claims will be *supported*. The last rule is because runs on other claims would
not match your new ones. Saving puts six claims of each label in `data/dev.jsonl` as your development
claims and the other 100 in `data/eval.jsonl` as your evaluation claims, in an order that mixes your
topics, and notes your topics in `data/my-topic.json`. You can save again until you run the agent on
your claims in step 1c.

**Write-up:** Answer these questions in `WRITEUP.md`, under 0b:

- Why did you choose the topics you did?
- Read through the [retrieval code](https://github.com/shilad/comp440-hw3/blob/main/finder/search.py#L1-L165) in `finder/search.py`. Describe its overall approach in three sentences.

**Troubleshooting:**

- Saving says you need more claims of one label. Select more claims with that label, from one of your
  topics or a new one.
- Saving says you have already run the agent on your claims. To change them, rename the three folders the
  message names, save your new claims, and do the runs of steps 1c, 1d and 1e again.
- Your selection is gone after you restarted the homework page. The page came back at another address
  (the number after `localhost:`), and the browser keeps a selection for each address. Restart it with
  `uv run python -m workbench --port <the old number>`, or select again; saved claims are not affected.
- The claim finder will not open in your browser. Ask Claude to run
  `uv run python -m finder --save "<topic>" "<another topic>"`, with one pair of quotes for each topic.
  It saves the best 112 claims for those topics, an even share from each, half *supported* and half *not
  supported*.
- Neither works. Post what you see in `#comp440-f26` on Slack right away. The later steps stay locked
  until your claims are saved, so I will help you get past it.

**Hint:** Broad topics that Wikipedia covers well work best: a sport, film, television, a broad kind of
music, or a country's geography or history. The claims were written from Wikipedia's most-read articles
of 2017, so the dataset has hundreds of claims on film or basketball and only a few dozen on jazz or
Minnesota. The best claims for a topic come first, so I expect most of you to need two to four topics.
Some claims are worded oddly, because people made them by rewriting other claims; select a claim if it is
on your topic, however it is worded. Claude will explain any line of `finder/search.py`, but the
three-sentence description is yours.

## 0c. Ask the model to assess a claim without tools

In this step you find out how well the model checks a single claim about Persian Surgery Dervishes from
memory alone, with no lookups. This is the no-tools baseline, the simplest of the three versions (no
tools, one search, the agent).

The claim you check in Part 0:

> The composer of "Persian Surgery Dervishes" was born on June 24, 1935.

**Words in this step:** *The model* is Claude Haiku, the small LLM that every version in this homework
calls with your key; it is not the Claude you are typing to. A *baseline* is a simpler method the agent is compared with. A *verdict* is one of *supported*,
*refuted* or *doesn't say*. A *token* is the unit the API counts and charges by, about three quarters of
a word.

**Actions:**

1. Start this step's Claude session (type `/exit` first if another one is open).
2. Ask Claude to run the no-tools baseline on the claim, and read the output it pastes.
3. Answer the question in `WRITEUP.md`.

**Interpreting output:** Claude runs this command:

```
uv run python check.py --method no-tools --out runs/part0 'The composer of "Persian Surgery Dervishes" was born on June 24, 1935.'
```

It prints the verdict, the model's explanation (its reason, from memory alone), and a line with the
lookups (none here), tokens, cost and time. The result is saved as `runs/part0/no-tools-<number>.json`.

**Write-up:** Answer this question in `WRITEUP.md`, under 0c:

- What verdict did the model give (*supported*, *refuted* or *doesn't say*), and what reason did it give? Quote the lines of the output that show them.

**Troubleshooting:** If the run says the API key is missing or wrong, check in your editor that your key
comes right after `ANTHROPIC_API_KEY=` in `.env`. Never paste the key into the chat.

## 0d. Give it one search

In this step you find out whether including information captured from one Wikipedia search improves your
claim assessor.

The claim you check in Part 0:

> The composer of "Persian Surgery Dervishes" was born on June 24, 1935.

**Words in this step:** In *the one-search baseline*, the model writes one Wikipedia search, the program
reads the opening paragraphs of the top page found, and the model answers from that page alone. A *claim
assessor* is a program that gives a verdict on a claim; here, the model with one search.

**Actions:**

1. Start this step's Claude session (type `/exit` first if another one is open).
2. Ask Claude to run the one-search baseline on the claim, and read the output it pastes.
3. Click "Open these results" under 0d on the homework page to read the whole page it read.
4. Answer the two questions in `WRITEUP.md`.

**Interpreting output:** Claude runs this command:

```
uv run python check.py --method one-search --out runs/part0 'The composer of "Persian Surgery Dervishes" was born on June 24, 1935.'
```

Line 1 is the search and a short version of its results; line 2 is the page it read, shortened. Then
come the verdict, the explanation, and the line of lookups, tokens, cost and time. The verdict is based
only on the page in line 2. The result is saved as `runs/part0/one-search-<number>.json`.

**Write-up:** Answer these questions in `WRITEUP.md`, under 0d:

- Which Wikipedia page did it read? Quote the line of the output that shows it.
- Did that page settle the claim correctly? If not, why do you think the search led there?

**Troubleshooting:**

- The run warns that `WIKIPEDIA_CONTACT` is not set. Add `WIKIPEDIA_CONTACT=` and your Macalester email
  to `.env`, in your editor.
- "Open these results" isn't there. Open **Results** at the top of the homework page and, under "Part 0:
  Set up and find your claims", click the claim in the row whose Version is "one-search baseline".

## 0e. Run the agent and read its trace

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

1. Start this step's Claude session (type `/exit` first if another one is open).
2. Ask Claude to run the agent on the claim, and read the trace it pastes, one entry at a time.
3. Click "Open these results" under 0e and read "The agent's trace", with each lookup's full result.
4. Answer the two questions in `WRITEUP.md`.

**Interpreting output:** Claude runs this command:

```
uv run python check.py --method agent --out runs/part0 'The composer of "Persian Surgery Dervishes" was born on June 24, 1935.'
```

The first line names the loop: `Agent loop: the reference loop (reference_loop.py)`, a loop I wrote (you
write your own in Part 1). Each numbered entry
is one tool call (`search`, `read`, `wikidata` or `answer`): what it asked for, then a short version of
what came back. Then come the verdict, the evidence, the explanation, and the line of lookups, tokens,
cost and time. The entry numbers count answers too, but the Lookups count does not, so it can be smaller
than the last entry's number; when a question asks for a number, give the entry's. The result is saved as
`runs/part0/agent-<number>.json`.

An answer that was sent back (rejected) before a later one was accepted is the loop's evidence check: a
quoted sentence was not in anything the agent had read. Text in a search result does not count as read.

**Write-up:** Answer these questions in `WRITEUP.md`, under 0e:

- In one or two sentences, how did the agent get from the claim to its verdict? Point to the trace entries by their numbers.
- Which lookup would you have done differently, and how? If none, which one surprised you?

**Troubleshooting:**

- Wikipedia asks the program to slow down. It waits and tries again by itself. If the run stops with an
  error anyway, ask Claude to run the same command again.
- "Open these results" isn't there. Open **Results** at the top of the homework page and, under "Part 0:
  Set up and find your claims", click the claim in the row whose Version is "agent".

## What I look for

Part 0 is 15% of the homework. At a minimum I am looking for the following:

- Set up: 25% - Your repository runs, and the three outputs are in `runs/part0/`.
- Your topics and claims: 30% - Your claims are saved, your first 0b answer says why you chose your
  topics, and your second describes the retrieval code's approach in three sentences of your own.
- Reading the outputs: 45% - Your answers to 0c, 0d and 0e say what each version did with this claim
  and point to the line of the output or trace that shows it.
