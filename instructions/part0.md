# COMP 440 HW3 Part 0: Set up

Due 8:00am Thursday, November 12 [TBD]. Back to the [assignment page](../README.md).

In this part you'll get the repository running and watch three ways of checking the same claim:
the model on its own, a fixed one-search pipeline, and the agent.

## Step 1: Get the repository and start Claude

- Fork `shilad/comp440-hw3` [TBD: repository] on GitHub, and clone your fork.
- In a terminal, go to its folder and start `claude`.
- Write your name after `Name:` at the top of `WRITEUP.md`.
- Ask Claude to install the packages and run the tests. These tests need no key and no network.
- Hint: the agent calls the Claude API directly, not through your Claude Code account, so it needs
  an API key. I will give you one [TBD: how it reaches you]. It only works with Claude Haiku, a
  small, fast and cheap Claude model, which is the one the agent uses.
- In your editor, copy `.env.example` to a new file named `.env`. Paste the key after
  `ANTHROPIC_API_KEY=` and your Macalester email after `WIKIPEDIA_CONTACT=`, as in
  `WIKIPEDIA_CONTACT=student@macalester.edu`. Claude never sees this file.
  The key never goes in the chat, because your conversation with Claude is saved and committed
  with your work; `.env` is not.
  The email gives your runs their own Wikipedia allowance, because Wikipedia counts requests by
  the contact each program gives it; without it, you share one allowance with the whole class.
- Ask Claude to check that your `.env` file is there. The first run that reaches Wikipedia and
  the Claude API is in Step 2.

## Step 2: Ask the model on its own

- Claude runs `uv run python check.py --method no-tools "<claim>"` on the claim from
  the assignment page:

  ```
  Claim: The director of the 1994 film that won the Academy Award for Best Picture was born in Illinois.
  ```

- The model answers from what it learned in training, with no searching at all. It prints its
  verdict and its reasoning.
- What did it say? How much would you trust it, and why?

## Step 3: Run one search

- Claude runs the same claim with `--method one-search`. This version asks the model for one
  Wikipedia search, reads the top page that search finds, and answers from that page.
- Look at which page it read. Was it the page that settles the claim? If not, why did the search
  land there?

## Step 4: Run the agent and read its trace

- Claude runs the same claim with `--method agent`. This time the model chooses its own searches
  and pages, one at a time, until it answers or runs out of steps.
- Claude prints the *trace*: every tool the agent called, what it asked for, and a short version
  of what came back.

  ```
  [TBD: expected output, from a real run]
  ```

- Walk through the trace with Claude. How did the agent break the claim into pieces? Was there a
  step you would have done differently?

## What to submit

Submit your repository URL through the [assignment submission form](https://forms.gle/mgKcnqzTGxNaGvteA),
choosing "HW3 Part 0" [TBD]. At a minimum I am looking for the following in `WRITEUP.md`:

- Your answers to the questions in Steps 2, 3 and 4.
- The three outputs, which Claude saves to `runs/part0/`.

## Grading

- Setup: 40% - The repository runs, and the three outputs are in `runs/part0/`.
- Reading the outputs: 60% - Your answers say what each version did with this claim and point to
  the line of the output or trace that shows it.
