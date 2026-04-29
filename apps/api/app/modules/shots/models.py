from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.modules.chapters.models import Chapter
    from app.modules.projects.models import Project


class Shot(Base):
    __tablename__ = "shots"
    __table_args__ = (
        Index("ix_shots_project_id", "project_id"),
        Index("ix_shots_chapter_id", "chapter_id"),
        Index("ix_shots_chapter_id_sort_order", "chapter_id", "sort_order"),
        Index("ix_shots_status", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    chapter_id: Mapped[int] = mapped_column(ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    shot_type: Mapped[str] = mapped_column(String(50), nullable=False, default="normal")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    visual_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    voiceover: Mapped[str | None] = mapped_column(Text, nullable=True)
    on_screen_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    project: Mapped["Project"] = relationship(back_populates="shots")
    chapter: Mapped["Chapter"] = relationship(back_populates="shots")
