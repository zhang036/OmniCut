from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AssistantChatRequest(BaseModel):
    message: str = Field(min_length=1)
    session_id: int | None = None
    model: str = "deepseek-v4-flash"
    reasoning_mode: str = "high"


class AssistantModelOption(BaseModel):
    id: str
    label: str
    description: str


class AssistantReasoningModeOption(BaseModel):
    id: str
    label: str
    description: str


class AssistantOptionsResponse(BaseModel):
    models: list[AssistantModelOption]
    reasoning_modes: list[AssistantReasoningModeOption]


class AssistantSessionCreate(BaseModel):
    title: str = Field("新对话", min_length=1, max_length=200)
    model: str = "deepseek-v4-flash"
    reasoning_mode: str = "high"


class AssistantSessionUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    is_pinned: int | None = None
    is_archived: int | None = None


class AssistantSessionListItem(BaseModel):
    id: int
    title: str
    model: str
    reasoning_mode: str
    last_message_preview: str | None
    message_count: int
    is_pinned: int
    updated_at: datetime


class AssistantSessionListResponse(BaseModel):
    items: list[AssistantSessionListItem]


class AssistantMessageItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    content: str
    reasoning_content: str | None
    sequence: int
    created_at: datetime


class AssistantMessageListResponse(BaseModel):
    items: list[AssistantMessageItem]
