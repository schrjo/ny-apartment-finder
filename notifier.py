"""Notifier helpers: send Telegram messages or fallback to stdout."""
from __future__ import annotations
import os
import time
import requests
from typing import Dict, List
from dotenv import load_dotenv


load_dotenv()


def _telegram_config() -> tuple[str | None, str | None, float]:
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    delay = float(os.getenv("TELEGRAM_DELAY", "0.5"))
    return bot_token, chat_id, delay

def _notify_telegram(listings: List[Dict]) -> bool:
    """Send notifications via Telegram bot API (one message per listing).

    Requires `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` env vars. Returns
    True if at least one message was sent successfully.
    """
    bot_token, chat_id, delay = _telegram_config()
    if not (bot_token and chat_id):
        return False

    sent = False
    errors = 0
    for idx, l in enumerate(listings):
        title = l.get("title") or "(no title)"
        url = l.get("url") or ""
        source = l.get("source") or "listing"
        parts = [f"[{source}] <b>{title}</b>"]
        if l.get("price"):
            parts.append(f"Price: {l.get('price')}")
        parts.append(url)
        text = "\n".join(parts)

        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        try:
            r = requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", data=payload, timeout=10)
            r.raise_for_status()
            sent = True
        except Exception as exc:
            errors += 1
            if errors == 1:
                print(f"Telegram send failed: {exc}")

        if idx < len(listings) - 1 and delay > 0:
            time.sleep(delay)

    return sent

def notify(listings: List[Dict]) -> None:
    """Notify about new listings via Telegram.
    If Telegram is not configured, falls back to printing to stdout.
    """
    if not listings:
        return

    telegram_sent = False

    bot_token, chat_id, _ = _telegram_config()
    if bot_token and chat_id:
        telegram_sent = _notify_telegram(listings)

    if not telegram_sent:
        # Fallback: print to stdout so CI logs show them
        for l in listings:
            print("NEW LISTING:")
            print(f"- {l.get('title')}")
            print(f"  {l.get('url')}")
            if l.get("price"):
                print(f"  Price: {l.get('price')}")
