# COMP 440 HW3: Checking Claims Against Wikipedia

> Draft, Nov 7, 2026, on branch `claude/project-thread-ibfinw` of `shilad/comp440-main`, for the
> instructor's review. It is meant to become the README of a template repository
> (`shilad/comp440-hw3`, not yet created) and the step list for the interactive homework web app.
> Every `[TBD]` is listed in `docs/hw3/OPEN-ITEMS.md`. The starter code is in `hw3-template/` on the
> same branch and passes its offline tests, but it has not yet run against Claude, so no output
> shown here has been run.

In this homework assignment you will build a small AI agent that checks claims against
Wikipedia, and measure what the agent adds over simpler approaches. You will:

- Understand what makes a program an *agent*: a language model that picks the next tool to call,
  reads what comes back, and decides when to stop.
- Gain hands-on experience with the loop around the model: its tools, its instructions, its
  step budget, and the checks that keep it honest.
- Compare the agent with two simpler baselines, and measure where it helps, where it doesn't,
  and what it costs.
- Apply it to claims you write about a topic you know well, and find out where Wikipedia, which
  is the collective work of its editors, is thin, out of date or wrong.

## The task

The agent is given a claim and nothing else. Here is one:

```
Claim: The director of the 1994 film that won the Academy Award for Best Picture was born in Illinois.
```

It has to decide whether Wikipedia *supports* the claim, *refutes* it, or *doesn't say*, and
quote the sentences it relied on. No source comes with the claim. The agent finds its own
evidence by searching and reading live Wikipedia.

One search on the whole sentence rarely lands on the right page. The agent has to work out that
the claim is about three things in a chain (the film, then its director, then where they were
born), look each one up, and put the pieces together. That chaining is what you'll study.

## The parts

Part 1 builds on Part 0, and so on, so keep your repository from one part to the next.

| Part | What you do | Due | Weight |
|---|---|---|---|
| [Part 0: Set up](instructions/part0.md) | Get the repository, start Claude, run the two baselines and the agent on one claim | 8:00am Thursday, November 12 [TBD] | 10% [TBD] |
| [Part 1: The loop and the tools](instructions/part1.md) | Read the agent's loop, meet its tools, predict how it will do, and write its instructions | 8:00am Thursday, November 19 | 25% [TBD] |
| [Part 2: The agent against the baselines](instructions/part2.md) | Run all three on the same claims, compare accuracy and cost by how many articles a claim needs, and check the agent's evidence by hand | 8:00am Thursday, November 19 | 35% [TBD] |
| [Part 3: Your own claims](instructions/part3.md) | Write claims about a topic you know, sort the agent's failures, make one change, and write up what you found | 8:00am Thursday, November 19 | 30% [TBD] |

## How this assignment works

1. The agent itself is a short Python file, `agent.py`, that you can read top to bottom: a loop
   that sends the claim to Claude, runs whatever tool Claude asks for, sends back the result, and
   stops when Claude answers or runs out of steps. Nothing about the agent is hidden in a library.
2. You run Claude Code in the repository's folder, as your tutor and lab assistant. It runs every command and explains anything you
   ask about: the loop, the tools, Wikipedia's API, the scores.
3. You make the choices and the judgments: your predictions, the agent's instructions, which
   traces to read, how to label a failure, and what the results mean.
4. Claude asks you one question at a time. Answer in a sentence or two, and Claude writes your
   answer into `WRITEUP.md`.
5. Claude commits and pushes at the end of each step, so your work is saved on GitHub as you go.

You are graded on your own explanations and judgments, not on the code. Claude will do the
mechanical work well, but it will bring every judgment back to you.

## Working together

This homework is individual. You are welcome to
help classmates get set up and to talk through what you're seeing. I ask that you not share your
`WRITEUP.md` answers, though, since the point is to form your own judgment. Ask questions in
`#comp440-f26` on Slack. Follow the class's
[AI-use norms](https://docs.google.com/document/d/1Eb6qxeS2wy-9TBzL8eGk9j75iYu_yEV4VoLQaywRz8E/edit).

## Resources

- [The HoVer paper](https://arxiv.org/abs/2011.03088) (Jiang et al., 2020): the claims you'll
  test the agent on. Each one needs evidence from two to four Wikipedia articles.
- Wikipedia's API documentation, which the agent's tools use to search and read pages
  [TBD: link].
- The slides from Tuesday, November 10, on tools and agent workflows [TBD: link].

## What to submit

Submit your repository URL through the
[assignment submission form](https://forms.gle/mgKcnqzTGxNaGvteA) at the end of each part, choosing
"HW3 Part N" [TBD: form options]. Each part's page lists what it must contain.

Your repository also holds `TRANSCRIPT.md`, a record of your Claude sessions. Claude updates it
before every commit. Start `claude` in this repository's folder, since sessions run anywhere else
aren't captured, and never edit it by hand, because it is regenerated each time.

## FAQ

FAQ: TBA (ask a question on `#comp440-f26`!)

## Notes on the data

- HoVer was built from Wikipedia as it stood around 2017. The agent reads Wikipedia as it
  is today, so for some claims the dataset's answer is out of date. That is not a bug in your
  agent. Part 2 asks you to find a few of these.
- The claims come from published research and are shared under HoVer's own license (MIT).
- A small sample of claims is in `data/dev.jsonl` for trying things quickly. Running the
  agent costs real money and time, so use the sample until a step asks for more.
