"""The reference loop. The homework uses it until your own loop, in my_loop.py,
passes the check (uv run python check_loop.py).

Do not open this file before step 1a is done: reading it first gives the
exercise away. After that, compare it with yours (the write-up asks you to).
"""

import anthropic

from agent import (ACCEPTED, DECLINED, INSTRUCTIONS, MAX_REJECTED, MAX_STEPS, MODEL, NO_ANSWER,
                   OUT_OF_STEPS, RAN_OUT, REJECTED, REJECTED_TOO_OFTEN, REMINDED, REMINDER,
                   TOOLS, answer_problem, clean_answer, finish, run_tool)


def run_agent(claim, client=None, max_steps=MAX_STEPS, lookup=run_tool):
    """Check one claim. Returns a dict with the verdict, the evidence, the
    trace of every step, and the tokens used."""
    client = client or anthropic.Anthropic()
    system = INSTRUCTIONS.read_text()
    messages = [{"role": "user", "content": f"Claim: {claim}"}]
    trace, read_so_far = [], []
    tokens = {"input": 0, "output": 0}
    steps = 0
    rejected = 0        # how many answers the loop has sent back
    warned = False      # has it been told it is out of steps?

    while True:
        response = client.messages.create(
            model=MODEL, max_tokens=16000, system=system, tools=TOOLS, messages=messages,
        )
        tokens["input"] += response.usage.input_tokens
        tokens["output"] += response.usage.output_tokens
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "refusal":
            return finish(claim, None, [], DECLINED, trace, tokens, steps)

        calls = [block for block in response.content if block.type == "tool_use"]
        if not calls:
            # Claude stopped without calling a tool. Remind it once how to finish.
            if trace and trace[-1]["tool"] == "(reminder)":
                return finish(claim, None, [], NO_ANSWER, trace, tokens, steps)
            trace.append({"tool": "(reminder)", "input": {}, "result": REMINDED})
            messages.append({"role": "user", "content": REMINDER})
            continue

        results = []
        warned_before = warned
        for call in calls:
            if call.name == "answer":
                answer = clean_answer(call.input)
                problem = answer_problem(answer, read_so_far)
                if problem is None:
                    trace.append({"tool": "answer", "input": call.input, "result": ACCEPTED})
                    return finish(claim, answer["verdict"], answer["evidence"],
                                  answer["explanation"], trace, tokens, steps)
                result = REJECTED + problem
                rejected += 1
                if rejected >= MAX_REJECTED:
                    trace.append({"tool": "answer", "input": call.input, "result": result})
                    return finish(claim, None, [], REJECTED_TOO_OFTEN.format(n=rejected),
                                  trace, tokens, steps)
            elif steps >= max_steps:
                if warned_before:
                    # It was told last turn that it was out of steps: stop here.
                    return finish(claim, None, [], RAN_OUT, trace, tokens, steps)
                result = OUT_OF_STEPS.format(n=max_steps)
                warned = True
            else:
                steps += 1
                result = lookup(call.name, call.input)
                if call.name != "search":  # snippets are too short to count as evidence
                    read_so_far.append(result)
            trace.append({"tool": call.name, "input": call.input, "result": result})
            results.append({"type": "tool_result", "tool_use_id": call.id, "content": result})

        messages.append({"role": "user", "content": results})
