"""REST API: every endpoint, error codes and the optional API key."""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pyxon_parser import PyxonParser
from pyxon_parser.api import create_app

SAMPLES = Path(__file__).resolve().parent.parent / "samples"


@pytest.fixture()
def client():
    parser = PyxonParser(build_raptor=False)
    with TestClient(create_app(parser)) as c:
        for name in ["water_ar.txt", "inspection_report.txt"]:
            with open(SAMPLES / name, "rb") as fh:
                r = c.post("/api/documents", files={"file": (name, fh)})
            assert r.status_code == 201, r.text
        yield c
    parser.close()


def test_health_and_listing(client):
    h = client.get("/api/health").json()
    assert h["status"] == "ok" and h["documents"] == 2 and h["chunks"] > 0
    docs = client.get("/api/documents").json()
    assert {d["filename"] for d in docs} == {"water_ar.txt", "inspection_report.txt"}
    water = next(d for d in docs if d["filename"] == "water_ar.txt")
    one = client.get(f"/api/documents/{water['id']}").json()
    assert one["language"] == "ar" and one["sections"] and one["key_concepts"]


def test_upload_reports_analysis():
    parser = PyxonParser(build_raptor=False)
    with TestClient(create_app(parser)) as c, open(SAMPLES / "water_ar.txt", "rb") as fh:
        r = c.post("/api/documents", files={"file": ("water_ar.txt", fh)}, data={"strategy": "auto"}).json()
    assert r["language"] == "ar" and r["has_diacritics"] and r["strategy"] == "dynamic" and r["reasons"]
    parser.close()


def test_search_and_ask(client):
    res = client.post("/api/search", json={"query": "الجفاف", "k": 3}).json()["results"]
    assert res[0]["filename"] == "water_ar.txt" and "keyword" in res[0]["retrievers"]
    ans = client.post("/api/ask", json={"question": "Which forklift failed inspection?"}).json()
    assert ans["route"] == "rag" and "FL-07" in ans["answer"] and ans["contexts"][0]["filename"] == "inspection_report.txt"
    meta = client.post("/api/ask", json={"question": "How many documents are indexed?"}).json()
    assert meta["route"] == "sql" and meta["sql"]


def test_sql_is_read_only(client):
    rows = client.post("/api/sql", json={"sql": "SELECT filename FROM documents"}).json()["rows"]
    assert len(rows) == 2
    assert client.post("/api/sql", json={"sql": "DELETE FROM documents"}).status_code == 400


def test_errors(client):
    assert client.get("/api/documents/999").status_code == 404
    assert client.delete("/api/documents/999").status_code == 404
    r = client.post("/api/documents", files={"file": ("notes.xyz", b"hello")})
    assert r.status_code == 415
    r = client.post("/api/documents", files={"file": ("empty.txt", b"   ")})
    assert r.status_code == 422
    assert client.post("/api/search", json={"query": ""}).status_code == 422


def test_delete_and_api_key(client, monkeypatch):
    doc_id = client.get("/api/documents").json()[0]["id"]
    monkeypatch.setenv("PYXON_API_KEY", "secret")
    assert client.delete(f"/api/documents/{doc_id}").status_code == 401
    assert client.delete(f"/api/documents/{doc_id}", headers={"X-API-Key": "secret"}).status_code == 200
    assert len(client.get("/api/documents").json()) == 1  # reads need no key
