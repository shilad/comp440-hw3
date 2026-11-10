# COMP 440 HW3 write-up

Name:

Type each answer after the `>` under its question. A longer answer can go on over the following lines,
with no blank line inside it (to start a new paragraph, put a line with just `>` between the two). In a
table, fill every cell of every numbered row. Claude may paste a program's output where a question asks
for it, never an answer, and the homework page ticks a step when every answer in its section is filled in.

# Part 0: Set up

## 0a. Get your copy running

There is nothing to write for this step except your name, after `Name:` at the top of this file.

## 0b. Ask the model with no tools

What verdict did the model give, and what reason did it give? Quote the lines of the output that show them.

>

How much would you trust this answer, and why?

>

## 0c. Give it one search

Which Wikipedia page did it read? Quote the line of the output that shows it.

>

Did that page settle the claim? If not, why do you think the search led there?

>

## 0d. Run the agent and read its trace

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

Your lookups for both claims, in order. Ask Claude to paste every column but the last from `runs/part1/lookups.jsonl`. Type every "Why you chose it" yourself.

| # | Claim (1 or 2) | Tool | What you asked for | Why you chose it |
|---|---|---|---|---|
| 1 | | | | |

Your verdict on the first claim, and the sentence it rests on.

>

Your verdict on the second claim, and the sentence or sentences it rests on. If you stopped at 12 lookups without settling it, your verdict is *doesn't say*: say where you got stuck.

>

How many lookups did the second claim take? Which one was hardest to choose, and why?

>

Did you have to back up and try something else? What happened?

>

## 1c. Watch the agent work

The three traces you read closely: one claim each that needs 2, 3 and 4 articles, with claim 2 from 1b as the one that needs 3. At least one is a claim the agent got wrong, where there is one.

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

Your predictions: the share of claims each version will get right (its verdict matches the dataset's label), as a percentage. A guess is fine; the reasons are what I grade.

| Version | 2 articles | 3 articles | 4 articles | Why you think so |
|---|---|---|---|---|
| No tools | | | | |
| One search | | | | |
| Agent | | | | |

How many lookups will the agent make per claim, on average? Will that grow with the number of articles? Why?

>

# Part 2: The agent against the baselines

## 2a. Compare accuracy

The report of your full run, from `runs/part2/report.txt`. Ask Claude to paste it into the empty block below.

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

The first five claims in your Part 2 run, in the order of the claims file, where the agent's verdict is *supported* or *refuted*.

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

# Part 3: Your own claims

## 3a. Pick a topic and write your claims

Your topic, and why you know it well.

>

Your claims, at least eight: some true and some false, at least two that need two or more Wikipedia articles, and at least two where you think Wikipedia doesn't say or says something wrong. Write each verdict as `supported` if the claim is true or `refuted` if it is false, according to the source you trust. For more claims, add rows numbered 9, 10 and so on.

| # | Claim | Your verdict | The source you would trust (a link, a book, or how you know it first-hand) |
|---|---|---|---|
| 1 | | | |
| 2 | | | |
| 3 | | | |
| 4 | | | |
| 5 | | | |
| 6 | | | |
| 7 | | | |
| 8 | | | |

## 3b. Run the agent on your claims

On how many of your claims did each version agree with you?

>

What surprised you?

>

## 3c. Sort the failures

One row for each claim where the agent's verdict differs from yours: the claim's number from your 3a table, your label, and the line of the trace that shows it. Type your labels before you ask Claude for its own. Then ask Claude to add its labels to the last column, or type them in yourself.

| Claim # | Your label | The line of the trace that shows it | Claude's label |
|---|---|---|---|
| | | | |

Where did you and Claude disagree, and who do you think is right?

>

Which kind of failure was most common?

>

## 3d. Make one change

What did you change, and why did you expect it to help?

>

Did it fix the failure you aimed at? Give how many of your claims the agent matched before and after, and say whether the claims you gave that label now match.

>

## 3e. Write it up

### Write-up

What does the agent's loop add over one search? Use your numbers from Part 2 and your claims from Part 3.

>

What does the agent cost, and when would you not use an agent for a job like this?

>

What did your topic show you about Wikipedia as a source? Where it was thin or wrong, why might that be, given who writes it?

>

### How I used AI

How did you use AI in this homework, what did you check yourself, and what is one decision you made on your own?

>
