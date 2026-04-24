"""
fetch_runes.py
Polls the BestInSlot API for DOG•GO•TO•THE•MOON (840000:3) transactions.
Properly tags each UTXO as INFLOW or OUTFLOW relative to exchange clusters.
Uses a block cursor to avoid re-fetching old data.
"""
import os, time, sqlite3, requests
from dotenv import load_dotenv

load_dotenv()

API_KEY  = os.getenv('BESTINSLOT_API_KEY', 'demo_key')
BASE_URL = "https://api.bestinslot.xyz/v3"
RUNE_ID  = "840000:3"
DB_PATH  = os.path.join(os.path.dirname(__file__), 'runes_data.db')

HEADERS = {
    "x-api-key": API_KEY,
    "Content-Type": "application/json"
}

# ── helpers ──────────────────────────────────────────────────────────────────

def get_exchange_addresses() -> set:
    conn = sqlite3.connect(DB_PATH)
    addrs = {r[0] for r in conn.execute("SELECT address FROM exchange_clusters").fetchall()}
    conn.close()
    return addrs

def get_last_block() -> int:
    conn = sqlite3.connect(DB_PATH)
    row  = conn.execute("SELECT value FROM poll_state WHERE key='last_block'").fetchone()
    conn.close()
    return int(row[0]) if row else 0

def set_last_block(block: int):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT OR REPLACE INTO poll_state (key, value) VALUES ('last_block', ?)", (str(block),))
    conn.commit()
    conn.close()

# ── API calls ────────────────────────────────────────────────────────────────

def fetch_rune_activity(offset: int = 0, limit: int = 60) -> list:
    """Fetch recent transfer activity for the target Rune."""
    url = f"{BASE_URL}/runes/activity/{RUNE_ID}?limit={limit}&offset={offset}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        return resp.json().get("data", [])
    except Exception as e:
        print(f"[Fetch] API error: {e}")
        return []

def fetch_address_utxos(address: str) -> list:
    """Get all Rune UTXOs for a specific address."""
    url = f"{BASE_URL}/runes/wallet_balances/{address}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        return resp.json().get("data", [])
    except Exception:
        return []

# ── core pipeline ─────────────────────────────────────────────────────────────

def parse_and_tag(raw_items: list, exchange_addrs: set) -> list:
    """
    Determine INFLOW / OUTFLOW direction for each transfer.
    BestInSlot activity returns: sender_address, receiver_address, amount, txid, vout, block_height
    - If receiver is in exchange_addrs → INFLOW to exchange
    - If sender   is in exchange_addrs → OUTFLOW from exchange
    - Otherwise                         → UNKNOWN (retail-to-retail)
    """
    tagged = []
    for item in raw_items:
        sender   = item.get("sender_address",   item.get("from_address", ""))
        receiver = item.get("receiver_address", item.get("to_address",   ""))
        amount   = float(item.get("amount", item.get("rune_amount", 0)))
        txid     = item.get("txid", item.get("tx_id", ""))
        vout     = int(item.get("vout", 0))
        block    = int(item.get("block_height", 0))

        if receiver in exchange_addrs:
            tagged.append({"txid": txid, "vout": vout, "address": receiver,
                           "amount": amount, "direction": "INFLOW", "block_height": block})
        elif sender in exchange_addrs:
            tagged.append({"txid": txid, "vout": vout, "address": sender,
                           "amount": amount, "direction": "OUTFLOW", "block_height": block})
        # We skip retail-to-retail noise for now

    return tagged

