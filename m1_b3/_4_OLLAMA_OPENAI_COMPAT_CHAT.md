# Ollama: OpenAI-совместимый Chat Completions API

```bash
# Тот же формат, что и OpenAI API!
curl http://localhost:11434/v1/chat/completions -d '{
  "model": "gemma3:1b",
  "messages": [
    {"role": "user", "content": "Привет! Как дела?"}
  ]
}' | jq
```
```json
{
  "id": "chatcmpl-588",
  "object": "chat.completion",
  "created": 1776598496,
  "model": "gemma3:1b",
  "system_fingerprint": "fp_ollama",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Привет! У меня всё отлично, спасибо, что спросил! Как у тебя? Чем занимаешься? 😊 \n\nЧто-нибудь интересное сегодня произошло?\n"                                                                             
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 14,
    "completion_tokens": 34,
    "total_tokens": 48
  }
}
```

# OpenAI: Chat Completions API

```bash
curl https://api.openai.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -d '{
    "model": "gpt-5-mini",
    "messages": [
      {"role": "user", "content": "Привет! Как дела?"}
    ]
}' | jq
```

```json
{
  "id": "chatcmpl-DWKosuVxtvrYj4BR53FZ5hpa15pUD",
  "object": "chat.completion",
  "created": 1776598898,
  "model": "gpt-5-mini-2025-08-07",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Привет! У меня всё хорошо, спасибо. А у тебя как дела? Чем могу помочь — ответить на вопрос, перевести текст, написать письмо, помочь с кодом или что-то ещё?",                                               
        "refusal": null,
        "annotations": []
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 12,
    "completion_tokens": 178,
    "total_tokens": 190,
    "prompt_tokens_details": {
      "cached_tokens": 0,
      "audio_tokens": 0
    },
    "completion_tokens_details": {
      "reasoning_tokens": 128,
      "audio_tokens": 0,
      "accepted_prediction_tokens": 0,
      "rejected_prediction_tokens": 0
    }
  },
  "service_tier": "default",
  "system_fingerprint": null
}
```