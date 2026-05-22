"""Репозиторий версионированных системных промптов.

Хранит активные кандидаты для A/B traffic-split. Активные — те, у которых
`active = TRUE AND traffic_pct > 0`. Сумма traffic_pct по активным
рекомендуется = 100, но не enforced на уровне БД (оператор отвечает сам).
"""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text


@dataclass
class SystemPrompt:
    id: UUID
    version: str
    body: str
    traffic_pct: int


class SystemPromptRepository:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    async def list_active(self) -> list[SystemPrompt]:
        """Возвращает активные промпты с traffic_pct > 0, новые сначала."""
        if self.session_factory is None:
            return []
        async with self.session_factory() as s:
            rows = (
                await s.execute(
                    text(
                        """
                        SELECT id, version, body, traffic_pct
                        FROM system_prompts
                        WHERE active = TRUE AND traffic_pct > 0
                        ORDER BY created_at DESC
                        """
                    )
                )
            ).all()
        return [
            SystemPrompt(
                id=r.id,
                version=r.version,
                body=r.body,
                traffic_pct=r.traffic_pct,
            )
            for r in rows
        ]
