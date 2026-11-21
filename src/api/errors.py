"""Bounded HTTP error mapping with no exception/path disclosure."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.onboarding import OnboardingError
from src.application import ResourceNotFound


def _body(status, code, message, *, field=None, data=None):
    return {
        "api_version": "1",
        "status": status,
        "data": data,
        "limitations": [],
        "errors": [{"code": code, "field": field, "message": message}],
    }


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, error: RequestValidationError):
        locations = [".".join(str(item) for item in detail.get("loc", ()) if item != "body")
                     for detail in error.errors()[:20]]
        field = next((item for item in locations if item), None)
        return JSONResponse(
            status_code=422,
            content=_body(
                "INVALID_REQUEST", "transport_validation_failed",
                "The request does not match the closed API schema.", field=field,
            ),
        )

    @app.exception_handler(OnboardingError)
    async def onboarding_error(request: Request, error: OnboardingError):
        not_found = error.code in {"invalid_dataset_id", "dataset_not_found"}
        sheet_required = error.code == "sheet_selection_required"
        choices = error.details.get("choices", ()) if sheet_required else ()
        return JSONResponse(
            status_code=404 if not_found else (409 if sheet_required else 400),
            content=_body(
                "CLARIFICATION_REQUIRED" if sheet_required else "INVALID_REQUEST", error.code,
                "Select one of the available workbook sheets."
                if sheet_required else "The dataset request could not be completed safely.",
                field="dataset_id" if not_found else ("sheet" if sheet_required else None),
                data={"field": "sheet", "choices": list(choices)} if sheet_required else None,
            ),
        )

    @app.exception_handler(ResourceNotFound)
    async def missing_resource(request: Request, error: ResourceNotFound):
        return JSONResponse(
            status_code=404,
            content=_body("INVALID_REQUEST", "resource_not_found", "The exact resource was not found."),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, error: StarletteHTTPException):
        too_large = error.status_code == 413
        return JSONResponse(
            status_code=error.status_code,
            content=_body(
                "INVALID_REQUEST",
                "request_too_large" if too_large else "http_error",
                "The request exceeds the configured safe size limit."
                if too_large else "The requested API resource is unavailable.",
            ),
        )

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, error: Exception):
        return JSONResponse(
            status_code=500,
            content=_body("INTERNAL_ERROR", "internal_error", "The request could not be completed."),
        )

