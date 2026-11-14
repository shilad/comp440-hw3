"""The reference loop. The homework uses it in Part 0, before your own loop, in
my_loop.py, has passed the check (uv run python check_loop.py), and not after.
It is built from the same parts as yours, in loop_parts.py.

Do not open this file before step 1a is done: reading it first gives the
exercise away. After that, compare it with yours (the write-up asks you to).
"""

import anthropic

from agent import (DECLINED, INSTRUCTIONS, MAX_REJECTED, MAX_STEPS, NO_ANSWER, OUT_OF_STEPS,
                   RAN_OUT, REJECTED_TOO_OFTEN, run_tool)
from loop_parts import Conversation


def run_agent(claim, client=None, max_steps=MAX_STEPS, lookup=run_tool):
    """Check one claim. Returns what talk.accept() or talk.stop() returns."""
    client = client or anthropic.Anthropic()
    system = INSTRUCTIONS.read_text()
    messages = [{"role": "user", "content": f"Claim: {claim}"}]
    trace, read_so_far = [], []
    talk = Conversation(claim, client, system, messages, trace, read_so_far, lookup)
    steps = 0           # lookups made so far
    rejected = 0        # answers sent back so far
    warned = False      # has the model been told it is out of lookups?
    reminded = False    # was the model reminded after its last reply?

    while True:
        reply = talk.ask()
        if reply.refused:
            return talk.stop(DECLINED, steps)
        if not reply.calls:
            # The model asked for nothing. Remind it once how to finish.
            if reminded:
                return talk.stop(NO_ANSWER, steps)
            talk.remind()
            reminded = True
            continue
        reminded = False

        warned_before = warned
        for call in reply.calls:
            if call.is_answer:
                problem = talk.problem_with(call)
                if problem is None:
                    return talk.accept(call, steps)
                talk.give(call, problem)
                rejected += 1
                if rejected >= MAX_REJECTED:
                    return talk.stop(REJECTED_TOO_OFTEN.format(n=rejected), steps)
            elif steps >= max_steps:
                if warned_before:
                    # It was told on an earlier reply that it was out of lookups: stop here.
                    return talk.stop(RAN_OUT, steps)
                talk.give(call, OUT_OF_STEPS.format(n=max_steps))
                warned = True
            else:
                talk.give(call, talk.run(call))
                steps += 1
        talk.send_results()
