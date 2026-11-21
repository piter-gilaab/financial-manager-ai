"""FastAPI application factory for the local versioned HTTP adapter."""

from dataclasses import dataclass
from pathlib import Path

from fastapi import APIRouter, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from src.application import (
    AnalysisApplication,
    ConversationApplication,
    DatasetApplication,
)
from src.dynamic_anomaly import DYNAMIC_ANOMALY_OPERATIONS
from src.dynamic_financial import DYNAMIC_FINANCIAL_OPERATIONS
from src.manager import FinancialManagerAgent, FinancialManagerSession
from src.multidomain_financial import CASH_OPERATIONS, PAYABLE_OPERATIONS, RECEIVABLE_OPERATIONS
from src.onboarding import OnboardingManager

from .errors import install_error_handlers
from .analysis import build_analysis_router
from .conversation import build_conversation_router
from .datasets import build_dataset_router
from .schemas import (
    CapabilityCatalogResponse, ERROR_RESPONSES, HealthData, ProjectionEnvelope,
    ReadinessResponse,
)
from .serialization import to_json_safe


@dataclass(frozen=True, slots=True)
class ApplicationModules:
    datasets: DatasetApplication
    analysis: AnalysisApplication
    conversations: ConversationApplication


def _projection(data, *, status="SUCCESS", limitations=(), errors=()):
    return {
        "api_version": "1", "status": status, "data": to_json_safe(data),
        "limitations": list(limitations), "errors": to_json_safe(errors),
    }


def create_app(
    *,
    onboarding_root: Path | str = Path("data/onboarding"),
    dataset_application: DatasetApplication | None = None,
    analysis_application: AnalysisApplication | None = None,
    conversation_application: ConversationApplication | None = None,
    provider_factory=None,
    cors_origins: tuple[str, ...] = (),
) -> FastAPI:
    if "*" in cors_origins:
        raise ValueError("CORS origins must be an explicit local allowlist.")

    onboarding = OnboardingManager(onboarding_root)
    manager = FinancialManagerAgent(onboarding_root=onboarding_root)
    datasets = dataset_application or DatasetApplication(onboarding)
    analysis = analysis_application or AnalysisApplication(manager, onboarding=onboarding)
    conversations = conversation_application or ConversationApplication(
        session_factory=lambda: FinancialManagerSession(manager=manager),
        provider_factory=provider_factory,
    )
    modules = ApplicationModules(datasets, analysis, conversations)

    app = FastAPI(
        title="Financial Manager AI Local API",
        version="1.0.0",
        description=("Local-first Financial Manager AI V2 transport. API v1 is a transport "
                     "version and is not product V1. Session IDs are not authentication."),
        max_body_size=10 * 1024 * 1024 + 64 * 1024,
    )
    app.state.applications = modules
    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(cors_origins),
            allow_credentials=False,
            allow_methods=["GET", "POST", "DELETE"],
            allow_headers=["Content-Type"],
        )
    install_error_handlers(app)

    router = APIRouter(prefix="/api/v1", responses=ERROR_RESPONSES)
    router.include_router(build_dataset_router(datasets))
    router.include_router(build_analysis_router(analysis))
    router.include_router(build_conversation_router(conversations))

    @router.get("/health", response_model=ProjectionEnvelope[HealthData], tags=["system"])
    async def health():
        return _projection(HealthData(status="ok", api_version="1", product_version="V2"))

    @router.get(
        "/capabilities",
        response_model=ProjectionEnvelope[CapabilityCatalogResponse] | ProjectionEnvelope[ReadinessResponse],
        tags=["system"],
    )
    async def capabilities(dataset_id: str | None = Query(default=None, pattern=r"^ds_[0-9a-f]{20}$")):
        if dataset_id is not None:
            return _projection(analysis.capabilities(dataset_id))
        return _projection({
            "capabilities": analysis.capabilities(),
            "financial_operations": {
                "SALES_RECORD": DYNAMIC_FINANCIAL_OPERATIONS,
                "PAYABLE": tuple(item.value for item in PAYABLE_OPERATIONS),
                "RECEIVABLE": tuple(item.value for item in RECEIVABLE_OPERATIONS),
                "CASH_TRANSACTION": tuple(item.value for item in CASH_OPERATIONS),
            },
            "anomaly_operations": DYNAMIC_ANOMALY_OPERATIONS,
        })

    app.include_router(router)
    return app

