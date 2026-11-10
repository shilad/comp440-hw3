# COMP 440 HW3 write-up

Name:

Type each answer after the `>` under its question. A longer answer can go on over the following lines,
with no blank line inside it (to start a new paragraph, put a line with just `>` between the two). In a
table, fill every cell of every numbered row. Claude may paste a program's output where a question asks
for it, never an answer, and the homework page ticks a step when every answer in its section is filled in.

# Part 0: Set up and find your claims

## 0a. Get your copy running

There is nothing to write for this step except your name, after `Name:` at the top of this file.

## 0b. Pick your topics and find your claims

What are your topics, and why do you know each of them better than most people?

>

What did you type in the claim finder for each topic, and which way of searching did you keep (by keyword, by meaning or both)? Why that one?

>

Quote one claim that only the search by meaning found, or only the search by keyword found, with its rank in the search that found it. What does it show about how the two searches differ?

>

## 0c. Ask the model with no tools

What verdict did the model give, and what reason did it give? Quote the lines of the output that show them.

>

How much would you trust this answer, and why?

>

## 0d. Give it one search

Which Wikipedia page did it read? Quote the line of the output that shows it.

>

Did that page settle the claim? If not, why do you think the search led there?

>

## 0e. Run the agent and read its trace

In one or two sentences, how did the agent get from the claim to its verdict? Point to the entries by their numbers in the trace.

>

Which lookup would you have done differently, and how? If none, which one surprised you?

>

# Part 1: How the agent works

## 1a. Write the loop

What does your loop send to the model on each turn? Give the line numbers in `my_loop.py`.

>

What are the ways your loop can end? Give the line number of each.

>

Which rule took you longest to get right, and what was wrong with your first try?

>

Now open `reference_loop.py` and compare it with your loop. Name one difference, and say whether it changes what the agent does. (If you used `--use-reference`, say how far your own loop got and what stopped you.)

>

## 1b. Be the agent

Claim 1, to learn the tools: "Mel Duncan holds a history degree from the private, coeducational liberal arts Macalester College located in Saint Paul, Minnesota, US."

Claim 2: "Vic & Anthony's Steakhouse is located at the American casino that was combined with the California Club. The casino is owned by Landry's, Inc."

List your lookups for both claims, in order. Ask Claude to paste every column but the last from `runs/part1/lookups.jsonl`. Type every "Why you chose it" yourself.

| # | Claim (1 or 2) | Tool | What you asked for | Why you chose it |
|---|---|---|---|---|
| 1 | | | | |

What is your verdict on the first claim, and which sentence does it rest on?

>

What is your verdict on the second claim, and which sentence or sentences does it rest on? If you stopped at 12 lookups without settling it, your verdict is *doesn't say*: say where you got stuck.

>

How many lookups did the second claim take? Which one was hardest to choose, and why?

>

Did you have to back up and try something else? What happened?

>

## 1c. Watch the agent work

List the three traces you read closely, one claim each that needs 2, 3 and 4 articles, where your development claims have one. At least one is a claim the agent got wrong, where there is one.

| # | Claim (first few words) | Articles | Did it match the dataset's label? | Did it get there for a good reason? Why or why not |
|---|---|---|---|---|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |

Which trace did you find most interesting, and what did the agent do well or badly in it?

>

## 1d. Write the agent's instructions

What changed in the agent's traces after you wrote your instructions? Give one claim as an example.

>

Was that the change you expected? If not, what do you think happened?

>

## 1e. Start the full run, and predict

Predict the share of claims each version will get right (its verdict matches the dataset's label), as a percentage. A guess is fine; the reasons are what I grade.

| Version | 2 articles | 3 articles | 4 articles | Why you think so |
|---|---|---|---|---|
| No tools | | | | |
| One search | | | | |
| Agent | | | | |

How many lookups will the agent make per claim, on average? Will that grow with the number of articles? Why?

>

# Part 2: The agent against the baselines

## 2a. Compare accuracy

Ask Claude to paste the report of your full run, from `runs/part2/report.txt`, into the empty block below.

```
```

How do the results compare with your predictions? Where were you furthest off? Use the numbers from your run, by number of articles.

>

Does the gap between the agent and the one-search baseline grow with the number of articles? If it does not, what might explain that?

>

The no-tools baseline read nothing. How did it do, and what does that tell you about these claims?

>

## 2b. Compare cost

How much more does the agent cost per claim than the one-search baseline? Give the numbers.

>

For which kinds of claims (for example by number of articles, or by what the claim asks) is that extra cost worth paying, and for which is it not?

>

Did the agent ever use all 12 lookups? If so, pick one such claim and say what it was doing.

>

## 2c. Check the evidence yourself

Fill in one row for each of the first five claims in your Part 2 run, in the order of the claims file, where the agent's verdict is *supported* or *refuted*.

| # | Claim (first few words) | Agent's verdict | Matched the dataset's label? | Does the quoted evidence support that verdict? | Why or why not |
|---|---|---|---|---|---|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |
| 4 | | | | | |
| 5 | | | | | |

Of the five, how many matched the dataset's label, and for how many of those does the quoted evidence support the verdict?

>

Is accuracy alone a good measure of this agent? Why or why not?

>

# Part 3: Why the agent fails, and one change

## 3a. Sort the failures

Fill in one row for each of the first eight failures in your full run from 1e, rows 1 to 8 of the claims table for runs/part2 with "Result" in "The agent" box set to "does not match the dataset's label (any reason)". If you have fewer than eight, fill a row for each and delete the rest. Type your labels before you ask Claude for its own. Then ask Claude to add its labels to the last column, or type them in yourself.

| Row | Claim (first few words) | Your label | The entry of the trace that shows it | Is the dataset's label right? (yes, no or can't tell) | Claude's label |
|---|---|---|---|---|---|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |
| 4 | | | | | |
| 5 | | | | | |
| 6 | | | | | |
| 7 | | | | | |
| 8 | | | | | |

Where did you and Claude disagree, and who do you think is right?

>

Which kind of failure was most common? If no kind repeats, say which failure you will aim at in 3b, and why.

>

## 3b. Make one change

What did you change, and why did you expect it to help?

>

How many of your evaluation claims did the agent match before the change and after it? Which of your eight failures from 3a now match?

>

Quote one claim the agent matched before the change and not after it, if there is one, and say what you think happened. If there is none, say so.

>

## 3c. Write it up

### Write-up

What does the agent's loop add over one search, what does it cost, and when would you not use an agent for a job like this? Use your numbers from Part 2 and Part 3.

>

What did your topics show you about Wikipedia as a source? Where it was thin or wrong, why might that be, given who writes it?

>

Your numbers rest on 100 claims about the topics you chose. Which of your conclusions would you trust on another 100 claims, which might be chance, and what would you measure to find out?

>

### How I used AI

How did you use AI in this homework, what did you check yourself, and what is one decision you made on your own?

>
