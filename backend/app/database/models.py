from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, ForeignKey, 
    JSON, Float, Enum as SQLEnum, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum
from .database import Base


class AgentStatus(str, enum.Enum):
    ON = "on"
    OFF = "off"


class AgentRunStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ProviderType(str, enum.Enum):
    OPENAI = "openai"
    XAI = "xai"
    GEMINI = "gemini"


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    display_name = Column(String(128), nullable=True)
    preferred_style = Column(String(32), default="professional")  # simple, detailed, friendly, professional
    use_case = Column(String(64), nullable=True)  # school, coding, productivity, research, personal, other
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    onboarding_completed = Column(Boolean, default=False)
    
    settings = relationship("UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    agents = relationship("Agent", back_populates="user", cascade="all, delete-orphan")
    ai_credentials = relationship("AICredential", back_populates="user", cascade="all, delete-orphan")
    oauth_accounts = relationship("OAuthAccount", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")


class UserSettings(Base):
    __tablename__ = "user_settings"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    default_model = Column(String(64), default="auto")
    auto_routing = Column(Boolean, default=True)
    auto_fallback = Column(Boolean, default=True)
    response_style = Column(String(32), default="professional")
    notifications_enabled = Column(Boolean, default=True)
    notification_sound = Column(Boolean, default=True)
    theme = Column(String(16), default="dark")
    notify_agent_completed = Column(Boolean, default=True)
    notify_agent_failed = Column(Boolean, default=True)
    notify_important_only = Column(Boolean, default=False)
    notify_email_needs_response = Column(Boolean, default=True)
    native_notifications = Column(Boolean, default=True)
    
    user = relationship("User", back_populates="settings")


class Session(Base):
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String(255), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_active = Column(DateTime(timezone=True), server_default=func.now())
    user_agent = Column(String(512), nullable=True)
    ip_address = Column(String(64), nullable=True)
    
    user = relationship("User", back_populates="sessions")


class AICredential(Base):
    __tablename__ = "ai_credentials"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider = Column(String(32), nullable=False)  # openai, xai, gemini
    encrypted_api_key = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    last_used = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(32), default="available")  # available, unavailable, rate_limited
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    user = relationship("User", back_populates="ai_credentials")
    
    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="uq_user_provider"),
    )


class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(256), default="New Chat")
    model = Column(String(64), default="auto")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")


class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(16), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    model_used = Column(String(64), nullable=True)
    provider_used = Column(String(32), nullable=True)
    tokens_used = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    conversation = relationship("Conversation", back_populates="messages")


class Agent(Base):
    __tablename__ = "agents"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    instructions = Column(Text, nullable=False)
    model = Column(String(64), default="auto")
    schedule_interval_minutes = Column(Integer, default=30)
    status = Column(String(16), default="off")  # on, off
    notification_enabled = Column(Boolean, default=True)
    permissions = Column(JSON, default=dict)  # e.g. {"send_email": false}
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    next_run_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    user = relationship("User", back_populates="agents")
    sources = relationship("AgentSource", back_populates="agent", cascade="all, delete-orphan")
    runs = relationship("AgentRun", back_populates="agent", cascade="all, delete-orphan", order_by="AgentRun.started_at.desc()")


class AgentSource(Base):
    __tablename__ = "agent_sources"
    
    id = Column(Integer, primary_key=True)
    agent_id = Column(Integer, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    source_type = Column(String(32), nullable=False)  # rss, api, web
    url = Column(String(1024), nullable=False)
    name = Column(String(256), nullable=True)
    config = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True)
    last_fetched_at = Column(DateTime(timezone=True), nullable=True)
    last_content_hash = Column(String(64), nullable=True)
    
    agent = relationship("Agent", back_populates="sources")


class AgentRun(Base):
    __tablename__ = "agent_runs"
    
    id = Column(Integer, primary_key=True)
    agent_id = Column(Integer, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(16), default="pending")
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    sources_checked = Column(Integer, default=0)
    changes_detected = Column(Integer, default=0)
    model_used = Column(String(64), nullable=True)
    provider_used = Column(String(32), nullable=True)
    ai_result = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    notification_sent = Column(Boolean, default=False)
    error_message = Column(Text, nullable=True)
    raw_data = Column(JSON, default=dict)
    
    agent = relationship("Agent", back_populates="runs")


class OAuthAccount(Base):
    __tablename__ = "oauth_accounts"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider = Column(String(32), nullable=False)  # google
    provider_user_id = Column(String(256), nullable=True)
    email = Column(String(256), nullable=True)
    encrypted_access_token = Column(Text, nullable=True)
    encrypted_refresh_token = Column(Text, nullable=True)
    token_expires_at = Column(DateTime(timezone=True), nullable=True)
    scopes = Column(JSON, default=list)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    user = relationship("User", back_populates="oauth_accounts")
    
    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="uq_user_oauth_provider"),
    )


class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    agent_id = Column(Integer, ForeignKey("agents.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(256), nullable=False)
    body = Column(Text, nullable=True)
    is_read = Column(Boolean, default=False)
    data = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="notifications")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    action = Column(String(64), nullable=False)
    resource_type = Column(String(32), nullable=True)
    resource_id = Column(Integer, nullable=True)
    details = Column(JSON, default=dict)
    ip_address = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="audit_logs")
    
    __table_args__ = (
        Index("ix_audit_logs_user_created", "user_id", "created_at"),
    )
