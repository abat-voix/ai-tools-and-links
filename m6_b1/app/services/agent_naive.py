"""Наивный агент на Responses API: цикл, диспетчер инструментов, трасса.

Вся "магия агента" умещается в один `for`-цикл вокруг одного вызова LLM:
модель либо возвращает финальный ответ, либо просит вызвать инструмент.
Никакого фреймворка — только `openai` и stdlib. Это учебная база, которую
дальше в модуле заменит управляемая обвязка на графе.
"""

import argparse
import json
import logging
import time

from openai import OpenAI

from app.tools.naive_tools import DISPATCH, TOOLS

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gpt-6-luna"
_RESULT_PREVIEW_LEN = 200


def run_agent(
    task: str,
    max_steps: int = 6,
    model: str = DEFAULT_MODEL,
    client: OpenAI | None = None,
) -> dict:
    """Прогоняет наивный agent loop и возвращает ответ, число шагов и трассу."""
    if max_steps < 1:
        raise ValueError("max_steps должен быть положительным")
    client = client or OpenAI()
    history: list = [{"role": "user", "content": task}]
    trace: list[dict] = []
    options = {}
    if model.startswith("gpt-6"):
        options["reasoning"] = {"effort": "none" if model.startswith("gpt-6-luna") else "low"}

    for step in range(max_steps):
        started = time.perf_counter()
        response = client.responses.create(
            model=model,
            input=history,
            tools=TOOLS,
            store=False,
            include=["reasoning.encrypted_content"],
            **options,
        )
        duration_ms = round((time.perf_counter() - started) * 1000, 1)

        if response.status != "completed":
            details = response.incomplete_details
            reason = details.reason if details and details.reason else response.status
            return {"answer": None, "steps": step + 1, "trace": trace,
                    "error": reason or "unknown_status"}

        usage = response.usage
        input_tokens = usage.input_tokens if usage else None
        output_tokens = usage.output_tokens if usage else None
        calls = [item for item in response.output if item.type == "function_call"]

        if not calls:
            answer = response.output_text
            if not answer.strip():
                return {"answer": None, "steps": step + 1, "trace": trace,
                        "error": "empty_response"}
            trace.append(_trace_entry(
                step, None, None, answer, input_tokens, output_tokens, duration_ms,
            ))
            logger.info("step=%d финальный ответ", step)
            return {"answer": answer, "steps": step + 1, "trace": trace}

        # Сохраняем весь output: следующий вызов видит запросы функций и reasoning items.
        history.extend(response.output)
        for call_index, call in enumerate(calls):
            result = _dispatch(call.name, call.arguments)
            trace.append(_trace_entry(
                step,
                call.name,
                call.arguments,
                result,
                input_tokens if call_index == 0 else None,
                output_tokens if call_index == 0 else None,
                duration_ms,
                call_id=call.call_id,
            ))
            history.append({
                "type": "function_call_output", "call_id": call.call_id, "output": result,
            })
            logger.info("step=%d инструмент=%s", step, call.name)

    logger.warning("исчерпан лимит шагов max_steps=%d", max_steps)
    return {"answer": None, "steps": max_steps, "trace": trace, "error": "max_steps"}


def _dispatch(name: str, raw_args: str) -> str:
    """Вызывает инструмент из allowlist; любую проблему возвращает строкой модели."""
    if name not in DISPATCH:
        return f"Ошибка: инструмент '{name}' недоступен. Доступные: {sorted(DISPATCH)}"
    try:
        arguments = json.loads(raw_args) if raw_args else {}
    except json.JSONDecodeError:
        return "Ошибка: не удалось разобрать аргументы"
    if not isinstance(arguments, dict):
        return "Ошибка: аргументы инструмента должны быть JSON-объектом"
    try:
        return str(DISPATCH[name](**arguments))
    except Exception:
        logger.exception("инструмент %s завершился ошибкой", name)
        return "Ошибка инструмента: действие не выполнено"


def _trace_entry(
    step: int,
    tool_name: str | None,
    tool_args: str | None,
    tool_result: str | None,
    input_tokens: int | None,
    output_tokens: int | None,
    duration_ms: float,
    *,
    call_id: str | None = None,
) -> dict:
    """Одна запись трассы — единый формат для шага с инструментом и без него."""
    preview = None if tool_result is None else str(tool_result)[:_RESULT_PREVIEW_LEN]
    return {
        "step": step,
        "call_id": call_id,
        "tool_name": tool_name,
        "tool_args": tool_args,
        "tool_result": preview,
        "llm_input_tokens": input_tokens,
        "llm_output_tokens": output_tokens,
        "duration_ms": duration_ms,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Наивный агент на Responses API")
    parser.add_argument("task", help="Задача для агента")
    parser.add_argument("--max-steps", type=int, default=6, help="Лимит шагов (guardrail)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Модель Responses API")
    parser.add_argument("--trace", action="store_true", help="Печатать пошаговую трассу")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    result = run_agent(args.task, max_steps=args.max_steps, model=args.model)

    if result.get("error"):
        print(f"Остановка: {result['error']} (шагов: {result['steps']})")
    else:
        print(result["answer"])

    if args.trace:
        print("\n--- trace ---")
        for entry in result["trace"]:
            print(json.dumps(entry, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
