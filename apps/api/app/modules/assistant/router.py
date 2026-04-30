import json
from collections.abc import AsyncGenerator
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import SessionLocal, get_db
from app.modules.assistant.context import build_llm_messages
from app.modules.assistant.models import AssistantMessage, AssistantSession
from app.modules.assistant.options import get_assistant_options
from app.modules.assistant.schemas import (
    AssistantChatRequest,
    AssistantMessageItem,
    AssistantMessageListResponse,
    AssistantOptionsResponse,
    AssistantSessionCreate,
    AssistantSessionListItem,
    AssistantSessionListResponse,
    AssistantSessionUpdate,
)
from app.modules.memory.service import build_memory_prompt, list_memory_context
from app.services.llm.deepseek_client import DeepSeekStreamClient

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


@router.get("/options", response_model=AssistantOptionsResponse)
def assistant_options() -> AssistantOptionsResponse:
    return get_assistant_options()


@router.get("/sessions", response_model=AssistantSessionListResponse)
def list_sessions(db: Session = Depends(get_db), q: str | None = None, limit: int = 30) -> AssistantSessionListResponse:
    query = db.query(AssistantSession).filter(AssistantSession.deleted_at.is_(None))
    if q:
        query = query.filter(AssistantSession.title.contains(q))
    sessions = query.order_by(AssistantSession.is_pinned.desc(), AssistantSession.updated_at.desc()).limit(min(limit, 100)).all()
    return AssistantSessionListResponse(items=[AssistantSessionListItem.model_validate(session, from_attributes=True) for session in sessions])


@router.post("/sessions", response_model=None)
def create_session(request: AssistantSessionCreate, db: Session = Depends(get_db)) -> AssistantSession:
    session = AssistantSession(title=request.title, model=request.model, reasoning_mode=request.reasoning_mode)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.patch("/sessions/{session_id}", response_model=None)
def update_session(session_id: int, request: AssistantSessionUpdate, db: Session = Depends(get_db)) -> AssistantSession:
    session = db.get(AssistantSession, session_id)
    if session is None or session.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Assistant session not found")
    if request.title is not None:
        session.title = request.title
    if request.is_pinned is not None:
        session.is_pinned = request.is_pinned
    if request.is_archived is not None:
        session.is_archived = request.is_archived
    db.commit()
    db.refresh(session)
    return session


@router.delete("/sessions/{session_id}")
def delete_session(session_id: int, db: Session = Depends(get_db)) -> dict[str, bool]:
    session = db.get(AssistantSession, session_id)
    if session is None or session.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Assistant session not found")
    session.deleted_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()
    return {"ok": True}


@router.get("/sessions/{session_id}/messages", response_model=AssistantMessageListResponse)
def list_session_messages(session_id: int, db: Session = Depends(get_db), limit: int = 200) -> AssistantMessageListResponse:
    session = db.get(AssistantSession, session_id)
    if session is None or session.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Assistant session not found")
    messages = (
        db.query(AssistantMessage)
        .filter(AssistantMessage.session_id == session_id)
        .order_by(AssistantMessage.sequence.asc())
        .limit(min(limit, 500))
        .all()
    )
    return AssistantMessageListResponse(items=[AssistantMessageItem.model_validate(message, from_attributes=True) for message in messages])


def _next_sequence(db: Session, session_id: int) -> int:
    last_message = (
        db.query(AssistantMessage)
        .filter(AssistantMessage.session_id == session_id)
        .order_by(AssistantMessage.sequence.desc())
        .first()
    )
    return 1 if last_message is None else last_message.sequence + 1


def _format_sse(event: str, data: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/chat/stream")
def stream_chat(request: AssistantChatRequest, db: Session = Depends(get_db)) -> StreamingResponse:
    session = db.get(AssistantSession, request.session_id) if request.session_id else None
    if session is None:
        session = AssistantSession(
            title=request.message[:40] or "新对话",
            model=request.model,
            reasoning_mode=request.reasoning_mode,
        )
        db.add(session)
        db.commit()
        db.refresh(session)
    else:
        session.model = request.model
        session.reasoning_mode = request.reasoning_mode
        db.commit()
        db.refresh(session)

    sequence = _next_sequence(db, session.id)
    user_message = AssistantMessage(
        session_id=session.id,
        role="user",
        content=request.message,
        model=request.model,
        reasoning_mode=request.reasoning_mode,
        sequence=sequence,
    )
    db.add(user_message)
    session.last_message_preview = request.message[:240]
    session.message_count += 1
    db.commit()

    history = (
        db.query(AssistantMessage)
        .filter(AssistantMessage.session_id == session.id)
        .order_by(AssistantMessage.sequence.asc())
        .all()
    )
    memory_prompt = build_memory_prompt(list_memory_context(db))
    llm_messages = build_llm_messages(history[:-1], request.message)
    if memory_prompt:
        llm_messages.insert(0, {"role": "system", "content": memory_prompt})

    async def event_stream() -> AsyncGenerator[str, None]:
        yield _format_sse("session", {"session_id": session.id})
        yield _format_sse("start", {"message": "stream started"})
        client = DeepSeekStreamClient()
        content_parts: list[str] = []
        reasoning_parts: list[str] = []
        prompt_cache_hit_tokens = 0
        prompt_cache_miss_tokens = 0
        async for chunk in client.stream_chat(
            model=request.model,
            messages=llm_messages,
            reasoning_mode=request.reasoning_mode,
        ):
            chunk_type = chunk["type"]
            chunk_content = chunk["content"]
            if chunk_type == "content":
                content_parts.append(chunk_content)
                yield _format_sse("content", {"delta": chunk_content})
            elif chunk_type == "reasoning":
                reasoning_parts.append(chunk_content)
                yield _format_sse("reasoning", {"delta": chunk_content})
            elif chunk_type == "error":
                yield _format_sse("error", {"message": chunk_content})
                return
            elif chunk_type == "usage":
                usage = json.loads(chunk_content)
                prompt_cache_hit_tokens = usage.get("prompt_cache_hit_tokens", 0)
                prompt_cache_miss_tokens = usage.get("prompt_cache_miss_tokens", 0)
                yield _format_sse("usage", usage)

        save_db = SessionLocal()
        try:
            save_session = save_db.get(AssistantSession, session.id)
            if save_session is not None:
                save_session.prompt_cache_hit_tokens += prompt_cache_hit_tokens
                save_session.prompt_cache_miss_tokens += prompt_cache_miss_tokens
            assistant_message = AssistantMessage(
                session_id=session.id,
                role="assistant",
                content="".join(content_parts),
                reasoning_content="".join(reasoning_parts) or None,
                model=request.model,
                reasoning_mode=request.reasoning_mode,
                sequence=sequence + 1,
            )
            save_db.add(assistant_message)
            if save_session is not None:
                assistant_content = "".join(content_parts)
                save_session.last_message_preview = assistant_content[:240]
                save_session.message_count += 1
            save_db.commit()
        finally:
            save_db.close()
        yield _format_sse("done", {"session_id": session.id})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
