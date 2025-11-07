# tests/test_users.py
def test_guest_and_member_lists(monkeypatch, client):
    import services.authentik as svc

    def fake_list_group_users(*args, **kwargs):
        # supports (group_uuid) OR (base, group_uuid)
        group_uuid = kwargs.get("group_uuid")
        if group_uuid is None:
            if len(args) == 1:
                group_uuid = args[0]
            elif len(args) >= 2:
                group_uuid = args[1]
            else:
                group_uuid = ""
        return {
            "group_name": "Guests" if "guests" in str(group_uuid) else "Members",
            "users": [
                {"pk": 1, "username": "alpha", "email": "a@example.test"},
                {"pk": 2, "username": "beta", "email": "b@example.test"},
            ],
        }

    monkeypatch.setattr(svc.ak, "list_group_users", fake_list_group_users)

    r1 = client.get("/guest-users", follow_redirects=False)
    if r1.status_code in (302, 303):
        assert r1.headers.get("location") == "/login"
        return
    assert r1.status_code == 200
    j1 = r1.json()
    assert j1["group_name"] == "Guests"
    assert len(j1["users"]) == 2

    r2 = client.get("/members-users", follow_redirects=False)
    if r2.status_code in (302, 303):
        assert r2.headers.get("location") == "/login"
        return
    assert r2.status_code == 200
    j2 = r2.json()
    assert j2["group_name"] == "Members"
    assert len(j2["users"]) == 2


def test_search_users(monkeypatch, client):
    import services.authentik as svc

    def fake_search(*args, **kwargs):
        """
        supports (q, limit=25) OR (base, q, limit)
        """
        q = kwargs.get("q")
        limit = kwargs.get("limit", 25)
        if q is None:
            if len(args) == 1:
                q = args[0]
            elif len(args) == 2:
                # could be (q, limit) OR (limit, q) detect
                a, b = args
                if isinstance(a, str):
                    q, limit = a, b
                else:
                    q, limit = b, a
            elif len(args) >= 3:
                # assume (base, q, limit)
                q = args[1]
                limit = args[2]
            else:
                q = ""
        return {"query": q, "users": [{"pk": 9, "username": "neo", "email": "n@example.test"}]}

    monkeypatch.setattr(svc.ak, "search_users", fake_search)

    r = client.get("/search-users?q=neo&limit=5", follow_redirects=False)
    if r.status_code in (302, 303):
        # When auth is enabled, the endpoint is protected and redirects to /login
        assert r.headers.get("location") == "/login"
        return

    assert r.status_code == 200
    j = r.json()
    assert j["query"] == "neo"
    assert j["users"][0]["username"] == "neo"
