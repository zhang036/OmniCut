from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.modules.chapters.models import Chapter
from app.modules.projects.history_models import ProjectOperation, ProjectSnapshot
from app.modules.projects.models import Project
from app.modules.projects.schemas import (
    ChapterDraftOutput,
    ProjectCreate,
    ProjectDetailResponse,
    ProjectDraftSave,
    ProjectListItem,
    ProjectListResponse,
    ProjectOperationCreate,
    ProjectOperationItem,
    ProjectOperationListResponse,
    ProjectSnapshotCreate,
    ProjectSnapshotItem,
    ProjectSnapshotListResponse,
    ProjectUpdate,
    ShotDraftOutput,
)
from app.modules.shots.models import Shot

router = APIRouter(prefix="/api/projects", tags=["projects"])


def _serialize_project_payload(project: Project) -> str:
    return _project_detail(project).model_dump_json()


def _get_project_or_404(project_id: int, db: Session) -> Project:
    project = db.get(Project, project_id)
    if project is None or project.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _project_detail(project: Project) -> ProjectDetailResponse:
    chapters = sorted([chapter for chapter in project.chapters if chapter.deleted_at is None], key=lambda item: item.sort_order)
    return ProjectDetailResponse(
        id=project.id,
        title=project.title,
        description=project.description,
        status=project.status,
        chapter_count=project.chapter_count,
        shot_count=project.shot_count,
        chapters=[
            ChapterDraftOutput(
                id=chapter.id,
                title=chapter.title,
                summary=chapter.summary,
                sort_order=chapter.sort_order,
                shots=[
                    ShotDraftOutput(
                        id=shot.id,
                        title=shot.title,
                        visual_description=shot.visual_description,
                        voiceover=shot.voiceover,
                        on_screen_text=shot.on_screen_text,
                        duration_seconds=shot.duration_seconds,
                        sort_order=shot.sort_order,
                    )
                    for shot in sorted([shot for shot in chapter.shots if shot.deleted_at is None], key=lambda item: item.sort_order)
                ],
            )
            for chapter in chapters
        ],
    )


@router.get("", response_model=ProjectListResponse)
def list_projects(db: Session = Depends(get_db), q: str | None = None, limit: int = 30) -> ProjectListResponse:
    query = db.query(Project).filter(Project.deleted_at.is_(None))
    if q:
        query = query.filter(Project.title.contains(q))
    projects = query.order_by(Project.is_pinned.desc(), Project.updated_at.desc()).limit(min(limit, 100)).all()
    return ProjectListResponse(items=[ProjectListItem.model_validate(project, from_attributes=True) for project in projects])


@router.post("", response_model=None)
def create_project(request: ProjectCreate, db: Session = Depends(get_db)) -> Project:
    project = Project(title=request.title, description=request.description, chapter_count=0, shot_count=0, last_opened_at=datetime.now(UTC).replace(tzinfo=None))
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectDetailResponse)
def get_project(project_id: int, db: Session = Depends(get_db)) -> ProjectDetailResponse:
    project = (
        db.query(Project)
        .options(selectinload(Project.chapters).selectinload(Chapter.shots))
        .filter(Project.id == project_id, Project.deleted_at.is_(None))
        .first()
    )
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return _project_detail(project)


@router.patch("/{project_id}", response_model=None)
def update_project(project_id: int, request: ProjectUpdate, db: Session = Depends(get_db)) -> Project:
    project = _get_project_or_404(project_id, db)
    if request.title is not None:
        project.title = request.title
    if request.description is not None:
        project.description = request.description
    if request.status is not None:
        project.status = request.status
    if request.is_pinned is not None:
        project.is_pinned = request.is_pinned
    if request.is_archived is not None:
        project.is_archived = request.is_archived
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db)) -> dict[str, bool]:
    project = _get_project_or_404(project_id, db)
    project.deleted_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()
    return {"ok": True}


@router.post("/{project_id}/open", response_model=None)
def open_project(project_id: int, db: Session = Depends(get_db)) -> Project:
    project = _get_project_or_404(project_id, db)
    project.last_opened_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()
    db.refresh(project)
    return project


@router.put("/{project_id}/draft", response_model=None)
def save_project_draft(project_id: int, request: ProjectDraftSave, db: Session = Depends(get_db)) -> Project:
    project = _get_project_or_404(project_id, db)
    project.title = request.title
    project.description = request.description
    project.chapters.clear()
    db.flush()
    shot_count = 0
    for chapter_input in request.chapters:
        chapter = Chapter(
            project_id=project.id,
            title=chapter_input.title,
            summary=chapter_input.summary,
            sort_order=chapter_input.sort_order,
        )
        project.chapters.append(chapter)
        db.flush()
        for shot_input in chapter_input.shots:
            chapter.shots.append(
                Shot(
                    project_id=project.id,
                    chapter_id=chapter.id,
                    title=shot_input.title,
                    visual_description=shot_input.visual_description,
                    voiceover=shot_input.voiceover,
                    on_screen_text=shot_input.on_screen_text,
                    duration_seconds=shot_input.duration_seconds,
                    sort_order=shot_input.sort_order,
                )
            )
            shot_count += 1
    project.chapter_count = len(request.chapters)
    project.shot_count = shot_count
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}/snapshots", response_model=ProjectSnapshotListResponse)
def list_project_snapshots(project_id: int, db: Session = Depends(get_db), limit: int = 30) -> ProjectSnapshotListResponse:
    _get_project_or_404(project_id, db)
    snapshots = (
        db.query(ProjectSnapshot)
        .filter(ProjectSnapshot.project_id == project_id)
        .order_by(ProjectSnapshot.created_at.desc())
        .limit(min(limit, 100))
        .all()
    )
    return ProjectSnapshotListResponse(items=[ProjectSnapshotItem.model_validate(snapshot, from_attributes=True) for snapshot in snapshots])


