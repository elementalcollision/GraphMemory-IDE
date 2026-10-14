# NOTE: TestClient is required for FastAPI endpoint testing. If linter fails, ensure fastapi is installed in your environment.
#
# Phase 9 rewrite: the original version of this file was written against a
# historical app architecture — it patched `server.main.conn` (an attribute
# that never existed; handlers use `app.state.ladybug_conn`), mocked five
# Kuzu vector-extension calls for a Top-K handler that is now a single Cypher
# query, and asserted pre-2025 response shapes ("status": "ok"). All 21 tests
# were rewritten against the CURRENT endpoint contracts.
from fastapi.testclient import TestClient
from server.main import app
from server.core.config import get_settings
from unittest.mock import patch, MagicMock
from copy import deepcopy
import json
import pytest
from typing import List, Any

# base_url must be an allowed host — the security middleware rejects
# TestClient's default Host header ("testserver") with 400
client = TestClient(app, base_url="http://localhost")


@pytest.fixture(autouse=True)
def _no_rate_limit(monkeypatch):
    """Bypass the security middleware rate limit for tests.

    TestClient requests present client IP 'testclient', which is not in the
    middleware whitelist (127.0.0.1/::1) — rapid test runs exhaust the
    20-request burst limit and fail with 429. Report the whitelisted IP
    instead so rate limiting is skipped entirely.
    """
    from server.middleware.security import RateLimitMiddleware
    monkeypatch.setattr(
        RateLimitMiddleware, "_get_client_ip", lambda self, request: "127.0.0.1"
    )

TELEMETRY_EVENT = {
    "event_type": "memory_operation",
    "timestamp": "2025-06-01T12:00:00Z",
    "user_id": "user-123",
    "session_id": "sess-456",
    "data": {"filename": "main.py", "language": "python"}
}


def mock_db(**kwargs):
    """Mock for app.state.ladybug_conn (the attribute handlers actually use)."""
    m = MagicMock()
    m.execute = MagicMock(**kwargs)
    return m


class MockQueryResult:
    """Mimics ladybug.QueryResult (snake_case iteration, list rows)."""

    def __init__(self, rows: List[Any]) -> None:
        self._rows = rows
        self._idx = 0

    def has_next(self) -> bool:
        return self._idx < len(self._rows)

    def get_next(self) -> Any:
        row = self._rows[self._idx]
        self._idx += 1
        return row


EVENT_ROW = ("memory_operation", "2025-06-01T12:00:00Z", "user-123", "sess-456",
            '{"filename": "main.py", "language": "python"}')


def with_db(**kwargs):
    """Patch the app's LadybugDB connection for the duration of a request."""
    return patch.object(app.state, "ladybug_conn", mock_db(**kwargs))


# --- /telemetry/ingest ---

def test_ingest_telemetry_success() -> None:
    """Test successful telemetry ingestion"""
    with with_db() as db:
        db.execute.return_value = None
        response = client.post("/telemetry/ingest", json=TELEMETRY_EVENT)
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "success"
        assert "ingested successfully" in body["message"]
        assert "event_id" in body


def test_ingest_telemetry_db_error() -> None:
    """Test telemetry ingestion with database error"""
    with with_db() as db:
        db.execute.side_effect = Exception("Database error")
        response = client.post("/telemetry/ingest", json=TELEMETRY_EVENT)
        assert response.status_code == 500
        assert "Failed to ingest telemetry event" in response.json()["detail"]


def test_ingest_telemetry_missing_event_type() -> None:
    """Test telemetry ingestion with missing event type (422 validation)"""
    bad_event = deepcopy(TELEMETRY_EVENT)
    del bad_event["event_type"]
    response = client.post("/telemetry/ingest", json=bad_event)
    assert response.status_code == 422
    assert "event_type" in response.text


def test_ingest_telemetry_invalid_timestamp_type() -> None:
    """Test telemetry ingestion with invalid timestamp (422 validation)"""
    bad_event = deepcopy(TELEMETRY_EVENT)
    bad_event["timestamp"] = "invalid-timestamp-format"
    response = client.post("/telemetry/ingest", json=bad_event)
    assert response.status_code == 422


