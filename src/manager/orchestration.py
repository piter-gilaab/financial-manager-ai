"""Execute only locally validated plans through the Step 17 public facade."""

from copy import deepcopy
import json

from .routing import route


CONTINUE_STATUSES = ("SUCCESS", "PARTIAL", "NO_DATA")


def orchestrate(manager, question):
    # Plans are created here, not accepted from caller-controlled dictionaries.
    plan = route(question, manager._registry)
    routing = plan.to_dict()
    output = {"orchestration_version": "1.0", "original_request": plan.original_request,
              "routing": routing, "execution_state": "NOT_PERFORMED",
              "execution_status": "CAPABILITY_UNAVAILABLE" if plan.status == "BLOCKED" else plan.status,
              "results": [], "not_performed": [], "explanations": [], "warnings": [],
              "limitations": [{"step_id": s["step_id"], "items": s["capability"]["limitations"]} for s in routing["steps"]],
              "errors": [], "clarification": deepcopy(routing["clarification"]), "clarification_step_id": None}
    if plan.status not in ("ROUTED", "MULTI_CAPABILITY"):
        output["not_performed"] = [{"step_id": s["step_id"], "capability": s["capability"]["identifier"],
                                    "reason": plan.reason_code} for s in routing["steps"]]
        if plan.status != "CLARIFICATION_REQUIRED":
            output["errors"] = [{"step_id": None, "items": [{"code": plan.reason_code, "message": plan.message}]}]
        return output
    for index, step in enumerate(plan.steps, 1):
        result = manager.execute(capability=step.capability.identifier, request=json.loads(step.request_json))
        output["results"].append({"step_id": index, "capability": step.capability.identifier.value,
                                  "response": deepcopy(result)})
        output["explanations"].append({"step_id": index, "text": result["summary"]})
        output["warnings"].append({"step_id": index, "items": deepcopy(result["warnings"])})
        output["errors"].append({"step_id": index, "items": deepcopy(result["errors"])})
        output["execution_state"] = "PERFORMED"
        if result["execution_status"] not in CONTINUE_STATUSES:
            output["execution_status"] = result["execution_status"]
            output["clarification"] = deepcopy(result["clarification"])
            if result["clarification"] is not None:
                output["clarification_step_id"] = index
            output["not_performed"] = [{"step_id": j, "capability": s.capability.identifier.value,
                                        "reason": "previous_step_not_answered"}
                                       for j, s in enumerate(plan.steps, 1) if j > index]
            if output["not_performed"]:
                output["execution_state"] = "PARTIALLY_PERFORMED"
            return output
    statuses = [r["response"]["execution_status"] for r in output["results"]]
    output["execution_status"] = statuses[0] if len(set(statuses)) == 1 else "PARTIAL"
    return output
