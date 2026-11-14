"""The parts your loop is built from, in step 1a.

Each part does one mechanical job: the exact call to the Claude API, the shape
of what is sent back for a tool call, the trace entries (every lookup, every
answer checked, every reminder), what finish() is given.
Your loop in my_loop.py decides when each part is used, and in what order. That
order, and what the loop counts and remembers, is the agent's logic, and it is
what you write.

    talk = Conversation(claim, client, system, messages, trace, read_so_far, lookup)
    reply = talk.ask()            # the model's next reply
    reply.refused                 # True if the model refused to check the claim
    reply.calls                   # the tool calls the reply asks for (empty if none)
    reply.usage                   # the tokens it used: .input_tokens, .output_tokens
    call.is_answer, call.is_lookup, call.name
    talk.run(call)                # run a lookup; returns what it found
    talk.problem_with(call)       # the evidence check on an answer: what to send back, or None
    talk.give(call, result)       # the result the model will be sent for this call
    talk.send_results()           # send the model every result given since its last reply
    talk.remind()                 # send the model the reminder to answer
    talk.accept(call, steps)      # what the loop returns for an accepted answer
    talk.stop(why, steps)         # what the loop returns with no verdict
                                  # (both take a token count last, once the loop keeps one: 3b)
"""

import agent
from agent import ACCEPTED, MODEL, REJECTED, REMINDED, REMINDER, TOOLS, clean_answer, finish


class Call:
    """One tool call in a reply. Every call that is not an answer is a lookup."""

    def __init__(self, block):
        self.name = block.name          # "search", "read", "wikidata" or "answer"
        self.input = block.input        # what the model gave the tool, as a dictionary
        self.id = block.id              # marks the result that answers this call
        self.is_answer = block.name == "answer"
        self.is_lookup = not self.is_answer


class Reply:
    """One reply from the model."""

    def __init__(self, response):
        self.refused = response.stop_reason == "refusal"
        self.calls = [Call(block) for block in response.content if block.type == "tool_use"]
        # The tokens this reply used, as the Claude API reports them: .usage.input_tokens and
        # .usage.output_tokens. Nothing here counts them: that is step 3b's first task.
        self.usage = response.usage


class Conversation:
    """One check of one claim: the conversation with the model, the lookups, and the trace."""

    def __init__(self, claim, client, system, messages, trace, read_so_far, lookup):
        self.claim, self.client, self.system, self.lookup = claim, client, system, lookup
        self.messages, self.trace, self.read_so_far = messages, trace, read_so_far
        self.results = []               # results given since the model's last reply, not sent yet

    def ask(self):
        """Send the model the system text, the tools and the whole conversation so far. Add its
        reply to the conversation, and return the reply."""
        response = self.client.messages.create(model=MODEL, max_tokens=16000, system=self.system,
                                               tools=TOOLS, messages=self.messages)
        self.messages.append({"role": "assistant", "content": response.content})
        return Reply(response)

    def run(self, call):
        """Run one lookup and return what it found. What read and wikidata find counts as read
        by the agent, so the evidence check can find quotes in it; what search finds does not."""
        found = self.lookup(call.name, call.input)
        if call.name != "search":
            self.read_so_far.append(found)
        return found

    def problem_with(self, call):
        """The evidence check on an answer: None if it passes, or else the sentence to send back
        about its problem, which starts "Answer rejected.". An answer with a problem is recorded
        in the trace here, when it is checked, so the trace is complete even if the loop stops
        before it gives the answer its result. (An answer that passes is recorded by accept().)"""
        problem = agent.answer_problem(clean_answer(call.input), self.read_so_far)
        if problem is None:
            return None
        self.trace.append({"tool": call.name, "input": call.input, "result": REJECTED + problem})
        return REJECTED + problem

    def give(self, call, result):
        """Set the result the model will be sent for this call. A lookup's result is recorded in
        the trace here; an answer's was recorded when it was checked."""
        if not call.is_answer:
            self.trace.append({"tool": call.name, "input": call.input, "result": result})
        self.results.append({"type": "tool_result", "tool_use_id": call.id, "content": result})

    def send_results(self):
        """Add one turn to the conversation that holds every result given since the model's last
        reply. The model sees them when it is next asked."""
        self.messages.append({"role": "user", "content": self.results})
        self.results = []

    def remind(self):
        """Add the reminder to answer to the conversation, and record it in the trace."""
        self.trace.append({"tool": "(reminder)", "input": {}, "result": REMINDED})
        self.messages.append({"role": "user", "content": REMINDER})

    def accept(self, call, steps, tokens=None):
        """Record the answer as accepted, and return what finish() returns for it. A loop that
        counts tokens (step 3b) passes its count last, as {"input": ..., "output": ...}."""
        answer = clean_answer(call.input)
        self.trace.append({"tool": "answer", "input": call.input, "result": ACCEPTED})
        return finish(self.claim, answer["verdict"], answer["evidence"], answer["explanation"],
                      self.trace, steps, tokens)

    def stop(self, why, steps, tokens=None):
        """Return what finish() returns with no verdict. why is one of the ready-made sentences
        in agent.py: RAN_OUT, NO_ANSWER, DECLINED or REJECTED_TOO_OFTEN.format(n=rejected). A
        loop that counts tokens (step 3b) passes its count last."""
        return finish(self.claim, None, [], why, self.trace, steps, tokens)
