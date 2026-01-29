"""
Smart scrobbling utilities with improved timestamp distribution and error handling
Based on ytmusic-scrobbler-web worker implementation
"""
import time
import math
import re
from enum import Enum
from typing import Dict, List, Optional
import hashlib
import xml.etree.ElementTree as ET
import lastpy


class FailureType(Enum):
    AUTH = "AUTH"
    NETWORK = "NETWORK"
    TEMPORARY = "TEMPORARY"  # For 503, rate limits, and other temporary issues
    LASTFM = "LASTFM"
    UNKNOWN = "UNKNOWN"


def clean_metadata(text: str) -> str:
    """
    The 'Nuclear Option' for metadata cleaning.
    Aggressively strips marketing, video, and version tags to ensure
    Last.fm stats aggregate to the correct 'Master' track.
    """
    if not text:
        return ""
        
    # 1. Decode generic YouTube junk first
    # Remove " - Topic" (common on auto-generated artist channels)
    text = re.sub(r'(?i)\s+-\s+Topic$', '', text)
    
    # 2. Define removal patterns
    # We use (?i) for case-insensitivity.
    patterns = [
        # --- VIDEO GARBAGE ---
        # (Official Video), [Official Audio], (Lyrics), (Visualizer), (MV), (Music Video)
        # Also catches technical specs like [4K], [HQ], [HD]
        r'(?i)\s*[\(\[](?:official\s*)?(music\s*)?(video|audio|lyrics|visualizer|clip|mv|hq|hd|4k|1080p)(?:.*?)?[\)\]]',

        # --- MARKETING / EDITIONS ---
        # (2011 Remaster), [Deluxe Edition], (Anniversary Edition), (Expanded)
        # Note: We intentionally DO NOT remove "Remix" so remixes stay separate.
        r'(?i)\s*[\(\[](?:.*?)?(remaster|deluxe|edition|anniversary|expanded|re-master|mastered)(?:.*?)?[\)\]]',
        r'(?i)\s*-\s*.*?(remaster|deluxe|edition|anniversary|expanded|re-master|mastered).*?$',

        # --- FEATURES (Standardize to Main Artist) ---
        # (feat. X), (ft. X), (featuring X), (with X) inside brackets
        r'(?i)\s*[\(\[](?:feat|ft\.|featuring|with|prod\.)\s+.*?[\)\]]',
        # "Song Name feat. X" (without brackets, at end of string)
        r'(?i)\s+(?:feat|ft\.|featuring|with|prod\.)\s+.*$',

        # --- VERSIONS / EDITS ---
        # (Radio Edit), (Single Edit), (Album Version), (Explicit), (Clean)
        # (Mono), (Stereo)
        r'(?i)\s*[\(\[](?:.*?)?(radio\s*edit|single\s*edit|album\s*version|explicit|clean|mono|stereo)(?:.*?)?[\)\]]',

        # --- LIVE PERFORMANCES ---
        # (Live), (Live at Wembley). 
        # Remove this if you WANT "Live" tracks to be separate from Studio versions.
        # Most users prefer accurate "Total Plays" for the song composition.
        r'(?i)\s*[\(\[](?:.*?)?(live)(?:.*?)?[\)\]]',
        r'(?i)\s*-\s*live(?:.*?)?$',

        # --- ALBUM SUFFIXES ---
        # "Album Name - Single", "Album Name - EP"
        r'(?i)\s+-\s+(?:single|ep)$'
    ]
    
    for pattern in patterns:
        text = re.sub(pattern, '', text)
        
    # 3. Final Polish
    # Remove empty brackets if any remain "Song []"
    text = re.sub(r'\s*[\(\[]\s*[\)\]]', '', text)
    # Remove double spaces
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()


