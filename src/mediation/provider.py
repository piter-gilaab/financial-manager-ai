"""Provider seam: text in, raw text out. Providers never see sessions, handles or databases."""

from dataclasses import dataclass
from typing import Protocol

from src.agents.provider import ProviderLocation


@dataclass(frozen=True, slots=True)
class ProviderRequest:
    task: str  # "interpret" or "respond"
    system: str
    user: str
    max_output_characters: int
    # Optional JSON Schema the endpoint may enforce while decoding. It only constrains the
    # model's output shape; the strict validators still decide what is accepted.
    schema: dict | None = None


class ProviderFailure(Exception):
    """Fixed-message provider failure; callers fall back to deterministic behavior."""


class MediationProvider(Protocol):
    location: ProviderLocation

    def complete(self, request: ProviderRequest) -> str: ...


class ScriptedProvider:
    """Deterministic LOCAL test provider: no network, model, GPU or credentials."""

    location = ProviderLocation.LOCAL

    def __init__(self, handler):
        self._handler = handler
        self.requests = []

    def complete(self, request):
        self.requests.append(request)
        return self._handler(request)
