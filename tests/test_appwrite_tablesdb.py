from types import SimpleNamespace

from core.appwrite_service import AppwriteService


class FakeTablesDB:
    def __init__(self):
        self.rows = {}
        self.calls = []

    @staticmethod
    def _row(row_id, data):
        return SimpleNamespace(model_dump=lambda: {"$id": row_id, "data": dict(data)})

    def create_row(self, *, database_id, table_id, row_id, data, **kwargs):
        self.calls.append(("create_row", database_id, table_id, row_id, dict(data)))
        self.rows[(table_id, row_id)] = dict(data)
        return self._row(row_id, data)

    def get_row(self, *, database_id, table_id, row_id, **kwargs):
        self.calls.append(("get_row", database_id, table_id, row_id))
        return self._row(row_id, self.rows[(table_id, row_id)])

    def update_row(self, *, database_id, table_id, row_id, data, **kwargs):
        self.calls.append(("update_row", database_id, table_id, row_id, dict(data)))
        self.rows[(table_id, row_id)].update(data)
        return self._row(row_id, self.rows[(table_id, row_id)])


def test_remote_tablesdb_job_and_result_operations():
    service = AppwriteService()
    fake = FakeTablesDB()
    service.tables_db = fake
    service.storage = object()
    service.database_id = "db-test"
    service.jobs_table_id = "jobs"
    service.results_table_id = "analysis_results"

    created = service.create_job_document(
        "job-1", "session-1", "tenant-a", "user-1", "hero.png", provider="modal"
    )
    assert created["job_id"] == "job-1"
    assert fake.calls[0][:4] == ("create_row", "db-test", "jobs", "job-1")

    updated = service.update_job_status("job-1", "PROCESSING", progress=35)
    assert updated["status"] == "PROCESSING"
    assert updated["progress_percent"] == 35

    fetched = service.get_job_document("job-1", tenant_id="tenant-a")
    assert fetched["job_id"] == "job-1"
    assert service.get_job_document("job-1", tenant_id="other-tenant") is None

    result = service.save_result_document(
        {
            "analysis_id": "analysis-1",
            "job_id": "job-1",
            "status": "COMPLETE",
            "warnings": [],
            "errors": [],
        },
        tenant_id="tenant-a",
    )
    assert result["analysis_id"] == "analysis-1"
    assert fake.calls[-1][:4] == ("create_row", "db-test", "analysis_results", "analysis-1")
