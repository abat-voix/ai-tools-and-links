"""Генерация golden dataset через RAGAS TestsetGenerator (группа eval).

RAGAS строит граф знаний из документов корпуса и генерирует разнотипные
вопросы (single-hop / multi-hop / abstract) с эталонным ответом и эталонными
контекстами. Сырой результат сохраняется в CSV — дальше обязательна ручная
вычитка (выкинуть дубли и слишком общие вопросы, доразметить reference).

Запуск:
    uv run --extra eval python scripts/generate_testset.py --size 30
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from llama_index.core import SimpleDirectoryReader  # noqa: E402
from llama_index.embeddings.openai import OpenAIEmbedding  # noqa: E402
from app.eval.llm import TestsetAnthropic  # noqa: E402
from app.services.rag_llm import OpenAIChatLLM  # noqa: E402
from ragas.testset import TestsetGenerator  # noqa: E402

from app.core.config import get_settings  # noqa: E402


def build_generator_llm(settings):
    if settings.eval_judge_provider == "anthropic":
        key = settings.anthropic_api_key
        return TestsetAnthropic(
            model=settings.eval_judge_model, max_tokens=4096,
            api_key=key.get_secret_value() if key else None,
        )
    return OpenAIChatLLM(
        model=settings.eval_judge_model, max_tokens=4096,
        api_key=settings.llm.openai_api_key.get_secret_value(),
        context_window=settings.rag_llm_context_window,
        is_chat_model=True, is_function_calling_model=False,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="RAGAS TestsetGenerator")
    parser.add_argument("--size", type=int, default=30, help="число пар Q/A")
    parser.add_argument(
        "--out", default="tests/eval/golden_dataset_raw.csv", help="куда писать CSV"
    )
    args = parser.parse_args()

    settings = get_settings()
    docs = SimpleDirectoryReader(
        str(settings.rag_data_dir), recursive=True
    ).load_data()
    print(f"Loaded {len(docs)} documents")

    # from_llama_index оборачивает LLM и эмбеддинги LlamaIndex под генератор.
    generator = TestsetGenerator.from_llama_index(
        llm=build_generator_llm(settings),
        embedding_model=OpenAIEmbedding(
            model=settings.embedding_model,
            api_key=settings.llm.openai_api_key.get_secret_value(),
        ),
    )
    testset = generator.generate_with_llamaindex_docs(docs, testset_size=args.size)

    df = testset.to_pandas()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    # Эталон: user_input / reference / reference_contexts. Поля retrieved_contexts
    # и response добавит run_eval.py при прогоне своего RAG.
    print(df[["user_input", "reference", "reference_contexts"]].head())
    print(f"\nСохранено: {out} ({len(df)} строк). Дальше — ручная вычитка.")


if __name__ == "__main__":
    main()
