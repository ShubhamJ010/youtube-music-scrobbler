#!/usr/bin/env python3
"""
Notification utility module for sending Discord notifications
about scrobbling results.
"""
import os
import requests


def send_success_notification(
    history_count: int,
    today_count: int,
    existing_count: int,
    to_scrobble_count: int,
    scrobbled_count: int,
    failed_count: int,
    failed_songs: list = None
):
    """
    Send a Discord notification for successful scrobbling.
    
    Only sends notification if there were actual songs to scrobble (to_scrobble_count > 0).
    
    Args:
        history_count: Total number of songs in history
        today_count: Number of songs played today
        existing_count: Number of songs already in database
        to_scrobble_count: Number of songs that needed to be scrobbled
        scrobbled_count: Number of songs successfully scrobbled
        failed_count: Number of songs that failed to scrobble
        failed_songs: List of song names that failed (optional)
    """
    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
    if not webhook_url:
        print("DISCORD_WEBHOOK_URL not set. Skipping notification.")
        return

    # Only send notification if there were songs to scrobble
    if to_scrobble_count == 0:
        print("No songs to scrobble. Skipping Discord notification.")
        return

    # Build the log summary
    log_lines = [
        "🎵 YouTube Music Last.fm Scrobbler",
        "🎵 Fetching YouTube Music history...",
        f"📋 History: {history_count} | Today: {today_count} | Existing: {existing_count} | To Scrobble: {to_scrobble_count}",
        "",
        "=" * 60,
        f"📊 SUMMARY: Processed: {today_count}, Success: {scrobbled_count}, Failed: {failed_count}",
        "=" * 60,
        "🎉 Completed successfully!"
    ]

    log = "\n".join(log_lines)

    # Discord has a 2000 character limit for embed descriptions
    if len(log) > 1980:
        log = log[:1980] + "\n... (log truncated)"

    # Add failed songs if any
    fields = []
    if failed_songs and len(failed_songs) > 0:
        failed_text = "\n".join([f"• {song}" for song in failed_songs[:10]])
        if len(failed_songs) > 10:
            failed_text += f"\n... and {len(failed_songs) - 10} more"
        fields.append({
            "name": "❌ Failed Songs",
            "value": failed_text,
            "inline": False
        })

    payload = {
        "content": "YouTube Music Scrobble Sync succeeded!",
        "embeds": [{
            "title": "Scrobble Log",
            "description": f"```\n{log}\n```",
            "fields": fields if fields else None,
            "color": 3066993  # Green color for success
        }]
    }

    # Remove None values from embeds
    if payload["embeds"][0]["fields"] is None:
        del payload["embeds"][0]["fields"]

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
