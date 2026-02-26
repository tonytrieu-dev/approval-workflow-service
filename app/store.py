from dataclasses import replace

from app.models import WorkflowRecord


class WorkflowStore:
    def __init__(self) -> None:
        self._data: dict[str, WorkflowRecord] = {}

    def create(self, record: WorkflowRecord) -> WorkflowRecord:
        self._data[record.workflow_id] = record
        return record

    def get(self, workflow_id: str) -> WorkflowRecord | None:
        return self._data.get(workflow_id)

    def update(self, workflow_id: str, **kwargs) -> WorkflowRecord:
        existing_record = self._data.get(workflow_id)
        if existing_record is None:
            raise KeyError(f"Workflow '{workflow_id}' not found in store")
        updated_record = replace(existing_record, **kwargs)
        self._data[workflow_id] = updated_record
        return updated_record


store = WorkflowStore()
