#!/usr/bin/env python
import os
import json
import requests
from datetime import datetime

def main():
    notification_data_str = os.environ.get("NOTIFICATION_DATA")
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")

    if not webhook_url:
        print("DISCORD_WEBHOOK_URL not set. Skipping notification.")
        return

    if not notification_data_str:
        print("NOTIFICATION_DATA not set. Skipping notification.")
        return

    try:
        data = json.loads(notification_data_str)
    except json.JSONDecodeError:
        print("Failed to decode notification data JSON. Skipping notification.")
        return

    total_scrobbled = data.get("total_songs_scrobbled", 0)
    total_listening_time = data.get("total_listening_time", "00:00:00")
    top_artist = data.get("top_artist", "N/A")
    top_album = data.get("top_album", "N/A")
    scrobbled_songs = data.get("scrobbled_songs", [])

    embed = {
        "title": "🎶 YouTube Music Scrobble Report",
        "description": f"**{total_scrobbled}** songs scrobbled successfully!",
        "color": 0x00FF00,  # Green
        "fields": [
            {
                "name": "Total Listening Time",
                "value": total_listening_time,
                "inline": True
            },
            {
                "name": "Top Artist",
                "value": top_artist,
                "inline": True
            },
            {
                "name": "Top Album",
                "value": top_album,
                "inline": True
            }
        ],
        "footer": {
            "text": f"Scrobble Report - {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
        }
    }

    if scrobbled_songs:
        # Group songs by playedAt
        songs_by_time = {}
        for song in scrobbled_songs:
            played_at = song.get('playedAt', 'Unknown Time')
            if played_at not in songs_by_time:
                songs_by_time[played_at] = []
            songs_by_time[played_at].append(song)

        for played_at, songs in songs_by_time.items():
            song_list = ""
            for song in songs[:10]: # Limit to 10 songs per group to avoid huge messages
                title = song.get('title', 'Unknown Title')
                artist = song.get('artist', 'Unknown Artist')
                duration = song.get('duration', 'N/A')
                song_list += f"**{title}** by {artist} ({duration})\n"
            
            if len(songs) > 10:
                song_list += f"\n... and {len(songs) - 10} more."

            embed["fields"].append({
                "name": f"Listened at {played_at}",
                "value": song_list,
                "inline": False
            })


    payload = {
        "content": "YouTube Music Scrobble Sync succeeded!",
        "embeds": [embed]
    }

    try:
        response = requests.post(webhook_url, json=payload)
        response.raise_for_status()
        print("Successfully sent Discord notification.")
    except requests.exceptions.RequestException as e:
        print(f"Failed to send Discord notification: {e}")
        exit(1)

if __name__ == "__main__":
    main()