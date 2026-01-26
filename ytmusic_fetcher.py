"""
YouTube Music History Fetcher using ytmusicapi
"""
import os
from typing import Dict, List

from ytmusicapi import YTMusic


class YTMusicFetcher:
    def __init__(self, auth_file: str = "browser.json"):
        """
        Initialize with the path to the authentication file.
        By default, it looks for 'browser.json' in the current directory.
        """
        if not os.path.exists(auth_file):
            raise FileNotFoundError(
                f"Authentication file not found at '{auth_file}'. "
                f"Please make sure the file exists and the path is correct."
            )
        self.ytmusic = YTMusic(auth_file)

    def get_history(self) -> List[Dict[str, str]]:
        """
        Get YouTube Music history.
        Returns list of songs with title, artist, album, and playedAt.
        """
        history = self.ytmusic.get_history()
        songs = []
        for item in history:
            artist_name = ', '.join([artist['name'] for artist in item['artists']]) if item.get('artists') else None
            album_name = item['album']['name'] if item.get('album') else None
            played_at = item.get('played')

            songs.append({
                "title": item['title'],
                "artist": artist_name,
                "album": album_name,
                "playedAt": played_at,
            })
        return songs

def get_ytmusic_history() -> List[Dict[str, str]]:
    """
    Convenience function to get YouTube Music history.

    Returns:
        List of songs with title, artist, album, and playedAt fields
    """
    fetcher = YTMusicFetcher()
    return fetcher.get_history()