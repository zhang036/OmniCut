from app.db.base import Base


def test_initial_metadata_contains_core_tables():
    table_names = set(Base.metadata.tables.keys())

    assert {"projects", "chapters", "shots"}.issubset(table_names)
    assert {"assistant_sessions", "assistant_messages", "memory_entries"}.issubset(table_names)


def test_core_tables_have_expected_indexes():
    projects = Base.metadata.tables["projects"]
    chapters = Base.metadata.tables["chapters"]
    shots = Base.metadata.tables["shots"]
    assistant_sessions = Base.metadata.tables["assistant_sessions"]

    project_indexes = {index.name for index in projects.indexes}
    chapter_indexes = {index.name for index in chapters.indexes}
    shot_indexes = {index.name for index in shots.indexes}
    assistant_session_indexes = {index.name for index in assistant_sessions.indexes}

    assert "ix_projects_status" in project_indexes
    assert "ix_projects_created_at" in project_indexes
    assert "ix_chapters_project_id_sort_order" in chapter_indexes
    assert "ix_shots_chapter_id_sort_order" in shot_indexes
    assert "ix_shots_status" in shot_indexes
    assert "ix_assistant_sessions_project_updated" in assistant_session_indexes


def test_history_tables_have_expected_columns():
    assistant_sessions = Base.metadata.tables["assistant_sessions"]
    assistant_messages = Base.metadata.tables["assistant_messages"]
    projects = Base.metadata.tables["projects"]

    assert {"summary", "last_message_preview", "message_count", "project_id", "is_pinned", "is_archived", "deleted_at"}.issubset(assistant_sessions.columns.keys())
    assert {"prompt_tokens", "completion_tokens", "total_tokens"}.issubset(assistant_messages.columns.keys())
    assert {"chapter_count", "shot_count", "last_opened_at", "is_pinned", "is_archived", "deleted_at"}.issubset(projects.columns.keys())
