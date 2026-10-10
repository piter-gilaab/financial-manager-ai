"""Deterministic scripted-LLM helpers shared by the Phase 12 mediation tests."""

import json

from src.mediation import ScriptedProvider


def intent(operation="NEW_REQUEST", language="en", **fields):
    payload = {
        "version": "1.0", "operation": operation, "intent": None, "capability_hint": None,
        "clarification_answer": None, "clarification_kind": None, "evidence_reference": None,
        "follow_up_intent": None, "presentation_hint": None, "response_language": language,
    }
    payload.update(fields)
    return payload


class ScriptedLLM:
    """Maps user_input to an intent and a packet to a response; records what it was sent.

    Values may be a dict (serialized), a raw string (returned verbatim) or an exception
    instance (raised), so tests can model good, malformed and failing providers.
    """

    def __init__(self, intents=None, respond=None):
        self.intents = dict(intents or {})
        self.respond = respond
        self.interpretations = []
        self.packets = []
        self.provider = ScriptedProvider(self)

    def __call__(self, request):
        data = json.loads(request.user)
        if request.task == "interpret":
            self.interpretations.append(data)
            value = self.intents.get(data["user_input"], RuntimeError("unscripted input"))
        else:
            packet = {**data["structured_evidence"], "user_question": data["user_input"]}
            self.packets.append(packet)
            value = (RuntimeError("no response script") if self.respond is None
                     else self.respond(packet))
        if isinstance(value, Exception):
            raise value
        return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
