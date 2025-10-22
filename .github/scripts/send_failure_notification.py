#!/usr/bin/env python3
"""
Script to send failure notification to Discord with details from the scrobble job
"""
import os
import requests
import sys
from datetime import datetime


def send_discord_notification():
    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
    if not webhook_url:
        print("Error: DISCORD_WEBHOOK_URL environment variable not set")
        sys.exit(1)
    
    scrobble_log = os.environ.get('SCROBBLE_LOG', 'No log available')
    
    # Analyze the log to determine failure reason and provide specific guidance
    failure_reason = "Unknown failure"
    resolution_steps = ""
    color = 15158332  # Default red color for errors
    
    # Check for specific error patterns in the log
    if "YouTube Music cookie validation failed" in scrobble_log or "401 UNAUTHENTICATED" in scrobble_log or "cookie appears to be expired" in scrobble_log:
        failure_reason = "❌ YouTube Music cookie is expired or invalid"
        resolution_steps = (
            "**Resolution:**\n"
            "1. Sign in to YouTube Music: https://music.youtube.com\n"
            "2. Open Developer Tools (F12)\n"
            "3. Go to Network tab\n"
            "4. Refresh the page and find any request to music.youtube.com\n"
            "5. Copy the 'Cookie' header value\n"
            "6. Update the YTMUSIC_COOKIE in your GitHub repository secrets"
        )
        color = 15105570  # Orange color for authentication issues
    elif "Missing the required __Secure-3PAPISID token" in scrobble_log:
        failure_reason = "❌ YouTube Music cookie is missing required token"
        resolution_steps = (
            "**Resolution:**\n"
            "1. Ensure you're copying the complete cookie from YouTube Music\n"
            "2. The cookie must contain '__Secure-3PAPISID=' token\n"
            "3. Update the YTMUSIC_COOKIE in your GitHub repository secrets"
        )
        color = 15105570  # Orange color for authentication issues
    elif "Authentication Error" in scrobble_log:
        failure_reason = "❌ Authentication error occurred"
        resolution_steps = (
            "**Resolution:**\n"
            "1. Check YouTube Music authentication status\n"
            "2. Ensure the cookie is properly formatted with '__Secure-3PAPISID'\n"
            "3. Update the YTMUSIC_COOKIE in your GitHub repository secrets"
        )
        color = 15105570  # Orange color for authentication issues
    elif "Failed to validate YouTube Music cookie" in scrobble_log:
        failure_reason = "❌ YouTube Music cookie validation failed"
        resolution_steps = (
            "**Resolution:**\n"
            "1. Verify your YouTube Music account is active\n"
            "2. Get a fresh cookie from YouTube Music\n"
            "3. Update the YTMUSIC_COOKIE in your GitHub repository secrets"
        )
        color = 15105570  # Orange color for authentication issues
    elif "LASTFM" in scrobble_log.upper() or "last.fm" in scrobble_log.lower():
        failure_reason = "❌ Last.fm authentication or scrobbling issue"
        resolution_steps = (
            "**Resolution:**\n"
            "1. Verify Last.fm API credentials are correct\n"
            "2. Check LAST_FM_API, LAST_FM_API_SECRET, and LASTFM_SESSION in GitHub secrets\n"
            "3. Regenerate Last.fm session if needed"
        )
        color = 16753920  # Yellow color for service issues
    elif "network" in scrobble_log.lower() or "timeout" in scrobble_log.lower() or "connection" in scrobble_log.lower():
        failure_reason = "⚠️ Network or connection error"
        resolution_steps = (
            "**Resolution:**\n"
            "This may be a temporary issue. The workflow will retry automatically.\n"
            "No action required unless this persists."
        )
        color = 16763904  # Yellow color for warnings
    elif scrobble_log.strip() == "No log available" or "Error: Process completed with exit code 1" in scrobble_log:
        # Special handling for minimal logs (which seems to happen in GitHub Actions)
        failure_reason = "❌ Script execution failed - likely cookie authentication issue"
        resolution_steps = (
            "**Resolution:**\n"
            "The most common cause is an expired YouTube Music cookie.\n\n"
            "**Steps to fix:**\n"
            "1. Sign in to YouTube Music: https://music.youtube.com\n"
            "2. Open Developer Tools (F12)\n"
            "3. Go to Network tab\n"
            "4. Refresh the page and find any request to music.youtube.com\n"
            "5. Copy the 'Cookie' header value\n"
            "6. Update the YTMUSIC_COOKIE in your GitHub repository secrets"
        )
        color = 15105570  # Orange for authentication issues
    else:
        failure_reason = "⚠️ General failure occurred"
        resolution_steps = (
            "**Resolution:**\n"
            "Check the logs below for more details.\n"
            "If issue persists, review GitHub secrets and service availability."
        )
        color = 8421504   # Gray color for general issues
    
    # Prepare the embed message
    embed = {
        "embeds": [
            {
                "title": "❌ YouTube Music Scrobble Sync Failed!",
                "description": failure_reason,
                "color": color,
                "fields": [
                    {
                        "name": "📋 Details",
                        "value": resolution_steps,
                        "inline": False
                    },
                    {
                        "name": "🔍 Failure Logs",
                        "value": f"```\n{scrobble_log[-800:] if len(scrobble_log) > 800 else scrobble_log}\n```",  # Truncate to avoid Discord limits
                        "inline": False
                    }
                ],
                "footer": {
                    "text": f"Run ID: {os.environ.get('GITHUB_RUN_ID', 'N/A')} | Attempt: {os.environ.get('GITHUB_RUN_ATTEMPT', 'N/A')} | {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
                },
                "timestamp": datetime.utcnow().isoformat()
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