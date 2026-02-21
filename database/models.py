import sqlite3
from config import DATABASE_PATH


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            phone_number  TEXT UNIQUE NOT NULL,
            display_name  TEXT,
            timezone      TEXT DEFAULT 'Asia/Riyadh',
            daily_goal    INTEGER DEFAULT 2000,
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS meals (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL REFERENCES users(id),
            food_items      TEXT NOT NULL,
            total_calories  INTEGER NOT NULL,
            image_id        TEXT,
            notes           TEXT,
            logged_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_summaries (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL REFERENCES users(id),
            summary_date    DATE NOT NULL,
            total_calories  INTEGER NOT NULL,
            meal_count      INTEGER NOT NULL,
            summary_text    TEXT,
            sent_at         TIMESTAMP,
            UNIQUE(user_id, summary_date)
        )
    """)

    # Migration: add macro columns to meals table if they don't exist
    cursor.execute("PRAGMA table_info(meals)")
    existing_columns = {row[1] for row in cursor.fetchall()}

    if "protein_g" not in existing_columns:
        cursor.execute("ALTER TABLE meals ADD COLUMN protein_g REAL DEFAULT 0")
    if "carbs_g" not in existing_columns:
        cursor.execute("ALTER TABLE meals ADD COLUMN carbs_g REAL DEFAULT 0")
    if "sugar_g" not in existing_columns:
        cursor.execute("ALTER TABLE meals ADD COLUMN sugar_g REAL DEFAULT 0")

    conn.commit()
    conn.close()
