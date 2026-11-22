import json
import os
import sqlite3
import time
from contextlib import closing
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel

JobStatus = Literal["queued", "running", "succeeded", "failed"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS report_jobs (
    job_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    ticket_ids TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    attempts INTEGER NOT NULL DEFAULT 0,
    lease_until REAL,
    claim_token TEXT,
    result TEXT,
    error TEXT,
    UNIQUE (user_id, idempotency_key)
)
"""


class KeyConflict(Exception):
    """Ключ уже привязан к другому запросу."""


class ReportResult(BaseModel):
    requested: int
    by_status: dict[str, int]


class ReportJob(BaseModel):
    job_id: str
    status: JobStatus
    result: ReportResult | None = None
    error: str | None = None


@dataclass(frozen=True)
class Claim:
    job_id: str
    user_id: str
    ticket_ids: list[str]
    token: str


class JobStore:
    def __init__(
        self, path: Path, *, lease_seconds: int = 15, max_attempts: int = 3
    ) -> None:
        self.path = path
        self.lease_seconds = lease_seconds
        self.max_attempts = max_attempts
        with closing(self._connect()) as connection, connection:
            connection.execute(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=5)
        connection.row_factory = sqlite3.Row
        return connection

    def enqueue(self, user_id: str, key: str, ticket_ids: list[str]) -> ReportJob:
        payload = json.dumps(sorted(ticket_ids))
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """
                INSERT INTO report_jobs (job_id, user_id, idempotency_key, ticket_ids)
                VALUES (?, ?, ?, ?)
                ON CONFLICT (user_id, idempotency_key) DO NOTHING
                """,
                (uuid4().hex, user_id, key, payload),
            )
            row = connection.execute(
                "SELECT * FROM report_jobs WHERE user_id = ? AND idempotency_key = ?",
                (user_id, key),
            ).fetchone()
            if row["ticket_ids"] != payload:
                raise KeyConflict
            return _read_job(row)

    def get(self, user_id: str, job_id: str) -> ReportJob | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT * FROM report_jobs WHERE job_id = ? AND user_id = ?",
                (job_id, user_id),
            ).fetchone()
        return _read_job(row) if row else None

    def claim(self, now: float | None = None) -> Claim | None:
        now = time.time() if now is None else now
        token = uuid4().hex
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """
                UPDATE report_jobs SET status = 'failed', error = 'worker_lease_expired',
                    lease_until = NULL, claim_token = NULL
                WHERE status = 'running' AND lease_until <= ? AND attempts >= ?
                """,
                (now, self.max_attempts),
            )
            row = connection.execute(
                """
                UPDATE report_jobs
                SET status = 'running', lease_until = ?, claim_token = ?, attempts = attempts + 1
                WHERE job_id = (
                    SELECT job_id FROM report_jobs
                    WHERE status = 'queued' OR (status = 'running' AND lease_until <= ?)
                    ORDER BY rowid LIMIT 1
                )
                RETURNING job_id, user_id, ticket_ids, claim_token
                """,
                (now + self.lease_seconds, token, now),
            ).fetchone()
        if row is None:
            return None
        return Claim(
            row["job_id"],
            row["user_id"],
            json.loads(row["ticket_ids"]),
            row["claim_token"],
        )

    def finish(
        self, claim: Claim, outcome: ReportResult | str, now: float | None = None
    ) -> bool:
        now = time.time() if now is None else now
        if isinstance(outcome, ReportResult):
            status, result, error = "succeeded", outcome.model_dump_json(), None
        else:
            status, result, error = "failed", None, outcome
        with closing(self._connect()) as connection, connection:
            cursor = connection.execute(
                """
                UPDATE report_jobs
                SET status = ?, result = ?, error = ?, lease_until = NULL, claim_token = NULL
                WHERE job_id = ? AND status = 'running' AND claim_token = ? AND lease_until > ?
                """,
                (status, result, error, claim.job_id, claim.token, now),
            )
            return cursor.rowcount == 1


def _read_job(row: sqlite3.Row) -> ReportJob:
    return ReportJob(
        job_id=row["job_id"],
        status=row["status"],
        result=ReportResult.model_validate_json(row["result"])
        if row["result"]
        else None,
        error=row["error"],
    )


@lru_cache(maxsize=1)
def get_job_store() -> JobStore:
    path = (
        Path(os.environ.get("REPORTS_DB", "./report-jobs.sqlite3"))
        .expanduser()
        .resolve()
    )
    return JobStore(path)
