import os
import time
import random
import threading
import subprocess
import urllib.request
import requests as std_requests
from datetime import datetime
from playwright.sync_api import sync_playwright, Response

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # fall back to system environment variables

# ════════════════════════════════════════════════════════════
#  CONFIG  — set these in a .env file (copy .env.example)
# ════════════════════════════════════════════════════════════
TELEGRAM_TOKEN    = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID  = os.getenv("TELEGRAM_CHAT_ID", "")
DISCORD_WEBHOOK   = os.getenv("DISCORD_WEBHOOK", "")

_missing = [k for k, v in {
    "TELEGRAM_TOKEN": TELEGRAM_TOKEN,
    "TELEGRAM_CHAT_ID": TELEGRAM_CHAT_ID,
    "DISCORD_WEBHOOK": DISCORD_WEBHOOK,
}.items() if not v]
if _missing:
    raise SystemExit(
        f"Missing required environment variables: {', '.join(_missing)}\n"
        "Copy .env.example to .env and fill in your credentials."
    )

CHECK_IN_URL      = "https://admission.1337.ma/candidature/check-in"
SLOTS_ENDPOINT    = "available-slots"
USER_DATA_DIR     = "1337_profile"

MIN_INTERVAL      = 2
MAX_INTERVAL      = 5

ALERT_REPEATS     = 20
ALERT_DELAY       = 0.5
# ════════════════════════════════════════════════════════════


# ── Detect system proxy automatically ────────────────────────
def get_system_proxies():
    """Auto-detect system proxy (handles school/work networks)."""
    proxies = urllib.request.getproxies()
    if proxies:
        log(f"Using system proxy: {proxies}", "INFO")
    return proxies or None

SYSTEM_PROXIES = None  # set after first log call


# ── Logging ──────────────────────────────────────────────────
LOG_SEPARATOR = "─" * 52

def log(msg: str, level: str = "INFO"):
    icons = {"INFO": "·", "OK": "✅", "WARN": "⚠️ ",
             "ERROR": "❌", "ALERT": "🚨", "SEND": "📨",
             "WAIT": "⏳", "START": "🟢"}
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{ts}] {icons.get(level,'·')}  {msg}", flush=True)

def log_section(title: str):
    print(f"\n{LOG_SEPARATOR}", flush=True)
    print(f"  {title}", flush=True)
    print(f"{LOG_SEPARATOR}", flush=True)


# ── Local alert (sound + popup — works with no internet) ─────
def local_alert(slot_count: int):
    """Beep + Windows popup as instant local fallback."""
    try:
        import winsound
        for _ in range(10):
            winsound.Beep(1000, 400)
            time.sleep(0.1)
    except Exception:
        # Non-Windows fallback: terminal bell
        print("\a" * 10, flush=True)

    try:
        # Windows toast notification
        subprocess.Popen([
            "powershell", "-Command",
            f"Add-Type -AssemblyName System.Windows.Forms; "
            f"[System.Windows.Forms.MessageBox]::Show("
            f"'{slot_count} SLOT(S) AVAILABLE AT 1337.ma — BOOK NOW!', "
            f"'🚨 SLOTS FOUND', 'OK', 'Exclamation')"
        ])
    except Exception:
        pass


# ── Telegram ──────────────────────────────────────────────────
def send_telegram(message: str) -> bool:
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        r = std_requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
        }, timeout=10, proxies=SYSTEM_PROXIES)
        r.raise_for_status()
        return True
    except Exception as e:
        log(f"Telegram error: {e}", "WARN")
        return False


# ── Discord ───────────────────────────────────────────────────
def send_discord(message: str) -> bool:
    try:
        r = std_requests.post(DISCORD_WEBHOOK, json={
            "content": message,
            "username": "1337 Slot Monitor",
        }, timeout=10, proxies=SYSTEM_PROXIES)
        r.raise_for_status()
        return True
    except Exception as e:
        log(f"Discord error: {e}", "WARN")
        return False


