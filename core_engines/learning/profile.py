"""Investigator Profile — persistent behavioural model.

Stores anonymous metrics about the investigator's workflow, preferences,
and success history. All data is local-first and never leaves the instance
without explicit user consent.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, Integer, String
from sqlalchemy.sql import func

from database.db import Base, SessionLocal

# ─── SQLAlchemy Models ─────────────────────────────────────────────────────

class InvestigatorProfile(Base):
    """Persistent user profile storing behavioural metrics."""

    __tablename__ = "investigator_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, nullable=False, index=True)

    # ── Discovery ──────────────────────────────────────────────────────
    total_targets = Column(Integer, default=0, nullable=False)
    industries = Column(JSON, default=list)
    technologies = Column(JSON, default=list)
    programs = Column(JSON, default=list)
    domains = Column(JSON, default=list)

    # ── Activity ───────────────────────────────────────────────────────
    total_hours_active = Column(Float, default=0.0)
    total_sessions = Column(Integer, default=0)
    average_session_minutes = Column(Float, default=0.0)
    favorite_modules = Column(JSON, default=list)  # [{"module": "targets", "count": 42}, ...]
    average_findings_per_session = Column(Float, default=0.0)

    # ── Preferences ────────────────────────────────────────────────────
    favorite_bug_classes = Column(JSON, default=list)  # [{"class": "IDOR", "count": 18}, ...]
    favorite_tools = Column(JSON, default=list)
    favorite_asset_types = Column(JSON, default=list)
    favorite_report_styles = Column(JSON, default=list)
    preferred_ai_model = Column(String, default="")
    notification_preferences = Column(JSON, default=dict)

    # ── Success History ────────────────────────────────────────────────
    confirmed_findings = Column(Integer, default=0)
    rejected_findings = Column(Integer, default=0)
    duplicates_found = Column(Integer, default=0)
    informational_findings = Column(Integer, default=0)
    high_severity_findings = Column(Integer, default=0)
    average_time_to_validation_hours = Column(Float, default=0.0)
    total_roi_estimate = Column(Float, default=0.0)

    # ── Meta ───────────────────────────────────────────────────────────
    adaptive_mode = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class LearningEvent(Base):
    """Individual event log for trend analysis."""

    __tablename__ = "learning_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    event_type = Column(String, nullable=False, index=True)  # e.g. "target_viewed", "finding_created"
    data = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ─── Service Layer ────────────────────────────────────────────────────────

class ProfileService:
    """Read/write the investigator profile."""

    def get(self, user_id: str) -> InvestigatorProfile | None:
        session = SessionLocal()
        try:
            return session.query(InvestigatorProfile).filter(
                InvestigatorProfile.user_id == user_id
            ).first()
        finally:
            session.close()

    def get_or_create(self, user_id: str) -> InvestigatorProfile:
        session = SessionLocal()
        try:
            profile = session.query(InvestigatorProfile).filter(
                InvestigatorProfile.user_id == user_id
            ).first()
            if profile:
                return profile
            profile = InvestigatorProfile(user_id=user_id)
            session.add(profile)
            session.commit()
            session.refresh(profile)
            return profile
        finally:
            session.close()

    def save(self, profile: InvestigatorProfile) -> None:
        session = SessionLocal()
        try:
            session.add(profile)
            session.commit()
        finally:
            session.close()

    def update_field(self, user_id: str, field: str, value: Any) -> bool:
        session = SessionLocal()
        try:
            rows = session.query(InvestigatorProfile).filter(
                InvestigatorProfile.user_id == user_id
            ).update({field: value})
            session.commit()
            return rows > 0
        finally:
            session.close()

    def increment(self, user_id: str, field: str, amount: int = 1) -> bool:
        session = SessionLocal()
        try:
            profile = session.query(InvestigatorProfile).filter(
                InvestigatorProfile.user_id == user_id
            ).with_for_update().first()
            if not profile:
                profile = InvestigatorProfile(user_id=user_id)
                session.add(profile)
                session.flush()
            current = getattr(profile, field, 0)
            setattr(profile, field, current + amount)
            session.commit()
            return True
        finally:
            session.close()

    def append_json_list(self, user_id: str, field: str, value: Any) -> bool:
        """Append to a JSON list field (e.g. industries, technologies)."""
        session = SessionLocal()
        try:
            profile = session.query(InvestigatorProfile).filter(
                InvestigatorProfile.user_id == user_id
            ).with_for_update().first()
            if not profile:
                profile = InvestigatorProfile(user_id=user_id)
                session.add(profile)
                session.flush()
            lst: list = getattr(profile, field, []) or []
            if value and value not in lst:
                lst.append(value)
                setattr(profile, field, lst)
                session.commit()
            return True
        finally:
            session.close()

    def increment_nested(self, user_id: str, field: str, key: str) -> bool:
        """Increment a counter in a [{key, count}, ...] list field."""
        session = SessionLocal()
        try:
            profile = session.query(InvestigatorProfile).filter(
                InvestigatorProfile.user_id == user_id
            ).with_for_update().first()
            if not profile:
                profile = InvestigatorProfile(user_id=user_id)
                session.add(profile)
                session.flush()
            lst: list = list(getattr(profile, field, []) or [])
            found = False
            for item in lst:
                if item.get("class") == key or item.get("module") == key or item.get("name") == key or item.get("type") == key or item.get("tool") == key or item.get("style") == key:
                    item["count"] = item.get("count", 0) + 1
                    found = True
                    break
            if not found:
                lst.append({"class" if field == "favorite_bug_classes" else "module" if field == "favorite_modules" else "name" if field == "favorite_asset_types" else "tool" if field == "favorite_tools" else "style" if field == "favorite_report_styles" else "key": key, "count": 1})
            setattr(profile, field, lst)
            session.commit()
            return True
        finally:
            session.close()

    def log_event(self, user_id: str, event_type: str, data: dict | None = None) -> None:
        session = SessionLocal()
        try:
            event = LearningEvent(user_id=user_id, event_type=event_type, data=data or {})
            session.add(event)
            session.commit()
        finally:
            session.close()

    def get_events(self, user_id: str, event_type: str | None = None, limit: int = 100) -> list[LearningEvent]:
        session = SessionLocal()
        try:
            query = session.query(LearningEvent).filter(LearningEvent.user_id == user_id).order_by(LearningEvent.created_at.desc())
            if event_type:
                query = query.filter(LearningEvent.event_type == event_type)
            return query.limit(limit).all()
        finally:
            session.close()

    def get_stats(self, user_id: str) -> dict[str, Any]:
        """Build a stats dictionary from the profile."""
        profile = self.get(user_id)
        if not profile:
            return {"exists": False}
        return {
            "exists": True,
            "discovery": {
                "total_targets": profile.total_targets,
                "industries": profile.industries or [],
                "technologies": profile.technologies or [],
                "programs": profile.programs or [],
                "domains": profile.domains or [],
            },
            "activity": {
                "total_hours_active": profile.total_hours_active,
                "total_sessions": profile.total_sessions,
                "average_session_minutes": profile.average_session_minutes,
                "favorite_modules": profile.favorite_modules or [],
                "average_findings_per_session": profile.average_findings_per_session,
            },
            "preferences": {
                "favorite_bug_classes": profile.favorite_bug_classes or [],
                "favorite_tools": profile.favorite_tools or [],
                "favorite_asset_types": profile.favorite_asset_types or [],
                "favorite_report_styles": profile.favorite_report_styles or [],
                "preferred_ai_model": profile.preferred_ai_model or "",
                "notification_preferences": profile.notification_preferences or {},
            },
            "success_history": {
                "confirmed_findings": profile.confirmed_findings,
                "rejected_findings": profile.rejected_findings,
                "duplicates_found": profile.duplicates_found,
                "informational_findings": profile.informational_findings,
                "high_severity_findings": profile.high_severity_findings,
                "average_time_to_validation_hours": profile.average_time_to_validation_hours,
                "total_roi_estimate": profile.total_roi_estimate,
            },
            "adaptive_mode": profile.adaptive_mode,
            "created_at": profile.created_at.isoformat() if profile.created_at else "",
            "updated_at": profile.updated_at.isoformat() if profile.updated_at else "",
        }

    def reset(self, user_id: str) -> bool:
        session = SessionLocal()
        try:
            profile = session.query(InvestigatorProfile).filter(
                InvestigatorProfile.user_id == user_id
            ).first()
            if not profile:
                return False
            profile.total_targets = 0
            profile.industries = []
            profile.technologies = []
            profile.programs = []
            profile.domains = []
            profile.total_hours_active = 0.0
            profile.total_sessions = 0
            profile.average_session_minutes = 0.0
            profile.favorite_modules = []
            profile.average_findings_per_session = 0.0
            profile.favorite_bug_classes = []
            profile.favorite_tools = []
            profile.favorite_asset_types = []
            profile.favorite_report_styles = []
            profile.preferred_ai_model = ""
            profile.notification_preferences = {}
            profile.confirmed_findings = 0
            profile.rejected_findings = 0
            profile.duplicates_found = 0
            profile.informational_findings = 0
            profile.high_severity_findings = 0
            profile.average_time_to_validation_hours = 0.0
            profile.total_roi_estimate = 0.0
            profile.adaptive_mode = True
            session.commit()
            return True
        finally:
            session.close()


# ─── Singleton ─────────────────────────────────────────────────────────────

_service: ProfileService | None = None


def get_profile_service() -> ProfileService:
    global _service
    if _service is None:
        _service = ProfileService()
    return _service
