def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_demo_data_seeded(client):
    r = client.get("/api/runways")
    assert r.status_code == 200
    assert {x["id"] for x in r.json()} >= {"09L", "09R", "18"}

    r = client.get("/api/flights")
    assert len(r.json()) == 6

    r = client.get("/api/closures")
    assert len(r.json()) == 1


def test_analyze_finds_demo_conflicts(client):
    r = client.post("/api/analyze")
    assert r.status_code == 200
    data = r.json()
    kinds = {c["type"] for c in data["conflicts"]}
    # 演示数据覆盖四类冲突中的三类
    assert {"SEPARATION", "CROSSING", "CLOSURE"} & kinds
    assert len(data["resolutions"]) > 0


def test_separation_matrix_update(client):
    new_matrix = {
        "departure": {"departure": 180, "arrival": 120},
        "arrival": {"departure": 120, "arrival": 150},
    }
    r = client.put("/api/separation", json={"matrix": new_matrix})
    assert r.status_code == 200
    r = client.get("/api/separation")
    assert r.json()["matrix"]["departure"]["departure"] == 180


def test_flight_crud(client):
    flight = {
        "id": "T9999",
        "callsign": "TEST9999",
        "operation": "departure",
        "runway_id": "09L",
        "takeoff_time": "2026-09-19T20:00:00Z",
        "route": [],
    }
    r = client.post("/api/flights", json=flight)
    assert r.status_code == 200

    r = client.post("/api/flights", json=flight)
    assert r.status_code == 409

    flight["takeoff_time"] = "2026-09-19T20:30:00Z"
    r = client.put("/api/flights/T9999", json=flight)
    assert r.json()["takeoff_time"].startswith("2026-09-19T20:30:00")

    r = client.delete("/api/flights/T9999")
    assert r.status_code == 204
    assert client.get("/api/flights/T9999").status_code == 404


def test_departure_requires_takeoff_time(client):
    bad = {
        "id": "X1",
        "callsign": "X1",
        "operation": "departure",
        "runway_id": "09L",
    }
    assert client.post("/api/flights", json=bad).status_code == 422


def test_closure_validation(client):
    bad = {
        "id": "BAD",
        "runway_id": "09L",
        "start_time": "2026-09-19T10:00:00Z",
        "end_time": "2026-09-19T09:00:00Z",
    }
    assert client.post("/api/closures", json=bad).status_code == 422


def test_auto_resolve_endpoint(client):
    r = client.post("/api/auto-resolve")
    assert r.status_code == 200
    data = r.json()
    # 关闭、穿越等全部可通过顺延消解
    assert data["remaining_conflicts"] == []
    assert data["total_delay_seconds"] >= 0


def test_create_closure_then_conflict(client):
    closure = {
        "id": "NEWC",
        "runway_id": "18",
        "start_time": "2026-09-19T08:00:00Z",
        "end_time": "2026-09-19T09:00:00Z",
        "reason": "临时关闭",
    }
    r = client.post("/api/closures", json=closure)
    assert r.status_code == 200
    r = client.post("/api/analyze")
    assert any(c["type"] == "CLOSURE" for c in r.json()["conflicts"])


def test_route_is_persisted(client):
    flight = {
        "id": "T1",
        "callsign": "T1",
        "operation": "departure",
        "runway_id": "18",
        "takeoff_time": "2026-09-19T21:00:00Z",
        "route": [
            {"name": "A1", "type": "taxiway"},
            {"name": "RWY18", "type": "runway", "runway_id": "18",
             "primary": True},
        ],
    }
    client.post("/api/flights", json=flight)
    r = client.get("/api/flights")
    saved = next(f for f in r.json() if f["id"] == "T1")
    assert len(saved["route"]) == 2
    assert saved["route"][1]["type"] == "runway"
