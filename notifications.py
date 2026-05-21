#!/usr/bin/env python3
"""
Notification utility module for sending Discord notifications
about scrobbling results.
"""
import os
import requests
from datetime import datetime


def build_sync_footer_text(
    successful_count: int,
    failed_count: int,
    loved_count: int,
    scrobbled_count: int
) -> str:
    """Build a compact footer summary for Discord reports."""
    footer_parts = ["GitHub Actions sync", f"{successful_count} successful"]
    if failed_count > 0:
        footer_parts.append(f"{failed_count} failed")
    footer_parts.append(f"{loved_count} loved")
    footer_parts.append(f"{scrobbled_count} scrobbled")
    return " • ".join(footer_parts)


def send_success_notification(
    history_count: int,
    today_count: int,
    existing_count: int,
    to_scrobble_count: int,
    scrobbled_count: int,
    failed_count: int,
    failed_songs: list = None,
    scrobbled_songs: list = None,
    loved_count: int = 0,
    loved_songs: list = None,
    love_failed_count: int = 0,
    love_failed_songs: list = None,
    unique_artist_count: int = 0,
    unique_album_count: int = 0
):
    """
    Send a Discord notification for successful scrobbling.

    Only sends notification if there were actual successful scrobbles (scrobbled_count > 0).

    Args:
        history_count: Total number of songs in history
        today_count: Number of songs played today
        existing_count: Number of songs already in database
        to_scrobble_count: Number of songs that needed to be scrobbled
        scrobbled_count: Number of songs successfully scrobbled
        failed_count: Number of songs that failed to scrobble
        failed_songs: List of song names that failed (optional)
        scrobbled_songs: List of successfully scrobbled songs (optional)
        loved_count: Number of successfully loved tracks on Last.fm
        loved_songs: List of successfully loved tracks on Last.fm
        love_failed_count: Number of failed Last.fm love attempts
        love_failed_songs: List of songs that failed to be loved (optional)
        unique_artist_count: Unique artists from today's songs
        unique_album_count: Unique albums from today's songs
    """
    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
    if not webhook_url:
        print("DISCORD_WEBHOOK_URL not set. Skipping notification.")
        return

    # Only send notification if there were successful scrobbles
    if scrobbled_count == 0:
        print("No songs were successfully scrobbled. Skipping Discord notification.")
        return

    footer_text = build_sync_footer_text(
        successful_count=scrobbled_count,
        failed_count=failed_count,
        loved_count=loved_count,
        scrobbled_count=scrobbled_count
    )
    now = datetime.utcnow()
    day = now.day
    if day % 10 == 1 and day != 11:
        ordinal = "st"
    elif day % 10 == 2 and day != 12:
        ordinal = "nd"
    elif day % 10 == 3 and day != 13:
        ordinal = "rd"
    else:
        ordinal = "th"
    title_date = f"{day}{ordinal} {now.strftime('%b')} '{now.strftime('%y')}"

    estimated_minutes = scrobbled_count * 4
    listening_hours = estimated_minutes // 60
    listening_mins = estimated_minutes % 60
    listening_value = f"{listening_hours}h {listening_mins}m"

    liked_today_lines = []
    if loved_songs:
        max_items = 5
        liked_today_lines.extend([f"- {song}" for song in loved_songs[:max_items]])
        if len(loved_songs) > max_items:
            liked_today_lines.append(f"- +{len(loved_songs) - max_items} more")
    else:
        liked_today_lines.append("- None")

    highlights = []
    highlights.append(f"- Most Played Scope — {unique_artist_count} artists")
    highlights.append(f"- Collection Scope — {unique_album_count} albums")

    body_lines = [
        f"# Scrobble Report — {title_date}",
        "```txt",
        f"Scrobbled    {scrobbled_count} tracks",
        f"Listening    {listening_value}",
        f"Artists      {unique_artist_count}",
        f"Albums       {unique_album_count}",
        "```",
        "## Liked Today",
        *liked_today_lines,
        "## Highlights",
        *highlights,
    ]
    if love_failed_count > 0 and love_failed_songs:
        body_lines.append("## Love Failures")
        body_lines.extend([f"- {song}" for song in love_failed_songs[:10]])
        if len(love_failed_songs) > 10:
            body_lines.append(f"- +{len(love_failed_songs) - 10} more")

    body_lines.append("")
    body_lines.append(f"> {footer_text}")

    payload = {"content": "\n".join(body_lines)}

    try:
        response = requests.post(webhook_url, json=payload)
        response.raise_for_status()
        print("Successfully sent Discord notification.")
    except requests.exceptions.RequestException as e:
        print(f"Failed to send Discord notification: {e}")


def send_failure_notification(error_message: str = None):
    """
    Send a Discord notification for failed scrobbling.

    This is a simplified version that can be called from the main script
    when an exception occurs.

    Args:
        error_message: Optional error message to include in the notification
    """
    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
    if not webhook_url:
        print("DISCORD_WEBHOOK_URL not set. Skipping failure notification.")
        return

    failure_reason = "❌ YouTube Music Scrobble Sync Failed!"
    if error_message:
        failure_reason += f"\n\nError: {error_message}"

    payload = {
        "content": failure_reason,
        "embeds": [{
            "title": "Scrobble Failed",
            "description": "Check the GitHub Actions logs for more details.",
            "color": 15105570  # Orange color for failure
        }]
    }

    try:
        response = requests.post(webhook_url, json=payload)
        response.raise_for_status()
        print("Successfully sent failure Discord notification.")
    except requests.exceptions.RequestException as e:
        print(f"Failed to send Discord notification: {e}")
