"""JSON-safe intent and agent-response models, separate from tool evidence."""

from dataclasses import dataclass
from hashlib import sha256
import json


def json_copy(value):
    return json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))


@dataclass(frozen=True, slots=True)
class ToolIntent:
    tool_name: str
    arguments_json: str = "{}"

    @classmethod
    def create(cls, tool_name, **arguments):
        return cls(tool_name, json.dumps(arguments, ensure_ascii=False, allow_nan=False))

    def arguments(self):
        def no_constant(value):
            raise ValueError("Nonfinite JSON is not an argument value.")

        def unique_object(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("Duplicate argument keys are not accepted.")
                result[key] = value
            return result

        result = json.loads(self.arguments_json, parse_constant=no_constant, object_pairs_hook=unique_object)
        if not isinstance(result, dict):
            raise ValueError("Tool arguments must be a JSON object.")
        return result


class RoutingDecision(Exception):
    def __init__(self, status, code, message, field=None, choices=()):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message
        self.field, self.choices = field, tuple(choices)


def agent_response(status, *, explanation="", request=None, evidence=None,
                   clarification=None, errors=()):
    # Copy evidence; never hand the core's object to a provider or modify it.
    result = json_copy(evidence) if evidence is not None else None
    digest = None if result is None else sha256(json.dumps(
        result, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False).encode("utf-8")).hexdigest()
    return {"agent_version": "1.0", "agent_status": status,
            "tool_request": json_copy(request), "tool_result": result,
            "evidence_sha256": digest,
            "explanation": {"method": "deterministic_template", "text": explanation},
            "clarification": clarification, "errors": list(errors)}


def decision_response(decision):
    clarification = None
    errors = []
    if decision.status == "CLARIFICATION_REQUIRED":
        clarification = {"code": decision.code, "field": decision.field,
                         "question": decision.message, "choices": list(decision.choices)}
    else:
        errors = [{"code": decision.code, "field": decision.field, "message": decision.message}]
    return agent_response(decision.status, explanation=decision.message,
                          clarification=clarification, errors=errors)
