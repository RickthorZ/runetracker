"""
tracking_engine.py
Calculates inflow/outflow and net accumulation per exchange using actual
UTXO direction tags stored in rune_transfers.direction.
"""
import sqlite3, os
import pandas as pd
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), 'runes_data.db')

def calculate_flows(hours: int = 24):
    conn = sqlite3.connect(DB_PATH)

    cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()

    query = '''
        SELECT
            t.address,
            t.amount,
            t.direction,
            t.timestamp,
            c.entity_name
        FROM rune_transfers t
        INNER JOIN exchange_clusters c ON t.address = c.address
        WHERE t.timestamp >= ?
    '''
    df = pd.read_sql_query(query, conn, params=(cutoff,))
    conn.close()

    if df.empty:
        print("[Engine] No data in window. Returning empty frame.")
        return pd.DataFrame(columns=["entity_name","inflow","outflow","net_flow"])

    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0)

    # Use the direction field — no more amount-based guessing
    df['inflow']  = df.apply(lambda r: float(r['amount']) if r['direction'] == 'INFLOW'  else 0.0, axis=1)
    df['outflow'] = df.apply(lambda r: float(r['amount']) if r['direction'] == 'OUTFLOW' else 0.0, axis=1)
    df['net_flow'] = df['inflow'] - df['outflow']

    summary = df.groupby('entity_name').agg(
        inflow=('inflow',  'sum'),
        outflow=('outflow','sum'),
        net_flow=('net_flow','sum')
    ).reset_index()

    # Persist to DB
    _save_flows(summary, hours)

    print(f"[Engine] Flow summary ({hours}h):")
    print(summary.to_string(index=False))
    return summary

def _save_flows(df: pd.DataFrame, hours: int):
    conn = sqlite3.connect(DB_PATH)
    ts = datetime.utcnow().isoformat()
    for _, row in df.iterrows():
        conn.execute('''
            INSERT OR REPLACE INTO aggregated_flows (timestamp, entity_name, net_flow, inflow, outflow)
            VALUES (?, ?, ?, ?, ?)
        ''', (ts, row['entity_name'], row['net_flow'], row['inflow'], row['outflow']))
    conn.commit()
    conn.close()

def get_flows_json(hours: int = 24) -> dict:
    """Returns flow data as a dict ready for JSON serialization."""
    df = calculate_flows(hours)
    from price_feed import get_cached_price
    price = get_cached_price()

    exchanges = []
    for _, row in df.iterrows():
        exchanges.append({
            "name":     row["entity_name"],
            "inflow":   row["inflow"],
            "outflow":  row["outflow"],
            "net_flow": row["net_flow"],
            "inflow_usd":   round(row["inflow"]   * price, 2),
            "outflow_usd":  round(row["outflow"]  * price, 2),
            "net_flow_usd": round(row["net_flow"] * price, 2),
        })

    total_inflow  = df["inflow"].sum()
    total_outflow = df["outflow"].sum()
    return {
        "price_usd":      price,
        "hours":          hours,
        "total_inflow":   total_inflow,
        "total_outflow":  total_outflow,
        "net_accumulation": total_inflow - total_outflow,
        "total_inflow_usd":   round(total_inflow  * price, 2),
        "total_outflow_usd":  round(total_outflow * price, 2),
        "net_accumulation_usd": round((total_inflow - total_outflow) * price, 2),
        "exchanges": exchanges
    }

if __name__ == '__main__':
    calculate_flows(24)
