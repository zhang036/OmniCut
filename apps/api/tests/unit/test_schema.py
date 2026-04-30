from sqlalchemy import create_engine, inspect, text

from app.db.schema import ensure_history_schema


def test_ensure_history_schema_adds_missing_columns_and_indexes_to_existing_tables():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE assistant_sessions (id INTEGER PRIMARY KEY, title VARCHAR(200), model VARCHAR(100), reasoning_mode VARCHAR(50), created_at DATETIME, updated_at DATETIME)"))
        connection.execute(text("CREATE TABLE assistant_messages (id INTEGER PRIMARY KEY, session_id INTEGER, role VARCHAR(50), content TEXT, sequence INTEGER, created_at DATETIME)"))
        connection.execute(text("CREATE TABLE projects (id INTEGER PRIMARY KEY, title VARCHAR(200), description TEXT, status VARCHAR(50), created_at DATETIME, updated_at DATETIME)"))

    ensure_history_schema(engine)

    inspector = inspect(engine)
    assistant_session_columns = {column["name"] for column in inspector.get_columns("assistant_sessions")}
    assistant_message_columns = {column["name"] for column in inspector.get_columns("assistant_messages")}
    project_columns = {column["name"] for column in inspector.get_columns("projects")}
    assistant_session_indexes = {index["name"] for index in inspector.get_indexes("assistant_sessions")}
    project_indexes = {index["name"] for index in inspector.get_indexes("projects")}

    assert {"summary", "project_id", "last_message_preview", "message_count", "is_pinned", "is_archived", "deleted_at"}.issubset(assistant_session_columns)
    assert {"prompt_tokens", "completion_tokens", "total_tokens"}.issubset(assistant_message_columns)
    assert {"chapter_count", "shot_count", "is_pinned", "is_archived", "last_opened_at", "deleted_at"}.issubset(project_columns)
    assert "ix_assistant_sessions_project_updated" in assistant_session_indexes
    assert "ix_projects_deleted_last_opened" in project_indexes
