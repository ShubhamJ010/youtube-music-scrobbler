# Last.fm Syncing Tool
# Lean, fast, and functional
import os
import time
import requests
import hashlib
from dotenv import load_dotenv

load_dotenv()

api_head = 'http://ws.audioscrobbler.com/2.0/'
secret = os.environ['LAST_FM_API_SECRET']


def authorize(user_token):
    params = {
        'api_key': os.environ['LAST_FM_API'],
        'method': 'auth.getSession',
        'token': user_token
    }
    requestHash = hashRequest(params, secret)
    params['api_sig'] = requestHash
    apiResp = requests.post(api_head, params)
    return apiResp.text


def nowPlaying(song_name, artist_name, session_key):
    params = {
        'method': 'track.updateNowPlaying',
        'api_key': os.environ['LAST_FM_API'],
        'track': song_name,
        'artist': artist_name,
        'sk': session_key
    }
    requestHash = hashRequest(params, secret)
    params['api_sig'] = requestHash
    apiResp = requests.post(api_head, params)
    return apiResp.text


def scrobble(song_name, artist_name, album_name, session_key, timestamp=str(int(time.time() - 30))):
    # Currently this sort of cheats the timestamp protocol
    params = {
        'method': 'track.scrobble',
        'api_key': os.environ['LAST_FM_API'],
        'timestamp': timestamp,
        'track': song_name,
        'artist': artist_name,
        'album': album_name,
        'sk': session_key
    }
    requestHash = hashRequest(params, secret)
    params['api_sig'] = requestHash
    apiResp = requests.post(api_head, params)
    return apiResp.text


def get_recent_tracks(username, api_key, track=None, artist=None, limit=5):
    """Get user's recent tracks from Last.fm.
    
    Args:
        username: Last.fm username
        api_key: Last.fm API key
        track: Optional track name to filter by
        artist: Optional artist name to filter by
        limit: Number of recent tracks to return (default 5)
    
    Returns:
        XML response from Last.fm API
    """
    params = {
        'method': 'user.getRecentTracks',
        'user': username,
        'api_key': api_key,
        'limit': limit
    }
    if track:
        params['track'] = track
    if artist:
        params['artist'] = artist
    
    response = requests.get(api_head, params=params)
    return response.text


def hashRequest(obj, secretKey):
    string = ''
    items = list(obj.keys())
    items.sort()
    for i in items:
        string += i
        if obj[i] is not None:
            string += obj[i]
    string += secretKey
    stringToHash = string.encode('utf8')
    requestHash = hashlib.md5(stringToHash).hexdigest()
    return requestHash
