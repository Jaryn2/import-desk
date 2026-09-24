"""Measure a vehicle lookup before and after adding an index on sample data."""
import json
from pathlib import Path
import statistics
import sys
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))
def settings():
    return dict(line.split('=', 1) for line in (Path(__file__).resolve().parents[1]/'.env.test').read_text().splitlines() if '=' in line and not line.startswith('#'))
import psycopg


def run():
    config = settings()
    with psycopg.connect(host="127.0.0.1",port=54402,user="portfolio",password=config["DB_PASSWORD"],dbname="importdesk_test") as db:
        # A temporary table keeps the demo and its saved readings untouched.
        db.execute("CREATE TEMP TABLE benchmark_readings AS SELECT n AS reading_id,'VAN-'||(n % 1000) AS vehicle_id,now()-n*interval '1 minute' AS recorded_at FROM generate_series(1,200000) AS n")
        db.execute("ANALYZE benchmark_readings")
        query="EXPLAIN (ANALYZE,BUFFERS,FORMAT JSON) SELECT * FROM benchmark_readings WHERE vehicle_id='VAN-42' ORDER BY recorded_at DESC LIMIT 20"
        before=[db.execute(query).fetchone()[0][0] for _ in range(6)]
        db.execute("CREATE INDEX ON benchmark_readings(vehicle_id,recorded_at DESC)")
        db.execute("ANALYZE benchmark_readings")
        after=[db.execute(query).fetchone()[0][0] for _ in range(6)]
        result={"recorded_at":datetime.now(timezone.utc).isoformat(),"dataset":"200,000 generated rows; 1,000 vehicles; local PostgreSQL 17.11", "method":"Six EXPLAIN ANALYZE runs per case. Median of the last five; first run warms the cache.",
                "before_ms":statistics.median(row["Execution Time"] for row in before[1:]),"after_ms":statistics.median(row["Execution Time"] for row in after[1:]),
                "before_plan":before[-1],"after_plan":after[-1],"limit":"Synthetic local measurement. Not a production result or a guarantee on another machine."}
        output=Path(__file__).resolve().parents[1]/"docs/query-benchmark.json"
        output.write_text(json.dumps(result,indent=2))
        print(json.dumps({key:value for key,value in result.items() if not key.endswith("_plan")},indent=2))


if __name__=="__main__":
    run()
