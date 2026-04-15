# Полезные инструменты и ссылки

## Что желательно установить

1. Установить `Python`, `Git`, IDE или редактор кода (`PyCharm` в приоритете, можно `VS Code`), `Docker`, `Ollama`.
2. Проверить, что открывается терминал и работают команды `python`, `git`, `docker`.
3. Завести аккаунт на `GitHub`.
4. Завести хотя бы один API-ключ: `OpenAI`, `OpenRouter` или `Groq`.

## Что установить и зачем

### Python

Основной язык. На нем будут собраны CLI-утилиты, API-интеграции, FastAPI-сервисы, RAG и агенты.

- Скачать: [Python](https://www.python.org/downloads/)

### Git

Нужен для работы с репозиториями, домашними заданиями и дипломным проектом.

- Скачать: [Git](https://git-scm.com/downloads)

### GitHub

Нужен для доступа к репозиториям и работы с кодом через Git.

- Зарегистрироваться: [GitHub](https://github.com/)

### PyCharm

Предпочтительная IDE, особенно если вы планируете много работать с Python, FastAPI, отладкой и дипломным проектом. Удобно управлять виртуальным окружением, запуском, структурой проекта и навигацией по коду.

- Скачать: [PyCharm](https://www.jetbrains.com/pycharm/download/)

### VS Code

Хороший легкий редактор, если вы уже привыкли к нему. Подходит для Python, API, Docker и работы с проектом целиком, но в идеале лучше использовать `PyCharm`.

- Скачать: [Visual Studio Code](https://code.visualstudio.com/download)

### Docker Desktop

Понадобится для запуска сервисов и инфраструктуры: контейнеров, баз данных, локального окружения проекта.

- Скачать: [Docker Desktop](https://www.docker.com/products/docker-desktop/)

### Ollama

Нужен для запуска локальных моделей.

- Сайт: [Ollama](https://ollama.com/)
- Документация: [Ollama Docs](https://docs.ollama.com/)

## Что желательно подготовить дополнительно

### API-ключ для облачных моделей

На курсе мы будем работать с ИИ API, поэтому заранее подготовьте хотя бы один ключ:

- [Groq Console](https://console.groq.com/) - консоль с быстрым API для LLM, подходит как бесплатный API для старта и экспериментов
- [OpenAI Platform](https://platform.openai.com/)
- [OpenRouter](https://openrouter.ai/)
- [Yandex Cloud Foundation Models](https://yandex.cloud/ru/services/foundation-models) - доступ к YandexGPT и другим моделям через API
- [GigaChat API](https://developers.sber.ru/portal/products/gigachat) - API-модели от Сбера для чата, генерации текста и других ИИ-задач

Если у вас уже есть доступ к другим LLM-платформам, это тоже будет полезно, но для старта достаточно одного сервиса.

## Что проверить после установки

Откройте терминал и убедитесь, что команды ниже запускаются без ошибок:

```bash
python --version
git --version
docker --version
```

Если `Docker` установлен, но команда не работает, проверьте, что приложение `Docker Desktop` запущено.

## Полезные ссылки

### Документация и основные сервисы

- [Python](https://www.python.org/downloads/) - установка Python
- [Git](https://git-scm.com/downloads) - установка Git
- [GitHub](https://github.com/) - аккаунт для работы с репозиториями и отправки домашних заданий
- [PyCharm](https://www.jetbrains.com/pycharm/download/) - предпочтительная IDE для Python-проектов
- [VS Code](https://code.visualstudio.com/download) - редактор кода
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) - контейнеры и локальная инфраструктура
- [Ollama](https://ollama.com/) - запуск локальных моделей
- [Ollama Docs](https://docs.ollama.com/) - документация по Ollama
- [OpenAI Platform](https://platform.openai.com/) - API и ключи OpenAI
- [OpenRouter](https://openrouter.ai/) - единая точка доступа к разным моделям через API
- [Yandex Cloud Foundation Models](https://yandex.cloud/ru/services/foundation-models) - API-доступ к YandexGPT и related AI-сервисам
- [GigaChat API](https://developers.sber.ru/portal/products/gigachat) - российский API-сервис для работы с LLM от Сбера

### Полезные веб-инструменты для знакомства с моделями

Эти сервисы могут быть полезны, если вы хотите быстро посмотреть, как ведут себя разные модели в браузере.

Международные сервисы:

- [DeepSeek Chat](https://chat.deepseek.com/) - чат с моделями DeepSeek, удобно для быстрых экспериментов и сравнения ответов
- [Kimi](https://www.kimi.com/) - веб-чат с ИИ-моделью Kimi, полезен для повседневных задач и тестирования промптов
- [Claude](https://claude.ai/) - чат с моделью от Anthropic, интересен для сравнения с OpenAI и другими LLM
- [ChatGPT](https://chat.openai.com/) - официальный чат от OpenAI, полезен для знакомства с моделями GPT и их поведением

Варианты для российского сегмента:

- [GigaChat](https://developers.sber.ru/portal/products/gigachat) - российская LLM-платформа от Сбера, подходит для знакомства с локальными сценариями и API
- [Yandex Cloud Foundation Models](https://yandex.cloud/ru/services/foundation-models) - платформа YandexGPT и related AI-моделей для экспериментов через облако и API

### Онлайн-токенайзеры

Эти сервисы помогают быстро проверить, как текст разбивается на токены и примерно оценить размер запроса к модели.

- [OpenAI Tokenizer](https://platform.openai.com/tokenizer) - официальный токенайзер OpenAI для быстрой проверки текста
- [Tiktokenizer](https://tiktokenizer.vercel.app/) - удобный веб-интерфейс для оценки токенов в моделях OpenAI
- [Anthropic Tokenizer](https://docs.anthropic.com/en/docs/build-with-claude/token-counting) - документация и инструменты для подсчета токенов Claude

### Observability и мониторинг LLM

Инструменты для отладки, трейсинга и мониторинга LLM-приложений в продакшене. Позволяют видеть, что происходит внутри цепочки вызовов: промпты, ответы, tool calls, шаги RAG.

- [Arize Phoenix](https://phoenix.arize.com/) - open-source платформа для LLM-observability от Arize AI. Трейсинг на базе OpenTelemetry, оценка качества ответов, отладка RAG и агентов. Можно развернуть локально без ограничений
- [Arize AX](https://arize.com/) - enterprise-платформа для мониторинга LLM и ML-моделей в продакшене. Алерты, дашборды, анализ дрифта
- [Arize Phoenix на GitHub](https://github.com/Arize-ai/phoenix) - исходный код Phoenix, удобно для self-hosted установки и контрибуции

### AI-ассистенты для разработки

Инструменты, которые помогают писать код, отлаживать и работать с проектами прямо из терминала или IDE.

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) — CLI-ассистент от Anthropic. Работает прямо в терминале: читает файлы, пишет код, запускает команды, делает коммиты. Понимает контекст всего проекта
- [OpenAI Codex CLI](https://github.com/openai/codex) — аналогичный CLI-инструмент от OpenAI. Работает в терминале, поддерживает автономное выполнение задач с кодом
- [Superpowers](https://github.com/obra/superpowers) — фреймворк агентных навыков для AI-ассистентов. Добавляет структурированный процесс разработки: TDD, систематический дебаг, code review. Работает с Claude Code, Cursor, GitHub Copilot CLI
- [Context7](https://context7.com/) — MCP-сервер и веб-сервис, который подтягивает актуальную документацию библиотек прямо в контекст AI-ассистента. Полезно, когда модель «галлюцинирует» устаревшие API

### Python-библиотеки для токенизации и LLM

Если хочется не только смотреть токены в браузере, но и считать их прямо в коде, пригодятся такие библиотеки:

- [tiktoken](https://github.com/openai/tiktoken) - популярная библиотека Python для подсчета токенов в моделях OpenAI
- [transformers](https://github.com/huggingface/transformers) - большая библиотека Hugging Face с токенайзерами и моделями
- [tokenizers](https://github.com/huggingface/tokenizers) - быстрые токенайзеры от Hugging Face, удобно для работы с текстом и своими пайплайнами
