from contextlib import asynccontextmanager
from pathlib import Path
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .auth import router, session
from .db import connect, initialize
from .importer import enqueue


@asynccontextmanager
async def lifespan(app):
    initialize()
    yield


app = FastAPI(title="Import Desk", lifespan=lifespan)
app.include_router(router, prefix="/api")


class Upload(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    csv: str = Field(min_length=1, max_length=1_000_000)


class ScheduleUpdate(BaseModel):
    enabled: bool
    interval_seconds: int = Field(ge=30, le=86400)


@app.get("/api/health")
def health():
    with connect() as db:
        db.execute("SELECT 1")
    return {"status": "ok"}


@app.get("/api/dashboard", dependencies=[Depends(session)])
def dashboard():
    with connect() as db:
        jobs = db.execute("SELECT id,source_name,status,attempts,accepted,rejected,duplicates,error,created_at,finished_at,duration_ms FROM jobs ORDER BY created_at DESC LIMIT 50").fetchall()
        summary = db.execute("SELECT count(*) AS readings,count(DISTINCT vehicle_id) AS vehicles FROM readings").fetchone()
        summary.update(db.execute("SELECT max(finished_at) FILTER(WHERE status IN ('completed','warnings')) AS last_success, count(*) FILTER(WHERE status='failed') AS failed_jobs FROM jobs").fetchone())
        return {"jobs": jobs, "summary": summary, "schedule": db.execute("SELECT * FROM schedule WHERE id=1").fetchone(),
                "readings": db.execute("SELECT * FROM readings ORDER BY imported_at DESC LIMIT 25").fetchall()}


@app.post("/api/imports", dependencies=[Depends(session)])
def upload(body: Upload):
    if len(body.csv.encode()) > 1_000_000:
        raise HTTPException(413, "Choose a CSV smaller than 1 MB.")
    return enqueue(body.name.strip() or "Uploaded file", body.csv.lstrip("\ufeff"))


@app.post("/api/sample", dependencies=[Depends(session)])
def sample():
    return enqueue("Fleet sample with bad rows", Path("samples/fleet-readings.csv").read_text())


@app.get("/api/jobs/{job_id}", dependencies=[Depends(session)])
def job(job_id: UUID):
    with connect() as db:
        row = db.execute("SELECT * FROM jobs WHERE id=%s", (job_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Import not found.")
        row.pop("raw_csv")
        row["rejections"] = db.execute("SELECT row_number,reason,raw_row FROM rejections WHERE job_id=%s ORDER BY row_number", (job_id,)).fetchall()
        return row


@app.get("/api/jobs/{job_id}/raw", dependencies=[Depends(session)])
def raw(job_id: UUID):
    with connect() as db:
        row = db.execute("SELECT raw_csv FROM jobs WHERE id=%s", (job_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Import not found.")
    return PlainTextResponse(row["raw_csv"], headers={"Content-Disposition": 'attachment; filename="source.csv"'})


@app.post("/api/jobs/{job_id}/retry", dependencies=[Depends(session)])
def retry(job_id: UUID):
    with connect() as db:
        changed = db.execute("UPDATE jobs SET status='queued',error=NULL,finished_at=NULL WHERE id=%s AND status='failed' RETURNING id", (job_id,)).fetchone()
    if not changed:
        raise HTTPException(409, "Only a failed import can be retried. Fix rejected rows in a new file.")
    return {"ok": True}


@app.post("/api/schedule", dependencies=[Depends(session)])
def schedule(body: ScheduleUpdate):
    with connect() as db:
        db.execute("UPDATE schedule SET enabled=%s,interval_seconds=%s,next_run=now() WHERE id=1", (body.enabled, body.interval_seconds))
    return {"ok": True}


if Path("web/dist").exists():
    app.mount("/", StaticFiles(directory="web/dist", html=True), name="web")
