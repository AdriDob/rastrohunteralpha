import json
import ast
import logging
from sqlalchemy import Boolean, Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.sql import func

from .db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

SCAN_STATUS = (
    "pending",
    "running",
    "completed",
    "failed",
    "timeout",
)


class Target(Base):
    __tablename__ = "targets"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, nullable=False, index=True)

    domain = Column(String, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class Endpoint(Base):
    __tablename__ = "endpoints"

    id = Column(Integer, primary_key=True, index=True)

    target_id = Column(
        Integer,
        ForeignKey("targets.id"),
        nullable=False,
        index=True,
    )

    path = Column(
        String,
        nullable=False,
        default="/",
    )

    method = Column(
        String,
        nullable=False,
        default="GET",
    )

    # JSON metadata / labels / scoring cache
    params = Column(
        Text,
        nullable=True,
    )

    discovered_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    @property
    def parsed_params(self) -> dict:
        if not self.params:
            return {}
        try:
            return json.loads(self.params)
        except (json.JSONDecodeError, ValueError):
            try:
                return ast.literal_eval(self.params)
            except (ValueError, SyntaxError):
                logging.getLogger("rastro.models").warning(
                    f"Could not parse params for endpoint {self.id}"
                )
                return {}


class Finding(Base):
    __tablename__ = "findings"

    id = Column(Integer, primary_key=True, index=True)

    target_id = Column(
        Integer,
        ForeignKey("targets.id"),
        nullable=False,
        index=True,
    )

    endpoint_id = Column(
        Integer,
        ForeignKey("endpoints.id"),
        nullable=True,
    )

    title = Column(
        String,
        nullable=False,
    )

    severity = Column(
        String,
        nullable=True,
        default="medium",
    )

    description = Column(
        Text,
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class MemoryRecord(Base):
    __tablename__ = "memory_records"

    id = Column(Integer, primary_key=True, index=True)

    category = Column(
        String,
        nullable=False,
        index=True,
    )

    key = Column(
        String,
        nullable=False,
        index=True,
    )

    details = Column(
        Text,
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class Verdict(Base):
    """Stores validation loop results: confirmed/rejected/inconclusive status."""
    __tablename__ = "verdicts"

    id = Column(Integer, primary_key=True, index=True)

    hot_path_id = Column(String, nullable=False, index=True)

    endpoint_id = Column(
        Integer,
        ForeignKey("endpoints.id"),
        nullable=True,
        index=True,
    )

    # confirmed | rejected | inconclusive
    status = Column(String, nullable=False, index=True)

    # confidence score 0-1
    confidence = Column(
        String,  # JSON serialized float breakdown
        nullable=True,
    )

    reproducibility_score = Column(
        String,  # Consistency across attempts
        nullable=True,
    )

    # JSON: passed_rules, failed_rules, details
    validation_report = Column(Text, nullable=True)

    # JSON: breakdown of confidence calculation
    confidence_details = Column(Text, nullable=True)

    # Comma-separated evidence_ids or JSON array
    evidence_links = Column(Text, nullable=True)

    reason = Column(Text, nullable=True)

    retry_count = Column(Integer, default=3)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class Evidence(Base):
    """Stores captured request/response pairs and diffs from validation attempts."""
    __tablename__ = "evidence"

    id = Column(Integer, primary_key=True, index=True)

    verdict_id = Column(
        Integer,
        ForeignKey("verdicts.id"),
        nullable=False,
        index=True,
    )

    endpoint_id = Column(
        Integer,
        ForeignKey("endpoints.id"),
        nullable=True,
    )

    # attempt_1, attempt_2, etc
    attempt_label = Column(String, nullable=False)

    # Request context
    request_url = Column(String, nullable=False)
    request_method = Column(String, default="GET")
    request_headers = Column(Text, nullable=True)  # JSON
    request_params = Column(Text, nullable=True)  # JSON
    request_body = Column(Text, nullable=True)
    auth_label = Column(String, nullable=True)  # "user_a", "user_b", "anonymous"

    # Response
    response_status = Column(Integer, nullable=False)
    response_headers = Column(Text, nullable=True)  # JSON
    response_body = Column(Text, nullable=True)
    response_body_hash = Column(String, nullable=True)

    # Comparison metadata
    status_match = Column(String, default="unknown")  # boolean as string
    body_diff_ratio = Column(String, nullable=True)  # float as string
    sensitive_fields = Column(Text, nullable=True)  # JSON array
    consistent = Column(String, default="true")  # boolean

    # Replay instruction
    curl_command = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class ValidationResult(Base):
    """Stores detailed comparison results from each attempt."""
    __tablename__ = "validation_results"

    id = Column(Integer, primary_key=True, index=True)

    verdict_id = Column(
        Integer,
        ForeignKey("verdicts.id"),
        nullable=False,
        index=True,
    )

    attempt = Column(Integer, nullable=False)

    # JSON: baseline & probe response metadata
    baseline_response = Column(Text, nullable=True)
    probe_response = Column(Text, nullable=True)

    # JSON: comparison details
    comparison_summary = Column(Text, nullable=True)

    # Rate limit / timeout flags
    has_rate_limit = Column(String, default="false")
    has_timeout = Column(String, default="false")

    # Pass/fail on rules
    rule_results = Column(Text, nullable=True)  # JSON

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class ScanRun(Base):
    __tablename__ = "scan_runs"

    id = Column(Integer, primary_key=True, index=True)

    target_id = Column(
        Integer,
        ForeignKey("targets.id"),
        nullable=False,
        index=True,
    )

    mode = Column(
        String,
        nullable=True,
        default="FAST",
    )

    status = Column(
        String,
        nullable=False,
        default="pending",
    )

    endpoint_count = Column(
        Integer,
        nullable=False,
        default=0,
    )

    # Store lightweight metadata only.
    # Never store huge raw scan blobs here.
    outputs = Column(
        Text,
        nullable=True,
    )

    started_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    finished_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )


class Favorite(Base):
    """User workspace favorites — metadata only, never modifies core data."""
    __tablename__ = "favorites"

    id = Column(Integer, primary_key=True, index=True)
    item_type = Column(String, nullable=False, index=True)  # target, endpoint, evidence, report, quick_win
    item_id = Column(Integer, nullable=False, index=True)
    label = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Task(Base):
    """Operational task queue — organizational only, never modifies core data."""
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="pending", index=True)  # pending, in_progress, waiting, completed
    priority = Column(String, nullable=True, default="medium")  # low, medium, high, critical
    linked_type = Column(String, nullable=True, index=True)  # target, evidence, report, quick_win, replay
    linked_id = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Session(Base):
    """Persistent working context — tracks current investigation state."""
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=True, default="Default Session")
    current_target_id = Column(Integer, nullable=True)
    current_investigation = Column(Text, nullable=True)  # JSON
    open_evidence_ids = Column(Text, nullable=True)  # JSON array
    current_replay_id = Column(Integer, nullable=True)
    current_report_draft = Column(Text, nullable=True)  # JSON
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Notification(Base):
    """Internal operational notifications — persisted from NotificationHub."""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    notification_type = Column(String, nullable=False, index=True)
    title = Column(String, nullable=True)
    message = Column(String, nullable=False)
    severity = Column(String, nullable=True, default="info")
    priority = Column(String, nullable=True, default="medium")
    linked_type = Column(String, nullable=True)
    linked_id = Column(Integer, nullable=True)
    dedup_key = Column(String, nullable=True)
    is_read = Column(String, nullable=False, default="false")
    delivered_via = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Device(Base):
    """Push notification device registrations."""
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=True, index=True)
    platform = Column(String, nullable=False, index=True)  # fcm, apns, webpush
    token = Column(String, nullable=False)
    name = Column(String, nullable=True)
    is_active = Column(String, nullable=False, default="true")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class DeliveryRecord(Base):
    """Notification delivery status per channel."""
    __tablename__ = "delivery_records"

    id = Column(Integer, primary_key=True, index=True)
    notification_id = Column(Integer, ForeignKey("notifications.id"), nullable=False, index=True)
    channel = Column(String, nullable=False)  # desktop, web, mobile, email, fcm
    status = Column(String, nullable=False, default="pending")  # pending, sent, failed
    error = Column(Text, nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class QuickWin(Base):
    """Stores actionable quick wins associated with a target."""
    __tablename__ = "quick_wins"

    id = Column(Integer, primary_key=True, index=True)

    target_id = Column(
        Integer,
        ForeignKey("targets.id"),
        nullable=False,
        index=True,
    )

    title = Column(String, nullable=False)
    impact = Column(String, nullable=False, default="medium")
    description = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class TargetIdentity(Base):
    """An identity/persona the investigator uses when interacting with a target."""
    __tablename__ = "target_identities"

    id = Column(Integer, primary_key=True, index=True)

    target_id = Column(
        Integer,
        ForeignKey("targets.id"),
        nullable=False,
        index=True,
    )

    label = Column(
        String,
        nullable=False,
        default="Default",
    )

    # login_form | bearer_token | api_key | cookie | basic_auth | none
    auth_type = Column(String, nullable=False, default="none")

    # AES-256-GCM encrypted JSON: {username?, password?, token?, api_key?, login_url?, login_params?}
    credentials_encrypted = Column(Text, nullable=True)

    # Nonce/IV for AES-GCM decryption
    credentials_nonce = Column(String, nullable=True)

    # Whether this is the primary identity for baseline comparisons
    is_baseline = Column(Boolean, default=False)

    is_active = Column(Boolean, default=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class TargetSession(Base):
    """Active authenticated session for a target identity."""
    __tablename__ = "target_sessions"

    id = Column(Integer, primary_key=True, index=True)

    identity_id = Column(
        Integer,
        ForeignKey("target_identities.id"),
        nullable=False,
        index=True,
        unique=True,
    )

    # AES-256-GCM encrypted access token
    token_encrypted = Column(Text, nullable=True)

    # AES-256-GCM encrypted JSON cookies object
    cookies_encrypted = Column(Text, nullable=True)

    expires_at = Column(DateTime(timezone=True), nullable=True)

    last_refresh_at = Column(DateTime(timezone=True), nullable=True)

    is_valid = Column(Boolean, default=True)

    failure_count = Column(Integer, default=0)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class Investigation(Base):
    """Central workspace unit — ties together target, identities, and pipeline state."""
    __tablename__ = "investigations"

    id = Column(Integer, primary_key=True, index=True)

    target_id = Column(
        Integer,
        ForeignKey("targets.id"),
        nullable=False,
        index=True,
    )

    name = Column(String, nullable=False)

    # active | paused | completed | archived
    status = Column(String, nullable=False, default="active", index=True)

    # JSON: {recon, hypotheses, validation, reporting} stage flags
    pipeline_state = Column(Text, nullable=True)

    notes = Column(Text, nullable=True)

    # JSON array of tag strings
    tags = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class ValidationRun(Base):
    """A single execution of the validation pipeline against an endpoint."""
    __tablename__ = "validation_runs"

    id = Column(Integer, primary_key=True, index=True)

    investigation_id = Column(
        Integer,
        ForeignKey("investigations.id"),
        nullable=True,
        index=True,
    )

    endpoint_id = Column(
        Integer,
        ForeignKey("endpoints.id"),
        nullable=False,
        index=True,
    )

    identity_baseline_id = Column(
        Integer,
        ForeignKey("target_identities.id"),
        nullable=True,
    )

    identity_probe_id = Column(
        Integer,
        ForeignKey("target_identities.id"),
        nullable=True,
    )

    # running | completed | failed | aborted
    status = Column(String, nullable=False, default="running", index=True)

    verdict_id = Column(
        Integer,
        ForeignKey("verdicts.id"),
        nullable=True,
    )

    started_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    finished_at = Column(DateTime(timezone=True), nullable=True)


class Report(Base):
    """Generated report for an investigation."""
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)

    investigation_id = Column(
        Integer,
        ForeignKey("investigations.id"),
        nullable=True,
        index=True,
    )

    # hackerone_json | bugcrowd_html | markdown | html
    format = Column(String, nullable=False, default="markdown")

    content = Column(Text, nullable=True)

    # JSON array of finding IDs included in this report
    finding_ids = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
