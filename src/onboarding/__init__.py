"""Public facade for safe local dataset onboarding."""

from .manager import OnboardingManager
from .models import IngestionLimits, OnboardingError
from .preparation import DataQualityReport, PreparationEngine, PreparationManifest

__all__ = [
    "DataQualityReport",
    "IngestionLimits",
    "OnboardingError",
    "OnboardingManager",
    "PreparationEngine",
    "PreparationManifest",
]
