# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python script that fetches YouTube Music listening history from the last 24 hours and scrobbles it to Last.fm. The application has been completely rewritten to eliminate the YTMusic API dependency and includes significant improvements in multilingual support, timestamp distribution, and error handling.

## Environment Setup

The project uses conda for environment management:

```bash
# Create and activate environment
conda env create -f environment.yml
conda activate ytmusic-scrobbler

# Alternative for pip-only setup
pip install -r requirements.txt
```

## Authentication Setup

1. **YouTube Music Auth**: The script uses an encrypted auth file:
   - Run `ytmusicapi browser` to create `browser.json`
   - Run `python encrypt_auth.py` to create `browser.json.enc`
   - Set `YTMUSIC_AUTH_KEY` in `.env` with the generated key

2. **Last.fm API Setup**: Create `.env` file with:
   ```
   LAST_FM_API=YOUR_LASTFM_API_KEY
   LAST_FM_API_SECRET=YOUR_LASTFM_API_SECRET
   ```

3. **First Run**: The script will open a browser for Last.fm OAuth and create `LASTFM_SESSION` in `.env` for subsequent runs

## Running the Application

```bash
python start_ytm_scobble.py
```

The standalone version includes:
- No YTMusic API dependency (direct HTML scraping)
- Multilingual date detection (50+ languages)
- Smart timestamp distribution
- Better error handling
- Improved position tracking

## Code Architecture

- **Single-file application**: `start.py` contains all logic
- **Process class**: Main application logic with methods:
  - `get_token()`: Handles Last.fm OAuth flow via local web server (port 5588)
  - `get_session()`: Converts OAuth token to session key
  - `execute()`: Main processing logic
- **SQLite database**: `data.db` tracks scrobbled songs to prevent duplicates
- **Authentication flow**: Uses `TokenHandler` and `TokenServer` for OAuth callback handling

## Key Dependencies

- `ytmusicapi`: YouTube Music API client
- `lastpy`: Last.fm scrobbling (custom library, not in requirements)
- `python-dotenv`: Environment variable management
- `sqlite3`: Built-in SQLite support

## Database Schema

```sql
CREATE TABLE scrobbles (
    id INTEGER PRIMARY KEY,
    track_name TEXT,
    artist_name TEXT,
    album_name TEXT,
    scrobbled_at TEXT DEFAULT CURRENT_TIMESTAMP,
    array_position INTEGER
)
```

## Important Files

- `start_ytm_scobble.py`: Main application script
- `browser.json.enc`: Encrypted YouTube Music authentication
- `.env`: API keys and session tokens
- `data.db`: SQLite database for tracking scrobbles
- `encrypt_auth.py`: Utility for encrypting browser.json
- `ytmusic_fetcher.py`: History fetching logic

## Scrobbling Logic

The application processes YouTube Music history by:
1. Fetching history and filtering "Today" tracks
2. Cleaning local database to match current day's tracks
3. Identifying new/updated tracks based on array position
4. Scrobbling to Last.fm with artificial timestamps (90-second intervals)
5. Skipping artists ending with "- Topic"
6. Using track name as album name when album is missing