class ScrobbleTimestampCalculator:
    """Smart timestamp calculator with different distribution strategies"""
    
    @staticmethod
    def calculate_scrobble_timestamp(
        songs_scrobbled_so_far: int,
        total_songs_to_scrobble: int,
        is_pro_user: bool = False,
        is_first_time_scrobbling: bool = False
    ) -> str:
        """
        Calculate timestamp for scrobbling with smart distribution
        
        Three-case approach:
        1. First-time scrobbling: logarithmic distribution over 24 hours
        2. Free user (not first time): logarithmic distribution over 1 hour
        3. Pro user (not first time): linear distribution over 5 minutes
        """
        now = int(time.time())
        
        if total_songs_to_scrobble == 1:
            return str(now - 30)
        
        use_linear_distribution = False
        
        if is_first_time_scrobbling:
            distribution_seconds = 24 * 60 * 60
        elif not is_pro_user:
            distribution_seconds = 60 * 60
        else:
            distribution_seconds = 5 * 60
            use_linear_distribution = True
        
        min_offset = 30
        position_ratio = songs_scrobbled_so_far / (total_songs_to_scrobble - 1)
        
        if use_linear_distribution:
            interval_seconds = distribution_seconds / total_songs_to_scrobble
            offset = min_offset + (interval_seconds * songs_scrobbled_so_far)
        else:
            max_offset = distribution_seconds
            log_scale = math.log(1 + position_ratio * (math.e - 1))
            offset = min_offset + (max_offset - min_offset) * log_scale
        
        return str(int(now - offset))


class ErrorCategorizer:
    """Categorize different types of errors for smart handling"""
    
    @staticmethod
    def categorize_error(error: Exception) -> FailureType:
        error_message = str(error)
        
        if any(keyword in error_message for keyword in [
            "401", "UNAUTHENTICATED", "authentication credential",
            "Headers.append", "invalid header value", "Authentication required",
            "cookie appears to be expired", "login is required", "__Secure-3PAPISID"
        ]):
            return FailureType.AUTH
        
        if any(keyword in error_message for keyword in [
            "503", "Service Unavailable", "502", "Bad Gateway",
            "429", "Too Many Requests", "rate limit",
            "temporarily unavailable", "try again later"
        ]):
            return FailureType.TEMPORARY
        
        if any(keyword in error_message for keyword in [
            "Failed to fetch", "network", "timeout",
            "ECONNRESET", "ENOTFOUND", "ConnectionError"
        ]):
            return FailureType.NETWORK
        
        if any(keyword in error_message for keyword in [
            "audioscrobbler", "last.fm", "scrobble"
        ]):
            return FailureType.LASTFM
        
        return FailureType.UNKNOWN
    
    @staticmethod
    def should_deactivate_user(failure_type: FailureType, consecutive_failures: int) -> bool:
        thresholds = {
            FailureType.AUTH: 3,
            FailureType.NETWORK: 8,
            FailureType.TEMPORARY: 15,
            FailureType.LASTFM: 5,
            FailureType.UNKNOWN: 7,
        }
        return consecutive_failures >= thresholds.get(failure_type, 7)


