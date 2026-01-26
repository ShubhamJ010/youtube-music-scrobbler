"""
YouTube Music History Fetcher using ytmusicapi
"""
from typing import Dict, List
from ytmusicapi import YTMusic
import os

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
            # The 'artists' key can be a list of artists. We'll join them.
            # The old implementation only returned one artist.
            artist_name = ', '.join([artist['name'] for artist in item['artists']]) if item['artists'] else None

            # The 'album' key might be missing for some tracks.
            album_name = item['album']['name'] if item['album'] else None
            
            # The 'played' key is not always present
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