# ── Spam alert burst ──────────────────────────────────────────
def spam_alerts(slots: list, now: str, check_count: int):
    tg_msg = (
        f"🚨🚨🚨 <b>SLOTS AVAILABLE — 1337.ma</b> 🚨🚨🚨\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📅 <b>{len(slots)} slot(s)</b> open RIGHT NOW\n"
        f"🕐 Detected at {now}  |  check #{check_count}\n"
        f"🔗 {CHECK_IN_URL}\n\n"
        f"⚡ <b>BOOK NOW BEFORE THEY'RE GONE!</b>"
    )
    dc_msg = (
        f"🚨🚨🚨 **SLOTS AVAILABLE — 1337.ma** 🚨🚨🚨\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📅 **{len(slots)} slot(s)** open RIGHT NOW\n"
        f"🕐 Detected at {now}  |  check #{check_count}\n"
        f"🔗 {CHECK_IN_URL}\n\n"
        f"⚡ **BOOK NOW BEFORE THEY'RE GONE!**"
    )

    # 🔊 Local alert fires INSTANTLY — no network needed
    local_thread = threading.Thread(target=local_alert, args=(len(slots),), daemon=True)
    local_thread.start()

    log_section(f"🚨  ALERT BURST — {len(slots)} slot(s)  🚨")

    success_tg = 0
    success_dc = 0

    for i in range(1, ALERT_REPEATS + 1):
        tg_ok = send_telegram(tg_msg)
        dc_ok = send_discord(dc_msg)

        if tg_ok: success_tg += 1
        if dc_ok: success_dc += 1

        channels = []
        if tg_ok: channels.append("Telegram")
        if dc_ok: channels.append("Discord")
        result = " + ".join(channels) if channels else "FAILED (network?)"

        log(f"Alert {i:02d}/{ALERT_REPEATS} → {result}  "
            f"[TG:{success_tg} DC:{success_dc}]", "SEND")

        if i < ALERT_REPEATS:
            time.sleep(ALERT_DELAY)

    log_section(
        f"Burst done — TG: {success_tg}/{ALERT_REPEATS}  "
        f"DC: {success_dc}/{ALERT_REPEATS}"
    )


# ── Slot parser ───────────────────────────────────────────────
def parse_slots(data) -> list:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("data", "slots", "available_slots"):
            if key in data and isinstance(data[key], list):
                return data[key]
    return []


# ── Main ──────────────────────────────────────────────────────
def main():
    global SYSTEM_PROXIES
    log_section(f"1337 Slot Monitor  |  browser intercept  |  {MIN_INTERVAL}–{MAX_INTERVAL}s")

    SYSTEM_PROXIES = get_system_proxies()

    captured = {"slots": None}

    def handle_response(response: Response):
        if SLOTS_ENDPOINT in response.url:
            try:
                captured["slots"] = parse_slots(response.json())
            except Exception:
                pass

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=False,
            channel="chrome",
            args=["--disable-blink-features=AutomationControlled"],
        )

        page = browser.new_page()
        page.on("response", handle_response)

        log(f"Opening {CHECK_IN_URL}", "START")
        page.goto(CHECK_IN_URL, wait_until="domcontentloaded")
        log("Complete login / Cloudflare in the browser if needed.", "WARN")
        input("\n  ↳ Once you're on the check-in page, press ENTER...\n")

        log_section("Monitoring started")

        startup_msg = (
            f"🟢 <b>Slot monitor active</b>\n"
            f"Interval: {MIN_INTERVAL}–{MAX_INTERVAL}s random\n"
            f"Alert burst: {ALERT_REPEATS}×  every {ALERT_DELAY}s → Telegram + Discord + local sound"
        )
        tg_up = send_telegram(startup_msg)
        dc_up = send_discord(startup_msg.replace("<b>","**").replace("</b>","**"))
        log(f"Startup ping → Telegram: {'✅' if tg_up else '❌'}  Discord: {'✅' if dc_up else '❌'}", "INFO")

        alerted      = False
        alert_thread = None
        check_count  = 0
        empty_streak = 0

        while True:
            check_count += 1
            captured["slots"] = None

            try:
                page.reload(wait_until="domcontentloaded")
                page.wait_for_timeout(1500)

                slots = captured["slots"]
                now   = datetime.now().strftime("%H:%M:%S")

                if slots is None:
                    log(f"No API response captured — check #{check_count}", "WARN")

                elif len(slots) > 0:
                    empty_streak = 0
                    if not alerted:
                        alerted = True
                        log(f"SLOTS FOUND: {len(slots)} — launching alert burst!", "ALERT")
                        alert_thread = threading.Thread(
                            target=spam_alerts,
                            args=(slots, now, check_count),
                            daemon=True,
                        )
                        alert_thread.start()
                    else:
                        log(f"{len(slots)} slot(s) still open — check #{check_count}", "OK")

                else:
                    empty_streak += 1
                    if alerted:
                        alerted = False
                        gone_msg = "ℹ️ Slots are <b>gone</b>. Still watching..."
                        send_telegram(gone_msg)
                        send_discord(gone_msg.replace("<b>","**").replace("</b>","**"))
                        log("Slots gone — alert state reset", "WARN")

                    bar = ("." * (empty_streak % 10)) or "|"
                    log(f"[ ] Empty  check #{check_count:04d}  streak {empty_streak}  {bar}", "WAIT")

            except KeyboardInterrupt:
                log("Stopped by user.", "WARN")
                if alert_thread and alert_thread.is_alive():
                    alert_thread.join(timeout=2)
                browser.close()
                return

            except Exception as e:
                err = str(e)
                log(f"{err[:120]}", "ERROR")
                if "429" in err:
                    backoff = random.randint(60, 120)
                    log(f"Rate-limited — backing off {backoff}s", "WARN")
                    time.sleep(backoff)
                    continue

            wait = round(random.uniform(MIN_INTERVAL, MAX_INTERVAL), 2)
            log(f"Next check in {wait}s", "INFO")
            time.sleep(wait)


if __name__ == "__main__":
    main()