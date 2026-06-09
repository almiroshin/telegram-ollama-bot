# Эксплуатация

## Локальный запуск

1. Установить системные зависимости.

macOS:

```bash
brew install ollama poppler tesseract tesseract-lang
```

Linux:

```bash
sudo apt-get update
sudo apt-get install -y poppler-utils tesseract-ocr tesseract-ocr-rus
```

2. Подготовить Ollama.

```bash
ollama pull qwen3:8b
ollama serve
```

Если Ollama уже запущена как сервис, отдельный `ollama serve` не нужен.

3. Подготовить Python-окружение.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

4. Создать `.env`.

```bash
cp .env.example .env
```

Минимально нужно заполнить:

```text
TELEGRAM_TOKEN=...
```

5. Запустить бота.

```bash
set -a
source .env
set +a
python bot.py
```

## Проверка после запуска

В Telegram:

```text
/status
```

Ожидаемый результат:

- `Статус: работает`;
- корректная модель Ollama;
- корректные лимиты файлов и OCR;
- корректные пути `POPPLER_PATH` и `TESSERACT_CMD`.

Локальная проверка Ollama:

```bash
curl http://127.0.0.1:11434/api/tags
```

Проверка Tesseract:

```bash
tesseract --list-langs
```

Для текущего `OCR_LANG=rus+eng` в списке должны быть `rus` и `eng`.

## Переменные окружения

### Telegram и LLM

- `TELEGRAM_TOKEN` - обязательный токен бота.
- `OLLAMA_URL` - URL chat endpoint, обычно `http://127.0.0.1:11434/api/chat`.
- `OLLAMA_MODEL` - модель, например `qwen3:8b`, `llama3.1:8b`, `mistral`.
- `MAX_HISTORY_MESSAGES` - сколько последних сообщений держать в контексте.

### Голос

- `WHISPER_MODEL_SIZE` - размер модели: `tiny`, `base`, `small`, `medium`, `large-v3`.
- `WHISPER_DEVICE` - `cpu`, `cuda` или `auto`.
- `WHISPER_COMPUTE_TYPE` - для CPU обычно `int8`, для GPU часто `float16`.

### Документы и OCR

- `MAX_FILE_SIZE_MB` - ограничение размера входящего файла.
- `MAX_DOCUMENT_CHARS` - ограничение текста, отправляемого в LLM.
- `OCR_DPI` - качество рендера PDF перед OCR.
- `OCR_LANG` - языки Tesseract, например `rus+eng`.
- `MAX_OCR_PAGES` - максимум страниц для OCR.
- `POPPLER_PATH` - путь к Poppler. На Apple Silicon Homebrew обычно `/opt/homebrew/bin`.
- `TESSERACT_CMD` - путь к Tesseract.

## Производительность

Самые тяжелые операции:

- первый запуск `faster-whisper`, потому что модель загружается в память;
- OCR PDF-сканов;
- длинные запросы к Ollama.

Практические настройки:

- Для слабого CPU оставить `WHISPER_MODEL_SIZE=small` и `WHISPER_COMPUTE_TYPE=int8`.
- Для более быстрого STT использовать GPU и `WHISPER_COMPUTE_TYPE=float16`.
- Если OCR медленный, уменьшить `MAX_OCR_PAGES` или `OCR_DPI`.
- Если Ollama отвечает медленно, выбрать модель меньшего размера.

## Безопасность

Сейчас в коде нет allowlist пользователей. До эксплуатации вне личного окружения нужно добавить проверку `update.effective_user.id`.

Рекомендуемая модель:

```text
ALLOWED_TELEGRAM_USER_IDS=123,456
```

И поведение:

- команды и сообщения от неизвестных пользователей отклонять;
- не раскрывать конфигурацию неизвестным пользователям;
- не отправлять в ответ подробные stack traces.

Также не стоит коммитить `.env`: он уже закрыт в [.gitignore](../.gitignore).

## Диагностика проблем

### `RuntimeError: Не задан TELEGRAM_TOKEN`

Не экспортирована переменная `TELEGRAM_TOKEN`.

Проверка:

```bash
echo "$TELEGRAM_TOKEN"
```

### `/status` возвращает ошибку Ollama

Проверить, что Ollama запущена:

```bash
curl http://127.0.0.1:11434/api/tags
```

Проверить, что модель скачана:

```bash
ollama list
```

### OCR не работает

Проверить Poppler:

```bash
which pdftoppm
```

Проверить Tesseract:

```bash
which tesseract
tesseract --list-langs
```

Если Homebrew стоит не в `/opt/homebrew`, обновить `POPPLER_PATH` и `TESSERACT_CMD`.

### Голос распознается медленно

Снизить размер модели:

```text
WHISPER_MODEL_SIZE=base
```

Или оставить `small`, но учитывать, что первый voice-запрос будет самым долгим из-за загрузки модели.

## Запуск как сервис

Для постоянной эксплуатации лучше запускать процесс через `launchd`, `systemd`, `supervisord` или Docker. Минимальные требования к сервису:

- автозапуск после перезагрузки;
- рестарт при падении;
- запись stdout/stderr в лог;
- отдельный пользователь без лишних прав;
- отдельный каталог для `.env`;
- лимиты ресурсов для OCR/STT.
