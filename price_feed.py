"""
price_feed.py
Fetches the live DOG•GO•TO•THE•MOON price in USD.
Cascades through multiple free, keyless APIs until one responds.
"""
import sqlite3
import requests
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'runes_data.db')

FALLBACK_PRICE = 0.000788  # Updated fallback based on last known live price

def fetch_price() -> float:
    """Returns live DOG price in USD. Tries CoinPaprika → DexScreener → Gate.io → CoinGecko."""

    # 1. CoinPaprika (Best free aggregator — whitelisted on PythonAnywhere, no key needed)
    try:
        resp = requests.get("https://api.coinpaprika.com/v1/tickers/dog-dog-bitcoin", timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            price = float(data['quotes']['USD']['price'])
            print(f"[Price] Fetched from CoinPaprika: ${price:.6f}")
            return price
    except Exception as e:
        print(f"[Price] CoinPaprika failed: {e}")

    # 2. DexScreener (100% free, 300 req/min, great for on-chain tokens)
    try:
        resp = requests.get("https://api.dexscreener.com/latest/dex/search?q=DOG%20bitcoin", timeout=8)
        if resp.status_code == 200:
            pairs = resp.json().get('pairs', [])
            if pairs:
                price = float(pairs[0]['priceUsd'])
                print(f"[Price] Fetched from DexScreener: ${price:.6f}")
                return price
    except Exception as e:
        print(f"[Price] DexScreener failed: {e}")

    # 3. Gate.io (Direct CEX feed)
    try:
        resp = requests.get("https://api.gateio.ws/api/v4/spot/tickers?currency_pair=DOG_USDT", timeout=5)
        if resp.status_code == 200:
            price = float(resp.json()[0]['last'])
            print(f"[Price] Fetched from Gate.io: ${price:.6f}")
            return price
    except Exception as e:
        print(f"[Price] Gate.io failed: {e}")

    # 4. CoinGecko (rate-limited on free tier but good backup)
    try:
        resp = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=dog-bitcoin&vs_currencies=usd", timeout=5)
        if resp.status_code == 200:
            price = float(resp.json()['dog-bitcoin']['usd'])
            print(f"[Price] Fetched from CoinGecko: ${price:.6f}")
            return price
    except Exception as e:
        print(f"[Price] CoinGecko failed: {e}")

    # 5. Hardcoded Fallback
    print(f"[Price] All APIs failed. Using fallback: ${FALLBACK_PRICE}")
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
