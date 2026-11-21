"""Closed analysis use cases delegated to FinancialManagerAgent."""

from src.anomaly.dynamic import DynamicAnomalyRequest
from src.dynamic_financial import SalesRecordOperation
from src.execution import DynamicQueryParameters, DynamicQueryRequest
from src.multidomain_financial import MultiDomainOperation

from .models import AnalysisCommand, AnomalyCommand, ApplicationResult


class AnalysisApplication:
    def __init__(self, manager, *, onboarding=None):
        self._manager = manager
        self._onboarding = onboarding

    def capabilities(self, dataset_id: str | None = None):
        if dataset_id is not None:
            if self._onboarding is None:
                raise RuntimeError("Dataset capability projection is not configured.")
            return self._onboarding.capabilities(dataset_id)
        return tuple(
            item if type(item) is dict else item.to_dict()
            for item in self._manager.list_capabilities()
        )

    def execute(self, command: AnalysisCommand) -> ApplicationResult:
        try:
            operation = SalesRecordOperation(command.operation.value)
        except ValueError:
            operation = MultiDomainOperation(command.operation.value)
        response = self._manager.execute_dataset_request(DynamicQueryRequest(
            dataset_id=command.dataset_id,
            operation=operation,
            parameters=DynamicQueryParameters(
                granularity=(command.granularity.value if command.granularity else None),
                missing_dimension=(command.missing_dimension.value if command.missing_dimension else None),
                as_of_date=command.as_of_date,
            ),
        ))
        return self._result(response)

    def execute_anomaly(self, command: AnomalyCommand) -> ApplicationResult:
        response = self._manager.execute_dataset_anomaly_request(
            DynamicAnomalyRequest(command.dataset_id, command.operation.value),
        )
        return self._result(response)

    @staticmethod
    def _result(response) -> ApplicationResult:
        return ApplicationResult(
            status=response["execution_status"],
            payload=response,
            limitations=tuple(response.get("limitations", ())),
            errors=tuple(response.get("errors", ())),
        )

