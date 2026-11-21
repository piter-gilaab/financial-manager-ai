"""Process-local conversation HTTP adapter; session IDs are not authentication."""

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from .schemas import (
    ClarificationAnswerRequest,
    ConversationTurnResponse,
    FollowUpRequest,
    ProjectionEnvelope,
    SessionActionResponse,
    SessionId,
    SessionProjectionResponse,
    SessionTurnRequest,
    ERROR_RESPONSES,
)
from .serialization import to_json_safe


def _body(data, *, status_value="SUCCESS"):
    return {
        "api_version": "1", "status": status_value, "data": to_json_safe(data),
        "limitations": [], "errors": [],
    }


def _response(data, *, status_code=200):
    application_status = getattr(data, "status", "SUCCESS")
    transport_status = (
        503 if application_status in {"PROVIDER_UNAVAILABLE", "PROVIDER_ERROR"}
        else status_code
    )
    return JSONResponse(
        status_code=transport_status,
        content=_body(data, status_value=application_status),
    )


def build_conversation_router(application) -> APIRouter:
    router = APIRouter(responses=ERROR_RESPONSES)

    @router.post(
        "/sessions", response_model=ProjectionEnvelope[SessionProjectionResponse],
        status_code=status.HTTP_201_CREATED, tags=["sessions"],
    )
    async def create_session():
        return _response(application.create_session(), status_code=201)

    @router.get("/sessions/{session_id}", response_model=ProjectionEnvelope[SessionProjectionResponse], tags=["sessions"])
    async def session_status(session_id: SessionId):
        return _response(application.status(session_id))

    @router.post(
        "/sessions/{session_id}/turns", response_model=ProjectionEnvelope[ConversationTurnResponse], tags=["sessions"],
    )
    async def session_turn(session_id: SessionId, request: SessionTurnRequest):
        return _response(application.turn(session_id, request.message))

    @router.post(
        "/sessions/{session_id}/answers", response_model=ProjectionEnvelope[SessionActionResponse], tags=["sessions"],
    )
    async def clarification_answer(session_id: SessionId, request: ClarificationAnswerRequest):
        return _response(application.answer(session_id, request.value))

    @router.post(
        "/sessions/{session_id}/follow-ups", response_model=ProjectionEnvelope[SessionActionResponse], tags=["sessions"],
    )
    async def evidence_follow_up(session_id: SessionId, request: FollowUpRequest):
        return _response(application.follow_up(
            session_id, reference=request.reference, intent=request.intent.value,
        ))

    @router.post(
        "/sessions/{session_id}/reset", response_model=ProjectionEnvelope[SessionActionResponse], tags=["sessions"],
    )
    async def reset_session(session_id: SessionId):
        return _response(application.reset(session_id))

    @router.post(
        "/sessions/{session_id}/cancel", response_model=ProjectionEnvelope[SessionActionResponse], tags=["sessions"],
    )
    async def cancel_session(session_id: SessionId):
        return _response(application.cancel(session_id))

    @router.delete(
        "/sessions/{session_id}", response_model=ProjectionEnvelope, tags=["sessions"],
    )
    async def delete_session(session_id: SessionId):
        application.delete(session_id)
        return _response({"deleted": True})

    return router

