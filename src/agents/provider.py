"""Vendor-independent interpretation boundary. No model client or network adapter."""

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from .models import ToolIntent
from .registry import ToolMetadata
from .routing import route


class ProviderLocation(str, Enum):
    LOCAL = "LOCAL"
    PRIVATE = "PRIVATE"
    EXTERNAL = "EXTERNAL"


@dataclass(frozen=True, slots=True)
class InterpretationRequest:
    question: str
    dataset: str | None
    tools: tuple[ToolMetadata, ...]


class ProviderError(Exception):
    """Expected provider failure; no guessing or automatic fallback follows."""


class IntentProvider(Protocol):
    location: ProviderLocation

    def interpret(self, request: InterpretationRequest) -> ToolIntent: ...


class LocalQuestionProvider:
    """Conservative, offline English interpretation; not an LLM."""

    location = ProviderLocation.LOCAL

    def interpret(self, request):
        return route(request.question, request.dataset)
