def test_demote_bulk_requires_nonempty_list(client):
    r = client.post("/demote/bulk", json={"pks": []})
    assert r.status_code == 400
    r = client.post("/demote/bulk", json={"pks": None})
    assert r.status_code == 400
    r = client.post("/demote/bulk", json={})
    assert r.status_code == 400


def test_demote_bulk_pk_must_be_int(client):
    r = client.post("/demote/bulk", json={"pks": ["x", 2]})
    assert r.status_code == 400


def test_demote_bulk_too_many(client):
    too_many = list(range(1000))  # > 200 limit in router
    r = client.post("/demote/bulk", json={"pks": too_many})
    assert r.status_code == 413


def test_demote_bulk_dedupes_and_counts(monkeypatch, client):
    import services.authentik as svc

    # Always succeed
    monkeypatch.setattr(
        svc.ak, "switch_group_user_pk", lambda *a, **k: {"add": 200, "remove": 200}, raising=True
    )

    payload = {"pks": [1, 1, 2, 2, 3]}
    r = client.post("/demote/bulk", json=payload)
    assert r.status_code == 200
    j = r.json()
    # Dedup to {1,2,3}
    assert j["count_ok"] + j["count_failed"] == 3
    assert len(j["results"]) == 3
    assert all(item["ok"] for item in j["results"])
