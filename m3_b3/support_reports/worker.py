import argparse
import logging
import time
from collections import Counter

from app.services.tickets import get_ticket_status
from support_reports.queue import JobStore, ReportResult, get_job_store

logger = logging.getLogger(__name__)


def run_one(store: JobStore, *, delay_seconds: float = 2) -> bool:
    claim = store.claim()
    if claim is None:
        return False

    logger.info("В работе job_id=%s", claim.job_id)
    time.sleep(delay_seconds)
    counts: Counter[str] = Counter()
    for ticket_id in claim.ticket_ids:
        status = get_ticket_status(claim.user_id, ticket_id)
        if status is None:
            store.finish(claim, "ticket_not_found")
            return True
        counts[status] += 1

    result = ReportResult(requested=len(claim.ticket_ids), by_status=dict(counts))
    if store.finish(claim, result):
        logger.info("Отчёт сохранён job_id=%s", claim.job_id)
    else:
        logger.info("Срок попытки истёк job_id=%s", claim.job_id)
    return True


def _main() -> None:
    parser = argparse.ArgumentParser(description="Воркер очереди отчётов")
    parser.add_argument(
        "--once", action="store_true", help="Проверить очередь один раз"
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    store = get_job_store()
    if args.once:
        run_one(store)
        return

    try:
        while True:
            if not run_one(store):
                time.sleep(0.25)
    except KeyboardInterrupt:
        logger.info("Воркер остановлен")


if __name__ == "__main__":
    _main()
