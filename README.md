# 1337 Check-In Slot Monitor

Automatically monitors the [1337.ma](https://admission.1337.ma/candidature/check-in) check-in page and blasts alerts the moment a slot becomes available — via Telegram, Discord, and a local Windows sound/popup.

---

## How it works

- Opens the check-in page in a real Chrome window (so Cloudflare passes without issues)
- Intercepts the `available-slots` API response on every page reload
- If slots are found, fires an **alert burst** (20 messages, 0.5 s apart) to Telegram + Discord simultaneously, plus an instant local beep and popup
- Reloads the page every 2–5 seconds (randomized) to stay under the radar
- Persists your Chrome session in `1337_profile/` so you only log in once

---

## Requirements

- Python 3.8+
- Google Chrome installed
- A Telegram bot token + chat ID
- A Discord webhook URL

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/MostafaElBakhti/ta3sa_bot.git
cd ta3sa_bot
```

### 2. Create and activate a virtual environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux / macOS
python -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install playwright requests python-dotenv
playwright install chromium
```

### 4. Configure credentials

Copy the example env file and fill in your values:

```bash
cp .env.example .env
```

Open `.env` and set:

```
TELEGRAM_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
DISCORD_WEBHOOK=https://discord.com/api/webhooks/...
```

**How to get these:**

| Credential | How to get it |
|---|---|
| `TELEGRAM_TOKEN` | Message [@BotFather](https://t.me/BotFather) → `/newbot` → copy the token |
| `TELEGRAM_CHAT_ID` | Message [@userinfobot](https://t.me/userinfobot) → copy the `id` field |
| `DISCORD_WEBHOOK` | Channel Settings → Integrations → Webhooks → New Webhook → Copy URL |

---

## Running

```bash
python ta3sa.py
```

On first run, Chrome opens and navigates to the check-in page. If a login or Cloudflare challenge appears, **complete it manually** in the browser. Once you see the normal check-in page, switch back to the terminal and press **ENTER** to start monitoring.

From that point on the bot runs silently, printing a one-line status after each check.

---

## Configuration options

All tunable constants are at the top of `ta3sa.py`:

| Variable | Default | Description |
|---|---|---|
| `MIN_INTERVAL` | `2` | Minimum seconds between checks |
| `MAX_INTERVAL` | `5` | Maximum seconds between checks |
| `ALERT_REPEATS` | `20` | Number of alert messages sent per burst |
| `ALERT_DELAY` | `0.5` | Seconds between each alert message |
| `USER_DATA_DIR` | `1337_profile` | Chrome profile folder (keeps session alive) |

---

## Stopping

Press `Ctrl+C` in the terminal.

---

## Notes

- `1337_profile/` stores your Chrome session and is excluded from git via `.gitignore`. Never commit it — it contains cookies and login data.
- The bot works behind a system proxy automatically (school/work networks).
- On non-Windows systems the local sound falls back to a terminal bell (`\a`).
