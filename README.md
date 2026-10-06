# ARIA — Personal AI Assistant

ARIA is a local Python AI-assistant backend with persistent memory, chat history, sessions, safe local tools, retries, logging, and Responses API function calling.

## Requirements

- Python 3.11+
- An API key for a compatible Responses API endpoint

## Setup

1. Copy `.env.example` to `.env`.
2. Copy `.env.example` to `.env` and set `OPENAI_API_KEY`. ARIA includes a small dependency-free `.env` loader.
3. Run:

```bash
python aria.py
```

## Tests

```bash
python -m unittest discover -s tests -v
```

## Commands

- `yardım`
- `hafıza`
- `ara <kelime>`
- `hatırla anahtar: değer`
- `unut <kelime>`
- `hafızayı temizle`
- `geçmişi temizle`
- `yeni sohbet`
- `sohbetler`
- `araçlar`
- `durum`
- `çıkış`

Normal language requests can trigger tools automatically. Current tools are calculator, date/time, memory search/save/forget, and basic system information.

## Architecture

The core is intentionally separated from voice and GUI layers. Voice and GUI can later call the same `ask_ai()` backend without rewriting memory, history, tools, or security.
