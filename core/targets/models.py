from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
)
from sqlalchemy.sql import func

from database.db import Base


class TargetIntel(Base):
    __tablename__ = "targets_intel"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=True)
    domain = Column(String, nullable=True)
    source = Column(String, nullable=True)
    program_url = Column(String, nullable=True)

    quality_score = Column(Integer, nullable=True)
    complexity_score = Column(Integer, nullable=True)
    roi_score = Column(Integer, nullable=True)
    noise_score = Column(Integer, nullable=True)

    freshness_score = Column(Float, nullable=True, default=0.0)
    competition_score = Column(Float, nullable=True, default=0.0)
    opportunity_score = Column(Float, nullable=True, default=0.0)
    reward_score = Column(Float, nullable=True, default=0.0)
    reward_confidence = Column(Float, nullable=True, default=0.0)
    attack_surface_score = Column(Float, nullable=True, default=0.0)
    evidence_potential_score = Column(Float, nullable=True, default=0.0)

    saas_probability = Column(Float, nullable=True)
    api_density = Column(Integer, nullable=True)
    graphql_detected = Column(Boolean, nullable=True, default=False)
    b2b_indicator = Column(Boolean, nullable=True, default=False)
    admin_detected = Column(Boolean, nullable=True, default=False)
    multi_tenant = Column(Boolean, nullable=True, default=False)

    tags = Column(String, nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Scope(Base):
    __tablename__ = "target_scopes"

    id = Column(Integer, primary_key=True, index=True)
    target_id = Column(Integer, ForeignKey("targets_intel.id"), nullable=False)
    scope_text = Column(String, nullable=False)
    is_wildcard = Column(Boolean, nullable=True, default=False)
    is_api = Column(Boolean, nullable=True, default=False)
    is_graphql = Column(Boolean, nullable=True, default=False)
    extracted_domain = Column(String, nullable=True)
