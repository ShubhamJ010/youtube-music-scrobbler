#!/usr/bin/env python3
"""
Notification utility module for sending Discord notifications
about scrobbling results.
"""
import os
import requests
from datetime import datetime, timedelta


def send_success_notification(
    history_count: int,
    today_count: int,
    existing_count: int,
    to_scrobble_count: int,
    scrobbled_count: int,
    failed_count: int,
    failed_songs: list = None,
    scrobbled_songs: list = None
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
    """
    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
    if not webhook_url:
        print("DISCORD_WEBHOOK_URL not set. Skipping notification.")
        return

    # Only send notification if there were successful scrobbles
    if scrobbled_count == 0:
        print("No songs were successfully scrobbled. Skipping Discord notification.")
        return

    # Generate session time (last 30 minutes)
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(minutes=30)
    session_time = f"Session time: **{start_time.strftime('%Y-%m-%d %H:%M')} – {end_time.strftime('%H:%M')} UTC**"

    # Determine color based on failed count
    # AMBER (16776960) if there are failures, GREEN (3066993) if all successful
    color = 16776960 if failed_count > 0 else 3066993

    # Build fields
    fields = []

    # History field
    fields.append({
        "name": "History (Last 4 Weeks)",
        "value": f"Total tracks: **{history_count}**",
        "inline": False
    })

    # Today field
    today_value = f"Discovered: **{today_count}**\nScrobbled: **{scrobbled_count}**\nFailed: **{failed_count}**"
    fields.append({
        "name": "Today",
        "value": today_value,
        "inline": False
    })

    # Scrobbled This Session field
    if scrobbled_songs and len(scrobbled_songs) > 0:
        scrobbled_text = "\n".join([f"{i+1}. {song}" for i, song in enumerate(scrobbled_songs)])
        fields.append({
            "name": "Scrobbled This Session",
            "value": scrobbled_text,
            "inline": False
        })

    # Failure Detected field (only if there are failures)
    if failed_songs and len(failed_songs) > 0:
        failed_text = "Failed scrobbles:\n" + "\n".join([f"{i+1}. {song}" for i, song in enumerate(failed_songs)])
        fields.append({
            "name": "Failure Detected",
            "value": failed_text,
            "inline": False
        })

    payload = {
        "embeds": [{
            "title": "Scrobble Report",
            "description": session_time,
            "fields": fields,
            "color": color,
            "footer": {
                "text": "Automated scrobble sync (30-minute interval using GitHub Actions)"
            }
        }]
    }

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
