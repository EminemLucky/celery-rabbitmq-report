def test_batch_export_requires_auth(client):
    r = client.post("/api/report/batch-export", json={"report_ids": [1]})
    assert r.status_code == 401


def test_batch_export_empty(client, register_and_login):
    access, _, _ = register_and_login()
    headers = {"Authorization": f"Bearer {access}"}
    r = client.post("/api/report/batch-export", json={"report_ids": []}, headers=headers)
    assert r.status_code == 400