from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from datetime import datetime, date
import json
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from database import init_db, get_conn
from summarizer import process_today_notes

logger = logging.getLogger(__name__)

app = FastAPI(title="Brain Dump")
_scheduler = BackgroundScheduler()


@app.on_event("startup")
def startup():
    init_db()
    _scheduler.add_job(process_today_notes, CronTrigger(hour=23, minute=59))
    _scheduler.start()
    logger.info("Scheduler started — nightly summary at 23:59")


@app.on_event("shutdown")
def shutdown():
    _scheduler.shutdown(wait=False)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class NoteIn(BaseModel):
    text: str


# ---------------------------------------------------------------------------
# POST /log
# ---------------------------------------------------------------------------

@app.post("/log", status_code=201)
def log_note(note: NoteIn):
    if not note.text.strip():
        raise HTTPException(status_code=400, detail="text must not be empty")

    with get_conn() as conn:
        cursor = conn.execute(
            "INSERT INTO notes (raw_text) VALUES (?)",
            (note.text.strip(),),
        )
        note_id = cursor.lastrowid

    return {"id": note_id, "status": "saved"}


# ---------------------------------------------------------------------------
# GET /api/today
# ---------------------------------------------------------------------------

@app.get("/api/today")
def today():
    today_str = date.today().isoformat()
    with get_conn() as conn:
        notes = conn.execute(
            "SELECT id, raw_text, timestamp FROM notes "
            "WHERE date(timestamp) = ? ORDER BY timestamp",
            (today_str,),
        ).fetchall()

        summary_row = conn.execute(
            "SELECT * FROM daily_summary WHERE date = ?",
            (today_str,),
        ).fetchone()

    raw_notes = [dict(r) for r in notes]
    summary = None
    if summary_row:
        summary = {
            "categories":   json.loads(summary_row["categories"]),
            "summary":      summary_row["summary"],
            "action_items": json.loads(summary_row["action_items"]),
            "patterns":     json.loads(summary_row["patterns"]),
        }

    return {"date": today_str, "notes": raw_notes, "summary": summary}


# ---------------------------------------------------------------------------
# GET /api/history
# ---------------------------------------------------------------------------

@app.get("/api/history")
def history(q: str = "", limit: int = 30):
    with get_conn() as conn:
        if q:
            rows = conn.execute(
                "SELECT id, raw_text, timestamp FROM notes "
                "WHERE raw_text LIKE ? ORDER BY timestamp DESC LIMIT ?",
                (f"%{q}%", limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, raw_text, timestamp FROM notes "
                "ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            ).fetchall()

    return {"results": [dict(r) for r in rows]}


# ---------------------------------------------------------------------------
# POST /api/process — manual trigger for nightly summarizer
# ---------------------------------------------------------------------------

@app.post("/api/process")
def process():
    result = process_today_notes()
    return result


# ---------------------------------------------------------------------------
# GET / — dashboard (placeholder)
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def dashboard():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Brain Dump</title>
  <style>
    body { font-family: sans-serif; max-width: 720px; margin: 2rem auto; padding: 0 1rem; }
    h1   { font-size: 1.8rem; }
    pre  { background: #f4f4f4; padding: 1rem; border-radius: 6px; overflow-x: auto; }
  </style>
</head>
<body>
  <h1>🧠 Brain Dump</h1>
  <p>Dashboard coming soon. Endpoints available:</p>
  <pre>
POST /log           { "text": "your note" }
GET  /api/today     today's notes + AI summary
GET  /api/history   searchable history  (?q=keyword)
GET  /docs          interactive API docs (FastAPI)</pre>
  <p><a href="/docs">Open API docs →</a></p>
</body>
</html>
"""
