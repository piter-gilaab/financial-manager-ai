"""Four explicit capabilities; no discovery, runtime registration or model loading."""

from src.agents import FinancialAnalysisAgent
from src.anomaly import AnomalyService

from .models import Availability, Capability, CapabilityInfo


CAPABILITIES = (
    CapabilityInfo(Capability.FINANCIAL_ANALYSIS, "Financial Analysis", Availability.AVAILABLE, None,
                   ("docs/financial_analysis_agent.md", "docs/query_contracts.md"),
                   ("The Step 13 agent supports a bounded question grammar and 17 approved contracts.",
                    "Source currency, grain and provenance limitations remain in the tool evidence.")),
    CapabilityInfo(Capability.ANOMALY_DETECTION, "Anomaly Detection", Availability.AVAILABLE, None,
                   ("docs/anomaly_detection.md", "docs/step14_validation.md"),
                   ("IQR screening supports RG accounting amount and CF Sales/Profit with the existing fixed peer policies.",
                    "CANDIDATE means a screening candidate requiring investigation; NOT_SELECTED is not a validity finding.",
                    "NOT_ASSESSED remains an abstention. Currency and comparability remain unresolved.")),
    CapabilityInfo(Capability.CASH_FLOW_FORECASTING, "Cash Flow Forecasting", Availability.BLOCKED,
                   "Forecasting readiness is BLOCKED: current datasets do not contain authoritative actual cash inflows/outflows, and currency remains unresolved.",
                   ("docs/forecasting_readiness.md",),
                   ("No forecasting model is implemented. Verified cash semantics, scope, comparable history and known currency are required.",)),
    CapabilityInfo(Capability.DOCUMENT_RETRIEVAL, "Document Retrieval", Availability.BLOCKED,
                   "Production corpus readiness is BLOCKED: no approved real financial-document corpus exists. RAG architecture is documented; implementation readiness is DEFERRED.",
                   ("docs/rag_architecture.md",),
                   ("The RAG design is documentation only; no retrieval, embeddings, index or citations are operational.",
                    "Project documentation and structured financial rows are not a production financial-document corpus.")),
)


class CapabilityRegistry:
    def __init__(self, financial_analysis=None, anomaly_detection=None):
        # Construction performs no queries or provider calls. Injection is trusted
        # application configuration; request data can never select implementations.
        analysis = financial_analysis if financial_analysis is not None else FinancialAnalysisAgent()
        anomaly = anomaly_detection if anomaly_detection is not None else AnomalyService()
        self._entries = {info.identifier.value: info for info in CAPABILITIES}
        self._analysis = analysis
        self._anomaly = anomaly

    def list_capabilities(self):
        return [info.to_dict() for info in self._entries.values()]

    def get(self, identifier):
        return self._entries.get(identifier) if type(identifier) in (str, Capability) else None

    def delegate(self, capability, payload):
        if capability == Capability.FINANCIAL_ANALYSIS:
            return self._analysis.ask(**payload)
        if capability == Capability.ANOMALY_DETECTION:
            return self._anomaly.analyze(payload)
        # Unavailable capabilities have no handler, model or retrieval placeholder.
        raise ValueError("Capability has no executable implementation.")
