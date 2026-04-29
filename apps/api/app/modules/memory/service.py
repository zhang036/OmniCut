from sqlalchemy.orm import Session

from app.modules.memory.models import MemoryEntry


def list_memory_context(db: Session, limit: int = 10) -> list[MemoryEntry]:
    return db.query(MemoryEntry).order_by(MemoryEntry.created_at.desc()).limit(limit).all()


def build_memory_prompt(entries: list[MemoryEntry]) -> str:
    if not entries:
        return ""
    lines = ["以下是用户长期记忆和项目偏好，回答时需要参考："]
    for entry in entries:
        lines.append(f"- {entry.title}: {entry.content}")
    return "\n".join(lines)