def test_ingest_telemetry_missing_data() -> None:
    """data has a default_factory in the current model — missing data is
    accepted (stored as {}), unlike the pre-2025 model this file assumed."""
    with with_db() as db:
        db.execute.return_value = None
        bad_event = deepcopy(TELEMETRY_EVENT)
        del bad_event["data"]
        response = client.post("/telemetry/ingest", json=bad_event)
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        # the stored params must include the empty-dict default
        stored = db.execute.call_args[0][1]
        assert json.loads(stored["data"]) == {}


def test_ingest_telemetry_empty_data() -> None:
    """Test telemetry ingestion with empty data dict"""
    with with_db() as db:
        db.execute.return_value = None
        bad_event = deepcopy(TELEMETRY_EVENT)
        bad_event["data"] = {}
        response = client.post("/telemetry/ingest", json=bad_event)
        assert response.status_code == 200
        assert response.json()["status"] == "success"


# --- /telemetry/list ---

def test_list_telemetry_success() -> None:
    """Test successful telemetry listing"""
    with with_db() as db:
        db.execute.return_value = MockQueryResult([list(EVENT_ROW)])
        response = client.get("/telemetry/list")
        assert response.status_code == 200
        events = response.json()
        assert isinstance(events, list)
        assert events[0]["event_type"] == "memory_operation"
        assert events[0]["data"]["filename"] == "main.py"


def test_list_telemetry_db_error() -> None:
    with with_db() as db:
        db.execute.side_effect = Exception("DB error")
        response = client.get("/telemetry/list")
        assert response.status_code == 500
        assert "Failed to retrieve telemetry events" in response.json()["detail"]


def test_list_telemetry_empty() -> None:
    with with_db() as db:
        db.execute.return_value = MockQueryResult([])
        response = client.get("/telemetry/list")
        assert response.status_code == 200
        assert response.json() == []


# --- /telemetry/query ---

def test_query_telemetry_success() -> None:
    with with_db() as db:
        db.execute.return_value = MockQueryResult([list(EVENT_ROW)])
        response = client.get("/telemetry/query?event_type=file_open")
        assert response.status_code == 200
        events = response.json()
        assert len(events) == 1
        assert events[0]["event_type"] == "memory_operation"
        db.execute.assert_called()


def test_query_telemetry_db_error() -> None:
    with with_db() as db:
        db.execute.side_effect = Exception("DB error")
        response = client.get("/telemetry/query?event_type=file_open")
        assert response.status_code == 500
        assert "Failed to query telemetry events" in response.json()["detail"]


def test_query_telemetry_empty() -> None:
    with with_db() as db:
        db.execute.return_value = MockQueryResult([])
        response = client.get("/telemetry/query?event_type=file_open")
        assert response.status_code == 200
        assert response.json() == []


def test_query_telemetry_invalid_filter() -> None:
    """Unknown event_type value simply matches no rows."""
    with with_db() as db:
        db.execute.return_value = MockQueryResult([])
        response = client.get("/telemetry/query?event_type=not_a_real_type")
        assert response.status_code == 200
        assert response.json() == []


# --- /tools/topk ---

def make_mock_embedding() -> MagicMock:
    mock_embedding_obj = MagicMock()
    mock_embedding_obj.tolist.return_value = [0.1] * 384
    return mock_embedding_obj


TOPK_PAYLOAD = {
    "query_text": "find foo",
    "k": 2,
    "table": "Node",
    "embedding_field": "embedding",
    "index_name": "node_embedding_idx",
}


