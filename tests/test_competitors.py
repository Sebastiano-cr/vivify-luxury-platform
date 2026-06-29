import pytest
import os

os.environ["VIVIFY_DEFENSE_DB"] = "/tmp/vivify_competitors_test.db"

from fastapi.testclient import TestClient
from backend.server import app

client = TestClient(app)


def _clean():
    from backend.storage.db import get_connection
    with get_connection() as conn:
        conn.execute("DELETE FROM monitored_competitors")


@pytest.fixture(autouse=True)
def cleanup():
    _clean()
    yield
    _clean()


def test_list_empty():
    resp = client.get("/competitors/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["competitors"] == []


def test_add_competitor():
    resp = client.post("/competitors/?url=https://joalheriax.com.br&label=Joalheria%20X")
    assert resp.status_code == 200
    data = resp.json()
    assert data["url"] == "https://joalheriax.com.br"
    assert data["label"] == "Joalheria X"
    assert data["active"] == 1


def test_add_duplicate_returns_409():
    client.post("/competitors/?url=https://joalheriax.com.br&label=X")
    resp = client.post("/competitors/?url=https://joalheriax.com.br&label=X")
    assert resp.status_code == 409


def test_list_after_add():
    client.post("/competitors/?url=https://joalheriax.com.br&label=X")
    client.post("/competitors/?url=https://joalheriay.com.br&label=Y")
    resp = client.get("/competitors/")
    assert resp.json()["total"] == 2


def test_toggle_competitor():
    resp = client.post("/competitors/?url=https://joalheriax.com.br&label=X")
    cid = resp.json()["id"]

    resp = client.post(f"/competitors/{cid}/toggle")
    assert resp.json()["active"] is False

    resp = client.post(f"/competitors/{cid}/toggle")
    assert resp.json()["active"] is True


def test_toggle_not_found():
    resp = client.post("/competitors/nao-existe/toggle")
    assert resp.status_code == 404


def test_remove_competitor():
    resp = client.post("/competitors/?url=https://joalheriax.com.br&label=X")
    cid = resp.json()["id"]

    resp = client.delete(f"/competitors/{cid}")
    assert resp.json()["deleted"] is True

    resp = client.get("/competitors/")
    assert resp.json()["total"] == 0


def test_remove_not_found():
    resp = client.delete("/competitors/nao-existe")
    assert resp.status_code == 404


def test_scan_not_found():
    resp = client.post("/competitors/nao-existe/scan")
    assert resp.status_code == 404
