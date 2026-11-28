"""Три запроса для демонстрации кеша префикса Responses API.

По умолчанию выводятся учебные токены и цены. В режиме --live
обработчик печатает счётчики OpenAI и полное время HTTP-запроса.
"""

import argparse
import json
import os
from time import perf_counter
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from cost import calculate_cost

MODEL = "gpt-6.2-sol"
CASES = (
    ("Первый запрос", "A", "Учебная заявка T-1042 принята в работу.", 0),
    ("Новая заявка", "A", "Учебная заявка T-1043 ожидает ответа клиента.", 2000),
    ("Правка начала регламента", "B", "Учебная заявка T-1043 ожидает ответа клиента.", 0),
)
TOOL = {
    "type": "function",
    "name": "get_ticket_status",
    "description": "Получить статус учебной заявки по идентификатору.",
    "parameters": {
        "type": "object",
        "properties": {"ticket_id": {"type": "string"}},
        "required": ["ticket_id"],
        "additionalProperties": False,
    },
    "strict": True,
}
TEACHING_INPUT_RATES = {"input": "1", "cache_read": "0.05", "cache_write_30m": "1.25"}


def _policy(revision: str, run_id: str) -> str:
    rules = "\n".join(
        f"Правило {number}: проверь идентификатор обращения, передай только "
        "текущий статус и не обещай срок без подтверждения."
        for number in range(1, 65)
    )
    return (
        f"Редакция {revision}. Номер эксперимента {run_id}.\n"
        "Кратко сообщи статус из последнего сообщения.\n"
        f"Учебный регламент:\n{rules}"
    )


def _request_body(
    model: str, revision: str, run_id: str, ticket: str, baseline_id: str | None,
) -> dict[str, Any]:
    options = {"mode": "explicit", "ttl": "30m"}
    if baseline_id is not None:
        options["comparison_response_id"] = baseline_id
    return {
        "model": model,
        "store": False,
        "tools": [TOOL],
        "tool_choice": "none",
        "max_output_tokens": 256,
        "prompt_cache_options": options,
        "input": [
            {
                "role": "developer",
                "content": [{
                    "type": "input_text",
                    "text": _policy(revision, run_id),
                    "prompt_cache_breakpoint": {"mode": "explicit"},
                }],
            },
            {"role": "user", "content": ticket},
        ],
    }


def _request_openai(body: dict[str, Any], api_key: str) -> dict[str, Any]:
    request = Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=60) as response:
        return json.load(response)


def _example_response(case: int, cached_tokens: int) -> dict[str, Any]:
    written_tokens = 2000 - cached_tokens
    diagnostics = {
        2: {"type": "cache_hit"},
        3: {
            "type": "cache_miss",
            "reason": "input_changed",
            "comparison_reusable_tokens": 2000,
            "cache_missed_tokens": 2000,
        },
    }
    return {
        "id": f"fixture_{case}",
        "status": "completed",
        "usage": {
            "input_tokens": 2200,
            "input_tokens_details": {
                "cached_tokens": cached_tokens,
                "cache_write_tokens": written_tokens,
                "cache_write_tokens_details": {
                    "ttl_30m_tokens": written_tokens,
                    "ttl_12h_tokens": 0,
                },
            },
            "output_tokens": 20,
        },
        "prompt_cache_diagnostics": diagnostics.get(case),
    }


def _main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="три платных запроса к OpenAI")
    parser.add_argument("--model", default=MODEL, help="модель с явными границами кеша")
    args = parser.parse_args()
    api_key = os.environ.get("OPENAI_API_KEY") if args.live else None
    if args.live and not api_key:
        parser.error("Для режима --live задайте OPENAI_API_KEY")

    print(f"OpenAI Responses API · {args.model}" if args.live else "Учебные данные · без сети")
    baseline_id = None
    run_id = uuid4().hex if args.live else "demo"
    for case, (name, revision, ticket, cached_tokens) in enumerate(CASES, 1):
        body = _request_body(args.model, revision, run_id, ticket, baseline_id)
        started = perf_counter()
        if api_key:
            try:
                response = _request_openai(body, api_key)
            except HTTPError as exc:
                request_id = exc.headers.get("x-request-id", "не указан")
                raise SystemExit(f"OpenAI вернул HTTP {exc.code}, request ID: {request_id}") from None
            except (URLError, TimeoutError, json.JSONDecodeError):
                raise SystemExit("Не удалось получить ответ OpenAI") from None
        else:
            response = _example_response(case, cached_tokens)
        elapsed = perf_counter() - started
        if response["status"] != "completed" or response.get("usage") is None:
            raise SystemExit(f"Запрос {case} не завершён, usage неполон: {response['status']}")
        if baseline_id is None:
            baseline_id = response["id"]

        usage = response["usage"]
        details = usage["input_tokens_details"]
        print(f"\n{case}. {name}. {ticket} Редакция {revision}")
        print(
            f"   Вход: {usage['input_tokens']}. "
            f"Чтение: {details.get('cached_tokens', 'н/д')}. "
            f"Запись: {details.get('cache_write_tokens', 'н/д')}."
        )
        if api_key:
            print(f"   Полное время запроса: {elapsed:.2f} с")
        else:
            input_cost = calculate_cost({**usage, "output_tokens": 0}, TEACHING_INPUT_RATES)
            print(f"   Учебная цена входа: ${input_cost['total']:.4f}")
        diagnostics = response.get("prompt_cache_diagnostics")
        if diagnostics:
            reason = f" ({diagnostics['reason']})" if "reason" in diagnostics else ""
            print(f"   Сравнение с первым запросом: {diagnostics['type']}{reason}")


if __name__ == "__main__":
    _main()
