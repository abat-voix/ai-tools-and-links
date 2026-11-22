"""Демо мультиагентного супервизора: researcher (RAG) → writer (цитирование).

Требует реальную модель (ключ читается из .env). База знаний замокана, чтобы
демо запускалось без Qdrant. Печатает порядок узлов и финальный ответ.

    uv run python -m scripts.multi_agent_demo
"""

import asyncio
import sys
from pathlib import Path

from langchain_core.messages import HumanMessage

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agents.supervisor import build_supervisor, extract_final_answer  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.agents.model import build_agent_model  # noqa: E402


async def _fake_search(query: str) -> dict:
    return {
        "answer": "Возврат средств за подписку — в течение 14 дней с момента оплаты.",
        "sources": [{"id": 1, "file_name": "billing_refunds.md"}],
        "confident": True,
    }


async def main() -> None:
    settings = get_settings()
    model = build_agent_model(settings)
    app = build_supervisor(model, _fake_search)
    config = {"configurable": {"thread_id": "demo-multi-agent"}}
    question = "Каков срок возврата денег за подписку? Ответь с источниками."

    print(f"вопрос: {question}\n--- поток узлов ---")
    async for event in app.astream(
        {"messages": [HumanMessage(question)]}, config, stream_mode="updates"
    ):
        for node in event:
            print(f"  → {node}")

    state = await app.aget_state(config)
    print("\n--- финальный ответ ---")
    print(extract_final_answer(state.values["messages"]))


if __name__ == "__main__":
    asyncio.run(main())
