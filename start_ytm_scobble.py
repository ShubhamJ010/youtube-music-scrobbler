import os
import argparse
import http.server
import socketserver
import sqlite3
import threading
import time
import webbrowser
import xml.etree.ElementTree as ET
import logging
from dotenv import set_key


import lastpy
from date_detection import (
    get_detected_languages,
    get_unknown_date_values,
    is_today_song,
)
from notifications import send_success_notification
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


# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('ytm-scrobbler')

# --- Main Scrobbling Process ---

class ImprovedProcess:
    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.api_key = os.environ.get('LAST_FM_API')
        self.api_secret = os.environ.get('LAST_FM_API_SECRET')
        if not self.api_key or not self.api_secret:
            raise ValueError("Missing LAST_FM_API or LAST_FM_API_SECRET environment variables")

        try:
            self.session = os.environ['LASTFM_SESSION']
        except KeyError:
            self.session = None

        self.scrobbler = SmartScrobbler(self.api_key, self.api_secret, dry_run=self.dry_run)
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
        logger.info("Waiting for Last.fm authentication...")
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
        logger.info("Getting Last.fm session...")
        xml_response = lastpy.authorize(token)
        try:
            root = ET.fromstring(xml_response)
            session_key = root.find('session/key').text
            set_key('.env', 'LASTFM_SESSION', session_key)
            return session_key
        except Exception as e:
            logger.error(f"Error getting session: {xml_response}")
            raise Exception(e)

    def execute(self):
        """Main execution logic"""
        if not self.session:
            if self.dry_run:
                logger.info("Dry run: Skipping Last.fm authentication")
                self.session = "dry_run_session"
            else:
                try:
                    token = self.get_token()
                    self.session = self.get_session(token)
                except Exception as e:
                    logger.error(f"Failed to authenticate with Last.fm: {e}")
                    return False

        if self.dry_run:
            logger.info("--- DRY RUN MODE ENABLED ---")
            logger.info("No scrobbles will be sent to Last.fm and database will not be updated.")

        logger.info("Fetching YouTube Music history...")
        try:
            history = get_ytmusic_history()
        except FileNotFoundError as e:
            logger.error(f"{e}")
            logger.error("Please ensure 'browser.json' or 'browser.json.enc' with YTMUSIC_AUTH_KEY is provided.")
            return False
        except Exception as error:
            logger.error(f"An error occurred while fetching history: {error}")
            return False

        today_songs = [song for song in history if is_today_song(song.get('playedAt'))]
        
        if not today_songs:
            logger.info(f"History: {len(history)} | Today: 0 | Existing: 0 | To Scrobble: 0")
            logger.info("No songs played today. Nothing to scrobble.")
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
                for song in songs_to_delete:
                    cursor.execute('DELETE FROM scrobbles WHERE track_name = ? AND artist_name = ? AND album_name = ?', (song['title'], song['artist'], song['album']))
                self.conn.commit()

        songs_to_process = self.position_tracker.detect_songs_to_scrobble(
            today_songs, database_songs, is_first_time, 10
        )

        songs_to_scrobble = [s for s in songs_to_process if s['should_scrobble']]
        total_to_scrobble = len(songs_to_scrobble)
        existing_count = len(songs_to_process) - total_to_scrobble

        logger.info(f"History: {len(history)} | Today: {len(today_songs)} | Existing: {existing_count} | To Scrobble: {total_to_scrobble}")

        songs_scrobbled = 0
        scrobble_position = 0
        failed_songs = []
        scrobbled_songs = []

        for item in songs_to_process:
            song = item['song']
            position = item['position']
            should_scrobble = item['should_scrobble']
            
            try:
                if should_scrobble:
                    timestamp = self.scrobbler.calculate_timestamp(
                        scrobble_position, total_to_scrobble, is_first_time=is_first_time
                    )
                    success = self.scrobbler.scrobble_song(song, self.session, timestamp)
                    
                    if success:
                        songs_scrobbled += 1
                        scrobble_position += 1
                        scrobbled_songs.append(f"{song['title']} — {song['artist']}")
                    else:
                        failed_songs.append(f"{song['title']} by {song['artist']}")
                
                if not self.dry_run:
                    existing_song = cursor.execute('SELECT id, max_array_position FROM scrobbles WHERE track_name = ? AND artist_name = ? AND album_name = ?', (song['title'], song['artist'], song['album'])).fetchone()
                    
                    if existing_song:
                        song_id, current_max = existing_song
                        new_max = max(current_max or position, position)
                        cursor.execute('UPDATE scrobbles SET array_position = ?, max_array_position = ?, scrobbled_at = CURRENT_TIMESTAMP WHERE id = ?', (position, new_max, song_id))
                    else:
                        cursor.execute('INSERT INTO scrobbles (track_name, artist_name, album_name, array_position, max_array_position, is_first_time_scrobble) VALUES (?, ?, ?, ?, ?, ?)', (song['title'], song['artist'], song['album'], position, position, is_first_time))
                    
                    self.conn.commit()
                else:
                    logger.debug(f"Dry run: Skipping database update for {song['title']}")
                
            except Exception as error:
                failure_type = self.scrobbler.categorize_error(error)
                logger.error(f"Failed to process '{song['title']}' by {song['artist']}: {error} (Type: {failure_type.value})")
                if failure_type == FailureType.AUTH:
                    logger.critical("Last.fm authentication error detected. Stopping execution.")
                    break
                failed_songs.append(f"{song['title']} by {song['artist']}")

        cursor.close()

        logger.info(f"SUMMARY: Processed: {len(songs_to_process)}, Success: {songs_scrobbled}, Failed: {len(failed_songs)}")

        # Send Discord notification only if there were songs to scrobble
        send_success_notification(
            history_count=len(history),
            today_count=len(today_songs),
            existing_count=existing_count,
            to_scrobble_count=total_to_scrobble,
            scrobbled_count=songs_scrobbled,
            failed_count=len(failed_songs),
            failed_songs=failed_songs if failed_songs else None,
            scrobbled_songs=scrobbled_songs if scrobbled_songs else None
        )

        return True

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="YouTube Music Last.fm Scrobbler")
    parser.add_argument("--dry-run", action="store_true", help="Perform a dry run without scrobbling or updating database")
    args = parser.parse_args()

    logger.info("YouTube Music Last.fm Scrobbler started")

    try:
        process = ImprovedProcess(dry_run=args.dry_run)
        success = process.execute()

        if success:
            logger.info("Process completed successfully")
        else:
            logger.error("Process failed. Please check the errors above.")
            return 1

    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        return 1
    except Exception as e:
        logger.critical(f"Unexpected error: {e}", exc_info=True)
        return 1

    return 0

if __name__ == '__main__':
    exit(main())
