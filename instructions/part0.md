# COMP 440 HW3 Part 0: Set up and find your claims

Due 8:00am Tuesday, November 24. Back to the [assignment page](../README.md).

In this part you get your copy of the homework running, and select the dataset's claims about a few
topics you know: every run in this homework uses them. Then you check one claim three ways: with the
model alone, with one Wikipedia search, and with the agent. You'll see what each does with the same claim
before you look inside any of them. It should take about 1 hour and 35 minutes.

## 0a. Get your copy running

In this step you get the homework running on your laptop, so the later steps can reach Wikipedia and the
Claude API.

**Words in this step:** *Claude* is your Claude Code session, your tutor and lab assistant; each step
has its own. *`.env`* is the file that holds your API key and your email, and only you edit it.

**Actions:** First fork the repository, clone your fork and start the homework page, as the README's
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

**Output:** Claude runs this command:

```
uv run python check_setup.py
```

It prints one line each, marked `ok` or `NOT READY`, for five things: the `.env` file is there, the key
is filled in, the email is filled in, Wikipedia answered a search, and the Claude API accepted your key.
A `NOT READY` line says what to fix. The check never prints your key or email, and costs a small
fraction of a cent.

**Write-up:** Write only your name, after `Name:` at the top of `WRITEUP.md`.

**Completion:** The check's last line reads "Everything is ready." and the homework page ticks 0a:
the saved `WRITEUP.md` has your name after `Name:`, and the check has passed (it then saves
`runs/part0/setup-check.txt`, which is how the page knows).

**Troubleshooting:**

- Claude says the model in the command is not available. Delete `--model claude-opus-5-5 --effort medium`
  from the command, and run the rest of it.
- The check says `NOT READY` again after you fixed `.env`. Save the file and run the check again. If it
  still fails, post the `NOT READY` line in `#comp440-f26` on Slack.
- The output starts with a line reading "ANTHROPIC_API_KEY is set and takes precedence...". That is a
  harmless notice from Anthropic's library, which a few laptops print before every run.
- Your editor's Open window does not show `.env`. Press Command-Shift-period in that window to show
  hidden files, or open the whole `comp440-hw3` folder in your editor.
- You can't find the key I sent you. Ask me on Slack.

**Hint:** The agent calls the Claude API directly, not through your Claude Code account, so it needs
your key. The email gives your runs their own allowance of Wikipedia requests; without it, you share
one with the whole class. `.env` is never committed and no Claude session reads it. The key never goes
in the chat, because your conversations are saved in `TRANSCRIPT.md` and pushed to GitHub, where anyone
can read them.

## 0b. Pick your topics and find your claims

In this step you pick a few topics you know better than most people, and select the dataset's claims about
them. Every run in this homework uses those claims.

**Words in this step:** The *claim finder* is the screen that opens from **Find claims** at the top of
the homework page. It searches about 11,700 claims from HoVer, the public dataset of claims this homework
uses. A search *by keyword* finds the claims that contain your words. A search *by meaning* finds the
claims whose words are close in meaning to what you typed, even when they share no word with it, using
word vectors (a short list of numbers for each word, made so that words used in similar ways get similar
numbers). A search by *both* combines the two rankings into one. *Your claims* are the 112 claims you
select and save: your 12 *development claims*, for trying things out in Part 1, and your 100 *evaluation
claims*, for the full run in 1e and everything after it.

**Actions:**

1. Start this step's Claude session with the command the homework page shows for 0b, in a terminal tab in the
   homework's folder. If the last step's Claude is still open in that tab, type `/exit` first.
2. Pick two to four topics you know better than most people.
3. Open **Find claims** at the top of the homework page.
4. Type your first topic in the box, in a few words, and press **Search**.
5. Try all three ways of searching: by keyword, by meaning and both. Try other words for the topic too.
6. Read down the list, and press **Select** on each claim that is on your topic. **Show 50 more**, at the
   end of the list, shows the next 50.
7. When the claims stop being about your topic, stop selecting and search your next topic.
8. Keep going until the line at the top says you have selected 112 of 112 claims. That line also shows how
   many of them are labeled *supported* and how many *not supported*.
9. Press **Show my selection** to read your claims once more, and press **Remove** on any you no longer
   want.
10. Press **Save these as my claims**.
11. Answer the three questions.

This step is mostly reading, and it is the longest step of Part 0.

Topics that work are broad areas that Wikipedia covers well: a sport, film, television, a broad kind of
music, or a country's geography or history. Pick ones you could fact-check yourself without looking much
up. The dataset's claims were written from Wikipedia's most-read articles of 2017, mostly about films,
television, music, sports and places. So it has hundreds of claims on a broad area such as film or
basketball, and only a few dozen on a narrow one such as jazz or Minnesota. The best claims for a topic
come first, so I expect most of you to need two to four topics to reach 112. Film, television,
basketball, American football and rock music each give a list that stays on the topic for 100 claims or
more. The lists for jazz, physics and Formula One drift off their topic much sooner. A topic typed as a
phrase the dataset rarely uses, such as "the Cold War", finds few claims on it at all, so try other words
for it.

