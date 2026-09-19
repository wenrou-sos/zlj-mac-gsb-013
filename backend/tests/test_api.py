"""End-to-end API tests against a seeded SQLite database."""
from datetime import datetime, timedelta


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_config_endpoint(client, reseed):
    r = client.get("/api/config")
    data = r.json()
    assert "09L" in data["runways"]
    assert data["dep_occupy"] == 60
    assert data["wake_sep"]["HL"] == 180


def test_seeded_flights_listed(client, reseed):
    r = client.get("/api/flights")
    assert r.status_code == 200
    callsigns = {f["callsign"] for f in r.json()}
    assert {"CA1201", "CA9021", "MU2310", "HU7788"} <= callsigns


def test_rehearse_finds_demo_conflicts(client, reseed):
    r = client.get("/api/rehearse")
    data = r.json()
    assert data["conflict_count"] >= 3
    kinds = {c["type"] for c in data["conflicts"]}
    assert "SEPARATION" in kinds
    assert "CLOSURE" in kinds
    # every conflict carries at least one actionable suggestion
    for c in data["conflicts"]:
        assert c["suggestions"]
        assert c["suggestions"][0]["action"] in {"DELAY", "CHANGE_RUNWAY"}


def test_windows_payload_shape(client, reseed):
    data = client.get("/api/rehearse").json()
    assert data["windows"]
    w = data["windows"][0]
    assert {"flight_id", "callsign", "runway_start",
            "runway_end", "taxi"} <= set(w)
    assert data["closures"] and data["closures"][0]["runway"] == "09L"


def test_create_flight_then_conflict(client, reseed):
    # add a second departure exactly on top of CA9021
    ca9021 = next(f for f in client.get("/api/flights").json()
                  if f["callsign"] == "CA9021")
    payload = {
        "callsign": "TEST99",
        "operation": "DEP",
        "runway": "09L",
        "wake": "M",
        "scheduled": ca9021["scheduled"],
        "route": ["GATE1", "A", "R09L"],
        "eta_to_runway": 300,
        "vacate_to_gate": 240,
    }
    r = client.post("/api/flights", json=payload)
    assert r.status_code == 201
    data = client.get("/api/rehearse").json()
    pairs = [c for c in data["conflicts"]
             if "TEST99" in c["flights"] and c["type"] == "SEPARATION"]
    assert pairs


def test_update_and_delete_flight(client, reseed):
    f = client.get("/api/flights").json()[0]
    r = client.put(f"/api/flights/{f['id']}", json={"callsign": "RENAM1"})
    assert r.status_code == 200 and r.json()["callsign"] == "RENAM1"
    assert client.delete(f"/api/flights/{f['id']}").status_code == 204
    assert client.delete(f"/api/flights/{f['id']}").status_code == 404


def test_closure_crud(client, reseed):
    start = datetime.now().replace(microsecond=0) + timedelta(hours=3)
    payload = {
        "runway": "09R",
        "start": start.isoformat(),
        "end": (start + timedelta(hours=1)).isoformat(),
        "reason": "除冰作业",
    }
    r = client.post("/api/closures", json=payload)
    assert r.status_code == 201
    cid = r.json()["id"]
    bad = dict(payload, start=payload["end"], end=payload["start"])
    assert client.post("/api/closures", json=bad).status_code == 422
    assert client.delete(f"/api/closures/{cid}").status_code == 204


def test_adjust_delay_clears_separation(client, reseed):
    before = client.get("/api/rehearse").json()
    sep = next(c for c in before["conflicts"] if c["type"] == "SEPARATION")
    sug = next(s for s in sep["suggestions"] if s["action"] == "DELAY"
               and s["delay_seconds"] is not None)
    r = client.post("/api/rehearse/adjust", json={
        "flight_id": sug["flight_id"],
        "action": "DELAY",
        "delay_seconds": sug["delay_seconds"],
    })
    assert r.status_code == 200
    after = r.json()
    # the specific pair must no longer conflict
    still = [c for c in after["conflicts"] if c["id"] == sep["id"]]
    assert not still


def test_change_runway_validation(client, reseed):
    flights = client.get("/api/flights").json()
    fid = flights[0]["id"]
    r = client.post("/api/rehearse/adjust", json={
        "flight_id": fid,
        "action": "CHANGE_RUNWAY",
        "to_runway": "99X",
    })
    assert r.status_code == 422


def test_auto_resolve_clears_schedule(client, reseed):
    r = client.post("/api/rehearse/auto-resolve")
    assert r.status_code == 200
    data = r.json()
    assert data["resolved_count"] >= 1
    assert data["remaining"] == []
    # persistent: rehearse again and the schedule is clean
    again = client.get("/api/rehearse").json()
    assert again["conflicts"] == []


def test_reset_demo(client, reseed):
    # mess up the schedule
    flights = client.get("/api/flights").json()
    client.delete(f"/api/flights/{flights[0]['id']}")
    r = client.post("/api/rehearse/reset-demo")
    assert r.status_code == 200
    assert r.json()["conflict_count"] >= 3
    assert len(client.get("/api/flights").json()) == 7
