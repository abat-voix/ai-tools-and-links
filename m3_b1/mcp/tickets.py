import re

PROFILE = "support-a"
TICKETS = {
    "T-1042": {"owner": "support-a", "status": "in_progress"},
    "T-2042": {"owner": "support-b", "status": "resolved"},
}


def get_ticket_status(ticket_id: str) -> dict[str, str]:
    """Получить текущий статус доступной заявки по её номеру."""
    if not re.fullmatch(r"T-[0-9]{4}", ticket_id):
        return {"error": "invalid_ticket_id"}
    ticket = TICKETS.get(ticket_id)
    if ticket is None or ticket["owner"] != PROFILE:
        return {"error": "ticket_unavailable"}
    return {"ticket_id": ticket_id, "status": ticket["status"]}
