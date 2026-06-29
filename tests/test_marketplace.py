import pytest
import json
import os

os.environ["VIVIFY_DEFENSE_DB"] = "/tmp/vivify_mp_test.db"

from fastapi.testclient import TestClient
from backend.server import app

client = TestClient(app)


def _seed():
    for i in range(3):
        client.post("/jewels/", json={
            "name": f"Anel Ouro {i}",
            "metal": "ouro_18k",
            "gemstones": ["diamante"],
            "weight_grams": 5.0 + i,
            "origin": "Teste",
            "status": "disponivel",
            "price": 1500.0 + i * 500,
        })
    client.post("/jewels/", json={
        "name": "Anel Vendido",
        "metal": "prata_925",
        "gemstones": [],
        "weight_grams": 3.0,
        "origin": "Teste",
        "status": "vendida",
        "price": 500.0,
    })


def _clean():
    from backend.storage.db import get_connection
    with get_connection() as conn:
        conn.execute("DELETE FROM jewels")
        conn.execute("DELETE FROM provenance_steps")


@pytest.fixture(autouse=True)
def cleanup():
    _clean()
    _seed()
    yield
    _clean()


def test_list_empty_search():
    resp = client.get("/marketplace/?search=naoexiste")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []


def test_list_all_available():
    resp = client.get("/marketplace/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3


def test_list_filter_by_metal():
    resp = client.get("/marketplace/?metal=prata_925")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0

    resp = client.get("/marketplace/?metal=ouro_18k")
    assert resp.json()["total"] == 3


def test_list_filter_by_gemstone():
    resp = client.get("/marketplace/?gemstone=diamante")
    assert resp.status_code == 200
    assert resp.json()["total"] == 3


def test_list_pagination():
    resp = client.get("/marketplace/?limit=2")
    data = resp.json()
    assert len(data["items"]) == 2
    assert data["total"] == 3


def test_get_product():
    resp = client.get("/marketplace/")
    first = resp.json()["items"][0]
    pid = first["id"]

    resp = client.get(f"/marketplace/{pid}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == first["name"]
    assert data["price"] == first["price"]
    assert "provenance" in data


def test_get_product_not_found():
    resp = client.get("/marketplace/nao-existe")
    assert resp.status_code == 404


def test_sold_jewels_not_in_listing():
    resp = client.get("/marketplace/")
    names = [item["name"] for item in resp.json()["items"]]
    assert "Anel Vendido" not in names
