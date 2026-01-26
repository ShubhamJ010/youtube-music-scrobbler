# YouTube Music to Last.fm Scrobbler 🎵

An intelligent, automated scrobbler that syncs your YouTube Music history to Last.fm. It supports encryption for secure credential storage and can run 24/7 using GitHub Actions.

## ✨ Features

- **Smart Scrobbling**: Tracks position in history to handle replays and avoid duplicates.
- **Secure**: AES-256 encryption for your YouTube Music session cookies.
- **Multilingual Support**: Advanced date detection for 50+ languages.
- **Automated**: Integrated with GitHub Actions for 24/7 synchronization.
- **Discord Notifications**: Get success/failure alerts for automated runs.
- **Lightweight**: Minimal dependencies and efficient SQLite tracking.

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.11+
- A [Last.fm account](https://www.last.fm/)
- [Last.fm API Credentials](https://www.last.fm/api/account/create)

### 2. Setup YouTube Music Authentication
To fetch your history, you need to provide your YouTube Music session headers.

1.  **Generate `browser.json`**:
    Follow the [ytmusicapi setup instructions](https://ytmusicapi.readthedocs.io/en/stable/setup/browser.html).
    Essentially:
    - Open YouTube Music in Chrome.
    - Open Developer Tools (F12) -> Network Tab.
    - Filter for `/browse`.
    - Right-click the request -> Copy -> Copy as cURL (bash).
    - Run `ytmusicapi browser` and paste the command when prompted.
2.  **Encrypt your credentials**:
    ```bash
    python encrypt_auth.py
    ```
    This will create `browser.json.enc` and output an **Encryption Key**.
    - **SAVE THIS KEY!** You will need it for your `.env` or GitHub Secrets.
    - Delete the original `browser.json` file.

### 3. Installation
```bash
git clone https://github.com/yourusername/youtube-music-scrobbler.git
cd youtube-music-scrobbler
pip install -r requirements.txt
```

### 4. Configuration
Create a `.env` file based on `.env.example`:
```ini
LAST_FM_API=your_api_key
LAST_FM_API_SECRET=your_api_secret
YTMUSIC_AUTH_KEY=your_encryption_key
DISCORD_WEBHOOK_URL=your_webhook_url (optional)
```

### 5. First Run
```bash
python start_ytm_scobble.py
```
On the first run, it will open your browser to authorize Last.fm. Once done, a `LASTFM_SESSION` will be saved to your `.env` file.

---

## 🤖 Automation (GitHub Actions)

You can run this scrobbler every 30 minutes automatically using GitHub Actions.

1.  Follow the [**GitHub Actions Guide**](GITHUB_ACTIONS_GUIDE.md) for detailed instructions.
2.  Add your secrets to the repository:
    - `LAST_FM_API`, `LAST_FM_API_SECRET`, `LASTFM_SESSION`
    - `YTMUSIC_AUTH_KEY`, `DISCORD_WEBHOOK_URL`
3.  Commit `browser.json.enc` (but **NEVER** `browser.json`).

---

## 🛠️ Project Structure

- `start_ytm_scobble.py`: Main process and Last.fm OAuth handler.
- `ytmusic_fetcher.py`: Fetches and parses YTM history.
- `scrobble_utils.py`: Logic for smart scrobbling and timestamp generation.
- `encrypt_auth.py`: Tool for securing your YouTube Music credentials.
- `data.db`: Local SQLite database tracking scrobble history.

---

## 🤝 Contributing
Contributions are welcome! Please refer to [AGENTS.md](AGENTS.md) for architectural details if you are using AI assistance.

## 📄 License
MIT License. See [LICENSE](LICENSE) for details.
