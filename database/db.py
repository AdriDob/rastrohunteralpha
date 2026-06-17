import os
import re
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./database/rastro.db")
IS_SQLITE = DATABASE_URL.startswith("sqlite")

_engine_args: dict = {}
if IS_SQLITE:
    _engine_args["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **_engine_args)
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
    from . import models

    _ensure_db_dir()
    Base.metadata.create_all(bind=engine)

    # Auto-migration for targets_intel (SQLite only)
    if IS_SQLITE:
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
                ("evidence_potential_score", "FLOAT DEFAULT 0.0")
            ]
            for col_name, col_type in columns_to_add:
                try:
                    session.execute(text(f"ALTER TABLE targets_intel ADD COLUMN {col_name} {col_type};"))
                except Exception:
                    pass
            session.commit()
            session.close()
        except Exception:
            pass
