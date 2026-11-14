"""Your agent's loop, which you design in step 1a. The homework page says what the
loop is for, under "1a. Design the loop" (also in instructions/part1.md), and the
check tells you each rule it must follow when your loop breaks it.

You design the loop as an outline in plain words, in WRITEUP.md under 1a. The
loop below the line that says where it goes is Claude's translation of that
outline, written with the parts in loop_parts.py: each line of your outline is a
comment, with about one line of Python for it under it. To change the loop,
change your outline and ask Claude to translate it again.

Check it after each translation. The check uses a scripted stand-in for the
model and for Wikipedia, so it needs no key and costs nothing:

    uv run python check_loop.py

Part 0 runs the agent on the reference loop. Once every rule passes, the agent
runs on this loop and no other: the runs of 1c and later need it to pass.
"""

import anthropic

# The names below include every one the file had before the parts, so that a loop written
# then still runs.
from agent import (ACCEPTED, DECLINED, INSTRUCTIONS, MAX_REJECTED, MAX_STEPS, MODEL, NO_ANSWER,
                   OUT_OF_STEPS, RAN_OUT, REJECTED, REJECTED_TOO_OFTEN, REMINDED, REMINDER,
                   TOOLS, answer_problem, clean_answer, finish, run_tool)
from loop_parts import Conversation


def run_agent(claim, client=None, max_steps=MAX_STEPS, lookup=run_tool):
    """Check one claim. Returns what talk.accept() or talk.stop() returns."""
    client = client or anthropic.Anthropic()
    system = INSTRUCTIONS.read_text()
    messages = [{"role": "user", "content": f"Claim: {claim}"}]
    trace, read_so_far = [], []
    talk = Conversation(claim, client, system, messages, trace, read_so_far, lookup)
    steps = 0          # lookups made so far
    rejected = 0       # answers sent back so far

    # Your loop should repeatedly call the model with the message history so far, and ask for
    # its next step. It should make the lookups that step asks for, and add what they return to
    # the history. It should check whether the model has given an answer that can be accepted
    # yet. It should also pay attention to its limits: a claim that runs out of lookups, or of
    # tries at an answer, may end undecided.
    # ---- your loop goes below this line (step 1a) ----
    raise NotImplementedError("The loop is not written yet: see step 1a.")
