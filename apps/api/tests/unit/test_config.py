from app.core.config import Settings


def test_default_database_url_uses_mysql_driver():
    settings = Settings()

    assert settings.database_url.startswith("mysql+pymysql://")