**Output:** The claim finder shows the claims for your search, best first, 50 at a time. Above them it
says how many claims contain all of your words. When that number is small, it says that the dataset has
few claims on this topic, so the list drifts off it further down. As a rule, a list stays on its topic
when about 200 claims or more contain all of its words. About six in ten of the dataset's claims are
labeled *supported*, so your selection will lean that way, and that is fine: saving asks only for at
least 30 of each label. Each claim shows the dataset's label, the number of articles it needs, the
titles of those articles with Wikipedia's one-line description of each, and its rank by keyword and by
meaning (1 is best). A claim that one search did not find has no rank in that search. A claim you have
selected says so, and its button says **Remove**. Your selection is kept in your browser, so another
search or reloading the page does not lose it.

**Save these as my claims** saves only when three things are true, and when one is not, it says which.
You need exactly 112 claims, because that makes 12 development claims and 100 evaluation claims. At
least 30 must be labeled *supported* and at least 30 *not supported*, so that an agent that always gives
the same answer cannot score well. And the agent must not have run on your claims yet, because runs made
on other claims would not match your new ones.

Saving puts your claims in the order of their ids, which is as good as random, so your topics are mixed
and the first claims in any list are not all from one topic. The first six *supported* and the first six
*not supported* claims in that order become your development claims, in `data/dev.jsonl`. The other 100
become your evaluation claims, in `data/eval.jsonl`. They replace the sample claims those two files hold
until then. Saving also writes `data/my-topic.json`, a note of your topics and how many claims came from
each. You can search and save again as often as you like until you run the agent on your claims in step
1c. After that the claim finder will not save over them: it refuses once `runs/part1/before`,
`runs/part1/after` or `runs/part2` holds anything, the folders that steps 1c, 1d and 1e write.

**Write-up:** Answer these questions in `WRITEUP.md`, under 0b:

- What are your topics, and why do you know each of them better than most people?
- What did you type in the claim finder for each topic, and which way of searching did you keep (by keyword, by meaning or both)? Why that one?
- Quote one claim that only the search by meaning found, or only the search by keyword found, with its rank in the search that found it. What does it show about how the two searches differ?

**Completion:** The homework page ticks 0b: `data/my-topic.json` exists (saving writes it), and the
three answers have text after the `>`.

**Troubleshooting:**

- Saving says you need more claims of one label. Search one of your topics again and select more claims
  with that label, or search another topic.
- Saving says you have already run the agent on your claims. To choose different claims, rename the three
  folders the message names, select and save your new claims, and do the runs of steps 1c, 1d and 1e
  again.
- The claim finder will not open in your browser. Ask Claude to save claims for you in the terminal with
  `uv run python -m finder --save "<topic>" "<another topic>"`, one pair of quotes for each topic. It
  saves the best 112 claims for those topics, an even share from each, half *supported* and half *not
  supported*. You then cannot choose claims one by one, so use it only when the screen does not work.
- Neither works. Post what you see in `#comp440-f26` on Slack right away. The steps after this one stay
  locked until your claims are saved, so I will help you get past it.

**Hint:** Claude will not suggest a topic, a word to search with, or a claim to select or remove,
because the topics and what counts as on them are yours to decide. It will explain how the two kinds of
search work, and show you the code in `finder/search.py`, if you ask. Some of the dataset's claims are
worded oddly, because people made them by rewriting other claims. Select a claim if it is on your topic,
however it is worded.

## 0c. Ask the model with no tools

In this step you find out how well the model checks a claim from memory alone, with no lookups. This is
the no-tools baseline, the simplest of the three versions (no tools, one search, the agent) you will
compare.

The claim you check in Part 0:

> The composer of "Persian Surgery Dervishes" was born on June 24, 1935.

**Words in this step:** *The model* is Claude Haiku, the small Claude model that every version in this
homework calls. A *baseline* is a simpler method the agent is compared with. A *verdict* is one of
*supported*, *refuted* or *doesn't say*. A *token* is the unit the API counts text in and charges by,
about three quarters of a word.

**Actions:**

1. Start this step's Claude session with the command the homework page shows for 0c, in a terminal tab in the
   homework's folder. If the last step's Claude is still open in that tab, type `/exit` first.
2. Ask Claude to run the no-tools baseline on the claim.
3. Tell Claude what verdict you expect, when it asks. "Not sure" is a fine answer.
4. Read the output Claude pastes into the chat.
5. Answer the two questions in `WRITEUP.md`.

**Output:** Claude runs this command:

```
uv run python check.py --method no-tools --out runs/part0 'The composer of "Persian Surgery Dervishes" was born on June 24, 1935.'
```

The output gives the verdict, the model's explanation, and a line with the lookups (none here),
tokens, cost and time. The result is saved as `runs/part0/no-tools-<number>.json`.

**Write-up:** Answer these questions in `WRITEUP.md`, under 0c:

- What verdict did the model give, and what reason did it give? Quote the lines of the output that show them.
- How much would you trust this answer, and why?

**Completion:** The homework page ticks 0c: a `runs/part0/no-tools-<number>.json` file exists,
and both answers have text after the `>`.

