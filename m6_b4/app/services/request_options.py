"""Параметры Chat Completions для выбранного семейства моделей."""


def completion_options(
    model: str,
    max_tokens: int | None = None,
    temperature: float | None = None,
) -> dict:
    options: dict = {}
    if model.startswith("gpt-6"):
        no_reasoning = model.startswith(("gpt-6-luna", "gpt-6-sol"))
        options["reasoning_effort"] = "none" if no_reasoning else "low"
        if max_tokens is not None:
            options["max_completion_tokens"] = max_tokens
        if no_reasoning and temperature is not None:
            options["temperature"] = temperature
    else:
        if max_tokens is not None:
            options["max_tokens"] = max_tokens
        if temperature is not None:
            options["temperature"] = temperature
    return options
