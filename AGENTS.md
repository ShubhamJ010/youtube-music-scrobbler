# AGENTS.md

This file provides guidance for AI agents (Gemini, Claude, etc.) when working with code in this repository.

## Project Overview

YouTube Music Scrobbler is a Python application that fetches your YouTube Music listening history and scrobbles it to Last.fm. It features smart duplicate detection, encryption for security, and can be automated via GitHub Actions.

## Environment Setup

The project uses a Python environment (managed via `venv` or `conda`):

```bash
# Setup with pip
python -m venv .venv
source .venv/bin/activate  # Or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

## Authentication & Configuration

1. **Last.fm API**: Obtain an API Key and Secret from [Last.fm API](https://www.last.fm/api/account/create).
2. **YouTube Music Auth**:
   - Install `ytmusicapi` globally or in your env.
   - Run `ytmusicapi browser` and follow instructions to create `browser.json`.
   - Run `python encrypt_auth.py` to encrypt it.
   - Save the outputted key as `YTMUSIC_AUTH_KEY` in `.env`.
3. **Environment Variables**: Use `.env.example` as a template for `.env`.

## Core Components

- `start_ytm_scobble.py`: Main entry point. Handles Last.fm OAuth and orchestrates the scrobbling process.
- `ytmusic_fetcher.py`: Handles fetching history from YouTube Music.
- `scrobble_utils.py`: Contains `SmartScrobbler` and `PositionTracker` for intelligent scrobbling logic.
- `encrypt_auth.py`: Utility to encrypt `browser.json` into `browser.json.enc`.
- `data.db`: SQLite database to track scrobble positions and prevent duplicates.

## Database Schema

```sql
CREATE TABLE IF NOT EXISTS scrobbles (
    id INTEGER PRIMARY KEY,
    track_name TEXT,
    artist_name TEXT,
    album_name TEXT,
    scrobbled_at TEXT DEFAULT CURRENT_TIMESTAMP,
    array_position INTEGER,
    max_array_position INTEGER,
    is_first_time_scrobble BOOLEAN DEFAULT FALSE
)
```

## Scrobbling Logic

The application uses a "Position Tracking" system:
- It tracks the position of songs in your "Today" history.
- If a song's position increases or a new song appears, it triggers a scrobble.
- This handles cases where songs are re-played or the history is updated.
- **Timestamp Generation**: It uses artificial timestamps (90-second intervals) to ensure songs are scrobbled in the correct order, as YouTube Music history doesn't provide exact play times.
- **Filtering**: It filters for songs played today using `date_detection.py`.

## GitHub Actions Integration

The workflow in `.github/workflows/sync.yml` automates the scrobbling every 30 minutes. It uses GitHub Secrets for all sensitive keys and relies on `browser.json.enc` committed to the repo.

## Best Practices for Agents

- Always verify `data.db` schema if making changes to the tracking logic.
- Use `encrypt_auth.py` for handling YouTube Music credentials.
- Ensure any new features are reflected in both local and GitHub Action environments.
- Refer to `GITHUB_ACTIONS_GUIDE.md` for CI/CD related changes.
