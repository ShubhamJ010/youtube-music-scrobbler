"""
YouTube Music History Fetcher using ytmusicapi
"""
import os
import json
from typing import Dict, List, Set, Tuple
from cryptography.fernet import Fernet
from ytmusicapi import YTMusic
from song_matching import normalize_song_key


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

    def get_liked_song_keys(self, limit: int = 5000) -> Set[Tuple[str, str]]:
        """
        Return normalized (title, artist) pairs from the user's liked songs.
        """
        liked_song_keys: Set[Tuple[str, str]] = set()
        liked_payload = self.ytmusic.get_liked_songs(limit=limit)
        tracks = liked_payload.get("tracks", []) if isinstance(liked_payload, dict) else []

        for item in tracks:
            title = item.get("title")
            artists = item.get("artists") or []
            artist_name = ", ".join([artist.get("name", "") for artist in artists if artist.get("name")]).strip()

            if not title or not artist_name:
                continue

            liked_song_keys.add(normalize_song_key(title, artist_name))

        return liked_song_keys

def get_ytmusic_history() -> List[Dict[str, str]]:
    """
    Convenience function to get YouTube Music history.

    Returns:
        List of songs with title, artist, album, and playedAt fields
    """
    fetcher = YTMusicFetcher()
    return fetcher.get_history()


def get_ytmusic_liked_song_keys(limit: int = 5000) -> Set[Tuple[str, str]]:
    """
    Convenience function to get normalized liked song keys from YouTube Music.
    """
    fetcher = YTMusicFetcher()
    return fetcher.get_liked_song_keys(limit=limit)
