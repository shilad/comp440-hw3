---
name: page
description: Tell the homework page, which the student has open beside this terminal, what this session is doing. Post a one-line status when what you are doing changes, note what the student expects a run to show if they say it, and tick each checkpoint of the step that you tick yourself once the student has reached it. Use it throughout every homework step session.
---

# Updating the homework page

The student has a web page open beside this terminal. For each step it shows the step's tasks (its
checkpoints) and the student's record of working on it: what they asked you to do, what you ran
and what came back. The page fills most of it in by itself, from your
session and from the student's files. This skill tells it three more things. Each is one command,
and each runs without asking. `<step>` is your step's label, such as `0b`; your instructions name it.

## Status: what you are doing, in one line

```bash
python3 .workbench/page.py <step> status "Walking through run_agent(), lines 40 to 80"
```

Post one when what you are doing changes, and at most once a turn. Plain words, under about ten,
about the homework rather than the tools: "Running the agent on your claim", not "Running Bash".
When you are waiting on the student, say for what: "Waiting for your answer in WRITEUP.md".

## Expected: what the student predicts a run will show

```bash
python3 .workbench/page.py <step> expected "supported"
```

If the student says what they expect a run to show, note it in a few words: a verdict, a page
title, a number. Use their words, never your own, and don't ask for a prediction just to note one. The page sets it beside the result, so they
can see where they were right and where they were not.

## Done: tick a checkpoint

```bash
python3 .workbench/page.py <step> done 1
```

The number is the checkpoint's number in your instructions. Most checkpoints tick themselves, when
their file exists or the student's answers are in WRITEUP.md. Tick only the ones your instructions
say you tick, and only once you have seen them happen in this session: a change you saw in
`git diff`, a table you read. Some tasks only the student can see done, such as reading a trace in
the results viewer: the page shows those with no tick. The page refuses a tick on any of these
others and says why.

A step with nothing to fill in WRITEUP.md is ticked as a whole with `done` and no number, once the
student has done what it asks.

If a command says the page isn't running, carry on without it and don't try again.
