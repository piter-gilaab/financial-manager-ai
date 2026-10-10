"""Public facade for safe local dataset onboarding."""

from .manager import OnboardingManager
from .models import IngestionLimits, OnboardingError

__all__ = ["IngestionLimits", "OnboardingError", "OnboardingManager"]