class SmartScrobbler:
    """Enhanced scrobbler with smart features"""
    
    def __init__(self, last_fm_api_key: str, last_fm_api_secret: str):
        self.last_fm_api_key = last_fm_api_key
        self.last_fm_api_secret = last_fm_api_secret
        self.timestamp_calculator = ScrobbleTimestampCalculator()
        self.error_categorizer = ErrorCategorizer()
    
    def _sanitize_string(self, s: str) -> str:
        """Sanitize string for Last.fm API"""
        
        # --- PHASE 1: NUCLEAR CLEANING ---
        s = clean_metadata(s)
        # ---------------------------------

        # --- PHASE 2: TECHNICAL SANITIZATION ---
        s = re.sub(r'\\u([0-9A-Fa-f]{4})', lambda m: chr(int(m.group(1), 16)), s)
        
        replacements = {
            '\u2026': '...',
            '\u2013': '-',
            '\u2014': '-',
            '\u2018': "'",
            '\u2019': "'",
            '\u201C': '"',
            '\u201D': '"',
        }
        for old, new in replacements.items():
            s = s.replace(old, new)
        
        s = re.sub(r'[\u0000-\u001F\u007F\uFFFE\uFFFF]', '', s)
        return s
    
    def _hash_request(self, params: Dict[str, str]) -> str:
        string = ""
        for key in sorted(params.keys()):
            string += key + params[key]
        string += self.last_fm_api_secret
        return hashlib.md5(string.encode('utf-8')).hexdigest()
    
    def scrobble_song(
        self,
        song: Dict[str, str],
        last_fm_session_key: str,
        timestamp: str
    ) -> bool:
        params = {
            'album': self._sanitize_string(song['album']),
            'api_key': self.last_fm_api_key,
            'method': 'track.scrobble',
            'timestamp': timestamp,
            'track': self._sanitize_string(song['title']),
            'artist': self._sanitize_string(song['artist']),
            'sk': last_fm_session_key,
        }
        
        api_sig = self._hash_request(params)
        
        try:
            xml_response = lastpy.scrobble(
                params['track'],
                params['artist'],
                params['album'],
                last_fm_session_key,
                timestamp
            )

            root = ET.fromstring(xml_response)
            scrobbles = root.find('scrobbles')

            if scrobbles is not None:
                accepted = scrobbles.get('accepted', '0')
                ignored = scrobbles.get('ignored', '0')

                if accepted != '0':
                    print(f"  ✅ Scrobbled: {params['track']} by {params['artist']}")
                elif ignored != '0':
                    print(f"  ⚠️  Ignored: {params['track']} by {params['artist']}")

                return accepted != '0' or ignored == '0'

            print(f"  [Last.fm Response] No scrobbles element found in XML response")
            print(f"  [Raw XML] {xml_response}")
            return False

        except Exception as e:
            print(f"❌ Error scrobbling '{song['title']}': {type(e).__name__}")
            raise e
    
    def calculate_timestamp(
        self,
        position: int,
        total: int,
        is_pro_user: bool = False,
        is_first_time: bool = False
    ) -> str:
        return self.timestamp_calculator.calculate_scrobble_timestamp(
            position, total, is_pro_user, is_first_time
        )
    
    def categorize_error(self, error: Exception) -> FailureType:
        return self.error_categorizer.categorize_error(error)
    
    def should_deactivate_user(self, failure_type: FailureType, consecutive_failures: int) -> bool:
        return self.error_categorizer.should_deactivate_user(failure_type, consecutive_failures)


class PositionTracker:
    def __init__(self):
        pass
    
    @staticmethod
    def detect_songs_to_scrobble(
        today_songs: List[Dict[str, str]],
        database_songs: List[Dict],
        is_first_time: bool = False,
        max_first_time_songs: int = 10
    ) -> List[Dict]:
        songs_to_scrobble = []
        
        if is_first_time:
            for i, song in enumerate(today_songs[:max_first_time_songs]):
                songs_to_scrobble.append({
                    'song': song,
                    'position': i + 1,
                    'reason': 'first_time',
                    'should_scrobble': True
                })
            for i, song in enumerate(today_songs[max_first_time_songs:], max_first_time_songs):
                songs_to_scrobble.append({
                    'song': song,
                    'position': i + 1,
                    'reason': 'first_time_no_scrobble',
                    'should_scrobble': False
                })
        else:
            for i, song in enumerate(today_songs):
                current_position = i + 1
                saved_song = None
                for db_song in database_songs:
                    if (db_song['title'] == song['title'] and 
                        db_song['artist'] == song['artist'] and 
                        db_song['album'] == song['album']):
                        saved_song = db_song
                        break
                
                if not saved_song:
                    songs_to_scrobble.append({
                        'song': song,
                        'position': current_position,
                        'reason': 'new_song',
                        'should_scrobble': True
                    })
                elif current_position < saved_song.get('array_position', float('inf')):
                    songs_to_scrobble.append({
                        'song': song,
                        'position': current_position,
                        'reason': 'reproduction',
                        'should_scrobble': True,
                        'previous_position': saved_song.get('array_position')
                    })
                else:
                    songs_to_scrobble.append({
                        'song': song,
                        'position': current_position,
                        'reason': 'position_update',
                        'should_scrobble': False
                    })
        
        return songs_to_scrobble
