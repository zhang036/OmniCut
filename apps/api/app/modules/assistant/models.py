from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.modules.assistant.models import AssistantMessage


class AssistantSession(Base):
    __tablename__ = "assistant_sessions"
    __table_args__ = (
        Index("ix_assistant_sessions_created_at", "created_at"),
        Index("ix_assistant_sessions_updated_at", "updated_at"),
        Index("ix_assistant_sessions_deleted_updated", "deleted_at", "updated_at"),
        Index("ix_assistant_sessions_pinned_updated", "is_pinned", "updated_at"),
        Index("ix_assistant_sessions_project_updated", "project_id", "updated_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, default="新对话")
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    model: Mapped[str] = mapped_column(String(100), nullable=False, default="deepseek-v4-flash")
    reasoning_mode: Mapped[str] = mapped_column(String(50), nullable=False, default="high")
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    last_message_preview: Mapped[str | None] = mapped_column(String(240), nullable=True)
    message_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_pinned: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_archived: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    prompt_cache_hit_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    prompt_cache_miss_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    messages: Mapped[list["AssistantMessage"]] = relationship(back_populates="session", cascade="all, delete-orphan")


class AssistantMessage(Base):
    __tablename__ = "assistant_messages"
    __table_args__ = (
        Index("ix_assistant_messages_session_id_sequence", "session_id", "sequence"),
        Index("ix_assistant_messages_role", "role"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("assistant_sessions.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    reasoning_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reasoning_mode: Mapped[str | None] = mapped_column(String(50), nullable=True)
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    session: Mapped[AssistantSession] = relationship(back_populates="messages")
