def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def test_submit_requires_auth(client):
    r = client.post("/api/encrypt", json={"data": "hi"})
    assert r.status_code == 401


def test_submit_and_get(client, register_and_login):
    access, _, _ = register_and_login()
    headers = auth_header(access)

    r = client.post("/api/encrypt", json={"data": "hello"}, headers=headers)
    assert r.status_code == 202
    task_id = r.get_json()["task_id"]

    r = client.get(f"/api/encrypt/{task_id}", headers=headers)
    assert r.status_code == 200
    assert r.get_json()["task_id"] == task_id


def test_user_isolation(client, register_and_login):
    """alice 的任务，bob 查不到"""
    alice_token, _, _ = register_and_login("alice", "123456")
    r = client.post("/api/encrypt", json={"data": "secret"},
                    headers=auth_header(alice_token))
    task_id = r.get_json()["task_id"]

    bob_token, _, _ = register_and_login("bob", "123456")
    r = client.get(f"/api/encrypt/{task_id}", headers=auth_header(bob_token))
    assert r.status_code == 404


def test_list_tasks_only_mine(client, register_and_login):
    alice_token, _, _ = register_and_login("alice", "123456")
    bob_token, _, _ = register_and_login("bob", "123456")

    client.post("/api/encrypt", json={"data": "a1"}, headers=auth_header(alice_token))
    client.post("/api/encrypt", json={"data": "a2"}, headers=auth_header(alice_token))
    client.post("/api/encrypt", json={"data": "b1"}, headers=auth_header(bob_token))

    r = client.get("/api/tasks", headers=auth_header(alice_token))
    assert r.status_code == 200
    assert r.get_json()["total"] == 2

    r = client.get("/api/tasks", headers=auth_header(bob_token))
    assert r.get_json()["total"] == 1


def test_admin_endpoint_forbidden_for_user(client, register_and_login):
    # alice 是 admin（第一个注册）
    register_and_login("alice", "123456")
    # bob 是 user
    bob_token, _, _ = register_and_login("bob", "123456")

    r = client.get("/api/admin/tasks", headers=auth_header(bob_token))
    assert r.status_code == 403


def test_admin_endpoint_ok_for_admin(client, register_and_login):
    alice_token, _, _ = register_and_login("alice", "123456")
    r = client.get("/api/admin/tasks", headers=auth_header(alice_token))
    assert r.status_code == 200