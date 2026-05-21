#!/usr/bin/env python3
"""
Notification utility module for sending Discord notifications
about scrobbling results.
"""
import os
import requests
from datetime import UTC, datetime
from typing import Mapping, Optional


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


def format_report_date(now_utc: datetime) -> str:
    """Format date as `12th May '27`."""
    day = now_utc.day
    if day % 10 == 1 and day != 11:
        ordinal = "st"
    elif day % 10 == 2 and day != 12:
        ordinal = "nd"
    elif day % 10 == 3 and day != 13:
        ordinal = "rd"
    else:
        ordinal = "th"
    return f"{day}{ordinal} {now_utc.strftime('%b')} '{now_utc.strftime('%y')}"


def format_listening_duration(total_minutes: int) -> str:
    """Format minute duration as `Xh Ym`."""
    listening_hours = total_minutes // 60
    listening_mins = total_minutes % 60
    return f"{listening_hours}h {listening_mins}m"


def extract_flow_minutes(flow: Optional[Mapping[str, int]]) -> tuple[int, int, int]:
    """Get Evening, Afternoon, Late Night minutes with safe defaults."""
    flow = flow or {}
    return (
        int(flow.get("Evening", 0)),
        int(flow.get("Afternoon", 0)),
        int(flow.get("Late Night", 0)),
    )


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
    unique_album_count: int = 0,
    listening_flow_minutes: Optional[Mapping[str, int]] = None,
    most_played_artist: str = "Unknown",
    longest_streak_tracks: int = 0,
    longest_streak_minutes: int = 0,
    report_now: Optional[datetime] = None
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
        listening_flow_minutes: Approx minute distribution across dayparts
        most_played_artist: Most frequently played artist today
        longest_streak_tracks: Longest contiguous streak in today's sequence
        longest_streak_minutes: Duration of longest streak in minutes
        report_now: timezone-aware datetime to use for report date
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
    now = report_now or datetime.now(UTC)
    title_date = format_report_date(now)

    estimated_minutes = scrobbled_count * 4
    listening_value = format_listening_duration(estimated_minutes)

    liked_today_lines = []
    if loved_songs:
        max_items = 5
        liked_today_lines.extend([f"- {song}" for song in loved_songs[:max_items]])
        if len(loved_songs) > max_items:
            liked_today_lines.append(f"- +{len(loved_songs) - max_items} more")
    else:
        liked_today_lines.append("- None")

    evening_minutes, afternoon_minutes, late_night_minutes = extract_flow_minutes(listening_flow_minutes)

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
        "## Listening Flow",
        f"- Evening • {evening_minutes}m",
        f"- Afternoon • {afternoon_minutes}m",
        f"- Late Night • {late_night_minutes}m",
        "## Highlights",
        f"- Longest Streak — {longest_streak_tracks} tracks • {longest_streak_minutes}m",
        f"- Most Played — {most_played_artist}",
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
