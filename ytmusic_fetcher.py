"""
YouTube Music History Fetcher using ytmusicapi
"""
import os
import json
from typing import Dict, List
from cryptography.fernet import Fernet
from ytmusicapi import YTMusic


class YTMusicFetcher:
    def __init__(self, auth_file: str = "browser.json", enc_auth_file: str = "browser.json.enc"):
        """
        Initialize with the path to the authentication file.
        Priority:
        1. Decrypt enc_auth_file using YTMUSIC_AUTH_KEY environment variable.
        2. Use local auth_file (browser.json).
        """
        auth_key = os.environ.get("YTMUSIC_AUTH_KEY")
        
        if auth_key and os.path.exists(enc_auth_file):
            try:
                fernet = Fernet(auth_key.encode())
                with open(enc_auth_file, "rb") as f:
                    encrypted_data = f.read()
                
                decrypted_data = fernet.decrypt(encrypted_data)
                auth_data = json.loads(decrypted_data)
                
                # ytmusicapi can take the dict directly
                self.ytmusic = YTMusic(auth_data)
                return
            except Exception as e:
                print(f"Error decrypting {enc_auth_file}: {e}")
                print("Falling back to local auth file...")

        if not os.path.exists(auth_file):
            raise FileNotFoundError(
                f"Authentication file not found at '{auth_file}' and no valid "
                f"encrypted file/key found. Please make sure one exists."
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