import pytest
from fastapi.testclient import TestClient
import os

os.environ["WEAK_SIGNAL_DB"] = "/tmp/vivify_trends_test.db"

from backend.server import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db():
    yield
    import sqlite3
    try:
        conn = sqlite3.connect("/tmp/vivify_trends_test.db")
        conn.execute("DELETE FROM signal_records")
        conn.execute("DELETE FROM monitored_targets")
        conn.commit()
        conn.close()
    except Exception:
        pass


def test_seed_targets():
    resp = client.post("/trends/seed")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["seeded"] >= 4


def test_list_targets():
    client.post("/trends/seed")
    resp = client.get("/trends/targets")
    assert resp.status_code == 200
    assert resp.json()["total"] >= 4


def test_submit_signal():
    client.post("/trends/seed")
    resp = client.post(
        "/trends/signals",
        params={
            "handle": "vivify_design_trends",
            "platform": "reddit",
            "text": "Rose gold engagement rings are trending this season",
            "topics": "rose gold,engagement ring,trends",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["handle"] == "vivify_design_trends"
    assert "topics" in data


def test_list_signals():
    client.post("/trends/seed")
    client.post("/trends/signals", params={"handle": "vivify_design_trends", "platform": "reddit", "text": "Test signal", "topics": "test"})
    resp = client.get("/trends/signals")
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


def test_summary():
    client.post("/trends/seed")
    client.post("/trends/signals", params={
        "handle": "vivify_design_trends",
        "platform": "reddit",
        "text": "Rose gold jewelry is very popular right now",
        "topics": "rose gold,jewelry",
    })
    resp = client.get("/trends/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "metal_mentions" in data
    assert "gemstone_mentions" in data
    assert "total_targets" in data
    print(f"Summary: metals={data['metal_mentions']}")


def test_anomalies():
    client.post("/trends/seed")
    resp = client.get("/trends/anomalies")
    assert resp.status_code == 200
    data = resp.json()
    assert "anomalies" in data


def test_alerts():
    resp = client.get("/trends/alerts")
    assert resp.status_code == 200
    assert "alerts" in resp.json()
