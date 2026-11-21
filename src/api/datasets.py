"""Dataset and onboarding HTTP adapter; all authority remains in DatasetApplication."""

from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi import APIRouter, Request, status

from src.onboarding import OnboardingError

from .multipart import stage_multipart_upload
from .schemas import (
    DatasetId,
    DatasetProfileResponse,
    DatasetSummaryResponse,
    DomainConfirmationRequest,
    OnboardingResponse,
    ProjectionEnvelope,
    QualifierConfirmationRequest,
    ReadinessResponse,
    SemanticDecisionKind,
    SemanticDecisionRequest,
    SemanticMappingResponse,
    StopDatasetRequest,
    ERROR_RESPONSES,
)
from .serialization import to_json_safe


def _projection(data, *, status_value="SUCCESS"):
    return {
        "api_version": "1", "status": status_value, "data": to_json_safe(data),
        "limitations": [], "errors": [],
    }


def build_dataset_router(application) -> APIRouter:
    router = APIRouter(responses=ERROR_RESPONSES)

    @router.get("/datasets", response_model=ProjectionEnvelope[list[DatasetSummaryResponse]], tags=["datasets"])
    async def list_datasets():
        return _projection(application.list_datasets())

    @router.get("/datasets/{dataset_id}", response_model=ProjectionEnvelope[DatasetSummaryResponse], tags=["datasets"])
    async def dataset_detail(dataset_id: DatasetId):
        return _projection(application.detail(dataset_id))

    @router.get("/datasets/{dataset_id}/profile", response_model=ProjectionEnvelope[DatasetProfileResponse], tags=["datasets"])
    async def dataset_profile(dataset_id: DatasetId):
        return _projection(application.profile(dataset_id))

    @router.get("/datasets/{dataset_id}/mappings", response_model=ProjectionEnvelope[SemanticMappingResponse], tags=["datasets"])
    async def dataset_mappings(dataset_id: DatasetId):
        return _projection(application.mappings(dataset_id))

    @router.get("/datasets/{dataset_id}/readiness", response_model=ProjectionEnvelope[ReadinessResponse], tags=["datasets"])
    async def dataset_readiness(dataset_id: DatasetId):
        return _projection(application.readiness(dataset_id))

    @router.post(
        "/datasets/{dataset_id}/mappings/decisions",
        response_model=ProjectionEnvelope[DatasetSummaryResponse],
        tags=["datasets"],
    )
    async def semantic_decision(dataset_id: DatasetId, request: SemanticDecisionRequest):
        role = request.role.value if request.role is not None else None
        if request.decision is not SemanticDecisionKind.REJECT and role is None:
            raise OnboardingError("missing_semantic_role")
        return _projection(application.decide_semantic(
            dataset_id, column=request.column, decision=request.decision.value,
            role=role, evidence=request.evidence, value_mapping=request.value_mapping,
            date_format=request.date_format,
        ))

    @router.post(
        "/datasets/{dataset_id}/domain-confirmation",
        response_model=ProjectionEnvelope[DatasetSummaryResponse],
        tags=["datasets"],
    )
    async def confirm_domain(dataset_id: DatasetId, request: DomainConfirmationRequest):
        return _projection(application.confirm_domain(
            dataset_id, domain=request.domain.value, evidence=request.evidence,
        ))

    @router.post(
        "/datasets/{dataset_id}/qualifiers",
        response_model=ProjectionEnvelope[DatasetSummaryResponse],
        tags=["datasets"],
    )
    async def confirm_qualifiers(dataset_id: DatasetId, request: QualifierConfirmationRequest):
        return _projection(application.confirm_qualifiers(
            dataset_id,
            evidence=request.evidence,
            amount_basis=(request.amount_basis.value if request.amount_basis else None),
            dataset_reference_date=request.dataset_reference_date,
            cash_amount_convention=(request.cash_amount_convention.value
                                    if request.cash_amount_convention else None),
        ))

    @router.post(
        "/datasets/{dataset_id}/lifecycle",
        response_model=ProjectionEnvelope[DatasetSummaryResponse],
        tags=["datasets"],
    )
    async def stop_dataset(dataset_id: DatasetId, request: StopDatasetRequest):
        return _projection(application.stop(
            dataset_id, reject=request.reject, evidence=request.evidence,
        ))

    @router.post(
        "/onboarding",
        response_model=ProjectionEnvelope[OnboardingResponse],
        status_code=status.HTTP_201_CREATED,
        tags=["onboarding"],
        openapi_extra={
            "requestBody": {
                "required": True,
                "content": {"multipart/form-data": {"schema": {
                    "type": "object",
                    "required": ["file"],
                    "properties": {
                        "file": {"type": "string", "format": "binary"},
                        "sheet": {"type": "string", "maxLength": 256},
                        "provenance_note": {"type": "string", "maxLength": 1000},
                    },
                }}},
            },
        },
    )
    async def upload_dataset(request: Request):
        with TemporaryDirectory(prefix="financial-manager-http-upload-") as temporary_root:
            command = await stage_multipart_upload(request, Path(temporary_root))
            dataset = application.upload_staged(command)
            return _projection({
                "dataset": dataset,
                "profile": application.profile(dataset.dataset_id),
                "mappings": application.mappings(dataset.dataset_id),
            })

    return router
