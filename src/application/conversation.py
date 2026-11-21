"""Process-local session use cases over the existing session and mediation seams."""

from src.agents.provider import ProviderLocation
from src.mediation import ConversationMediator

from .models import ConversationTurnResult, ResourceNotFound, SessionActionResult, SessionProjection


class _DeterministicFallbackProvider:
    location = ProviderLocation.EXTERNAL

    def complete(self, request):
        raise RuntimeError("No optional local mediation provider is configured.")


class ConversationApplication:
    def __init__(self, *, session_factory, provider_factory=None):
        self._session_factory = session_factory
        self._provider_factory = provider_factory or _DeterministicFallbackProvider
        self._sessions = {}

    def create_session(self) -> SessionProjection:
        session = self._session_factory()
        projection = self._projection(session.status())
        self._sessions[projection.session_id] = (
            session, ConversationMediator(session, self._provider_factory()),
        )
        return projection

    def status(self, session_id: str) -> SessionProjection:
        session, _ = self._get(session_id)
        projection = self._projection(session.status())
        if projection.status != "ACTIVE":
            self._sessions.pop(session_id, None)
        return projection

    def turn(self, session_id: str, message: str) -> ConversationTurnResult:
        _, mediator = self._get(session_id)
        result = mediator.handle(message)
        outcome = result.outcome
        return ConversationTurnResult(
            status=(outcome.get("status") if outcome is not None else "PROVIDER_UNAVAILABLE"),
            outcome=outcome,
            text=result.text,
            notice=result.notice,
            replaced_pending=result.replaced_pending,
            labels=tuple(label for label, _ in result.labels),
        )

    def answer(self, session_id: str, value: str) -> SessionActionResult:
        session, _ = self._get(session_id)
        return self._action(session_id, session.answer(value))

    def follow_up(self, session_id: str, *, reference: str, intent: str) -> SessionActionResult:
        session, _ = self._get(session_id)
        return self._action(session_id, session.follow_up(reference=reference, intent=intent))

    def cancel(self, session_id: str) -> SessionActionResult:
        session, _ = self._get(session_id)
        return self._action(session_id, session.cancel())

    def reset(self, session_id: str) -> SessionActionResult:
        session, mediator = self._get(session_id)
        outcome = session.reset()
        projection = self._projection(session.status())
        self._sessions.pop(session_id, None)
        self._sessions[projection.session_id] = (session, mediator)
        return SessionActionResult(outcome["status"], outcome, projection)

    def delete(self, session_id: str) -> None:
        session, _ = self._get(session_id)
        session.cancel()
        self._sessions.pop(session_id, None)

    def _action(self, session_id: str, outcome) -> SessionActionResult:
        session, _ = self._get(session_id)
        return SessionActionResult(outcome["status"], outcome, self._projection(session.status()))

    def _get(self, session_id: str):
        try:
            return self._sessions[session_id]
        except (KeyError, TypeError):
            raise ResourceNotFound("session_not_found") from None

    @staticmethod
    def _projection(status) -> SessionProjection:
        session_id = status.get("session_id")
        if type(session_id) is not str:
            session_id = ""
        return SessionProjection(
            session_id=session_id,
            status=status["status"],
            created_at=status.get("created_at"),
            last_activity_at=status.get("last_activity_at"),
            inactivity_expires_at=status.get("inactivity_expires_at"),
            absolute_expires_at=status.get("absolute_expires_at"),
            active_context=status.get("active_context"),
            dynamic_dataset=status.get("dynamic_dataset"),
        )

