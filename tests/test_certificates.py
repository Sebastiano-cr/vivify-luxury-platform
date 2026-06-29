import pytest
from fastapi.testclient import TestClient

from backend.server import app
from backend.storage.db import get_connection

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db():
    yield
    try:
        with get_connection() as conn:
            conn.execute("DELETE FROM provenance_steps")
            conn.execute("DELETE FROM jewels")
    except Exception:
        pass


def _create_jewel(name="Anel Rubi"):
    resp = client.post("/jewels", json={
        "name": name,
        "metal": "ouro_18k",
        "gemstones": ["rubi"],
        "weight_grams": 3.5,
        "origin": "Brasil",
    })
    return resp.json()


def test_issue_certificate():
    jewel = _create_jewel()
    resp = client.post(f"/certificates/{jewel['id']}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["certificate_id"].startswith("CERT-")
    assert data["worm_key"] is not None
    assert "verification_url" in data


def test_issue_certificate_twice_fails():
    jewel = _create_jewel()
    client.post(f"/certificates/{jewel['id']}")
    resp = client.post(f"/certificates/{jewel['id']}")
    assert resp.status_code == 409
    assert "already issued" in resp.json()["detail"].lower()


def test_get_certificate():
    jewel = _create_jewel()
    client.post(f"/certificates/{jewel['id']}")
    resp = client.get(f"/certificates/{jewel['id']}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["jewel_name"] == "Anel Rubi"
    assert data["metal"] == "ouro_18k"
    assert data["chain_integrity_valid"] is True
    assert data["chain_total_entries"] >= 1


def test_get_certificate_not_issued():
    jewel = _create_jewel()
    resp = client.get(f"/certificates/{jewel['id']}")
    assert resp.status_code == 404


def test_get_certificate_not_found():
    resp = client.get("/certificates/nonexistent")
    assert resp.status_code == 404


def test_verify_public():
    jewel = _create_jewel()
    client.post(f"/certificates/{jewel['id']}")
    resp = client.get(f"/verify/{jewel['id']}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["authentic"] is True
    assert data["name"] == "Anel Rubi"
    assert "certificate" in data


def test_verify_public_not_found():
    resp = client.get("/verify/nonexistent")
    assert resp.status_code == 404