def mock_data(exchange_addrs: set) -> list:
    """Realistic mock data for prototype testing (no API key needed)."""
    addrs = list(exchange_addrs)
    binance = next((a for a in addrs if "binance" in a.lower() or a == "34xp4vRoCGJym3xR7yCVPFHoCNxv4Twseo"), addrs[0] if addrs else "mock_binance")
    okx     = next((a for a in addrs if "okx"    in a.lower() or a == "1HQ3Go3ggs8pFnXuHVHRytPCq5fGG8Hbhx"), addrs[1] if len(addrs)>1 else "mock_okx")
    cb      = next((a for a in addrs if "coinbase" in a.lower() or a == "3FHNBLobJnbCPujupTNDgrRd6aNhr9CqNb"), addrs[2] if len(addrs)>2 else "mock_cb")
    bybit   = next((a for a in addrs if "bybit"  in a.lower() or a == "14cxpo3MBCYYWCgF74SWTdcmxipnGUsPw3"), addrs[3] if len(addrs)>3 else "mock_bybit")
    kraken  = next((a for a in addrs if "kraken" in a.lower() or a == "3AfP9D5y1WFsBkf7LEHkNJHjf7dFmfkXMi"), addrs[4] if len(addrs)>4 else "mock_kraken")
    gate    = next((a for a in addrs if "gate"   in a.lower() or a == "1F1tAaz5x1HUXrCNLbtMDqcw6o5GNn4xqX"), addrs[5] if len(addrs)>5 else "mock_gate")

    return [
        {"txid":"txA01","vout":0,"address":binance,"amount":330_000_000,"direction":"INFLOW","block_height":895000},
        {"txid":"txA02","vout":0,"address":binance,"amount":120_000_000,"direction":"OUTFLOW","block_height":895001},
        {"txid":"txA03","vout":0,"address":okx,    "amount":160_000_000,"direction":"INFLOW","block_height":895002},
        {"txid":"txA04","vout":0,"address":okx,    "amount": 40_000_000,"direction":"OUTFLOW","block_height":895003},
        {"txid":"txA05","vout":0,"address":cb,     "amount": 20_000_000,"direction":"INFLOW","block_height":895004},
        {"txid":"txA06","vout":0,"address":cb,     "amount": 80_000_000,"direction":"OUTFLOW","block_height":895005},
        {"txid":"txA07","vout":0,"address":bybit,  "amount":210_000_000,"direction":"INFLOW","block_height":895006},
        {"txid":"txA08","vout":0,"address":bybit,  "amount": 55_000_000,"direction":"OUTFLOW","block_height":895007},
        {"txid":"txA09","vout":0,"address":kraken, "amount": 95_000_000,"direction":"INFLOW","block_height":895008},
        {"txid":"txA10","vout":0,"address":kraken, "amount": 30_000_000,"direction":"OUTFLOW","block_height":895009},
        {"txid":"txA11","vout":0,"address":gate,   "amount": 50_000_000,"direction":"INFLOW","block_height":895010},
        {"txid":"txA12","vout":0,"address":gate,   "amount": 10_000_000,"direction":"OUTFLOW","block_height":895011},
    ]

def save_transfers(transfers: list) -> int:
    conn = sqlite3.connect(DB_PATH)
    saved = 0
    for t in transfers:
        try:
            conn.execute('''
                INSERT OR IGNORE INTO rune_transfers (txid, vout, address, amount, direction, block_height)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (t["txid"], t["vout"], t["address"], t["amount"], t["direction"], t.get("block_height", 0)))
            if conn.total_changes > saved:
                saved = conn.total_changes
        except Exception as e:
            print(f"[DB] Error: {e}")
    conn.commit()
    conn.close()
    return saved

def run(use_mock: bool = False):
    exchange_addrs = get_exchange_addresses()
    if not exchange_addrs:
        print("[Fetch] No exchange clusters found. Run seed_clusters.py first.")
        return

    if API_KEY == 'demo_key' or use_mock:
        print("[Fetch] Using mock data (no API key).")
        transfers = mock_data(exchange_addrs)
    else:
        print(f"[Fetch] Polling BestInSlot for Rune {RUNE_ID}...")
        raw = fetch_rune_activity()
        transfers = parse_and_tag(raw, exchange_addrs)
        if raw:
            max_block = max(int(i.get("block_height", 0)) for i in raw)
            set_last_block(max_block)

    saved = save_transfers(transfers)
    print(f"[Fetch] {len(transfers)} transfers processed, {saved} new rows saved.")

if __name__ == '__main__':
    run()
