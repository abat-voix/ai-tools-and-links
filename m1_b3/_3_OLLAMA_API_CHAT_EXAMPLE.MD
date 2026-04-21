curl http://localhost:11434/api/chat -d '{
  "model": "gemma3:1b",
  "messages": [
    {"role": "system", "content": "Ты — Python-разработчик. Отвечай кратко."},
    {"role": "user", "content": "Как прочитать JSON-файл?"}
  ],
  "stream": false
}' | jq


```json
// Ответ:
{
  "model": "gemma3:1b",
  "created_at": "2026-04-19T11:22:47.85136Z",
  "message": {
    "role": "assistant",
    "content": "```python\nimport json\n\nwith open('your_file.json', 'r') as f:\n    data = json.load(f)\n```\n\n(Замените 'your_file.json' на имя вашего файла)\n\n**Пояснение:**\n\n1.  `import json`: Импортируем модуль `json`.\n2.  `with open('your_file.json', 'r') as f:`: Открываем файл JSON с помощью `open()` в режиме чтения (`'r'`).  `with` гарантирует, что файл будет автоматически закрыт после завершения работы, даже если возникнут ошибки.\n3.  `data = json.load(f)`:  `json.load()` считывает данные из файла `f` (который является файлом) и преобразует их в структуру данных Python (обычно словарь или список).  Результат сохраняется в переменной `data`.\n"
  },
  "done": true,
  "done_reason": "stop",
  "total_duration": 3030466500,
  "load_duration": 1252463500,
  "prompt_eval_count": 36,
  "prompt_eval_duration": 109451750,
  "eval_count": 201,
  "eval_duration": 1562846875
}
```
