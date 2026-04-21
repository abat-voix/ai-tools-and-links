# Установка Ollama: одна команда

## macOS

```bash
# Вариант 1: Homebrew
brew install ollama
```

```bash
# Вариант 2: скачать .app с сайта ollama.com
# После установки Ollama запускается как фоновый сервис автоматически
```

## Linux

```bash
# Один скрипт — установка + автозапуск
curl -fsSL https://ollama.com/install.sh | sh

# Проверяем, что сервер работает
ollama --version
# ollama version is 0.18.3
```

## Windows

```bash
# Вариант 1 (рекомендуется): через WSL2
wsl --install  # если WSL еще не установлен

# Далее внутри WSL — как на Linux:
curl -fsSL https://ollama.com/install.sh | sh
```

```bash
# Вариант 2: нативный установщик с ollama.com
```

## Проверка установки

```bash

ollama serve
# Должен ответить "Ollama is running"
curl http://localhost:11434
# Ollama is running

# Скачиваем и запускаем первую модель
ollama run qwen3:8b
# >>> Скачивание... 4.9 GB
# >>> Готово. Введите сообщение:
```


```bash
OLLAMA_HOST:http://127.0.0.1:11434
Это адрес локального сервера Ollama. Он слушает только на вашем компьютере на порту 11434.

OLLAMA_MODELS:/Users/igor/.ollama/models
Здесь хранятся скачанные модели.

OLLAMA_KEEP_ALIVE:5m0s
Загруженная модель держится в памяти еще 5 минут после последнего запроса, чтобы следующий запуск был быстрее.

OLLAMA_LOAD_TIMEOUT:5m0s
Максимальное время ожидания загрузки модели.

OLLAMA_MAX_QUEUE:512
Максимум 512 запросов в очереди.

OLLAMA_NUM_PARALLEL:1
Одновременно обрабатывается 1 запрос. Это настройка параллелизма.

OLLAMA_CONTEXT_LENGTH:0
Явно длина контекста не задана. Значит используется значение по умолчанию модели.

OLLAMA_ORIGINS:[...]
Список источников, которым разрешено обращаться к серверу Ollama: localhost, 127.0.0.1, file://, vscode-webview:// и другие локальные origin.

OLLAMA_REMOTES:[ollama.com]
Разрешенный удаленный реестр моделей. Отсюда Ollama скачивает модели.

OLLAMA_DEBUG:INFO
Уровень логирования: информационный. Это нормальный рабочий режим.

Что означает false у многих флагов:

OLLAMA_FLASH_ATTENTION:false
Flash Attention не включен.
OLLAMA_MULTIUSER_CACHE:false
Нет многопользовательского кэша.
OLLAMA_NEW_ENGINE:false
Новый движок не используется.
OLLAMA_NOHISTORY:false
История не отключена.
OLLAMA_NOPRUNE:false
Автоочистка не отключена.
OLLAMA_NO_CLOUD:false
Облачные функции не запрещены.
```

Почитать лучше всего в официальной документации Ollama:

- [Ollama Docs](https://ollama.com/docs)
- [CLI reference](https://github.com/ollama/ollama/blob/main/docs/cli.md)
- [FAQ / configuration](https://github.com/ollama/ollama/blob/main/docs/faq.md)
- [API reference](https://ollama.com/docs/api)

