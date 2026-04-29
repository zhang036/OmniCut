from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.modules.chapters.models import Chapter
    from app.modules.shots.models import Shot


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        Index("ix_projects_status", "status"),
        Index("ix_projects_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    chapters: Mapped[list["Chapter"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    shots: Mapped[list["Shot"]] = relationship(back_populates="project", cascade="all, delete-orphan")
