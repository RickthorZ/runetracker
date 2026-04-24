"""
scheduler.py
Runs the full data pipeline on a 10-minute cycle in the background.
Start with: python scheduler.py
"""
import schedule, time, sys, os
sys.path.insert(0, os.path.dirname(__file__))

from price_feed import update_price
from fetch_runes import run as fetch_run
from seed_clusters import run_heuristics

def run_pipeline():
    print("\n[Scheduler] ▶ Running pipeline cycle...")
    update_price()
    fetch_run()
    run_heuristics()
    print("[Scheduler] ✔ Cycle complete.\n")

if __name__ == '__main__':
    print("[Scheduler] Starting. Pipeline will run every 10 minutes.")
    run_pipeline()  # Run immediately on start
    schedule.every(10).minutes.do(run_pipeline)
    while True:
        schedule.run_pending()
        time.sleep(30)
