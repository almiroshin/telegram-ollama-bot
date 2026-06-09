# Telegram Ollama Bot

Локальный Telegram-бот для работы с Ollama: текстовый ассистент, деловые режимы промптов, распознавание голосовых сообщений и анализ документов.

Проект сейчас реализован как один Python-модуль [bot.py](bot.py). Он подходит для персонального локального использования: Telegram выступает интерфейсом, Ollama отвечает за LLM, faster-whisper распознает голос, Tesseract/Poppler помогают извлекать текст из PDF-сканов.

## Возможности

- Обычный чат с локальной LLM через Ollama Chat API.
- Контекст диалога по пользователю в памяти процесса.
- Готовые режимы:
  - `/email` - деловое письмо.
  - `/rewrite` - редактура текста.
  - `/shorten` - сжатие текста.
  - `/vip` - текст для высокого руководителя или чиновника.
  - `/surf` - стиль SURF Consulting.
  - `/shell` - помощь по терминалу macOS/Linux.
  - `/followup` - follow-up после встречи.
- Служебные команды:
  - `/start` - справка.
  - `/status` - проверка Ollama и текущих лимитов.
  - `/model` - текущая Ollama-модель.
  - `/reset` - очистка истории текущего пользователя.
  - `/myid` - Telegram ID пользователя.
- Голосовые сообщения: локальная транскрибация через `faster-whisper`.
- Документы: `.txt`, `.md`, `.pdf`, `.docx`.
- OCR для PDF без текстового слоя.

## Архитектура и планы

- [Архитектура](docs/ARCHITECTURE.md)
- [Эксплуатация](docs/OPERATIONS.md)
- [Роудмэп](docs/ROADMAP.md)
- [Анализ проекта](docs/PROJECT_ANALYSIS.md)

## Требования

- Python 3.10+.
- Запущенная Ollama.
- Telegram bot token от BotFather.
- Системные утилиты для OCR и PDF:
  - macOS: `poppler`, `tesseract`, языковые пакеты Tesseract.
  - Linux: `poppler-utils`, `tesseract-ocr`, `tesseract-ocr-rus`.

Python-зависимости перечислены в [requirements.txt](requirements.txt).

## Быстрый старт на macOS

```bash
brew install ollama poppler tesseract tesseract-lang
ollama pull qwen3:8b
```

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

```bash
cp .env.example .env
```

Заполните `TELEGRAM_TOKEN` в `.env`, затем экспортируйте переменные и запустите бота:

```bash
set -a
source .env
set +a
python bot.py
```

Ollama должна быть доступна по `OLLAMA_URL`, по умолчанию:

```text
http://127.0.0.1:11434/api/chat
```

## Конфигурация

Основные переменные окружения:

| Переменная | По умолчанию | Назначение |
| --- | --- | --- |
| `TELEGRAM_TOKEN` | нет | Токен Telegram-бота. Обязателен. |
| `OLLAMA_URL` | `http://127.0.0.1:11434/api/chat` | Endpoint Ollama Chat API. |
| `OLLAMA_MODEL` | `qwen3:8b` | Модель Ollama. |
| `MAX_HISTORY_MESSAGES` | `12` | Сколько последних сообщений держать в памяти. |
| `WHISPER_MODEL_SIZE` | `small` | Размер модели faster-whisper. |
| `WHISPER_DEVICE` | `cpu` | Устройство для STT: `cpu`, `cuda`, `auto`. |
| `WHISPER_COMPUTE_TYPE` | `int8` | Тип вычислений faster-whisper. |
| `MAX_FILE_SIZE_MB` | `20` | Максимальный размер документа из Telegram. |
| `MAX_DOCUMENT_CHARS` | `18000` | Сколько символов документа отправлять в LLM. |
| `OCR_DPI` | `200` | DPI при рендере PDF-страниц для OCR. |
| `OCR_LANG` | `rus+eng` | Языки Tesseract. |
| `MAX_OCR_PAGES` | `20` | Максимум OCR-страниц PDF. |
| `POPPLER_PATH` | `/opt/homebrew/bin` | Путь к Poppler на macOS/Homebrew. |
| `TESSERACT_CMD` | `/opt/homebrew/bin/tesseract` | Путь к бинарнику Tesseract. |

Полный пример лежит в [.env.example](.env.example).

## Проверка

Синтаксис без записи bytecode cache:

```bash
python3 -c 'import ast, pathlib; ast.parse(pathlib.Path("bot.py").read_text())'
```

Проверка Ollama:

```bash
curl http://127.0.0.1:11434/api/tags
```

После запуска бота отправьте в Telegram:

```text
/status
```

## Текущие ограничения

- История хранится в памяти процесса и теряется после перезапуска.
- Нет allowlist пользователей: любой, кто знает бота, может писать ему.
- Один файл `bot.py` содержит все слои: конфигурацию, Telegram handlers, LLM-клиент, STT и document parsing.
- Документы длиннее `MAX_DOCUMENT_CHARS` обрезаются, RAG/индексации пока нет.
- Нет автоматических тестов.
- Ошибки показываются пользователю напрямую, без нормализации и без приватной диагностики.

## Рекомендуемый следующий шаг

Сначала добавить контроль доступа по Telegram ID и разнести код по модулям. Это снизит главный эксплуатационный риск и упростит дальнейшее развитие: персистентную память, очереди для тяжелых задач, RAG по документам и тесты.
