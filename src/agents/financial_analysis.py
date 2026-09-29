"""Single Financial Manager orchestrator over approved Financial Core tools."""

from src.financial import FinancialCore
from src.financial.models import ContractError

from .explanation import explain
from .models import RoutingDecision, ToolIntent, agent_response, decision_response, json_copy
from .provider import InterpretationRequest, LocalQuestionProvider, ProviderLocation
from .registry import ToolRegistry
from .routing import clarify, route


def merge_arguments(grounded, supplied):
    """Supplement an explicit question; never overwrite a textual constraint."""
    if supplied is None:
        return grounded
    if not isinstance(supplied, dict) or any(not isinstance(key, str) for key in supplied):
        raise RoutingDecision("INVALID_REQUEST", "invalid_parameters", "Parameters must be a JSON object.", "parameters")
    try:
        supplied = json_copy(supplied)
    except (TypeError, ValueError, OverflowError) as error:
        raise RoutingDecision("INVALID_REQUEST", "invalid_parameters", "Parameters must contain JSON-safe values.", "parameters") from error
    merged = dict(grounded)
    for key, value in supplied.items():
        if key == "filters" and isinstance(value, dict) and key in merged:
            combined = dict(merged[key])
            for field, predicate in value.items():
                if field in combined and combined[field] != predicate:
                    clarify("conflicting_parameters", "Textual and structured filters disagree. Supply the filter in one place.", "filters." + field)
                combined[field] = predicate
            merged[key] = combined
        elif key in merged and merged[key] != value:
            clarify("conflicting_parameters", "Textual and structured parameters disagree. Supply this option in one place.", key)
        else:
            merged[key] = value
    return merged


class FinancialAnalysisAgent:
    """Offline, stateless question orchestration. Provider code is trusted configuration."""

    def __init__(self, core=None, provider=None):
        self.registry = ToolRegistry(core if core is not None else FinancialCore())
        self.provider = provider if provider is not None else LocalQuestionProvider()

    def ask(self, question, *, dataset=None, parameters=None):
        try:
            # Ground all language, including unsupported meanings, before a provider
            # can propose a tool. An unconsumed clause never silently disappears.
            grounded = route(question, dataset)
            _, expected = self.registry.prepare(grounded)
            if getattr(self.provider, "location", None) != ProviderLocation.LOCAL:
                raise RoutingDecision("PROVIDER_UNAVAILABLE", "nonlocal_provider_disabled",
                                      "Step 13 enables local providers only; private/hosted transports require a separate privacy review.")
            try:
                proposed = self.provider.interpret(InterpretationRequest(question, dataset, self.registry.metadata))
            except Exception as error:
                # The provider may return an intent, never application errors or
                # explanations. Even a RoutingDecision raised by adapter code
                # is an opaque provider failure, not an approved public message.
                raise RoutingDecision("PROVIDER_ERROR", "interpretation_failed", "The local interpretation provider could not produce an intent.") from error
            _, actual = self.registry.prepare(proposed)
            if actual != expected:
                raise RoutingDecision("PROVIDER_ERROR", "ungrounded_intent", "Provider intent differs from the explicit question; no tool was executed.")
            arguments = merge_arguments(grounded.arguments(), parameters)
            request, _ = self.registry.prepare(ToolIntent.create(grounded.tool_name, **arguments))
        except RoutingDecision as decision:
            return decision_response(decision)
        except ContractError as error:
            return agent_response(error.status, explanation=error.error["message"], errors=[error.error])

        # Core failures remain original evidence, with their original status.
        evidence = self.registry.execute(request)
        status = "ANSWERED" if evidence["status"] in ("SUCCESS", "PARTIAL", "NO_DATA") else "TOOL_REJECTED"
        return agent_response(status, request=request, evidence=evidence, explanation=explain(evidence))
