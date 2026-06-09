import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./database/rastro.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def init_db():
    from . import models

    Path("./database").mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)

    # Auto-migration for targets_intel
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