@router.post("/{project_id}/snapshots", response_model=None)
def create_project_snapshot(project_id: int, request: ProjectSnapshotCreate, db: Session = Depends(get_db)) -> ProjectSnapshot:
    project = (
        db.query(Project)
        .options(selectinload(Project.chapters).selectinload(Chapter.shots))
        .filter(Project.id == project_id, Project.deleted_at.is_(None))
        .first()
    )
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    snapshot = ProjectSnapshot(
        project_id=project_id,
        title=request.title,
        summary=request.summary,
        snapshot_type=request.snapshot_type,
        payload_json=_serialize_project_payload(project),
        created_by=request.created_by,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


@router.get("/{project_id}/operations", response_model=ProjectOperationListResponse)
def list_project_operations(project_id: int, db: Session = Depends(get_db), limit: int = 30) -> ProjectOperationListResponse:
    _get_project_or_404(project_id, db)
    operations = (
        db.query(ProjectOperation)
        .filter(ProjectOperation.project_id == project_id)
        .order_by(ProjectOperation.created_at.desc())
        .limit(min(limit, 100))
        .all()
    )
    return ProjectOperationListResponse(items=[ProjectOperationItem.model_validate(operation, from_attributes=True) for operation in operations])


@router.post("/{project_id}/operations", response_model=None)
def create_project_operation(project_id: int, request: ProjectOperationCreate, db: Session = Depends(get_db)) -> ProjectOperation:
    _get_project_or_404(project_id, db)
    operation = ProjectOperation(
        project_id=project_id,
        assistant_session_id=request.assistant_session_id,
        operation_type=request.operation_type,
        status="pending",
        payload_json=request.payload_json,
    )
    db.add(operation)
    db.commit()
    db.refresh(operation)
    return operation


@router.post("/{project_id}/operations/{operation_id}/apply", response_model=None)
def apply_project_operation(project_id: int, operation_id: int, db: Session = Depends(get_db)) -> ProjectOperation:
    _get_project_or_404(project_id, db)
    operation = db.get(ProjectOperation, operation_id)
    if operation is None or operation.project_id != project_id:
        raise HTTPException(status_code=404, detail="Project operation not found")
    operation.status = "applied"
    operation.applied_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()
    db.refresh(operation)
    return operation


@router.post("/{project_id}/operations/{operation_id}/reject", response_model=None)
def reject_project_operation(project_id: int, operation_id: int, db: Session = Depends(get_db)) -> ProjectOperation:
    _get_project_or_404(project_id, db)
    operation = db.get(ProjectOperation, operation_id)
    if operation is None or operation.project_id != project_id:
        raise HTTPException(status_code=404, detail="Project operation not found")
    operation.status = "rejected"
    operation.rejected_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()
    db.refresh(operation)
    return operation


@router.post("/{project_id}/snapshots/{snapshot_id}/restore", response_model=None)
def restore_project_snapshot(project_id: int, snapshot_id: int, db: Session = Depends(get_db)) -> Project:
    project = _get_project_or_404(project_id, db)
    snapshot = db.get(ProjectSnapshot, snapshot_id)
    if snapshot is None or snapshot.project_id != project_id:
        raise HTTPException(status_code=404, detail="Project snapshot not found")
    import json

    payload = json.loads(snapshot.payload_json)
    project.title = payload["title"]
    project.description = payload.get("description")
    project.chapters.clear()
    db.flush()
    shot_count = 0
    chapters = payload.get("chapters", [])
    for chapter_payload in chapters:
        chapter = Chapter(
            project_id=project.id,
            title=chapter_payload["title"],
            summary=chapter_payload.get("summary"),
            sort_order=chapter_payload.get("sort_order", 0),
        )
        project.chapters.append(chapter)
        db.flush()
        for shot_payload in chapter_payload.get("shots", []):
            chapter.shots.append(
                Shot(
                    project_id=project.id,
                    chapter_id=chapter.id,
                    title=shot_payload["title"],
                    visual_description=shot_payload.get("visual_description"),
                    voiceover=shot_payload.get("voiceover"),
                    on_screen_text=shot_payload.get("on_screen_text"),
                    duration_seconds=shot_payload.get("duration_seconds"),
                    sort_order=shot_payload.get("sort_order", 0),
                )
            )
            shot_count += 1
    project.chapter_count = len(chapters)
    project.shot_count = shot_count
    db.commit()
    db.refresh(project)
    return project
