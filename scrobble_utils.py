"""
Smart scrobbling utilities with improved timestamp distribution and error handling
Based on ytmusic-scrobbler-web worker implementation
"""
import time
import math
import re
import logging
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
        # --- NEW: VIEW COUNTS (Specifically for your issue) ---
        # Catches "Artist Name, 509K views" or "Artist 1M views"
        r'(?i)(?:,?\s*)?\d+(?:[\.,]\d+)?\s*[KMB]?\s*views',

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
        Calculate timestamp using a DYNAMIC window based on song count.
        This prevents 'Overlap' where a new batch of songs gets pushed 
        so far back in time that it mixes with the previous batch.
        """
        now = int(time.time())
        
        # If only one song, place it 30 seconds ago
        if total_songs_to_scrobble == 1:
            return str(now - 30)
        
        # --- DYNAMIC WINDOW CALCULATION ---
        # We assume an average of 4 minutes (240 seconds) per song.
        estimated_listening_duration = total_songs_to_scrobble * 240
        
        # Set boundaries:
        # Min: 5 minutes (300s) - prevent squashing 2 songs into 1 second
        # Max: 24 hours (86400s) - prevent crazy values if you import 1000 songs
        distribution_seconds = max(300, estimated_listening_duration)
        distribution_seconds = min(distribution_seconds, 86400)
        
        # If it's the very first run ever, we can be looser (24h) to fill history
        if is_first_time_scrobbling:
            distribution_seconds = 86400
            
        # ----------------------------------

        min_offset = 30  # Minimum 30 seconds ago
        
        # Calculate position ratio (0 = most recent, 1 = oldest)
        position_ratio = songs_scrobbled_so_far / (total_songs_to_scrobble - 1)
        
        # Use logarithmic distribution to keep recent songs closer to 'now'
        # while respecting the calculated duration for older songs.
        max_offset = distribution_seconds
        log_scale = math.log(1 + position_ratio * (math.e - 1))
        offset = min_offset + (max_offset - min_offset) * log_scale
        
        return str(int(now - offset))


class ErrorCategorizer:
    """Categorize different types of errors for smart handling"""
    
    @staticmethod
    def categorize_error(error: Exception) -> FailureType:
        """Categorize error type based on error message"""
        error_message = str(error)
        
        # Authentication errors
        if any(keyword in error_message for keyword in [
            "401", "UNAUTHENTICATED", "authentication credential",
            "Headers.append", "invalid header value", "Authentication required",
            "cookie appears to be expired", "login is required", "__Secure-3PAPISID"
        ]):
            return FailureType.AUTH
        
        # Temporary service errors (503, 502, 429, rate limits)
        if any(keyword in error_message for keyword in [
            "503", "Service Unavailable", "502", "Bad Gateway",
            "429", "Too Many Requests", "rate limit",
            "temporarily unavailable", "try again later"
        ]):
            return FailureType.TEMPORARY
        
        # Network/YouTube Music errors
        if any(keyword in error_message for keyword in [
            "Failed to fetch", "network", "timeout",
            "ECONNRESET", "ENOTFOUND", "ConnectionError"
        ]):
            return FailureType.NETWORK
        
        # Last.fm specific errors
        if any(keyword in error_message for keyword in [
            "audioscrobbler", "last.fm", "scrobble"
        ]):
            return FailureType.LASTFM
        
        return FailureType.UNKNOWN
    
    @staticmethod
    def should_deactivate_user(failure_type: FailureType, consecutive_failures: int) -> bool:
        """Determine if user should be deactivated based on failure type and count"""
        thresholds = {
            FailureType.AUTH: 3,      # Auth issues are persistent
            FailureType.NETWORK: 8,   # Network issues might be temporary
            FailureType.TEMPORARY: 15, # Temporary issues should rarely deactivate users
            FailureType.LASTFM: 5,    # Last.fm issues might be temporary
            FailureType.UNKNOWN: 7,   # Give more chances for unknown errors
        }
        
        return consecutive_failures >= thresholds.get(failure_type, 7)


class SmartScrobbler:
    """Enhanced scrobbler with smart features"""
    
    def __init__(self, last_fm_api_key: str, last_fm_api_secret: str, dry_run: bool = False):
        self.last_fm_api_key = last_fm_api_key
        self.last_fm_api_secret = last_fm_api_secret
        self.dry_run = dry_run
        self.timestamp_calculator = ScrobbleTimestampCalculator()
        self.error_categorizer = ErrorCategorizer()
        self.logger = logging.getLogger('ytm-scrobbler.scrobbler')
    
    def _sanitize_string(self, s: str) -> str:
        """Sanitize string for Last.fm API"""
        
        # --- PHASE 1: NUCLEAR CLEANING ---
        s = clean_metadata(s)
        # ---------------------------------

        # --- PHASE 2: TECHNICAL SANITIZATION ---
        s = re.sub(r'\\u([0-9A-Fa-f]{4})', lambda m: chr(int(m.group(1), 16)), s)
        
        replacements = {
            '\u2026': '...',  # ellipsis
            '\u2013': '-',    # en dash
            '\u2014': '-',    # em dash
            '\u2018': "'",    # left single quotation mark
            '\u2019': "'",    # right single quotation mark
            '\u201C': '"',    # left double quotation mark
            '\u201D': '"',    # right double quotation mark
        }
        
        for old, new in replacements.items():
            s = s.replace(old, new)
        
        # Remove control characters and invalid Unicode
        s = re.sub(r'[\u0000-\u001F\u007F\uFFFE\uFFFF]', '', s)
        
        return s
    
    def _hash_request(self, params: Dict[str, str]) -> str:
        """Create MD5 hash for Last.fm API request"""
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
        """
        Scrobble a single song to Last.fm.
        Strictly requires Artist, Title, AND Album to prevent duplicates/bad data.
        """
        # --- STRICT METADATA CHECK ---
        # Filters out "Video" states or incomplete loads that cause double scrobbles.
        # We use .get() to avoid KeyErrors if a field is missing entirely.
        if not (song.get('artist') and song.get('title') and song.get('album')):
            # Optional: detailed logging if you need to debug specific skipped tracks
            # print(f"  ⏭️  Skipping: '{song.get('title', 'Unknown')}' - Missing metadata")
            return False
        # -----------------------------

        params = {
            'album': self._sanitize_string(song['album']),
            'api_key': self.last_fm_api_key,
            'method': 'track.scrobble',
            'timestamp': timestamp,
            'track': self._sanitize_string(song['title']),
            'artist': self._sanitize_string(song['artist']),
            'sk': last_fm_session_key,
        }
        
        # Create API signature
        api_sig = self._hash_request(params)
        
        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would scrobble: {song['title']} by {song['artist']}")
            return True

        try:
            # Use lastpy for scrobbling
            xml_response = lastpy.scrobble(
                params['track'],
                params['artist'],
                params['album'],
                last_fm_session_key,
                timestamp
            )

            # Parse XML response
            root = ET.fromstring(xml_response)
            scrobbles = root.find('scrobbles')

            if scrobbles is not None:
                accepted = scrobbles.get('accepted', '0')
                ignored = scrobbles.get('ignored', '0')

                # Minimal logging for scrobble result
                if accepted != '0':
                    self.logger.debug(f"Scrobbled: {song['title']} by {song['artist']}")
                elif ignored != '0':
                    self.logger.warning(f"Ignored: {song['title']} by {song['artist']}")

                # Return True if at least one scrobble was accepted
                return accepted != '0' or ignored == '0'

            self.logger.error(f"No scrobbles element found in XML response: {xml_response}")
            return False

        except Exception as e:
            # Errors are handled by the caller in ImprovedProcess.execute
            raise e
    
    def calculate_timestamp(
        self,
        position: int,
        total: int,
        is_pro_user: bool = False,
        is_first_time: bool = False
    ) -> str:
        """Calculate timestamp for scrobbling at given position"""
        return self.timestamp_calculator.calculate_scrobble_timestamp(
            position, total, is_pro_user, is_first_time
        )
    
    def categorize_error(self, error: Exception) -> FailureType:
        """Categorize an error for smart handling"""
        return self.error_categorizer.categorize_error(error)
    
    def should_deactivate_user(self, failure_type: FailureType, consecutive_failures: int) -> bool:
        """Check if user should be deactivated"""
        return self.error_categorizer.should_deactivate_user(failure_type, consecutive_failures)


class PositionTracker:
    """Track song positions for detecting re-reproductions"""
    
    def __init__(self):
        pass
    
    @staticmethod
    def detect_songs_to_scrobble(
        today_songs: List[Dict[str, str]],
        database_songs: List[Dict],
        is_first_time: bool = False,
        max_first_time_songs: int = 10
    ) -> List[Dict]:
        """
        Determine which songs should be scrobbled based on position tracking.
        Filters out songs with missing metadata BEFORE processing to avoid
        index mismatches.
        """
        songs_to_scrobble = []
        
        # --- PRE-FILTERING ---
        # Only process songs that actually have all required metadata.
        # We keep the original index (enumeration) because that represents 
        # the real time/order in the history list.
        valid_songs_with_indices = []
        for i, song in enumerate(today_songs):
            if song.get('artist') and song.get('title') and song.get('album'):
                valid_songs_with_indices.append((i, song))
        # ---------------------
        
        if is_first_time:
            # First time: scrobble recent valid songs up to the limit
            for i, song in valid_songs_with_indices[:max_first_time_songs]:
                songs_to_scrobble.append({
                    'song': song,
                    'position': i + 1,
                    'reason': 'first_time',
                    'should_scrobble': True
                })
            
            # Add remaining valid songs to database without scrobbling
            for i, song in valid_songs_with_indices[max_first_time_songs:]:
                songs_to_scrobble.append({
                    'song': song,
                    'position': i + 1,
                    'reason': 'first_time_no_scrobble',
                    'should_scrobble': False
                })
        else:
            # Regular processing: check for new songs and re-reproductions
            for i, song in valid_songs_with_indices:
                current_position = i + 1
                
                # Find matching song in database
                saved_song = None
                for db_song in database_songs:
                    if (db_song.get('title') == song['title'] and 
                        db_song.get('artist') == song['artist'] and 
                        db_song.get('album') == song['album']):
                        saved_song = db_song
                        break
                
                if not saved_song:
                    # New song - scrobble it
                    songs_to_scrobble.append({
                        'song': song,
                        'position': current_position,
                        'reason': 'new_song',
                        'should_scrobble': True
                    })
                elif current_position < saved_song.get('array_position', float('inf')):
                    # Re-reproduction - song moved up in the list
                    songs_to_scrobble.append({
                        'song': song,
                        'position': current_position,
                        'reason': 'reproduction',
                        'should_scrobble': True,
                        'previous_position': saved_song.get('array_position')
                    })
                else:
                    # Song exists and hasn't moved up - just update position
                    songs_to_scrobble.append({
                        'song': song,
                        'position': current_position,
                        'reason': 'position_update',
                        'should_scrobble': False
                    })
        
        return songs_to_scrobble
