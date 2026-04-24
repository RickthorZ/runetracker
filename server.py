"""
server.py
Lightweight Flask API that serves live flow data and DOG price to the frontend.
Run with: python server.py
"""
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import os, sys

sys.path.insert(0, os.path.dirname(__file__))
from tracking_engine import get_flows_json
from price_feed import get_cached_price, update_price
from seed_clusters import seed_database, run_heuristics
from fetch_runes import run as fetch_run
from database import init_db

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/flows')
def api_flows():
    from flask import request
    hours_map = {'24h': 24, '7d': 168, '30d': 720}
    range_param = request.args.get('range', '24h')
    hours = hours_map.get(range_param, 24)
    data = get_flows_json(hours)
    return jsonify(data)

@app.route('/api/wallets')
def api_wallets():
    import sqlite3
    conn = sqlite3.connect(os.path.join(os.path.dirname(__file__), 'runes_data.db'))
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT address, entity_name, reason, balance FROM exchange_clusters ORDER BY entity_name, balance DESC")
        rows = cursor.fetchall()
        wallets = [{"address": r[0], "exchange": r[1], "reason": r[2], "balance": r[3]} for r in rows]
    except sqlite3.OperationalError:
        wallets = [] # Handle case where DB isn't fully migrated yet
    conn.close()
    return jsonify(wallets)

@app.route('/api/price')
def api_price():
    price = get_cached_price()
    return jsonify({"price_usd": price})

@app.route('/api/refresh')
def api_refresh():
    """Manually trigger a full pipeline refresh."""
    update_price()
    fetch_run()
    run_heuristics()
    return jsonify({"status": "ok", "message": "Pipeline refreshed."})

# ── Startup ───────────────────────────────────────────────────────────────────

def bootstrap():
    print("[Server] Bootstrapping pipeline...")
    init_db()
    seed_database()
    update_price()
    fetch_run()
    run_heuristics()
    print("[Server] Bootstrap complete. Starting server...")

if __name__ == '__main__':
    bootstrap()
    app.run(host='0.0.0.0', port=5050, debug=False)
