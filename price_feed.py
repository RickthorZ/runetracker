"""
price_feed.py
Fetches the live DOG•GO•TO•THE•MOON price in USD from CoinGecko (free, no key required)
and caches it in the SQLite database.
"""
import sqlite3
import requests
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'runes_data.db')

# CoinGecko free endpoint for DOG rune price
# DOG is listed under the Runes market — we use the generic Bitcoin price
# and apply the DOG/BTC ratio from Magic Eden's free endpoint.
COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
MAGIC_EDEN_URL = "https://api-mainnet.magiceden.dev/v2/ord/btc/runes/market/DOG%E2%80%A2GO%E2%80%A2TO%E2%80%A2THE%E2%80%A2MOON/info"

FALLBACK_PRICE = 0.0072  # Last known price — only used if both APIs fail

def fetch_price() -> float:
    """Returns live DOG price in USD. Falls back gracefully."""
    try:
        # Attempt Magic Eden first (most accurate for Rune-specific price)
        resp = requests.get(MAGIC_EDEN_URL, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        price_sats = float(data.get("floorPrice", 0))
        if price_sats > 0:
            # Convert sats/DOG to USD/DOG using BTC price
            btc_usd = _get_btc_price()
            price_usd = (price_sats / 1e8) * btc_usd
            print(f"[Price] DOG price via Magic Eden: ${price_usd:.6f}")
            return price_usd
    except Exception as e:
        print(f"[Price] Magic Eden failed: {e}")

    try:
        # Fallback: use CoinGecko for BTC price × a hardcoded DOG/BTC estimate
        btc_usd = _get_btc_price()
        # ~16,000 sats per DOG as a reasonable mid estimate
        price_usd = (16000 / 1e8) * btc_usd
        print(f"[Price] DOG price estimated via BTC: ${price_usd:.6f}")
        return price_usd
    except Exception as e:
        print(f"[Price] BTC fallback failed: {e}")

    print(f"[Price] Using hardcoded fallback: ${FALLBACK_PRICE}")
    return FALLBACK_PRICE

def _get_btc_price() -> float:
    resp = requests.get(COINGECKO_URL, timeout=5)
    resp.raise_for_status()
    return float(resp.json()["bitcoin"]["usd"])

def save_price(price_usd: float):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO price_cache (id, price_usd, updated_at)
        VALUES (1, ?, ?)
        ON CONFLICT(id) DO UPDATE SET price_usd=excluded.price_usd, updated_at=excluded.updated_at
    ''', (price_usd, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def get_cached_price() -> float:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    row = cursor.execute("SELECT price_usd FROM price_cache WHERE id=1").fetchone()
    conn.close()
    return row[0] if row else FALLBACK_PRICE

def update_price():
    price = fetch_price()
    save_price(price)
    return price

if __name__ == '__main__':
    p = update_price()
    print(f"[Price] Saved: ${p:.8f} USD per DOG")
