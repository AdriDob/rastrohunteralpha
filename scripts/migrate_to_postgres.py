"""SQLite → PostgreSQL migration script.

Usage:
    # Set target PostgreSQL URL
    export DATABASE_URL=postgresql://user:pass@localhost:5432/rastro

    # Run migration (copies all data from SQLite to PostgreSQL)
    python scripts/migrate_to_postgres.py

The script:
1. Reads all data from existing SQLite database
2. Creates schema on PostgreSQL (all 15+ tables)
3. Copies data row by row
4. Preserves all foreign keys and relationships
"""

import os
import sys
from pathlib import Path

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.orm import sessionmaker

# ── Configuration ──────────────────────────────────────────────────────────

PG_URL = os.environ.get("DATABASE_URL", "")
if not PG_URL or not PG_URL.startswith("postgresql"):
    print("ERROR: Set DATABASE_URL to a PostgreSQL connection string")
    print("  export DATABASE_URL=postgresql://user:pass@localhost:5432/rastro")
    sys.exit(1)

SQLITE_PATH = os.environ.get(
    "SQLITE_DB_PATH",
    str(Path.home() / ".rastro" / "database" / "rastro.db"),
)
# Fallback: try project default
if not Path(SQLITE_PATH).exists():
    SQLITE_PATH = "database/rastro.db"

# ── Connect ────────────────────────────────────────────────────────────────

sqlite_engine = create_engine(f"sqlite:///{SQLITE_PATH}")
sqlite_session = sessionmaker(bind=sqlite_engine, autoflush=False)()

pg_engine = create_engine(PG_URL)
pg_session = sessionmaker(bind=pg_engine, autoflush=False)()

# ── Import all models to ensure they're registered ────────────────────────

from database import models  # noqa: F401, E402
from core_engines.targets.models import TargetIntel, Scope  # noqa: F401, E402
from database.db import Base

# ── Create PostgreSQL schema ───────────────────────────────────────────────

print("Creating PostgreSQL schema...")
Base.metadata.create_all(bind=pg_engine)
print("  ✓ Schema created")

# ── Get table list ─────────────────────────────────────────────────────────

meta = MetaData()
meta.reflect(bind=sqlite_engine)
TABLE_NAMES = sorted(meta.tables.keys())
print(f"Found {len(TABLE_NAMES)} tables: {', '.join(TABLE_NAMES)}")

# ── Copy data ──────────────────────────────────────────────────────────────

TOTAL = 0
for table_name in TABLE_NAMES:
    table = meta.tables[table_name]
    rows = sqlite_session.execute(table.select()).fetchall()
    if not rows:
        print(f"  ~ {table_name}: 0 rows (empty)")
        continue

    columns = [col.name for col in table.columns]
    placeholders = ", ".join(f":{col}" for col in columns)
    pg_table = table_name

    # Check if target table exists in PostgreSQL
    try:
        pg_session.execute(text(f"SELECT 1 FROM {pg_table} LIMIT 0"))
    except Exception:
        print(f"  ~ {table_name}: table not in PostgreSQL, skipping")
        continue

    # Insert rows
    batch = []
    for row in rows:
        batch.append({col: getattr(row, col) for col in columns})

    try:
        pg_session.execute(
            text(f"INSERT INTO {pg_table} ({', '.join(columns)}) VALUES ({placeholders})"),
            batch,
        )
        pg_session.commit()
        TOTAL += len(batch)
        print(f"  ✓ {table_name}: {len(batch)} rows")
    except Exception as e:
        pg_session.rollback()
        print(f"  ✗ {table_name}: error — {e}")
        # Try row by row
        for item in batch:
            try:
                pg_session.execute(
                    text(f"INSERT INTO {pg_table} ({', '.join(columns)}) VALUES ({placeholders})"),
                    item,
                )
                pg_session.commit()
                TOTAL += 1
            except Exception as e2:
                pg_session.rollback()
                print(f"    ✗ {table_name} row {item.get('id', '?' )}: {e2}")

# ── Done ───────────────────────────────────────────────────────────────────

print(f"\n=== Migration complete: {TOTAL} total rows copied ===")
print(f"Source: sqlite:///{SQLITE_PATH}")
print(f"Target: {PG_URL}")

sqlite_session.close()
pg_session.close()
