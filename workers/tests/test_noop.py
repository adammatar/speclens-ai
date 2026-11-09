"""Worker no-op task unit test (runs task body without a broker)."""

from __future__ import annotations

from speclens_worker.tasks import noop_job


def test_noop_job_echoes_payload() -> None:
    result = noop_job.run({"hello": "world"})
    assert result["status"] == "ok"
    assert result["echo"] == {"hello": "world"}
