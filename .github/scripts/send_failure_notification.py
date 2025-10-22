#!/usr/bin/env python3
"""
Script to send failure notification to Discord with details from the scrobble job
"""
import os
import requests
import sys


def send_discord_notification():
    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
    if not webhook_url:
        print("Error: DISCORD_WEBHOOK_URL environment variable not set")
        sys.exit(1)
    
    scrobble_log = os.environ.get('SCROBBLE_LOG', 'No log available')
    
    # Check if the failure was due to cookie validation
    failure_reason = "Unknown failure"
    if "YouTube Music cookie validation failed" in scrobble_log or "401 UNAUTHENTICATED" in scrobble_log:
        failure_reason = "YouTube Music cookie is expired or invalid"
    elif "Missing the required __Secure-3PAPISID token" in scrobble_log:
        failure_reason = "YouTube Music cookie is missing required token"
    elif "Failed to validate YouTube Music cookie" in scrobble_log:
        failure_reason = "YouTube Music cookie validation failed"
    elif "Authentication Error" in scrobble_log:
        failure_reason = "Authentication error occurred"
    
    # Prepare the embed message
    embed = {
        "embeds": [
            {
                "title": "❌ YouTube Music Scrobble Sync Failed!",
                "description": f"**Reason:** {failure_reason}",
                "color": 15158332,  # Red color
                "fields": [
                    {
                        "name": "Failure Details",
                        "value": f"```\n{scrobble_log[-1000:]}\n```",  # Truncate to last 1000 chars to avoid Discord limits
                        "inline": False
                    }
                ],
                "footer": {
                    "text": f"Run ID: {os.environ.get('GITHUB_RUN_ID', 'N/A')} | Attempt: {os.environ.get('GITHUB_RUN_ATTEMPT', 'N/A')}"
                },
                "timestamp": __import__('datetime').datetime.utcnow().isoformat()
            }
        ]
    }
    
    try:
        response = requests.post(webhook_url, json=embed)
        response.raise_for_status()
        print("Discord notification sent successfully")
    except requests.exceptions.RequestException as e:
        print(f"Error sending Discord notification: {e}")
        sys.exit(1)


if __name__ == "__main__":
    send_discord_notification()