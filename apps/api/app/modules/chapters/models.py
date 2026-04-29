from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.modules.projects.models import Project
    from app.modules.shots.models import Shot


class Chapter(Base):
    __tablename__ = "chapters"
    __table_args__ = (
        Index("ix_chapters_project_id", "project_id"),
        Index("ix_chapters_project_id_sort_order", "project_id", "sort_order"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    project: Mapped["Project"] = relationship(back_populates="chapters")
    shots: Mapped[list["Shot"]] = relationship(back_populates="chapter", cascade="all, delete-orphan")
