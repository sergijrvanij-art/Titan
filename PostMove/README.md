# PostMove

Production-ready async Telegram automation system powered by **Telethon** (userbot) and **Aiogram 3** (admin bot).

## Features

- Async userbot for channel parsing and transfer
- Admin panel entirely in Telegram
- SQLite with migrations + repositories
- Priority queue with retries, DLQ, rate limiting
- Content processing pipeline (replacers, deny words, formatting, buttons)
- Media processing service with temp cleanup
- Structured logging + live log stream + telemetry
- Parser engine with workers, cache, checkpoints
- Transfer service with resume/checkpoints and anti-duplicate
- Security layer (admin guard, audit actions)
- AI modules (moderation, fake detection, sentiment, categorization, summary/title)
- Graceful shutdown, auto reconnect, config live reload, module supervisor

## Project layout

```
PostMove/
├── ai/
├── bot/
├── core/
├── database/
├── logging/
├── media/
├── parsers/
├── processing/
├── queue/
├── security/
├── settings/
├── telemetry/
├── transfer/
├── userbot/
├── config.py
├── config.json
├── .env
├── main.py
└── requirements.txt
```

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r PostMove/requirements.txt
cp PostMove/.env .env
# edit PostMove/config.json and .env
python -m PostMove.main
```

> Use `python -m PostMove.main` to avoid name collisions with stdlib modules.

## Admin bot commands

- `/start` – control panel
- `/channels` – channel list
- `/transfer` – transfer controls
- `/parsers` – parser controls
- `/settings` – runtime settings
- `/logs` – live/export logs
- `/runtime` – runtime metrics

## Notes

- Keep the userbot account joined to source and target channels.
- Reactions are applied to discussion comments, not the channel post itself.
- Queue checkpoints and transfer state are persisted in SQLite to resume after restarts.
