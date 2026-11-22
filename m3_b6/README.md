# Проверка перед выпуском помощника

Проверяемый сервис находится в [m3_b1](../m3_b1/). [Фоновый отчёт](../m3_b3/) использует тот же каталог заявок и аутентификацию.

1. Из `m3_b1` выполните `uv sync --locked` и `uv run pytest -q`. Тесты проверяют успешную выдачу статуса, отсутствие доступа к чужой заявке, ошибки аргументов и предел цикла. Ключ OpenAI им не нужен.
2. Запустите тесты фоновых задач по [инструкции](../m3_b3/README.md). Повтор одного запроса должен вернуть тот же идентификатор. Другой профиль не должен видеть состояние задачи.
3. Соберите образ командой `docker build -t support-service:local .`. Для проверки процесса и HTTP без внешней сети запустите команду ниже из любого каталога.

```bash
docker run --rm --network none \
  -e OPENAI_API_KEY=offline-placeholder \
  -e DEMO_TOKEN_A=local-a -e DEMO_TOKEN_B=local-b \
  support-service:local sh -ec '
    test "$(id -u)" -ne 0
    uvicorn app.main:app --host 127.0.0.1 --port 8000 &
    pid=$!
    trap "kill $pid 2>/dev/null || true" EXIT
    for n in $(seq 1 15); do
      if python -c "import urllib.request as u; u.urlopen(\"http://localhost:8000/health\", timeout=1).close(); u.urlopen(\"http://localhost:8000/ready\", timeout=1).close()"; then
        exit 0
      fi
      sleep 1
    done
    exit 1
  '
```

Выпуск требует отдельно проверить доступ к данным, настройки экспорта логов и регрессию ответов. Для последней есть [пример проверки выпуска](../m3_b5/evaluation/). Запуск контейнера подтверждает готовность процесса без внешней инфраструктуры и вызовов модели.
