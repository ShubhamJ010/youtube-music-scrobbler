#!/usr/bin/env python3
"""
Debug script to analyze database for duplicate records
"""
import sqlite3
import os
from datetime import datetime, timedelta

def analyze_database():
    """Analyze database for duplicate patterns"""
    if not os.path.exists('data.db'):
        print("❌ No database found")
        return
    
    conn = sqlite3.connect('data.db')
    cursor = conn.cursor()
    
    print("🔍 Database Analysis")
    print("=" * 50)
    
    # Total records
    cursor.execute("SELECT COUNT(*) FROM scrobbles")
    total = cursor.fetchone()[0]
    print(f"📊 Total scrobbles: {total}")
    
    # Recent records (last 24 hours)
    cursor.execute('''
        SELECT COUNT(*) FROM scrobbles 
        WHERE scrobbled_at >= datetime('now', '-1 day')
    ''')
    recent = cursor.fetchone()[0]
    print(f"📅 Scrobbles in last 24 hours: {recent}")
    
    # Recent records (last 6 hours) - cron job frequency
    cursor.execute('''
        SELECT COUNT(*) FROM scrobbles 
        WHERE scrobbled_at >= datetime('now', '-6 hours')
    ''')
    recent_6h = cursor.fetchone()[0]
    print(f"🕐 Scrobbles in last 6 hours: {recent_6h}")
    
    # Potential duplicates in last hour
    cursor.execute('''
        SELECT track_name, artist_name, COUNT(*) as count, 
               GROUP_CONCAT(scrobbled_at) as timestamps
        FROM scrobbles 
        WHERE scrobbled_at >= datetime('now', '-1 hour')
        GROUP BY track_name, artist_name
        HAVING count > 1
        ORDER BY count DESC
    ''')
    
    duplicates = cursor.fetchall()
    if duplicates:
        print(f"\n⚠️  Potential duplicates in last hour:")
        for song, count, timestamps in duplicates:
            print(f"  🎵 {song}")
            print(f"     Count: {count}")
            print(f"     Timestamps: {timestamps}")
            print()
    else:
        print("\n✅ No duplicates found in last hour")
    
    # Check for position-based duplicates
    cursor.execute('''
        SELECT track_name, artist_name, array_position, max_array_position,
               COUNT(*) as position_count
        FROM scrobbles 
        WHERE scrobbled_at >= datetime('now', '-1 hour')
        GROUP BY track_name, artist_name, array_position, max_array_position
        HAVING position_count > 1
    ''')
    
    position_duplicates = cursor.fetchall()
    if position_duplicates:
        print(f"⚠️  Position-based duplicates:")
        for song, pos, max_pos, count in position_duplicates:
            print(f"  🎵 {song}")
            print(f"     Position: {pos}, Max: {max_pos}")
            print(f"     Count: {count}")
            print()
    
    # Show recent scrobbles
    cursor.execute('''
        SELECT track_name, artist_name, array_position, scrobbled_at
        FROM scrobbles 
        ORDER BY scrobbled_at DESC 
        LIMIT 10
    ''')
    
    recent_scrobbles = cursor.fetchall()
    print("🕐 Most recent scrobbles:")
    for song, artist, pos, timestamp in recent_scrobbles:
        print(f"  {timestamp} - {song} by {artist} (pos: {pos})")
    
    # Check cache key info (GitHub Actions specific)
    print(f"\n🔄 GitHub Actions Info:")
    print(f"  Run ID: {os.environ.get('GITHUB_RUN_ID', 'N/A')}")
    print(f"  Run Attempt: {os.environ.get('GITHUB_RUN_ATTEMPT', 'N/A')}")
    
    conn.close()

if __name__ == "__main__":
    analyze_database()