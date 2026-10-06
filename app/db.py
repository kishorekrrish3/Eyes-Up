import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from app.config import settings


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    path = db_path or settings.database_path
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    conn = get_connection(db_path)
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sightings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                common_name TEXT NOT NULL,
                scientific_name TEXT NOT NULL,
                confidence REAL NOT NULL,
                latitude REAL,
                longitude REAL,
                outing_id INTEGER,
                tip TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_sightings_scientific
            ON sightings (scientific_name)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_sightings_created
            ON sightings (created_at)
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS outings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_time TEXT NOT NULL,
                end_time TEXT,
                screen_seconds INTEGER DEFAULT 0,
                outing_seconds INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)
    conn.close()


def add_sighting(
    common_name: str,
    scientific_name: str,
    confidence: float,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    outing_id: Optional[int] = None,
    tip: Optional[str] = None,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection(db_path)
    with conn:
        cursor = conn.execute(
            """
            INSERT INTO sightings (
                common_name, scientific_name, confidence, latitude, longitude, outing_id, tip, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                common_name,
                scientific_name,
                round(confidence, 3),
                latitude,
                longitude,
                outing_id,
                tip,
                now,
            ),
        )
        sighting_id = cursor.lastrowid
    conn.close()

    return {
        "id": sighting_id,
        "common_name": common_name,
        "scientific_name": scientific_name,
        "confidence": round(confidence, 3),
        "latitude": latitude,
        "longitude": longitude,
        "outing_id": outing_id,
        "tip": tip,
        "created_at": now,
    }


def is_heard_before(scientific_name: str, db_path: Optional[str] = None) -> bool:
    conn = get_connection(db_path)
    cursor = conn.execute(
        "SELECT 1 FROM sightings WHERE LOWER(scientific_name) = LOWER(?) LIMIT 1",
        (scientific_name,),
    )
    row = cursor.fetchone()
    conn.close()
    return row is not None


def get_life_list(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection(db_path)
    cursor = conn.execute("""
        SELECT 
            common_name,
            scientific_name,
            COUNT(*) as total_heard,
            MAX(confidence) as max_confidence,
            MIN(created_at) as first_heard,
            MAX(created_at) as last_heard
        FROM sightings
        GROUP BY scientific_name
        ORDER BY last_heard DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_recent_sightings(limit: int = 10, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection(db_path)
    cursor = conn.execute(
        """
        SELECT id, common_name, scientific_name, confidence, latitude, longitude, tip, created_at
        FROM sightings
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def start_outing(db_path: Optional[str] = None) -> int:
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection(db_path)
    with conn:
        cursor = conn.execute(
            "INSERT INTO outings (start_time, created_at) VALUES (?, ?)",
            (now, now),
        )
        outing_id = cursor.lastrowid
    conn.close()
    return outing_id


def stop_outing(
    outing_id: int,
    screen_seconds: int = 0,
    db_path: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    conn = get_connection(db_path)
    cursor = conn.execute(
        "SELECT id, start_time FROM outings WHERE id = ?",
        (outing_id,),
    )
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None

    start_dt = datetime.fromisoformat(row["start_time"])
    now_dt = datetime.now(timezone.utc)
    elapsed_seconds = int((now_dt - start_dt).total_seconds())
    outing_seconds = max(elapsed_seconds, screen_seconds, 1)
    end_time_str = now_dt.isoformat()

    with conn:
        conn.execute(
            """
            UPDATE outings 
            SET end_time = ?, screen_seconds = ?, outing_seconds = ?
            WHERE id = ?
            """,
            (end_time_str, screen_seconds, outing_seconds, outing_id),
        )
    conn.close()

    return {
        "id": outing_id,
        "start_time": row["start_time"],
        "end_time": end_time_str,
        "outing_minutes": round(outing_seconds / 60.0, 1),
        "screen_minutes": round(screen_seconds / 60.0, 1),
        "outing_seconds": outing_seconds,
        "screen_seconds": screen_seconds,
    }


def get_active_outing(db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    conn = get_connection(db_path)
    cursor = conn.execute(
        "SELECT id, start_time FROM outings WHERE end_time IS NULL ORDER BY id DESC LIMIT 1"
    )
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return dict(row)


def get_touch_grass_stats(days: int = 7, db_path: Optional[str] = None) -> Dict[str, Any]:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    conn = get_connection(db_path)
    cursor = conn.execute(
        """
        SELECT 
            COUNT(*) as total_outings,
            COALESCE(SUM(outing_seconds), 0) as total_outing_secs,
            COALESCE(SUM(screen_seconds), 0) as total_screen_secs
        FROM outings
        WHERE end_time IS NOT NULL AND start_time >= ?
        """,
        (cutoff,),
    )
    row = cursor.fetchone()
    conn.close()

    total_outing_secs = row["total_outing_secs"] if row else 0
    total_screen_secs = row["total_screen_secs"] if row else 0
    total_outings = row["total_outings"] if row else 0

    outdoor_minutes = round(total_outing_secs / 60.0, 1)
    screen_minutes = round(total_screen_secs / 60.0, 1)

    # Ratio of outdoor minutes to screen minutes (avoid division by zero)
    effective_screen_min = max(screen_minutes, 0.5)
    ratio = round(outdoor_minutes / effective_screen_min, 1)

    # Percentage of time with "Eyes Up" (away from screen)
    if outdoor_minutes > 0:
        eyes_up_pct = max(0, min(100, round((1.0 - (screen_minutes / outdoor_minutes)) * 100)))
    else:
        eyes_up_pct = 100

    return {
        "days": days,
        "total_outings": total_outings,
        "outdoor_minutes": outdoor_minutes,
        "screen_minutes": screen_minutes,
        "ratio": ratio,
        "eyes_up_percentage": eyes_up_pct,
    }
