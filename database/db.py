import contextlib
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./database/orion.db")
IS_SQLITE = DATABASE_URL.startswith("sqlite")

_engine_args: dict = {}
if IS_SQLITE:
    _engine_args["connect_args"] = {"check_same_thread": False, "timeout": 5}

engine = create_engine(DATABASE_URL, **_engine_args)

if IS_SQLITE:
    with engine.connect() as conn:
        for pragma in ("PRAGMA journal_mode=WAL", "PRAGMA synchronous=NORMAL", "PRAGMA busy_timeout=5000"):
            with contextlib.suppress(Exception):
                conn.execute(text(pragma))
        conn.commit()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def _ensure_db_dir() -> None:
    if not IS_SQLITE:
        return
    match = re.match(r"sqlite:///(.+)", DATABASE_URL)
    if match:
        db_path = Path(match.group(1))
        db_path.parent.mkdir(parents=True, exist_ok=True)


def init_db():

    _ensure_db_dir()
    Base.metadata.create_all(bind=engine)

    # Auto-migration for targets_intel (SQLite only)
    if IS_SQLITE:
        session = None
        try:
            from sqlalchemy import text
            session = SessionLocal()
            columns_to_add = [
                ("freshness_score", "FLOAT DEFAULT 0.0"),
                ("competition_score", "FLOAT DEFAULT 0.0"),
                ("opportunity_score", "FLOAT DEFAULT 0.0"),
                ("reward_score", "FLOAT DEFAULT 0.0"),
                ("reward_confidence", "FLOAT DEFAULT 0.0"),
                ("attack_surface_score", "FLOAT DEFAULT 0.0"),
                ("evidence_potential_score", "FLOAT DEFAULT 0.0"),
                ("technology_tags", "VARCHAR DEFAULT ''"),
                ("cms_detected", "VARCHAR"),
                ("framework_detected", "VARCHAR"),
                ("wordpress_plugins_detected", "VARCHAR"),
            ]
            for col_name, col_type in columns_to_add:
                try:
                    session.execute(text(f"ALTER TABLE targets_intel ADD COLUMN {col_name} {col_type};"))
                except Exception as exc:
                    logger = __import__('logging').getLogger('orion.db')
                    logger.warning("Migration skip (targets_intel.%s): %s", col_name, exc)

            # Auto-migration for reports table
            report_columns = [
                ("program", "VARCHAR DEFAULT ''"),
                ("target", "VARCHAR DEFAULT ''"),
                ("vulnerability", "VARCHAR DEFAULT ''"),
                ("severity", "VARCHAR DEFAULT 'medium'"),
                ("status", "VARCHAR DEFAULT 'draft'"),
                ("estimated_reward", "FLOAT DEFAULT 0.0"),
                ("confirmed_reward", "FLOAT DEFAULT 0.0"),
                ("currency", "VARCHAR DEFAULT 'USD'"),
                ("evidence_count", "INTEGER DEFAULT 0"),
                ("notes", "TEXT DEFAULT ''"),
                ("timeline", "TEXT DEFAULT '[]'"),
                ("attachments", "TEXT DEFAULT '[]'"),
                ("updated_at", "DATETIME"),
            ]
            for col_name, col_type in report_columns:
                try:
                    session.execute(text(f"ALTER TABLE reports ADD COLUMN {col_name} {col_type};"))
                except Exception as exc:
                    logger = __import__('logging').getLogger('orion.db')
                    logger.warning("Migration skip (reports.%s): %s", col_name, exc)

            # Auto-migration for notifications table
            notification_columns = [
                ("title", "VARCHAR"),
                ("severity", "VARCHAR DEFAULT 'info'"),
                ("priority", "VARCHAR DEFAULT 'medium'"),
                ("dedup_key", "VARCHAR"),
                ("delivered_via", "VARCHAR"),
            ]
            for col_name, col_type in notification_columns:
                with contextlib.suppress(Exception):
                    session.execute(text(f"ALTER TABLE notifications ADD COLUMN {col_name} {col_type};"))

            session.commit()
        except Exception as exc:
            logger = __import__('logging').getLogger('orion.db')
            logger.warning("Migration block failed: %s", exc)
        finally:
            if session is not None:
                session.close()
