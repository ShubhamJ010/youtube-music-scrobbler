# Handoff: Scrobble Deduplication Feature

## Problem
Songs scrobbled by external sources (Pan Scrobble, etc.) were being duplicated when the YouTube Music Scrobbler ran its daily schedule.

## Solution Implemented
**Play-count based deduplication** — if an external source already scrobbled a song today, skip it in the scheduled run.

## Core Logic
1. **Single API call** to Last.fm `user.getRecentTracks` with `from`/`to` params (today's range, UTC)
2. **Client-side filtering** by track + artist (case-insensitive)
3. **Play-count matching**: For each song occurrence in history:
   - Query external scrobble count for that song today
   - If `play_number > external_count` → SCROBBLE (not captured externally)
   - If `play_number <= external_count` → SKIP (already captured externally)
4. **Discord footer** shows skipped count: `> GitHub Actions sync • 7 successful • 3 skipped • 1 loved • 7 scrobbled`

## Files Modified

| File | Change |
|------|--------|
| `scrobble_utils.py` | Added `get_all_today_scrobbles()`, `count_external_scrobbles()`, `check_existing_scrobble()` methods; Added play_number tracking in `detect_songs_to_scrobble()` |
| `start_ytm_scobble.py` | Fetch scrobbles once at start, integrate duplicate check before each scrobble, track skip count |
| `lastpy/__init__.py` | Added `get_recent_tracks()` function |
| `notifications.py` | Added `skipped_count` parameter to `build_sync_footer_text()` and `send_success_notification()` |
| `.env.example` | Added `LASTFM_USERNAME` environment variable |
| `.github/workflows/sync-dev.yml` | New dev dry-run workflow (triggers on push to dev, manual, or after production run) |

## Key Decisions Made
- **No schema changes** — dedup is real-time API query, not stored data
- **No backwards compatibility** needed (user confirmed)
- **Single query approach** — avoids rate limiting (was initially per-song query, fixed to single API call)
- **Valid API params only** — `track`/`artist` are NOT valid params for `user.getRecentTracks`, removed
- **Play numbers assigned chronologically** — oldest = 1, iterates history in reverse to assign

## API Reference
Last.fm `user.getRecentTracks` valid parameters:
- `user` (required), `api_key` (required)
- `limit` (optional, max 200)
- `from` (optional, Unix timestamp UTC)
- `to` (optional, Unix timestamp UTC)
- `page`, `extended`

**NOT valid**: `track`, `artist` — filtering must be done client-side.

## Verified
Dry run tested with real data: 29 songs processed, 3 correctly skipped (external), 7 correctly scrobbled (no external).

## Status
- PR #19 merged to `master`
- Verbose logs cleaned for production (only summary line remains)
- Dev workflow with dry-run mode ready for testing

## Environment Variables
```
LASTFM_USERNAME=your_last_fm_username  # NEW - auto-extracted from session on first auth
```

## Testing
- Dev workflow runs in `--dry-run` mode (no scrobbles sent, no DB updates)
- Trigger via: push to `dev`, manual dispatch, or after production workflow completes
