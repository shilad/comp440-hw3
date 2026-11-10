"""Your agent's loop, which you write in step 1a. The six rules it follows are
on the homework page, under "1a. Write the loop" (also in instructions/part1.md).

Check it after each rule you write. The check uses a scripted stand-in for the
model and for Wikipedia, so it needs no key and costs nothing:

    uv run python check_loop.py

Until every rule passes, your copy's agent runs on the reference loop. Once
they all pass, it runs on this one.
"""

import anthropic

from agent import (ACCEPTED, DECLINED, INSTRUCTIONS, MAX_REJECTED, MAX_STEPS, MODEL, NO_ANSWER,
                   OUT_OF_STEPS, RAN_OUT, REJECTED, REJECTED_TOO_OFTEN, REMINDED, REMINDER,
                   TOOLS, answer_problem, clean_answer, finish, run_tool)

# The six rules:
#   1. Ask the model.
#   2. Run its lookups.
#   3. Send the results back.
#   4. Check the answer.
#   5. Enforce the limit.
#   6. Stop when the model stops.


def run_agent(claim, client=None, max_steps=MAX_STEPS, lookup=run_tool):
    """Check one claim. Returns what finish() returns."""
    client = client or anthropic.Anthropic()
    system = INSTRUCTIONS.read_text()
    messages = [{"role": "user", "content": f"Claim: {claim}"}]
    trace, read_so_far = [], []
    tokens = {"input": 0, "output": 0}
    steps = 0          # lookups made so far
    rejected = 0       # answers the loop has sent back so far

    # ---- your loop goes below this line (step 1a) ----
    raise NotImplementedError("The loop is not written yet: see step 1a.")
