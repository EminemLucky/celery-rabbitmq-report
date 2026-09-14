import pytest
from app import create_app
from app.extensions import db

@pytest.fixture
def app():
    """测试用 app：内存 SQLite，Celery 同步执行"""
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_ENGINE_OPTIONS": {},          # ← 关键，清掉 MySQL 专属参数
        "CELERY_TASK_ALWAYS_EAGER": True,
        "CELERY_TASK_EAGER_PROPAGATES": True,
        "JWT_SECRET_KEY": "test-secret-key-at-least-32-bytes-long-000",
    })

    print("TEST ENGINE_OPTIONS:", app.config["SQLALCHEMY_ENGINE_OPTIONS"])  # ← 加这行
    print("TEST URI:", app.config["SQLALCHEMY_DATABASE_URI"])  # ← 加这行

    with app.app_context():
        db.create_all()
        from app.models import Role
        for name in ("admin", "user"):
            if not Role.query.filter_by(name=name).first():
                db.session.add(Role(name=name))
        db.session.commit()

        yield app

        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def register_and_login(client):
    """注册并登录，返回 (access_token, refresh_token, user)"""
    def _do(username="alice", password="123456"):
        client.post("/api/auth/register", json={
            "username": username,
            "password": password,
        })
        r = client.post("/api/auth/login", json={
            "username": username,
            "password": password,
        })
        data = r.get_json()
        return data["access_token"], data["refresh_token"], data["user"]
    return _do