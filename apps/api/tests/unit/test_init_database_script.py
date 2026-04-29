from scripts.init_database import get_database_name, get_server_url


def test_get_database_name_from_mysql_url():
    database_name = get_database_name("mysql+pymysql://root:password@127.0.0.1:3306/omnicut?charset=utf8mb4")

    assert database_name == "omnicut"


def test_get_server_url_removes_database_name():
    server_url = get_server_url("mysql+pymysql://root:password@127.0.0.1:3306/omnicut?charset=utf8mb4")

    assert server_url.database is None
