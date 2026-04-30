from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


_COLUMN_DEFINITIONS: dict[str, dict[str, str]] = {
    "assistant_sessions": {
        "summary": "TEXT NULL",
        "project_id": "INTEGER NULL",
        "last_message_preview": "VARCHAR(240) NULL",
        "message_count": "INTEGER NOT NULL DEFAULT 0",
        "is_pinned": "INTEGER NOT NULL DEFAULT 0",
        "is_archived": "INTEGER NOT NULL DEFAULT 0",
        "deleted_at": "DATETIME NULL",
    },
    "assistant_messages": {
        "prompt_tokens": "INTEGER NOT NULL DEFAULT 0",
        "completion_tokens": "INTEGER NOT NULL DEFAULT 0",
        "total_tokens": "INTEGER NOT NULL DEFAULT 0",
    },
    "projects": {
        "chapter_count": "INTEGER NOT NULL DEFAULT 0",
        "shot_count": "INTEGER NOT NULL DEFAULT 0",
        "is_pinned": "INTEGER NOT NULL DEFAULT 0",
        "is_archived": "INTEGER NOT NULL DEFAULT 0",
        "last_opened_at": "DATETIME NULL",
        "deleted_at": "DATETIME NULL",
    },
    "chapters": {
        "deleted_at": "DATETIME NULL",
    },
    "shots": {
        "deleted_at": "DATETIME NULL",
    },
}

_INDEX_DEFINITIONS: dict[str, dict[str, tuple[str, ...]]] = {
    "assistant_sessions": {
        "ix_assistant_sessions_created_at": ("created_at",),
        "ix_assistant_sessions_updated_at": ("updated_at",),
        "ix_assistant_sessions_deleted_updated": ("deleted_at", "updated_at"),
        "ix_assistant_sessions_pinned_updated": ("is_pinned", "updated_at"),
        "ix_assistant_sessions_project_updated": ("project_id", "updated_at"),
    },
    "assistant_messages": {
        "ix_assistant_messages_session_id_sequence": ("session_id", "sequence"),
        "ix_assistant_messages_role": ("role",),
    },
    "projects": {
        "ix_projects_status": ("status",),
        "ix_projects_created_at": ("created_at",),
        "ix_projects_deleted_updated": ("deleted_at", "updated_at"),
        "ix_projects_deleted_last_opened": ("deleted_at", "last_opened_at"),
        "ix_projects_pinned_updated": ("is_pinned", "updated_at"),
    },
    "chapters": {
        "ix_chapters_project_id": ("project_id",),
        "ix_chapters_project_id_sort_order": ("project_id", "sort_order"),
    },
    "shots": {
        "ix_shots_project_id": ("project_id",),
        "ix_shots_chapter_id_sort_order": ("chapter_id", "sort_order"),
        "ix_shots_status": ("status",),
    },
    "project_snapshots": {
        "ix_project_snapshots_project_created": ("project_id", "created_at"),
        "ix_project_snapshots_project_type_created": ("project_id", "snapshot_type", "created_at"),
    },
    "project_operations": {
        "ix_project_operations_project_created": ("project_id", "created_at"),
        "ix_project_operations_project_status_created": ("project_id", "status", "created_at"),
    },
}

def ensure_history_schema(engine: Engine) -> None:
    with engine.begin() as connection:
        inspector = inspect(connection)
        existing_tables = set(inspector.get_table_names())
        for table_name, columns in _COLUMN_DEFINITIONS.items():
            if table_name not in existing_tables:
                continue
            existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
            for column_name, definition in columns.items():
                if column_name in existing_columns:
                    continue
                connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}"))
                existing_columns.add(column_name)
        inspector = inspect(connection)
        for table_name, indexes in _INDEX_DEFINITIONS.items():
            if table_name not in existing_tables:
                continue
            existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
            existing_indexes = {index["name"] for index in inspector.get_indexes(table_name)}
            for index_name, columns in indexes.items():
                if index_name in existing_indexes or not set(columns).issubset(existing_columns):
                    continue
                column_names = ", ".join(columns)
                connection.execute(text(f"CREATE INDEX {index_name} ON {table_name} ({column_names})"))

