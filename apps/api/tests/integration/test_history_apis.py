from collections.abc import Generator
import asyncio

import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.modules.assistant.models import AssistantMessage, AssistantSession
from app.modules.chapters.models import Chapter
from app.modules.projects.models import Project
from app.modules.shots.models import Shot


def build_client() -> tuple[httpx.AsyncClient, Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    def override_get_db() -> Generator[Session, None, None]:
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver"), db


def teardown_client(db: Session) -> None:
    db.close()
    app.dependency_overrides.clear()


async def run_assistant_session_history_lists_and_loads_messages():
    client, db = build_client()
    try:
        session = AssistantSession(
            title="产品教程讨论",
            model="deepseek-v4-flash",
            reasoning_mode="high",
            last_message_preview="生成 5 个镜头",
            message_count=2,
        )
        db.add(session)
        db.flush()
        db.add_all(
            [
                AssistantMessage(session_id=session.id, role="user", content="帮我拆分镜", sequence=1),
                AssistantMessage(session_id=session.id, role="assistant", content="可以，先拆成 5 个镜头。", sequence=2),
            ]
        )
        db.commit()

        list_response = await client.get("/api/assistant/sessions")
        assert list_response.status_code == 200
        assert list_response.json()["items"][0]["title"] == "产品教程讨论"
        assert list_response.json()["items"][0]["last_message_preview"] == "生成 5 个镜头"
        assert list_response.json()["items"][0]["message_count"] == 2

        messages_response = await client.get(f"/api/assistant/sessions/{session.id}/messages")
        assert messages_response.status_code == 200
        assert [item["role"] for item in messages_response.json()["items"]] == ["user", "assistant"]
    finally:
        teardown_client(db)
        await client.aclose()


def test_assistant_session_history_lists_and_loads_messages():
    asyncio.run(run_assistant_session_history_lists_and_loads_messages())


async def run_assistant_session_can_be_created_renamed_and_soft_deleted():
    client, db = build_client()
    try:
        create_response = await client.post("/api/assistant/sessions", json={"title": "新对话"})
        assert create_response.status_code == 200
        session_id = create_response.json()["id"]

        rename_response = await client.patch(f"/api/assistant/sessions/{session_id}", json={"title": "改名后的对话"})
        assert rename_response.status_code == 200
        assert rename_response.json()["title"] == "改名后的对话"

        delete_response = await client.delete(f"/api/assistant/sessions/{session_id}")
        assert delete_response.status_code == 200

        list_response = await client.get("/api/assistant/sessions")
        assert list_response.json()["items"] == []
    finally:
        teardown_client(db)
        await client.aclose()


def test_assistant_session_can_be_created_renamed_and_soft_deleted():
    asyncio.run(run_assistant_session_can_be_created_renamed_and_soft_deleted())


async def run_project_history_lists_project_and_loads_draft_detail():
    client, db = build_client()
    try:
        project = Project(title="产品教程视频", description="教程草稿", chapter_count=1, shot_count=1)
        db.add(project)
        db.flush()
        chapter = Chapter(project_id=project.id, title="第一章", sort_order=1)
        db.add(chapter)
        db.flush()
        db.add(
            Shot(
                project_id=project.id,
                chapter_id=chapter.id,
                title="镜头 01",
                visual_description="画面描述",
                voiceover="旁白",
                on_screen_text="屏幕文字",
                duration_seconds=5,
                sort_order=1,
            )
        )
        db.commit()

        list_response = await client.get("/api/projects")
        assert list_response.status_code == 200
        assert list_response.json()["items"][0]["title"] == "产品教程视频"
        assert list_response.json()["items"][0]["chapter_count"] == 1
        assert list_response.json()["items"][0]["shot_count"] == 1

        detail_response = await client.get(f"/api/projects/{project.id}")
        assert detail_response.status_code == 200
        detail = detail_response.json()
        assert detail["chapters"][0]["title"] == "第一章"
        assert detail["chapters"][0]["shots"][0]["visual_description"] == "画面描述"
    finally:
        teardown_client(db)
        await client.aclose()


def test_project_history_lists_project_and_loads_draft_detail():
    asyncio.run(run_project_history_lists_project_and_loads_draft_detail())


async def run_project_can_be_created_saved_and_soft_deleted():
    client, db = build_client()
    try:
        create_response = await client.post("/api/projects", json={"title": "新项目", "description": ""})
        assert create_response.status_code == 200
        project_id = create_response.json()["id"]

        save_response = await client.put(
            f"/api/projects/{project_id}/draft",
            json={
                "title": "新项目",
                "description": "正式草稿",
                "chapters": [
                    {
                        "title": "章节 A",
                        "sort_order": 1,
                        "shots": [
                            {
                                "title": "镜头 A",
                                "visual_description": "画面 A",
                                "voiceover": "旁白 A",
                                "on_screen_text": "文字 A",
                                "duration_seconds": 6,
                                "sort_order": 1,
                            }
                        ],
                    }
                ],
            },
        )
        assert save_response.status_code == 200
        assert save_response.json()["chapter_count"] == 1
        assert save_response.json()["shot_count"] == 1

        detail_response = await client.get(f"/api/projects/{project_id}")
        assert detail_response.json()["chapters"][0]["shots"][0]["title"] == "镜头 A"

        delete_response = await client.delete(f"/api/projects/{project_id}")
        assert delete_response.status_code == 200
        list_response = await client.get("/api/projects")
        assert list_response.json()["items"] == []
    finally:
        teardown_client(db)
        await client.aclose()


def test_project_can_be_created_saved_and_soft_deleted():
    asyncio.run(run_project_can_be_created_saved_and_soft_deleted())


async def run_project_snapshot_can_be_created_and_restored():
    client, db = build_client()
    try:
        create_response = await client.post("/api/projects", json={"title": "快照项目", "description": "原始描述"})
        project_id = create_response.json()["id"]
        await client.put(
            f"/api/projects/{project_id}/draft",
            json={
                "title": "快照项目",
                "description": "原始描述",
                "chapters": [
                    {
                        "title": "原始章节",
                        "sort_order": 1,
                        "shots": [
                            {
                                "title": "原始镜头",
                                "visual_description": "原始画面",
                                "voiceover": "原始旁白",
                                "on_screen_text": "原始文字",
                                "duration_seconds": 8,
                                "sort_order": 1,
                            }
                        ],
                    }
                ],
            },
        )

        snapshot_response = await client.post(
            f"/api/projects/{project_id}/snapshots",
            json={"title": "第一版", "summary": "保存原始版本", "snapshot_type": "manual"},
        )
        assert snapshot_response.status_code == 200
        snapshot_id = snapshot_response.json()["id"]

        await client.put(
            f"/api/projects/{project_id}/draft",
            json={"title": "快照项目", "description": "已修改", "chapters": []},
        )
        restore_response = await client.post(f"/api/projects/{project_id}/snapshots/{snapshot_id}/restore")
        assert restore_response.status_code == 200

        detail_response = await client.get(f"/api/projects/{project_id}")
        detail = detail_response.json()
        assert detail["description"] == "原始描述"
        assert detail["chapters"][0]["title"] == "原始章节"
        assert detail["chapters"][0]["shots"][0]["title"] == "原始镜头"
    finally:
        teardown_client(db)
        await client.aclose()


def test_project_snapshot_can_be_created_and_restored():
    asyncio.run(run_project_snapshot_can_be_created_and_restored())


async def run_project_operation_can_be_created_applied_and_rejected():
    client, db = build_client()
    try:
        create_response = await client.post("/api/projects", json={"title": "操作项目", "description": ""})
        project_id = create_response.json()["id"]

        operation_response = await client.post(
            f"/api/projects/{project_id}/operations",
            json={"operation_type": "create_shot", "payload_json": "{\"title\": \"镜头建议\"}"},
        )
        assert operation_response.status_code == 200
        operation_id = operation_response.json()["id"]
        assert operation_response.json()["status"] == "pending"

        apply_response = await client.post(f"/api/projects/{project_id}/operations/{operation_id}/apply")
        assert apply_response.status_code == 200
        assert apply_response.json()["status"] == "applied"

        reject_operation_response = await client.post(
            f"/api/projects/{project_id}/operations",
            json={"operation_type": "create_chapter", "payload_json": "{\"title\": \"章节建议\"}"},
        )
        reject_operation_id = reject_operation_response.json()["id"]
        reject_response = await client.post(f"/api/projects/{project_id}/operations/{reject_operation_id}/reject")
        assert reject_response.status_code == 200
        assert reject_response.json()["status"] == "rejected"

        list_response = await client.get(f"/api/projects/{project_id}/operations")
        assert [item["status"] for item in list_response.json()["items"]] == ["rejected", "applied"]
    finally:
        teardown_client(db)
        await client.aclose()


def test_project_operation_can_be_created_applied_and_rejected():
    asyncio.run(run_project_operation_can_be_created_applied_and_rejected())
