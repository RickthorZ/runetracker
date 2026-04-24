import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'runes_data.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Raw Rune transfers with proper UTXO direction
    cursor.execute('DROP TABLE IF EXISTS rune_transfers')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS rune_transfers (
        txid        TEXT,
        vout        INTEGER,
        address     TEXT,
        amount      REAL,
        direction   TEXT CHECK(direction IN ('INFLOW','OUTFLOW','UNKNOWN')),
        block_height INTEGER,
        timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (txid, vout)
    )
    ''')

    # Exchange wallet clusters
    cursor.execute('DROP TABLE IF EXISTS exchange_clusters')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS exchange_clusters (
        address         TEXT PRIMARY KEY,
        entity_name     TEXT,
        confidence_score REAL,
        is_seed         INTEGER DEFAULT 0,
        reason          TEXT,
        balance         REAL DEFAULT 0
    )
    ''')

    # Time-series aggregated flows (per exchange, per hour)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS aggregated_flows (
        timestamp   DATETIME,
        entity_name TEXT,
        net_flow    REAL,
        inflow      REAL,
        outflow     REAL,
        PRIMARY KEY (timestamp, entity_name)
    )
    ''')

    # Live price cache
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS price_cache (
        id          INTEGER PRIMARY KEY DEFAULT 1,
        price_usd   REAL,
        updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Polling cursor — tracks the last fetched block so we never re-fetch
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS poll_state (
        key     TEXT PRIMARY KEY,
        value   TEXT
    )
    ''')
    cursor.execute("INSERT OR IGNORE INTO poll_state (key, value) VALUES ('last_block', '0')")

    conn.commit()
    conn.close()
    print(f"[DB] Initialized at {DB_PATH}")

if __name__ == '__main__':
    init_db()
