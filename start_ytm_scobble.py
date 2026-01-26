import os
import http.server
import socketserver
import sqlite3
import threading
import time
import webbrowser
import xml.etree.ElementTree as ET
from dotenv import set_key


import lastpy
from date_detection import (
    get_detected_languages,
    get_unknown_date_values,
    is_today_song,
)
from scrobble_utils import FailureType, PositionTracker, SmartScrobbler
from ytmusic_fetcher import get_ytmusic_history


# --- Last.fm Authentication ---

class TokenHandler(http.server.SimpleHTTPRequestHandler):
    def do_get_token(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b'<html><head><title>Token Received</title></head>')
        self.wfile.write(
            b'<body><p>Authentication successful! You can now close this window.</p></body></html>')
        self.server.token = self.path.split('?token=')[1]

    def do_GET(self):
        if self.path.startswith('/?token='):
            self.do_get_token()
        else:
            http.server.SimpleHTTPRequestHandler.do_GET(self)


class TokenServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    token = None


# --- Main Scrobbling Process ---

class ImprovedProcess:
    def __init__(self):
        self.api_key = os.environ.get('LAST_FM_API')
        self.api_secret = os.environ.get('LAST_FM_API_SECRET')
        if not self.api_key or not self.api_secret:
            raise ValueError("Missing LAST_FM_API or LAST_FM_API_SECRET environment variables")

        try:
            self.session = os.environ['LASTFM_SESSION']
        except KeyError:
            self.session = None

        self.scrobbler = SmartScrobbler(self.api_key, self.api_secret)
        self.position_tracker = PositionTracker()

        self.conn = sqlite3.connect('./data.db')
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scrobbles (
                id INTEGER PRIMARY KEY,
                track_name TEXT,
                artist_name TEXT,
                album_name TEXT,
                scrobbled_at TEXT DEFAULT CURRENT_TIMESTAMP,
                array_position INTEGER,
                max_array_position INTEGER,
                is_first_time_scrobble BOOLEAN DEFAULT FALSE
            )
        ''')
        
        try:
            cursor.execute('ALTER TABLE scrobbles ADD COLUMN max_array_position INTEGER')
        except sqlite3.OperationalError:
            pass
        
        try:
            cursor.execute('ALTER TABLE scrobbles ADD COLUMN is_first_time_scrobble BOOLEAN DEFAULT FALSE')
        except sqlite3.OperationalError:
            pass
        
        self.conn.commit()
        cursor.close()

    def get_token(self):
        print("Waiting for Last.fm authentication...")
        auth_url = f"https://www.last.fm/api/auth/?api_key={self.api_key}&cb=http://localhost:5588"
        
        with TokenServer(('localhost', 5588), TokenHandler) as httpd:
            webbrowser.open(auth_url)
            thread = threading.Thread(target=httpd.serve_forever)
            thread.start()
            while True:
                if httpd.token:
                    token = httpd.token
                    httpd.shutdown()
                    break
                time.sleep(0.1)
        return token

    def get_session(self, token):
        print("Getting Last.fm session...")
        xml_response = lastpy.authorize(token)
        try:
            root = ET.fromstring(xml_response)
            session_key = root.find('session/key').text
            set_key('.env', 'LASTFM_SESSION', session_key)
            return session_key
        except Exception as e:
            print(f"Error getting session: {xml_response}")
            raise Exception(e)

    def execute(self):
        """Main execution logic"""
        if not self.session:
            try:
                token = self.get_token()
                self.session = self.get_session(token)
            except Exception as e:
                print(f"Failed to authenticate with Last.fm: {e}")
                return False

        print("🎵 Fetching YouTube Music history...")
        try:
            history = get_ytmusic_history()
            print(f"📋 Retrieved: {len(history)} total songs from history")
        except FileNotFoundError as e:
            print(f"❌ {e}")
            print("Please ensure 'browser.json' or 'browser.json.enc' with YTMUSIC_AUTH_KEY is provided.")
            print("You can create 'browser.json' by running `ytmusicapi browser` and then secure it with `encrypt_auth.py`.")
            return False
        except Exception as error:
            print(f"An error occurred while fetching history: {error}")
            return False

        print("📅 Filtering songs played today...")
        today_songs = [song for song in history if is_today_song(song.get('playedAt'))]
        
        unknown_values = get_unknown_date_values(history)
        detected_languages = get_detected_languages(history)
        if detected_languages:
            print(f"🌐 Languages detected: {', '.join(detected_languages)}")

        print(f"🎯 Found: {len(today_songs)} songs played today")

        if len(today_songs) == 0:
            print("😴 No songs played today. Nothing to scrobble.")
            return True

        cursor = self.conn.cursor()
        db_songs = cursor.execute('''
            SELECT track_name, artist_name, album_name, array_position, 
                   max_array_position, is_first_time_scrobble
            FROM scrobbles
        ''').fetchall()
        
        database_songs = [{'title': r[0], 'artist': r[1], 'album': r[2], 'array_position': r[3], 'max_array_position': r[4] or r[3], 'is_first_time': bool(r[5])} for r in db_songs]

        is_first_time = len(database_songs) == 0
        
        if database_songs:
            songs_to_delete = [db_song for db_song in database_songs if not any(
                (today_song['title'] == db_song['title'] and 
                 today_song['artist'] == db_song['artist'] and 
                 today_song['album'] == db_song['album'])
                for today_song in today_songs
            )]
            
            if songs_to_delete:
                print(f"🧹 Removed {len(songs_to_delete)} outdated songs from database")
                for song in songs_to_delete:
                    cursor.execute('DELETE FROM scrobbles WHERE track_name = ? AND artist_name = ? AND album_name = ?', (song['title'], song['artist'], song['album']))
                self.conn.commit()

        songs_to_process = self.position_tracker.detect_songs_to_scrobble(
            today_songs, database_songs, is_first_time, 10
        )

        songs_to_scrobble = [s for s in songs_to_process if s['should_scrobble']]
        total_to_scrobble = len(songs_to_scrobble)

        scrobble_stats = {
            'new_songs': sum(1 for s in songs_to_process if s['reason'] == 'new_song'),
            'reproductions': sum(1 for s in songs_to_process if s['reason'] == 'reproduction'),
            'position_updates': sum(1 for s in songs_to_process if s['reason'] == 'position_update'),
            'first_time_no_scrobble': sum(1 for s in songs_to_process if s['reason'] == 'first_time_no_scrobble')
        }
        
        print(f"\n📋 PROCESSING PLAN:")
        print(f"   Songs in today's history: {len(today_songs):>3}")
        print(f"   Total to process: {len(songs_to_process):>11}")
        print(f"   └─ Songs to scrobble: {total_to_scrobble:>8}")
        print(f"   └─ DB updates only: {len(songs_to_process) - total_to_scrobble:>10}")
        print(f"\n📊 BREAKDOWN:")
        print(f"   New songs: {scrobble_stats['new_songs']:>16}")
        print(f"   Re-productions: {scrobble_stats['reproductions']:>11}")
        print(f"   Position updates: {scrobble_stats['position_updates']:>9}")
        
        songs_scrobbled = 0
        scrobble_position = 0
        failed_songs = []
        scrobbled_tracks = []
        db_only_tracks = []

        for item in songs_to_process:
            song = item['song']
            position = item['position']
            should_scrobble = item['should_scrobble']
            reason = item['reason']
            
            try:
                if should_scrobble:
                    timestamp = self.scrobbler.calculate_timestamp(
                        scrobble_position, total_to_scrobble, is_first_time=is_first_time
                    )
                    success = self.scrobbler.scrobble_song(song, self.session, timestamp)
                    
                    if success:
                        songs_scrobbled += 1
                        scrobble_position += 1
                        scrobbled_tracks.append(f"{song['title']} by {song['artist']}")
                    else:
                        failed_songs.append(f"{song['title']} by {song['artist']}")
                
                existing_song = cursor.execute('SELECT id, max_array_position FROM scrobbles WHERE track_name = ? AND artist_name = ? AND album_name = ?', (song['title'], song['artist'], song['album'])).fetchone()
                
                if existing_song:
                    song_id, current_max = existing_song
                    new_max = max(current_max or position, position)
                    cursor.execute('UPDATE scrobbles SET array_position = ?, max_array_position = ?, scrobbled_at = CURRENT_TIMESTAMP WHERE id = ?', (position, new_max, song_id))
                else:
                    cursor.execute('INSERT INTO scrobbles (track_name, artist_name, album_name, array_position, max_array_position, is_first_time_scrobble) VALUES (?, ?, ?, ?, ?, ?)', (song['title'], song['artist'], song['album'], position, position, is_first_time))
                
                if not should_scrobble:
                    db_only_tracks.append(f"{song['title']} by {song['artist']} ({reason})")
                
                self.conn.commit()
                
            except Exception as error:
                failure_type = self.scrobbler.categorize_error(error)
                print(f"ERROR processing '{song['title']}': {error} (Type: {failure_type.value})")
                if failure_type == FailureType.AUTH:
                    print("🔒 Last.fm authentication error detected. Stopping execution.")
                    break
                failed_songs.append(f"{song['title']} by {song['artist']}")

        duplicates = cursor.execute("SELECT track_name, artist_name, COUNT(*) FROM scrobbles WHERE scrobbled_at >= datetime('now', '-1 hour') GROUP BY track_name, artist_name HAVING COUNT(*) > 1").fetchall()
        cursor.close()
        
        print(f"\n{'='*60}\n🎵 SCROBBLING COMPLETED!\n{'='*60}")
        print(f"📊 FINAL SUMMARY:")
        print(f"   Total songs processed: {len(songs_to_process):>4}")
        print(f"   Successfully scrobbled: {songs_scrobbled:>3}")
        print(f"   Failed scrobbles: {len(failed_songs):>9}")
        if failed_songs:
            print(f"   Failed tracks: {', '.join(failed_songs[:3])}" + ("..." if len(failed_songs) > 3 else ""))
        print(f"   Duplicate checks: {'✅ No duplicates' if not duplicates else f'⚠️ Found {len(duplicates)} duplicates'}")
        
        if scrobbled_tracks:
            print(f"\n✅ SCROBBLED TRACKS ({len(scrobbled_tracks)}):")
            for i, track in enumerate(scrobbled_tracks, 1):
                print(f"   {i}. {track}")

        if unknown_values:
            print(f"\n🔍 DATE SUPPORT INFO:\n   Unrecognized date formats: {', '.join(unknown_values)}")
        
        print(f"\n{'='*60}")
        if songs_scrobbled > 0:
            print(f"✅ SUCCESS: {songs_scrobbled} songs sent to Last.fm")
        elif len(failed_songs) > 0:
            print(f"⚠️  PARTIAL: {len(failed_songs)} songs failed to scrobble")
        else:
            print(f"✅ COMPLETED: All songs processed (no new scrobbles needed)")
        print(f"{ '='*60}")
        
        return True

def main():
    """Main entry point"""
    print("🎵 YouTube Music Last.fm Scrobbler (ytmusicapi version)")
    print("=" * 60)
    
    try:
        process = ImprovedProcess()
        success = process.execute()
        
        if success:
            print("\n🎉 Process completed successfully!")
        else:
            print("\n❌ Process failed. Please check the errors above.")
            return 1
            
    except KeyboardInterrupt:
        print("\n⏹️  Process interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())
