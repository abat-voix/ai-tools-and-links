"""Демо мультиагентного супервизора: researcher (RAG) → writer (цитирование).

Требует реальную модель (ключ читается из .env). База знаний замокана, чтобы
демо запускалось без Qdrant. Печатает порядок узлов и финальный ответ.

    uv run python -m scripts.multi_agent_demo
"""

import asyncio
import sys
from pathlib import Path

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agents.supervisor import build_supervisor  # noqa: E402
from app.core.config import get_settings  # noqa: E402


async def _fake_search(query: str) -> dict:
    return {
        "answer": "Возврат средств за подписку — в течение 14 дней с момента оплаты.",
        "sources": [{"id": 1, "file_name": "billing_refunds.md"}],
        "confident": True,
    }


async def main() -> None:
    settings = get_settings()
    model = ChatOpenAI(
        model=settings.llm.default_model,
        temperature=0,
        api_key=settings.llm.openai_api_key.get_secret_value(),
    )
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
    print(state.values["messages"][-1].content)


if __name__ == "__main__":
    asyncio.run(main())
