"""Closed Financial Analysis and anomaly HTTP adapters."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from src.application import AnalysisCommand, AnomalyCommand

from .schemas import AnalysisRequest, AnomalyRequest, ERROR_RESPONSES, ExecutionEnvelope
from .serialization import to_json_safe


def _http_status(result) -> int:
    status = result.status
    if any(error.get("code") in {"DATASET_NOT_FOUND", "dataset_not_found"}
           for error in result.errors):
        return 404
    if status in {"INVALID_REQUEST", "UNSUPPORTED", "INVALID_DYNAMIC_REQUEST"}:
        return 400
    if status in {
        "BLOCKED", "DATA_QUALITY_BLOCKER", "STALE_DATASET_SELECTION",
        "INVALID_DATASET_SELECTION", "CAPABILITY_UNAVAILABLE",
    }:
        return 409
    if status in {"PROVIDER_UNAVAILABLE", "PROVIDER_ERROR"}:
        return 503
    return 200


def _body(result):
    return {
        "api_version": "1", "status": result.status,
        "evidence": to_json_safe(result.payload),
        "limitations": list(result.limitations), "errors": to_json_safe(result.errors),
    }


def build_analysis_router(application) -> APIRouter:
    router = APIRouter(responses=ERROR_RESPONSES)

    @router.post("/analysis", response_model=ExecutionEnvelope, tags=["analysis"])
    async def execute_analysis(request: AnalysisRequest):
        parameters = request.parameters
        result = application.execute(AnalysisCommand(
            dataset_id=request.dataset_id,
            operation=request.operation,
            granularity=parameters.granularity,
            missing_dimension=parameters.missing_dimension,
            as_of_date=parameters.as_of_date,
        ))
        return JSONResponse(status_code=_http_status(result), content=_body(result))

    @router.post("/anomalies", response_model=ExecutionEnvelope, tags=["anomalies"])
    async def execute_anomaly(request: AnomalyRequest):
        result = application.execute_anomaly(AnomalyCommand(
            dataset_id=request.dataset_id, operation=request.operation,
        ))
        return JSONResponse(status_code=_http_status(result), content=_body(result))

    return router

