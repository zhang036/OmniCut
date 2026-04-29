from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class MemoryEntry(Base):
    __tablename__ = "memory_entries"
    __table_args__ = (
        Index("ix_memory_entries_scope", "scope"),
        Index("ix_memory_entries_kind", "kind"),
        Index("ix_memory_entries_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    scope: Mapped[str] = mapped_column(String(50), nullable=False, default="global")
    kind: Mapped[str] = mapped_column(String(50), nullable=False, default="preference")
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