def test_topk_success() -> None:
    mock_rows = [
        [{"id": "n1", "snippet": "foo"}, 0.95],
        [{"id": "n2", "snippet": "bar"}, 0.80],
    ]
    with patch("server.main.SentenceTransformer") as MockModel, with_db() as db:
        MockModel.return_value.encode.return_value = make_mock_embedding()
        db.execute.return_value = MockQueryResult(mock_rows)
        response = client.post("/tools/topk", json=TOPK_PAYLOAD)
        assert response.status_code == 200, response.text
        data = response.json()
        assert len(data) == 2
        # current contract: node / similarity / query keys, sorted by the handler
        assert data[0]["node"]["snippet"] == "foo"
        assert data[0]["similarity"] >= data[1]["similarity"]
        assert data[0]["query"] == "find foo"


def test_topk_empty_result() -> None:
    """k=1 with no matching rows returns an empty list (replaces the obsolete
    auto-create-index test: the current handler has no vector-index logic)."""
    with patch("server.main.SentenceTransformer") as MockModel, with_db() as db:
        MockModel.return_value.encode.return_value = make_mock_embedding()
        db.execute.return_value = MockQueryResult([])
        payload = dict(TOPK_PAYLOAD, k=1, query_text="nothing matches")
        response = client.post("/tools/topk", json=payload)
        assert response.status_code == 200, response.text
        assert response.json() == []


def test_topk_error() -> None:
    with patch("server.main.SentenceTransformer") as MockModel, with_db() as db:
        MockModel.return_value.encode.side_effect = Exception("embedding error")
        response = client.post("/tools/topk", json=TOPK_PAYLOAD)
        assert response.status_code == 500
        assert "Top-K query failed" in response.text


def test_topk_with_filters() -> None:
    """The current handler ignores extra fields like filters (pydantic
    ignores them); the query still returns the matching node."""
    mock_rows = [[{"id": "n3", "snippet": "baz"}, 0.42]]
    with patch("server.main.SentenceTransformer") as MockModel, with_db() as db:
        MockModel.return_value.encode.return_value = make_mock_embedding()
        db.execute.return_value = MockQueryResult(mock_rows)
        payload = dict(TOPK_PAYLOAD, k=1, query_text="find baz",
                       filters={"user_id": "user-1"})
        response = client.post("/tools/topk", json=payload)
        assert response.status_code == 200, response.text
        data = response.json()
        assert data[0]["node"]["snippet"] == "baz"


# --- read-only mode ---
# NOTE: settings are a cached pydantic singleton and read env vars with the
# DB_ prefix, so the historical env-var monkeypatch never worked. Patch the
# settings object attribute directly instead.

@pytest.fixture
def read_only_mode(monkeypatch):
    monkeypatch.setattr(get_settings().database, "LADYBUG_READ_ONLY", True)
    yield
    monkeypatch.undo()


def test_ingest_telemetry_readonly(read_only_mode) -> None:
    response = client.post("/telemetry/ingest", json=TELEMETRY_EVENT)
    assert response.status_code == 403
    assert "Read-only mode enabled" in response.text


def test_topk_readonly(read_only_mode) -> None:
    response = client.post("/tools/topk", json=TOPK_PAYLOAD)
    assert response.status_code == 403
    assert "Read-only mode enabled" in response.text


def test_ingest_telemetry_not_readonly(monkeypatch) -> None:
    monkeypatch.setattr(get_settings().database, "LADYBUG_READ_ONLY", False)
    with with_db() as db:
        db.execute.return_value = None
        response = client.post("/telemetry/ingest", json=TELEMETRY_EVENT)
        assert response.status_code == 200
        assert response.json()["status"] == "success"


def test_topk_not_readonly(monkeypatch) -> None:
    monkeypatch.setattr(get_settings().database, "LADYBUG_READ_ONLY", False)
    mock_rows = [[{"id": "n1", "snippet": "foo"}, 0.9]]
    with patch("server.main.SentenceTransformer") as MockModel, with_db() as db:
        MockModel.return_value.encode.return_value = make_mock_embedding()
        db.execute.return_value = MockQueryResult(mock_rows)
        response = client.post("/tools/topk", json=TOPK_PAYLOAD)
        assert response.status_code == 200
        assert len(response.json()) == 1
