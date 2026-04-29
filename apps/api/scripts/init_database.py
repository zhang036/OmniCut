from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url

from app.core.config import settings
from app.db.base import Base


def get_database_name(database_url: str) -> str:
    url = make_url(database_url)
    database_name = url.database
    if not database_name:
        raise ValueError("DATABASE_URL must include a database name")
    return database_name


def get_server_url(database_url: str) -> URL:
    url = make_url(database_url)
    return URL.create(
        drivername=url.drivername,
        username=url.username,
        password=url.password,
        host=url.host,
        port=url.port,
    )


def create_database_if_not_exists(database_url: str) -> None:
    database_name = get_database_name(database_url)
    server_url = get_server_url(database_url)
    engine = create_engine(server_url, isolation_level="AUTOCOMMIT")
    with engine.connect() as connection:
        connection.execute(text(f"CREATE DATABASE IF NOT EXISTS `{database_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
    engine.dispose()


def create_tables(database_url: str) -> None:
    engine = create_engine(database_url)
    Base.metadata.create_all(bind=engine)
    engine.dispose()


def init_database() -> None:
    create_database_if_not_exists(settings.database_url)
    create_tables(settings.database_url)


if __name__ == "__main__":
    init_database()
    print("Database and initial tables are ready.")
