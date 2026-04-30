from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ShotDraftInput(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    visual_description: str | None = None
    voiceover: str | None = None
    on_screen_text: str | None = None
    duration_seconds: int | None = None
    sort_order: int = 0


class ChapterDraftInput(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    summary: str | None = None
    sort_order: int = 0
    shots: list[ShotDraftInput] = Field(default_factory=list)


class ProjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None


class ProjectUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    status: str | None = None
    is_pinned: int | None = None
    is_archived: int | None = None


class ProjectDraftSave(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    chapters: list[ChapterDraftInput] = Field(default_factory=list)


class ProjectListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    status: str
    chapter_count: int
    shot_count: int
    is_pinned: int
    last_opened_at: datetime | None
    updated_at: datetime


class ProjectListResponse(BaseModel):
    items: list[ProjectListItem]


class ShotDraftOutput(BaseModel):
    id: int
    title: str
    visual_description: str | None
    voiceover: str | None
    on_screen_text: str | None
    duration_seconds: int | None
    sort_order: int


class ChapterDraftOutput(BaseModel):
    id: int
    title: str
    summary: str | None
    sort_order: int
    shots: list[ShotDraftOutput]


class ProjectDetailResponse(BaseModel):
    id: int
    title: str
    description: str | None
    status: str
    chapter_count: int
    shot_count: int
    chapters: list[ChapterDraftOutput]


class ProjectSnapshotCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    summary: str | None = None
    snapshot_type: str = "manual"
    created_by: str | None = None


class ProjectSnapshotItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    title: str
    summary: str | None
    snapshot_type: str
    created_by: str | None
    created_at: datetime


class ProjectSnapshotListResponse(BaseModel):
    items: list[ProjectSnapshotItem]


class ProjectOperationCreate(BaseModel):
    assistant_session_id: int | None = None
    operation_type: str = Field(min_length=1, max_length=50)
    payload_json: str = Field(min_length=1)


class ProjectOperationItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    assistant_session_id: int | None
    operation_type: str
    status: str
    payload_json: str
    result_json: str | None
    error_message: str | None
    created_at: datetime
    applied_at: datetime | None
    rejected_at: datetime | None


class ProjectOperationListResponse(BaseModel):
    items: list[ProjectOperationItem]
