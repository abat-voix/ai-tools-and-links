from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from pydantic import BaseModel, Field, StringConstraints, field_validator

from app.deps.providers import DemoUserDep
from app.services.tickets import get_ticket_status
from support_reports.queue import JobStore, KeyConflict, ReportJob, get_job_store

router = APIRouter(prefix="/reports/jobs", tags=["reports"])
StoreDep = Annotated[JobStore, Depends(get_job_store)]
TicketId = Annotated[str, StringConstraints(pattern=r"^T-[0-9]{1,12}$")]


class CreateReport(BaseModel):
    ticket_ids: list[TicketId] = Field(min_length=1, max_length=20)

    @field_validator("ticket_ids")
    @classmethod
    def reject_duplicate_ids(cls, ticket_ids: list[str]) -> list[str]:
        if len(ticket_ids) != len(set(ticket_ids)):
            raise ValueError("Идентификаторы заявок должны быть уникальными")
        return ticket_ids


@router.post("", status_code=202)
def submit_report(
    data: CreateReport,
    response: Response,
    user_id: DemoUserDep,
    store: StoreDep,
    idempotency_key: Annotated[
        str, Header(min_length=1, max_length=128, pattern=r"^[a-zA-Z0-9_.:-]+$")
    ],
) -> ReportJob:
    if any(
        get_ticket_status(user_id, ticket_id) is None for ticket_id in data.ticket_ids
    ):
        raise HTTPException(status_code=404, detail="ticket_not_found")
    try:
        job = store.enqueue(user_id, idempotency_key, data.ticket_ids)
    except KeyConflict as exc:
        raise HTTPException(status_code=409, detail="idempotency_key_conflict") from exc
    response.headers["Location"] = f"/reports/jobs/{job.job_id}"
    return job


@router.get("/{job_id}")
def read_report(job_id: str, user_id: DemoUserDep, store: StoreDep) -> ReportJob:
    job = store.get(user_id, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job_not_found")
    return job
