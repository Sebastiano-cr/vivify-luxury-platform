import pytest
from fastapi.testclient import TestClient
import json
import os

from backend.server import app
from backend.storage.db import get_connection, DB_PATH

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


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["service"] == "vivify"


_created_id = None


def _create_test_jewel(name="Anel de Noivado"):
    global _created_id
    payload = {
        "name": name,
        "metal": "ouro_18k",
        "gemstones": ["diamante"],
        "weight_grams": 5.2,
        "origin": "Brasil",
    }
    resp = client.post("/jewels", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == name
    assert data["hash_chain_entry_hash"] != ""
    assert data["qr_code_url"] == f"/vivify/verify/{data['id']}"
    assert data["metal"] == "ouro_18k"
    assert data["gemstones"] == ["diamante"]
    assert data["weight_grams"] == 5.2
    _created_id = data["id"]
    return data


def test_create_jewel():
    _create_test_jewel()


def test_list_jewels():
    _create_test_jewel()
    resp = client.get("/jewels")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1


def test_list_jewels_empty():
    resp = client.get("/jewels")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_jewel():
    created = _create_test_jewel()
    resp = client.get(f"/jewels/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


def test_get_jewel_not_found():
    resp = client.get("/jewels/nonexistent-id")
    assert resp.status_code == 404


def test_update_jewel():
    created = _create_test_jewel()
    update = {"name": "Anel de Noivado Premium", "weight_grams": 6.0}
    resp = client.put(f"/jewels/{created['id']}", json=update)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Anel de Noivado Premium"
    assert resp.json()["weight_grams"] == 6.0


def test_delete_jewel():
    created = _create_test_jewel()
    jewel_id = created["id"]
    resp = client.delete(f"/jewels/{jewel_id}")
    assert resp.status_code == 204
    resp = client.get(f"/jewels/{jewel_id}")
    assert resp.json()["status"] == "baixada"


def test_filter_by_metal():
    _create_test_jewel()
    resp = client.get("/jewels?metal=ouro_18k")
    assert resp.status_code == 200
    assert all(j["metal"] == "ouro_18k" for j in resp.json())


def test_filter_by_status():
    _create_test_jewel()
    resp = client.get("/jewels?status=cadastrada")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_search_by_name():
    _create_test_jewel()
    resp = client.get("/jewels?search=Anel")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_list_pagination():
    for i in range(5):
        _create_test_jewel(f"Jewel {i}")
    resp = client.get("/jewels?skip=0&limit=2")
    assert len(resp.json()) == 2
    resp = client.get("/jewels?skip=2&limit=2")
    assert len(resp.json()) == 2


def test_chain_endpoint():
    created = _create_test_jewel()
    resp = client.get(f"/jewels/{created['id']}/chain")
    assert resp.status_code == 200
    assert resp.json()["jewel_id"] == created["id"]
    assert resp.json()["total"] >= 1


def test_create_jewel_invalid_weight():
    payload = {
        "name": "Invalid",
        "metal": "ouro_18k",
        "gemstones": [],
        "weight_grams": -1,
    }
    resp = client.post("/jewels", json=payload)
    assert resp.status_code == 422
