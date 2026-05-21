"""
Report metric helpers for Discord summary formatting.
"""
from collections import Counter
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple


AVG_TRACK_MINUTES = 4


def compute_most_played_artist(today_songs: List[Dict[str, str]]) -> str:
    """Return the most frequently occurring artist in today's songs."""
    artists = [song.get("artist") for song in today_songs if song.get("artist")]
    if not artists:
        return "Unknown"

    counts = Counter(artists)
    first_index = {}
    for idx, artist in enumerate(artists):
        if artist not in first_index:
            first_index[artist] = idx

    return min(counts.keys(), key=lambda artist: (-counts[artist], first_index[artist], artist))


def compute_longest_streak(today_songs: List[Dict[str, str]], avg_track_minutes: int = AVG_TRACK_MINUTES) -> Tuple[int, int]:
    """
    Longest contiguous streak in today's ordered history.
    Since history is contiguous by list order, this is today's song count.
    """
    tracks = len(today_songs)
    return tracks, tracks * avg_track_minutes


def _bucket_for_hour(hour: int) -> Optional[str]:
    if 0 <= hour <= 5:
        return "Late Night"
    if 12 <= hour <= 16:
        return "Afternoon"
    if 17 <= hour <= 21:
        return "Evening"
    return None


def compute_listening_flow(
    song_count: int,
    now_utc: Optional[datetime] = None,
    avg_track_minutes: int = AVG_TRACK_MINUTES
) -> Dict[str, int]:
    """
    Approximate listening flow by backfilling synthetic play timeline from now.
    """
    reference = now_utc or datetime.utcnow()
    totals = {"Evening": 0, "Afternoon": 0, "Late Night": 0}
    total_minutes = max(0, song_count * avg_track_minutes)

    for minute_offset in range(total_minutes):
        minute_ts = reference - timedelta(minutes=minute_offset)
        bucket = _bucket_for_hour(minute_ts.hour)
        if bucket:
            totals[bucket] += 1

    return totals
