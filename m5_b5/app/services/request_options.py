"""Параметры Responses API для выбранного семейства моделей."""


def response_options(
    model: str,
    max_tokens: int | None = None,
    temperature: float | None = None,
) -> dict:
    options: dict = {}
    if max_tokens is not None:
        options["max_output_tokens"] = max_tokens
    if model.startswith("gpt-6"):
        no_reasoning = model.startswith(("gpt-6-luna", "gpt-6-sol"))
        options["reasoning"] = {"effort": "none" if no_reasoning else "low"}
        if no_reasoning and temperature is not None:
            options["temperature"] = temperature
    elif temperature is not None:
        options["temperature"] = temperature
    return options
