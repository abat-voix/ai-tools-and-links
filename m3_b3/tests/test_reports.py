from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from support_reports.queue import JobStore, KeyConflict, ReportResult


def test_retry_reuses_job_and_rejects_changed_request(tmp_path: Path) -> None:
    store = JobStore(tmp_path / "reports.sqlite3")
    first = store.enqueue("support-a", "key", ["T-1042", "T-1043"])
    retry = store.enqueue("support-a", "key", ["T-1043", "T-1042"])

    assert retry.job_id == first.job_id
    assert retry.status == "queued"
    with pytest.raises(KeyConflict):
        store.enqueue("support-a", "key", ["T-1042"])
    assert store.enqueue("support-b", "key", ["T-2042"]).job_id != first.job_id
    assert store.get("support-b", first.job_id) is None


def test_parallel_submissions_and_claims_are_atomic(tmp_path: Path) -> None:
    store = JobStore(tmp_path / "reports.sqlite3")
    with ThreadPoolExecutor(max_workers=4) as executor:
        submissions = [
            executor.submit(store.enqueue, "support-a", "key", ["T-1042"])
            for _ in range(4)
        ]
        ids = {future.result().job_id for future in submissions}
        claims = list(executor.map(store.claim, range(1, 5)))
    assert len(ids) == 1
    assert len([claim for claim in claims if claim is not None]) == 1


def test_reclaim_after_expired_lease_and_ignore_old_completion(tmp_path: Path) -> None:
    path = tmp_path / "reports.sqlite3"
    store = JobStore(path, lease_seconds=10)
    job = store.enqueue("support-a", "key", ["T-1042"])
    first = store.claim(100)
    assert first is not None
    assert store.claim(109) is None

    reopened = JobStore(path, lease_seconds=10)
    second = reopened.claim(110)
    assert second is not None
    assert second.job_id == job.job_id
    assert second.token != first.token

    result = ReportResult(requested=1, by_status={"in_progress": 1})
    assert not store.finish(first, result, 111)
    assert reopened.finish(second, result, 111)
    finished = reopened.get("support-a", job.job_id)
    assert finished is not None
    assert finished.status == "succeeded"
    assert finished.result == result


def test_expired_leases_stop_after_attempt_limit(tmp_path: Path) -> None:
    store = JobStore(tmp_path / "reports.sqlite3", lease_seconds=5, max_attempts=2)
    job = store.enqueue("support-a", "key", ["T-1042"])

    for now in (10, 15):
        assert store.claim(now) is not None
    assert store.claim(20) is None
    failed = store.get("support-a", job.job_id)
    assert failed is not None
    assert failed.status == "failed"
    assert failed.error == "worker_lease_expired"