**Troubleshooting:** If the run says the API key is missing or wrong, check in your editor that
your key comes right after `ANTHROPIC_API_KEY=` in `.env`. Never paste the key into the chat.

## 0d. Give it one search

In this step you find out what one Wikipedia search adds. You also see whether the search lands on a page
that settles the claim.

The claim you check in Part 0:

> The composer of "Persian Surgery Dervishes" was born on June 24, 1935.

**Words in this step:** In *the one-search baseline*, the model (Claude Haiku) writes one Wikipedia
search, the program reads the opening paragraphs of the top page found, and the model answers from that
page alone. A *verdict* is one of *supported*, *refuted* or *doesn't say*.

**Actions:**

1. Start this step's Claude session with the command the homework page shows for 0d, in a terminal tab in the
   homework's folder. If the last step's Claude is still open in that tab, type `/exit` first.
2. Ask Claude to run the one-search baseline on the claim.
3. Tell Claude which page you would want it to read, when it asks. If you don't know its title,
   describe the page, or say you're not sure.
4. Read the output Claude pastes into the chat.
5. Click "Open these results" under 0d on the homework page to read the whole page it read.
6. Answer the two questions in `WRITEUP.md`.

**Output:** Claude runs this command:

```
uv run python check.py --method one-search --out runs/part0 'The composer of "Persian Surgery Dervishes" was born on June 24, 1935.'
```

The line numbered 1 is the search and a short version of its results; the line numbered 2 is the page
it read and a short version of that page. Then come the verdict, the explanation, and a line with the lookups, tokens, cost and
time. The result is saved as `runs/part0/one-search-<number>.json`. In the results viewer, a long result
is folded: click "+ Show the whole result".

**Write-up:** Answer these questions in `WRITEUP.md`, under 0d:

- Which Wikipedia page did it read? Quote the line of the output that shows it.
- Did that page settle the claim? If not, why do you think the search led there?

**Completion:** The homework page ticks 0d: a `runs/part0/one-search-<number>.json` file exists,
and both answers have text after the `>`.

**Troubleshooting:**

- The run warns that `WIKIPEDIA_CONTACT` is not set. Add `WIKIPEDIA_CONTACT=` and your Macalester email
  to `.env`, in your editor.
- "Open these results" isn't there. Open **Results** at the top of the homework page and, under "Part 0:
  Set up", click the claim in the row whose Version is "one-search baseline".

## 0e. Run the agent and read its trace

In this step you find out how the agent gets from the claim to a verdict when it chooses its own lookups.

The claim you check in Part 0:

> The composer of "Persian Surgery Dervishes" was born on June 24, 1935.

**Words in this step:** *The agent* is the program in `agent.py` and its loop, in which the model
(Claude Haiku) picks the next lookup, reads what comes back, and decides when to answer. The model is a
small Claude model that the program calls with your key; it is not the Claude you are typing to. In Part
0 the agent runs on the reference loop, a loop I wrote; you write your own in Part 1. A *lookup* is one
call to `search`, `read` or `wikidata`. `wikidata` asks Wikidata for one fact; Wikidata (wikidata.org)
is a separate site from Wikipedia that stores single facts, such as a person's date of birth. A *trace*
is the record of the agent's lookups for one claim, in order, with what each returned; it is not an
error report. An *entry* is one numbered line of a trace, a lookup or an answer. The *evidence* is the
sentences quoted from Wikipedia that a verdict rests on.

**Actions:**

1. Start this step's Claude session with the command the homework page shows for 0e, in a terminal tab in the
   homework's folder. If the last step's Claude is still open in that tab, type `/exit` first.
2. Ask Claude to run the agent on the claim.
3. Tell Claude what you expect the agent to do, when it asks.
4. Read the trace Claude pastes into the chat, one entry at a time.
5. Click "Open these results" under 0e and read "The agent's trace", with each lookup's full result.
6. Answer the two questions in `WRITEUP.md`.

**Output:** Claude runs this command:

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

**Write-up:** Answer these questions in `WRITEUP.md`, under 0e:

- In one or two sentences, how did the agent get from the claim to its verdict? Point to the entries by their numbers in the trace.
- Which lookup would you have done differently, and how? If none, which one surprised you?

**Completion:** The homework page ticks 0e: a `runs/part0/agent-<number>.json` file exists, and
both answers have text after the `>`. That finishes Part 0, so the page commits your work as
`Part 0 done` and pushes it to your fork.

**Troubleshooting:**

- Wikipedia asks the program to slow down. It waits and tries again by itself. If the run stops with an
  error anyway, ask Claude to run the same command again.
- "Open these results" isn't there. Open **Results** at the top of the homework page and, under "Part 0:
  Set up", click the claim in the row whose Version is "agent".

## What I look for

Part 0 is 10% of the homework. At a minimum I am looking for the following:

- Set up: 25% - Your repository runs, and the three outputs are in `runs/part0/`.
- Your topics and claims: 30% - Your claims are saved, and your 0b answers say why you know each topic
  and compare the two kinds of search with a real claim and its rank.
- Reading the outputs: 45% - Your answers to 0c, 0d and 0e say what each version did with this claim
  and point to the line of the output or trace that shows it.
