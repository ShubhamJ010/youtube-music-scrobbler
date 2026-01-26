# YOUTUBE MUSIC LAST.FM SCROBBLER

The YouTube Music Last.fm Scrobbler is a Python application that fetches your YouTube Music listening history from the last 24 hours and scrobbles it to Last.fm. This project offers two versions with different approaches and capabilities.

## 🚀 Quick Setup Options

- **Manual Setup**: Follow the instructions below to run locally
- **Automated Setup**: **[Recommended] Use GitHub Actions** - See our complete setup guide: [GITHUB_ACTIONS_GUIDE.md](GITHUB_ACTIONS_GUIDE.md)

## 📋 Available Versions

| Version | File | Approach | Best For |
|---------|------|----------|----------|
| **🌟 Recommended** | `start_ytm_scobble.py` | YTMusic API (Encrypted) | **Best for security** - Uses encrypted auth file |

---

## 🚀 Quick Start (Recommended)

### Prerequisites

1. Install Python 3.8+ and dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Get your Last.fm API credentials from [Last.fm API](https://www.last.fm/api/account/create)

3. Create a `.env` file:
   ```bash
   LAST_FM_API=your_lastfm_api_key
   LAST_FM_API_SECRET=your_lastfm_api_secret
   ```

### Run Scrobbler

```bash
python start_ytm_scobble.py
```

On first run, you'll be prompted to:
1. **Authenticate with Last.fm** (browser will open automatically)  
2. **Setup YouTube Music auth**: Run `ytmusicapi browser` to create `browser.json`, then use `encrypt_auth.py` to secure it.

**To secure your YouTube Music auth:**
1. Run `python encrypt_auth.py`.
2. This creates `browser.json.enc` and gives you a key.
3. Save the key in `.env` as `YTMUSIC_AUTH_KEY`.
4. You can now safely delete `browser.json`.

### GitHub Actions (Automated Setup)

For automatic, scheduled scrobbling without running the script manually, follow our comprehensive setup guide: [GITHUB_ACTIONS_GUIDE.md](GITHUB_ACTIONS_GUIDE.md)

---

## 🔧 Legacy Version Setup

If you prefer the original YTMusic API approach:

### Additional Setup for Legacy Version

1. Install ytmusicapi and authenticate:
   ```bash
   pip install ytmusicapi==1.10.3
   ytmusicapi browser
   ```
   
2. Follow the [ytmusicapi browser authentication](https://ytmusicapi.readthedocs.io/en/stable/setup/browser.html) instructions to create `browser.json`

3. Run the legacy version:
   ```bash
   python start.py
   ```

---

## 📊 Version Comparison

### 🌟 Standalone Version (`start_standalone.py`)

**✅ Advantages:**
- **No API dependencies** - Direct HTML scraping eliminates API rate limits
- **Multilingual support** - Detects "Today" in 50+ languages (English, Spanish, Chinese, Russian, Arabic, etc.)
- **Smart timestamp distribution**:
  - First-time users: Logarithmic over 24 hours
  - Regular users: Logarithmic over 1 hour
  - Pro users: Linear over 5 minutes
- **Better duplicate detection** - Tracks re-reproductions and position changes
- **Robust error handling** - Categorizes and handles different error types
- **Enhanced logging** - Better visibility into processing and language detection
- **No browser.json needed** - Just requires your browser cookie

**⚠️ Considerations:**
- Requires copying cookie from browser (but provides detailed instructions)
- Cookie needs periodic refresh (browser will notify when needed)

### 📜 Legacy Version (`start.py`)

**✅ Advantages:**
- **Simple setup** - Uses YTMusic API with `browser.json`
- **Established approach** - Original working implementation
- **No cookie handling** - API-based authentication

**⚠️ Limitations:**
- **API dependency** - Subject to rate limits and API changes
- **English-only date detection** - Only recognizes "Today" in English
- **Fixed timestamp intervals** - Simple 90-second spacing
- **Basic error handling** - Limited error categorization
- **Requires ytmusicapi** - Additional dependency for API access

---

## 🗄️ Database Schema

Both versions use SQLite to track scrobbled songs and prevent duplicates:

### Standalone Version Schema
```sql
CREATE TABLE scrobbles (
    id INTEGER PRIMARY KEY,
    track_name TEXT,
    artist_name TEXT,
    album_name TEXT,
    scrobbled_at TEXT DEFAULT CURRENT_TIMESTAMP,
    array_position INTEGER,
    max_array_position INTEGER,          -- NEW: Tracks highest position
    is_first_time_scrobble BOOLEAN       -- NEW: First-time user flag
)
```

### Legacy Version Schema
```sql
CREATE TABLE scrobbles (
    id INTEGER PRIMARY KEY,
    track_name TEXT,
    artist_name TEXT,  
    album_name TEXT,
    scrobbled_at TEXT DEFAULT CURRENT_TIMESTAMP,
    array_position INTEGER
)
```

---

## 📝 How It Works

### Standalone Version Process
1. **Fetches YouTube Music history page** directly via HTTP
2. **Extracts embedded JSON data** from HTML using regex parsing
3. **Detects today's songs** using multilingual date detection (50+ languages)
4. **Smart position tracking** - Identifies new songs and re-reproductions
5. **Calculates intelligent timestamps** - Different strategies for different user types
6. **Scrobbles to Last.fm** with proper error handling and retry logic
7. **Updates database** with enhanced tracking information

### Legacy Version Process  
1. **Uses YTMusic API** to fetch history data
2. **Filters "Today" songs** (English only)
3. **Simple duplicate prevention** based on position
4. **Fixed timestamp intervals** (90 seconds apart)
5. **Basic scrobbling** to Last.fm
6. **Database updates** with basic tracking

---

## 🌍 Multilingual Support (Standalone Only)

The standalone version automatically detects "Today" in these language families:

- **Latin**: English, Spanish, Portuguese, Italian, French, German, Dutch, etc.
- **Cyrillic**: Russian, Ukrainian, Bulgarian, Serbian, etc.
- **Arabic**: Arabic, Persian, Urdu
- **CJK**: Chinese (Simplified/Traditional), Japanese, Korean
- **Indic**: Hindi, Bengali, Tamil, Telugu, etc.
- **Southeast Asian**: Thai, Vietnamese, Indonesian, etc.
- **Others**: Hebrew, Georgian, Armenian, etc.

---

## 🚀 Migration to Encrypted Auth

1. **Secure your auth** - Run `python encrypt_auth.py`
2. **Add to .env file**: `YTMUSIC_AUTH_KEY=your_key_here`
3. **Run scrobbler**: `python start_ytm_scobble.py`
4. **Clean up** - Delete `browser.json`

---

## 🔧 Configuration

### Environment Variables (.env)
```bash
# Required
LAST_FM_API=your_lastfm_api_key
LAST_FM_API_SECRET=your_lastfm_api_secret

# Added automatically after first run
LASTFM_SESSION=your_session_token

# Required for encrypted auth
YTMUSIC_AUTH_KEY=your_aes_key
```

### Files Used
| File | Description |
|------|-------------|
| `.env` | API keys and tokens |
| `browser.json.enc` | Encrypted YTMusic API auth |
| `data.db` | SQLite tracking database |

---

## 🐛 Troubleshooting

### Common Issues

**❌ "Decryption failed"**
- Ensure `YTMUSIC_AUTH_KEY` in `.env` matches the one generated by `encrypt_auth.py`.

**❌ "Authentication failed"**  
- Your YouTube Music session (in the encrypted file) may have expired.
- Refresh your `browser.json` and re-encrypt it.

---

## 📋 Deployment

### GitHub Actions Deployment (Recommended)

Automate scrobbling using GitHub Actions for reliable, serverless execution:

1. **Follow the detailed setup guide:** See [GITHUB_ACTIONS_GUIDE.md](GITHUB_ACTIONS_GUIDE.md) for complete instructions.
2. **The workflow runs on a schedule** (default: every 30 minutes).
3. **Includes error notifications** via Discord webhook.

---

## 🤝 Contributing

Contributions are welcome! Please focus improvements on the standalone version as it's the recommended approach.

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more information.

---

## 🎵 Enjoy Your Scrobbles!

Whether you choose the standalone or legacy version, you'll be able to seamlessly sync your YouTube Music listening history with Last.fm. The standalone version is recommended for its reliability, multilingual support, and smart features, but both versions will get your music scrobbled! 🎶