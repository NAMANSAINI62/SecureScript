"""
Export MySQL `recordings` rows into backups/mysql_recordings_export/ for Hugging Face Space fallback.

Run from project root (loads .env from repo root):

    python scripts/export_mysql_recordings_backup.py

Then commit and push so the Space sync includes the folder:

    git add backups/mysql_recordings_export
    git commit -m "chore: refresh HF recording backup export"
    git push origin main
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.chdir(ROOT)

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

import mysql.connector  # noqa: E402


def main() -> None:
    out_dir = ROOT / "backups" / "mysql_recordings_export"
    out_dir.mkdir(parents=True, exist_ok=True)

    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "super_ai_transcript"),
    )
    cur = conn.cursor(dictionary=True)
    cur.execute(
        """
        SELECT id, filename, audio_data, audio_mime_type, original_transcript,
               cleaned_transcript, summary, key_points, created_at, updated_at, duration_seconds
        FROM recordings
        ORDER BY id
        """
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    ext_map = {
        "audio/webm": ".webm",
        "audio/wav": ".wav",
        "audio/x-wav": ".wav",
        "audio/mpeg": ".mp3",
        "audio/mp3": ".mp3",
        "audio/mp4": ".m4a",
        "audio/x-m4a": ".m4a",
        "audio/ogg": ".ogg",
    }

    meta: list[dict] = []
    for r in rows:
        mime = (r.get("audio_mime_type") or "").lower()
        ext = ext_map.get(mime, "")
        safe_name = f"recording_{r['id']}{ext}"
        audio_path = out_dir / safe_name
        data = r.get("audio_data") or b""
        audio_path.write_bytes(data)

        def _ser(v):
            if v is None:
                return None
            if hasattr(v, "isoformat"):
                return str(v)
            return v

        item = {k: _ser(v) for k, v in r.items() if k != "audio_data"}
        item["exported_audio_file"] = safe_name
        meta.append(item)

    meta_path = out_dir / "recordings_metadata.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Exported {len(rows)} recording(s) to {out_dir}")


if __name__ == "__main__":
    main()
