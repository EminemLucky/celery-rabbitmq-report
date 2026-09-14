def test_register_success(client):
    r = client.post("/api/auth/register", json={
        "username": "user1", "password": "123456"
    })
    assert r.status_code == 201
    body = r.get_json()
    assert body["username"] == "user1"
    # 第一个用户是 admin
    assert "admin" in body["roles"]


def test_register_duplicate(client):
    client.post("/api/auth/register", json={"username": "user1", "password": "123456"})
    r = client.post("/api/auth/register", json={"username": "user1", "password": "123456"})
    assert r.status_code == 409


def test_register_missing_fields(client):
    r = client.post("/api/auth/register", json={"username": "user1"})
    assert r.status_code == 400


def test_login_success(client):
    client.post("/api/auth/register", json={"username": "user1", "password": "123456"})
    r = client.post("/api/auth/login", json={"username": "user1", "password": "123456"})
    assert r.status_code == 200
    body = r.get_json()
    assert "access_token" in body
    assert "refresh_token" in body


def test_login_wrong_password(client):
    client.post("/api/auth/register", json={"username": "user1", "password": "123456"})
    r = client.post("/api/auth/login", json={"username": "user1", "password": "wrong"})
    assert r.status_code == 401


def test_me_requires_token(client):
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_me_with_token(client, register_and_login):
    access, _, _ = register_and_login()
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert r.status_code == 200
    assert r.get_json()["username"] == "alice"


def test_refresh_token(client, register_and_login):
    _, refresh, _ = register_and_login()
    r = client.post("/api/auth/refresh", headers={"Authorization": f"Bearer {refresh}"})
    assert r.status_code == 200
    assert "access_token" in r.get_json()