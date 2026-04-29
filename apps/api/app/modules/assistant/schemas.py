from pydantic import BaseModel, Field


class AssistantChatRequest(BaseModel):
    message: str = Field(min_length=1)
    session_id: int | None = None
    model: str = "deepseek-v4-pro"
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
