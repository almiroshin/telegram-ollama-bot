# Operations

## Local Run

1. Install system dependencies.

macOS:

```bash
brew install ollama poppler tesseract tesseract-lang
```

Linux:

```bash
sudo apt-get update
sudo apt-get install -y poppler-utils tesseract-ocr tesseract-ocr-rus
```

2. Prepare Ollama.

```bash
ollama pull qwen3:8b
ollama serve
```

If Ollama is already running as a service, a separate `ollama serve` process is not required.

3. Prepare the Python environment.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

4. Create `.env`.

```bash
cp .env.example .env
```

At minimum, set:

```text
TELEGRAM_TOKEN=...
```

5. Start the bot.

```bash
set -a
source .env
set +a
python bot.py
```

## Post-Start Check

In Telegram:

```text
/status
```

Expected result:

- `Status: works` or the current localized equivalent from the bot;
- the expected Ollama model;
- correct file and OCR limits;
- correct `POPPLER_PATH` and `TESSERACT_CMD` paths.

Local Ollama check:

```bash
curl http://127.0.0.1:11434/api/tags
```

Tesseract check:

```bash
tesseract --list-langs
```

For the current `OCR_LANG=rus+eng`, the list should contain `rus` and `eng`.

## Environment Variables

### Telegram And LLM

- `TELEGRAM_TOKEN` - required bot token.
- `OLLAMA_URL` - chat endpoint, usually `http://127.0.0.1:11434/api/chat`.
- `OLLAMA_MODEL` - model name, for example `qwen3:8b`, `llama3.1:8b`, or `mistral`.
- `MAX_HISTORY_MESSAGES` - number of recent messages kept in context.

### Voice

- `WHISPER_MODEL_SIZE` - model size: `tiny`, `base`, `small`, `medium`, `large-v3`.
- `WHISPER_DEVICE` - `cpu`, `cuda`, or `auto`.
- `WHISPER_COMPUTE_TYPE` - typically `int8` for CPU and `float16` for GPU.

### Documents And OCR

- `MAX_FILE_SIZE_MB` - incoming file size limit.
- `MAX_DOCUMENT_CHARS` - extracted text limit before sending content to the LLM.
- `OCR_DPI` - PDF rendering quality before OCR.
- `OCR_LANG` - Tesseract languages, for example `rus+eng`.
- `MAX_OCR_PAGES` - maximum PDF pages processed by OCR.
- `POPPLER_PATH` - path to Poppler. Apple Silicon Homebrew usually uses `/opt/homebrew/bin`.
- `TESSERACT_CMD` - path to the Tesseract binary.

## Performance

The most expensive operations are:

- the first `faster-whisper` call, because the model is loaded into memory;
- OCR for scanned PDFs;
- long Ollama requests.

Practical tuning:

- On weak CPUs, keep `WHISPER_MODEL_SIZE=small` and `WHISPER_COMPUTE_TYPE=int8`.
- For faster STT, use a GPU and `WHISPER_COMPUTE_TYPE=float16`.
- If OCR is slow, reduce `MAX_OCR_PAGES` or `OCR_DPI`.
- If Ollama is slow, use a smaller model.

## Security

The current code does not include a Telegram user allowlist. Before running the bot outside a personal environment, add a check for `update.effective_user.id`.

Recommended configuration:

```text
ALLOWED_TELEGRAM_USER_IDS=123,456
```

Expected behavior:

- reject commands and messages from unknown users;
- do not expose configuration to unknown users;
- do not send stack traces or low-level errors to users.

Do not commit `.env`; it is already ignored in [.gitignore](../.gitignore).

## Troubleshooting

### Missing `TELEGRAM_TOKEN`

`TELEGRAM_TOKEN` is not exported.

Check it with:

```bash
echo "$TELEGRAM_TOKEN"
```

### `/status` returns an Ollama error

Check that Ollama is running:

```bash
curl http://127.0.0.1:11434/api/tags
```

Check that the model is available:

```bash
ollama list
```

### OCR Does Not Work

Check Poppler:

```bash
which pdftoppm
```

Check Tesseract:

```bash
which tesseract
tesseract --list-langs
```

If Homebrew is not installed under `/opt/homebrew`, update `POPPLER_PATH` and `TESSERACT_CMD`.

### Voice Transcription Is Slow

Use a smaller model:

```text
WHISPER_MODEL_SIZE=base
```

Or keep `small`, but expect the first voice request to be slower because the model is loaded on demand.

## Running As A Service

For long-running usage, run the process with `launchd`, `systemd`, `supervisord`, or Docker. Minimum service requirements:

- start automatically after reboot;
- restart on failure;
- write stdout/stderr to logs;
- run as a dedicated user with limited privileges;
- keep `.env` in a controlled directory;
- set resource limits for OCR/STT workloads.
