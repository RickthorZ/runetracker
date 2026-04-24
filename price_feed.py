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

FALLBACK_PRICE = 0.0072  # Last known price — only used if all APIs fail

def fetch_price() -> float:
    """Returns live DOG price in USD. Gate.io is primary source."""

    # 1. Gate.io (Primary)
    try:
        resp = requests.get("https://api.gateio.ws/api/v4/spot/tickers?currency_pair=DOG_USDT", timeout=5)
        if resp.status_code == 200:
            price = float(resp.json()[0]['last'])
            print(f"[Price] Fetched from Gate.io: ${price:.6f}")
            return price
    except Exception as e:
        print(f"[Price] Gate.io failed: {e}")

    # 2. CoinGecko Fallback
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=dog-bitcoin&vs_currencies=usd"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            price = float(resp.json()['dog-bitcoin']['usd'])
            print(f"[Price] Fetched from CoinGecko: ${price:.6f}")
            return price
    except Exception as e:
        print(f"[Price] CoinGecko failed: {e}")

    # 3. Hardcoded Fallback
    print(f"[Price] All APIs failed. Using hardcoded fallback: ${FALLBACK_PRICE}")
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
