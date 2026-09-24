import logging
import os
import time
from datetime import datetime, timezone

from .db import connect, initialize
from .importer import enqueue, run_once


def tick():
    with connect() as db:
        row = db.execute("SELECT * FROM schedule WHERE id=1 FOR UPDATE").fetchone()
        db.execute("UPDATE schedule SET last_tick=now() WHERE id=1")
        if row["enabled"] and row["next_run"] <= datetime.now(timezone.utc):
            # This is a named sample feed. It never pretends to be live fleet data.
            stamp = datetime.now(timezone.utc).replace(microsecond=0)
            reading = "DEMO-" + stamp.strftime("%Y%m%d%H%M%S")
            raw = "reading_id,vehicle_id,recorded_at,miles,fuel_gallons\n"
            raw += f"{reading},VAN-01,{stamp.isoformat()},142.6,11.2\n"
            enqueue("Scheduled sample feed", raw)
            db.execute("UPDATE schedule SET next_run=now()+interval '1 second'*interval_seconds WHERE id=1")
    return run_once()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    while True:
        try:
            initialize()
            break
        except Exception:
            logging.warning("Waiting for the database")
            time.sleep(3)
    while True:
        try:
            tick()
        except Exception:
            logging.exception("Worker will retry in three seconds")
        time.sleep(3)
