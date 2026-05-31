import json
import logging
import os
from datetime import date

import anthropic

from database import get_conn

logger = logging.getLogger(__name__)

_PROMPT = """You are analyzing someone's personal brain dump notes from today.

Notes:
{notes}

Return ONLY valid JSON with exactly this structure — no other text:
{{
  "categories": {{
    "Work": ["note text", ...],
    "Personal": ["note text", ...]
  }},
  "summary": "2-3 sentence narrative paragraph summarizing the day.",
  "action_items": ["concrete next-step 1", "concrete next-step 2"],
  "patterns": ["recurring theme or habit observed"]
}}

Rules:
- categories: infer theme names from the notes (Work, Health, Learning, Ideas, etc.)
- summary: flowing prose, not bullets
- action_items: only concrete tasks — skip vague ones
- patterns: observations about mood, habits, or recurring topics
"""


def process_today_notes():
    today_str = date.today().isoformat()

    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, raw_text FROM notes "
            "WHERE processed = 0 AND date(timestamp) = ?",
            (today_str,),
        ).fetchall()

    if not rows:
        logger.info("No unprocessed notes for %s", today_str)
        return {"status": "no_notes"}

    note_ids = [r["id"] for r in rows]
    notes_text = "\n".join(f"- {r['raw_text']}" for r in rows)

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    message = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=2048,
        messages=[{"role": "user", "content": _PROMPT.format(notes=notes_text)}],
    )

    result = json.loads(message.content[0].text.strip())

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO daily_summary (date, categories, summary, action_items, patterns)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
                categories   = excluded.categories,
                summary      = excluded.summary,
                action_items = excluded.action_items,
                patterns     = excluded.patterns
            """,
            (
                today_str,
                json.dumps(result.get("categories", {})),
                result.get("summary", ""),
                json.dumps(result.get("action_items", [])),
                json.dumps(result.get("patterns", [])),
            ),
        )
        placeholders = ",".join("?" * len(note_ids))
        conn.execute(
            f"UPDATE notes SET processed = 1 WHERE id IN ({placeholders})",
            note_ids,
        )

    logger.info("Processed %d notes for %s", len(note_ids), today_str)
    return {"status": "ok", "notes_processed": len(note_ids), "date": today_str}
