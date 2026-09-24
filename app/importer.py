import csv
import hashlib
import io
import json
import re
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from psycopg.types.json import Jsonb
from .db import connect

COLUMNS = ["reading_id", "vehicle_id", "recorded_at", "miles", "fuel_gallons"]


def enqueue(name: str, raw: str):
    digest = hashlib.sha256(raw.encode()).hexdigest()
    with connect() as db:
        row = db.execute(
            "INSERT INTO jobs(id,source_name,raw_csv,digest) VALUES (%s,%s,%s,%s) "
            "ON CONFLICT(digest) DO NOTHING RETURNING id",
            (uuid.uuid4(), name, raw, digest),
        ).fetchone()
        if row:
            return {"id": str(row["id"]), "reused": False}
        row = db.execute("SELECT id FROM jobs WHERE digest=%s", (digest,)).fetchone()
        return {"id": str(row["id"]), "reused": True}


def clean(row):
    if None in row or any(value is None for value in row.values()):
        raise ValueError("Wrong number of columns")
    result = {key: value.strip() for key, value in row.items()}
    for key in ("reading_id", "vehicle_id"):
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,60}", result[key]):
            raise ValueError(f"Missing or invalid {key}")
    try:
        date = datetime.fromisoformat(result["recorded_at"].replace("Z", "+00:00"))
        if date.tzinfo is None:
            raise ValueError()
    except ValueError:
        raise ValueError("recorded_at must be a date and time with a time zone") from None
    result["recorded_at"] = date.astimezone(timezone.utc)
    for key, limit in (("miles", 5000), ("fuel_gallons", 500)):
        try:
            number = Decimal(result[key])
            if not number.is_finite() or not 0 <= number <= limit:
                raise ValueError()
            if number.as_tuple().exponent < -2:
                raise ValueError()
        except (InvalidOperation, ValueError):
            raise ValueError(f"{key} must be between 0 and {limit}, with at most two decimal places") from None
        result[key] = number
    return result


def run_once():
    """Claim one job, then save all its results in one transaction."""
    with connect() as db:
        # A worker that disappeared can be replaced after the lease expires.
        job = db.execute(
            "SELECT * FROM jobs WHERE status='queued' OR "
            "(status='running' AND started_at < now()-interval '5 minutes') "
            "ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 1"
        ).fetchone()
        if not job:
            return False
        claim = db.execute("UPDATE jobs SET status='running',started_at=now(),attempts=attempts+1,error=NULL WHERE id=%s RETURNING attempts", (job["id"],)).fetchone()
    started = time.perf_counter()
    try:
        reader = csv.DictReader(io.StringIO(job["raw_csv"]), strict=True)
        if reader.fieldnames != COLUMNS:
            raise ValueError("Columns changed. Expected: " + ", ".join(COLUMNS))
        accepted = rejected = duplicates = 0
        with connect() as db:
            # Lock the job while writing, including a worker recovering its lease.
            current = db.execute("SELECT status,attempts FROM jobs WHERE id=%s FOR UPDATE", (job["id"],)).fetchone()
            if current["status"] != "running" or current["attempts"] != claim["attempts"]:
                return True
            db.execute("DELETE FROM rejections WHERE job_id=%s", (job["id"],))
            for row_number, raw in enumerate(reader, 2):
                if row_number > 10001:
                    raise ValueError("A file can contain at most 10,000 data rows")
                try:
                    row = clean(raw)
                    inserted = db.execute(
                        "INSERT INTO readings(reading_id,vehicle_id,recorded_at,miles,fuel_gallons,job_id) "
                        "VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING RETURNING reading_id",
                        (*[row[key] for key in COLUMNS], job["id"]),
                    ).fetchone()
                    if inserted:
                        accepted += 1
                    else:
                        old = db.execute("SELECT * FROM readings WHERE reading_id=%s", (row["reading_id"],)).fetchone()
                        if any(old[key] != row[key] for key in COLUMNS):
                            raise ValueError("This reading_id exists with different values; the saved reading was kept")
                        duplicates += 1
                except ValueError as error:
                    rejected += 1
                    db.execute("INSERT INTO rejections(job_id,row_number,reason,raw_row) VALUES (%s,%s,%s,%s)",
                               (job["id"], row_number, str(error), Jsonb({str(k): v for k, v in raw.items()})))
            if reader.line_num <= 1:
                raise ValueError("The file contains no data rows")
            duration = round((time.perf_counter() - started) * 1000)
            db.execute("UPDATE jobs SET status=%s,accepted=%s,rejected=%s,duplicates=%s,finished_at=now(),duration_ms=%s WHERE id=%s",
                       ("warnings" if rejected else "completed", accepted, rejected, duplicates, duration, job["id"]))
    except Exception as error:
        # The failed transaction left no partial readings behind.
        message = str(error) if isinstance(error, (ValueError, csv.Error)) else "Import failed. Check the worker log, then retry."
        with connect() as db:
            db.execute("UPDATE jobs SET status='failed',error=%s,finished_at=now(),duration_ms=%s WHERE id=%s AND status='running' AND attempts=%s",
                       (message, round((time.perf_counter() - started) * 1000), job["id"], claim["attempts"]))
        if not isinstance(error, (ValueError, csv.Error)):
            import logging
            logging.exception("Import failed for job %s", job["id"])
    return True
