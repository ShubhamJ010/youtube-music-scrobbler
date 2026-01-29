"""
Smart scrobbling utilities with improved timestamp distribution and error handling
Based on ytmusic-scrobbler-web worker implementation
"""
import time
import math
import re  # Verified: Added for cleaning metadata
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
    Remove marketing junk from song titles and albums.
    Examples: "Song (2011 Remaster)" -> "Song"
              "Album [Deluxe Edition]" -> "Album"
    """
    if not text:
        return ""
        
    # Regex patterns to catch (Remastered), [Deluxe Edition], - Live, etc.
    # Case insensitive (?i)
    patterns = [
        # Catches (Remaster), [Deluxe Edition], (2011 Mix), etc.
        r'(?i)\s*[\(\[](?:.*?)?(remaster|deluxe|edition|anniversary|live|mono|stereo|mix)(?:.*?)?[\)\]]',
        # Catches " - Remastered" or " - Live at Wembley" at the end of a string
        r'(?i)\s*-\s*.*?(remaster|deluxe|edition|anniversary|live|mono|stereo|mix).*?$'
    ]
    
    for pattern in patterns:
        text = re.sub(pattern, '', text)
        
    # Remove extra spaces created by deletions and strip whitespace
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
        
        # If only one song, place it 30 seconds ago
        if total_songs_to_scrobble == 1:
            return str(now - 30)
        
        use_linear_distribution = False
        
        # Determine distribution strategy and time window
        if is_first_time_scrobbling:
            # Case 1: First-time scrobbling - use logarithmic with max 1 day (24 hours)
            distribution_seconds = 24 * 60 * 60  # 86400 seconds
        elif not is_pro_user:
            # Case 2: Free user (not first time) - use logarithmic with max 1 hour
            distribution_seconds = 60 * 60  # 3600 seconds
        else:
            # Case 3: Pro user (not first time) - use linear with max 5 minutes
            distribution_seconds = 5 * 60  # 300 seconds
            use_linear_distribution = True
        
        min_offset = 30  # Minimum 30 seconds ago
        
        # Calculate position ratio (0 = most recent, 1 = oldest)
        position_ratio = songs_scrobbled_so_far / (total_songs_to_scrobble - 1)
        
        if use_linear_distribution:
            # Linear distribution for pro users: evenly space songs across the time window
            interval_seconds = distribution_seconds / total_songs_to_scrobble
            offset = min_offset + (interval_seconds * songs_scrobbled_so_far)
        else:
            # Logarithmic distribution for first-time and free users
            # This places more recent songs closer together and spreads older ones further back
            max_offset = distribution_seconds
            
            # Use logarithmic scaling to concentrate recent songs
            # Most recent songs get clustered near min_offset
            # Older songs get distributed across the full time window
            log_scale = math.log(1 + position_ratio * (math.e - 1))
            offset = min_offset + (max_offset - min_offset) * log_scale
        
        return str(int(now - offset))


class ErrorCategorizer:
    """Categor
