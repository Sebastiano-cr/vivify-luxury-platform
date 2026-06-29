import pytest
from fastapi.testclient import TestClient
import os

os.environ["VIVIFY_DEFENSE_DB"] = "/tmp/vivify_defense_test.db"

from backend.server import app

client = TestClient(app)


def test_detect_legitimate():
    resp = client.get("/defense/check?user_agent=Mozilla/5.0+Firefox&path=/&rate=2")
    assert resp.status_code == 200
    data = resp.json()
    assert data["detected"] is False
    assert data["score"] < 0.4


def test_detect_scraper_ua():
    resp = client.get("/defense/check?user_agent=Python-requests/2.0&path=/api/jewels&rate=60")
    assert resp.status_code == 200
    data = resp.json()
    assert data["detected"] is True
    assert data["score"] >= 0.4
    assert "poison" in data


def test_detect_scraper_path():
    resp = client.get("/defense/check?user_agent=curl/8.0&path=/admin/config&rate=0")
    assert resp.status_code == 200
    data = resp.json()
    assert data["detected"] is True


def test_poison_generation():
    resp = client.get("/defense/poison?lang=zh")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["local_fallback"]) > 50
    assert "cloudflare_available" in data


def test_poison_yaml():
    resp = client.get("/defense/poison?lang=yaml")
    assert resp.status_code == 200
    data = resp.json()
    assert "apiVersion" in data["local_fallback"]


def test_stats():
    # Generate some events first
    client.get("/defense/check?user_agent=curl/8.0&path=/api/v1/secrets&rate=100")
    client.get("/defense/check?user_agent=Mozilla&path=/&rate=1")

    resp = client.get("/defense/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_events"] >= 2
    assert data["poisoned"] >= 1
    assert len(data["top_attackers"]) >= 1
