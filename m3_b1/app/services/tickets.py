TICKETS = {
    "T-1042": ("support-a", "in_progress"),
    "T-1043": ("support-a", "resolved"),
    "T-2042": ("support-b", "resolved"),
}


def get_ticket_status(user_id: str, ticket_id: str) -> str | None:
    ticket = TICKETS.get(ticket_id)
    if ticket and ticket[0] == user_id:
        return ticket[1]
    return None
