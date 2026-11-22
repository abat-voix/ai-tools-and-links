import asyncio
import os
import subprocess
import sys
from pathlib import Path

from fastapi import FastAPI, Header
from httpx import ASGITransport, AsyncClient

import app as service_package
from app.deps.providers import get_demo_user
from support_reports.api import router
from support_reports.queue import JobStore, get_job_store
from support_reports.worker import run_one


def test_http_submit_retry_worker_and_read(tmp_path: Path) -> None:
    async def scenario() -> None:
        store = JobStore(tmp_path / "reports.sqlite3")
        app = FastAPI()
        app.include_router(router)

        def demo_user(x_test_user: str = Header()) -> str:
            return x_test_user

        app.dependency_overrides[get_demo_user] = demo_user
        app.dependency_overrides[get_job_store] = lambda: store

        headers = {"X-Test-User": "support-a", "Idempotency-Key": "once"}
        data = {"ticket_ids": ["T-1042"]}
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            first = await client.post("/reports/jobs", headers=headers, json=data)
            assert first.status_code == 202
            assert first.json()["status"] == "queued"
            location = first.headers["Location"]
            retry = await client.post("/reports/jobs", headers=headers, json=data)
            assert retry.headers["Location"] == location
            assert (
                await client.post(
                    "/reports/jobs", headers=headers, json={"ticket_ids": ["T-1043"]}
                )
            ).status_code == 409
            assert (
                await client.get(location, headers={"X-Test-User": "support-b"})
            ).status_code == 404
            assert (
                await client.post(
                    "/reports/jobs", headers=headers, json={"ticket_ids": ["T-2042"]}
                )
            ).status_code == 404
            assert (
                await client.post(
                    "/reports/jobs",
                    headers=headers,
                    json={"ticket_ids": ["T-1042", "T-1042"]},
                )
            ).status_code == 422

            assert run_one(store, delay_seconds=0)
            finished = await client.get(location, headers=headers)
            assert finished.json()["status"] == "succeeded"
            assert finished.json()["result"] == {
                "requested": 1,
                "by_status": {"in_progress": 1},
            }
            assert not run_one(store, delay_seconds=0)

    asyncio.run(scenario())


def test_worker_checks_ticket_access_again(tmp_path: Path) -> None:
    store = JobStore(tmp_path / "reports.sqlite3")
    job = store.enqueue("support-a", "key", ["T-2042"])
    assert run_one(store, delay_seconds=0)
    finished = store.get("support-a", job.job_id)
    assert finished is not None
    assert finished.status == "failed"
    assert finished.result is None
    assert finished.error == "ticket_not_found"


def test_separate_worker_process_reads_shared_queue(tmp_path: Path) -> None:
    db = tmp_path / "reports.sqlite3"
    store = JobStore(db)
    initial = store.enqueue("support-a", "key", ["T-1042"])
    paths = [
        Path(__file__).resolve().parents[1],
        Path(service_package.__file__).resolve().parents[1],
    ]
    subprocess.run(
        [sys.executable, "-m", "support_reports.worker", "--once"],
        cwd=tmp_path,
        env={
            **os.environ,
            "REPORTS_DB": str(db),
            "PYTHONPATH": os.pathsep.join(map(str, paths)),
        },
        check=True,
        timeout=15,
    )
    finished = store.get("support-a", initial.job_id)
    assert finished is not None
    assert finished.status == "succeeded"
