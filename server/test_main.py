# NOTE: TestClient is required for FastAPI endpoint testing. If linter fails, ensure fastapi is installed in your environment.
from fastapi.testclient import TestClient
from server.main import app
from unittest.mock import patch, MagicMock
from copy import deepcopy
import json
import os
import pytest

client = TestClient(app)

TELEMETRY_EVENT = {
    "event_type": "file_open",
    "timestamp": "2025-06-01T12:00:00Z",
    "user_id": "user-123",
    "session_id": "sess-456",
    "data": {"filename": "main.py", "language": "python"}
}

def test_ingest_telemetry_success() -> None:
    with patch("server.main.conn.execute") as mock_execute:
        mock_execute.return_value = None
        response = client.post("/telemetry/ingest", json=TELEMETRY_EVENT)
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert "Event ingested" in response.json()["message"]

def test_ingest_telemetry_db_error() -> None:
    with patch("server.main.conn.execute", side_effect=Exception("DB error")):
        response = client.post("/telemetry/ingest", json=TELEMETRY_EVENT)
        assert response.status_code == 500
        assert "Failed to store event" in response.json()["detail"]

def test_ingest_telemetry_missing_event_type() -> None:
    bad_event = deepcopy(TELEMETRY_EVENT)
    del bad_event["event_type"]
    response = client.post("/telemetry/ingest", json=bad_event)
    assert response.status_code == 422
    assert "event_type" in response.text

def test_ingest_telemetry_invalid_timestamp_type() -> None:
    bad_event = deepcopy(TELEMETRY_EVENT)
    bad_event["timestamp"] = 1234567890
    response = client.post("/telemetry/ingest", json=bad_event)
    assert response.status_code == 422
    assert "timestamp" in response.text

def test_ingest_telemetry_missing_data() -> None:
    bad_event = deepcopy(TELEMETRY_EVENT)
    del bad_event["data"]
    response = client.post("/telemetry/ingest", json=bad_event)
    assert response.status_code == 422
    assert "data" in response.text

def test_ingest_telemetry_empty_data() -> None:
    with patch("server.main.conn.execute") as mock_execute:
        bad_event = deepcopy(TELEMETRY_EVENT)
        bad_event["data"] = {}
        mock_execute.return_value = None
        response = client.post("/telemetry/ingest", json=bad_event)
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

def make_mock_query_result(rows, col_names) -> None:
    class MockQueryResult:
        def __init__(self, rows, col_names) -> None:
            self._rows = rows
            self._col_names = col_names
            self._idx = 0
        def has_next(self) -> None:
            return self._idx < len(self._rows)
        def get_next(self) -> None:
            row = self._rows[self._idx]
            self._idx += 1
            return row
        def get_column_names(self) -> None:
            return self._col_names
    return MockQueryResult(rows, col_names)

MOCK_EVENT_ROW = [
    {
        "event_type": "file_open",
        "timestamp": "2025-06-01T12:00:00Z",
        "user_id": "user-123",
        "session_id": "sess-456",
        "data": "{'filename': 'main.py', 'language': 'python'}"
    }
]

MOCK_COL_NAMES = ["e"]

# /telemetry/list success

def test_list_telemetry_success() -> None:
    mock_result = make_mock_query_result([[MOCK_EVENT_ROW[0]]], MOCK_COL_NAMES)
    with patch("server.main.conn.execute", return_value=mock_result):
        response = client.get("/telemetry/list")
        assert response.status_code == 200
        events = response.json()
        assert isinstance(events, list)
        assert events[0]["event_type"] == "file_open"
        assert events[0]["data"]["filename"] == "main.py"

# /telemetry/list DB error

def test_list_telemetry_db_error() -> None:
    with patch("server.main.conn.execute", side_effect=Exception("DB error")):
        response = client.get("/telemetry/list")
        assert response.status_code == 500
        assert "Failed to list events" in response.json()["detail"]

# /telemetry/list empty result

def test_list_telemetry_empty() -> None:
    mock_result = make_mock_query_result([], MOCK_COL_NAMES)
    with patch("server.main.conn.execute", return_value=mock_result):
        response = client.get("/telemetry/list")
        assert response.status_code == 200
        assert response.json() == []

# /telemetry/query success with filter

def test_query_telemetry_success() -> None:
    mock_result = make_mock_query_result([[MOCK_EVENT_ROW[0]]], MOCK_COL_NAMES)
    with patch("server.main.conn.execute", return_value=mock_result) as mock_exec:
        response = client.get("/telemetry/query?event_type=file_open")
        assert response.status_code == 200
        events = response.json()
        assert len(events) == 1
        assert events[0]["event_type"] == "file_open"
        mock_exec.assert_called()

# /telemetry/query DB error

def test_query_telemetry_db_error() -> None:
    with patch("server.main.conn.execute", side_effect=Exception("DB error")):
        response = client.get("/telemetry/query?event_type=file_open")
        assert response.status_code == 500
        assert "Failed to query events" in response.json()["detail"]

# /telemetry/query empty result

def test_query_telemetry_empty() -> None:
    mock_result = make_mock_query_result([], MOCK_COL_NAMES)
    with patch("server.main.conn.execute", return_value=mock_result):
        response = client.get("/telemetry/query?event_type=file_open")
        assert response.status_code == 200
        assert response.json() == []

# /telemetry/query invalid filter value (should just return empty, as FastAPI validates types)
def test_query_telemetry_invalid_filter() -> None:
    mock_result = make_mock_query_result([], MOCK_COL_NAMES)
    with patch("server.main.conn.execute", return_value=mock_result):
        response = client.get("/telemetry/query?event_type=not_a_real_type")
        assert response.status_code == 200
        assert response.json() == []

# --- Top-K Endpoint Tests ---
def make_mock_query_result_topk(rows, col_names) -> None:
    class MockQueryResult:
        def __init__(self, rows, col_names) -> None:
            self._rows = rows
            self._col_names = col_names
            self._idx = 0
        def has_next(self) -> None:
            return self._idx < len(self._rows)
        def get_next(self) -> None:
            row = self._rows[self._idx]
            self._idx += 1
            return row
        def get_column_names(self) -> None:
            return self._col_names
    return MockQueryResult(rows, col_names)

def test_topk_success() -> None:
    mock_embedding = [0.1] * 384
    mock_embedding_obj = MagicMock()
    mock_embedding_obj.tolist.return_value = mock_embedding
    mock_rows = [[{"id": "n1", "snippet": "foo"}, 0.01], [{"id": "n2", "snippet": "bar"}, 0.02]]
    col_names = ["node", "distance"]
    with patch("server.main.SentenceTransformer") as MockModel, \
         patch("server.main.conn") as mock_conn:
        MockModel.return_value.encode.return_value = mock_embedding_obj
        # Mock SHOW_INDEXES (no index exists)
        mock_show_idx = make_mock_query_result_topk([], ["index name", "table name"])
        # Mock CREATE_VECTOR_INDEX (no-op)
        mock_conn.execute.side_effect = [None, None, mock_show_idx, None, make_mock_query_result_topk(mock_rows, col_names)]
        payload = {
            "query_text": "find foo",
            "k": 2,
            "table": "Node",
            "embedding_field": "embedding",
            "index_name": "node_embedding_idx"
        }
        response = client.post("/tools/topk", json=payload)
        if response.status_code != 200:
            print("test_topk_success error:", response.status_code, response.text)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["distance"] <= data[1]["distance"]

def test_topk_auto_create_index() -> None:
    mock_embedding = [0.1] * 384
    mock_embedding_obj = MagicMock()
    mock_embedding_obj.tolist.return_value = mock_embedding
    col_names = ["index name", "table name"]
    # SHOW_INDEXES returns no matching index
    mock_show_idx = make_mock_query_result_topk([], col_names)
    with patch("server.main.SentenceTransformer") as MockModel, \
         patch("server.main.conn") as mock_conn:
        MockModel.return_value.encode.return_value = mock_embedding_obj
        # SHOW_INDEXES, CREATE_VECTOR_INDEX, QUERY_VECTOR_INDEX
        mock_conn.execute.side_effect = [None, None, mock_show_idx, None, make_mock_query_result_topk([], ["node", "distance"])]
        payload = {
            "query_text": "find bar",
            "k": 1,
            "table": "Node",
            "embedding_field": "embedding",
            "index_name": "node_embedding_idx"
        }
        response = client.post("/tools/topk", json=payload)
        if response.status_code != 200:
            print("test_topk_auto_create_index error:", response.status_code, response.text)
        assert response.status_code == 200

def test_topk_error() -> None:
    with patch("server.main.SentenceTransformer") as MockModel, \
         patch("server.main.conn") as mock_conn:
        MockModel.return_value.encode.side_effect = Exception("embedding error")
        payload = {
            "query_text": "fail",
            "k": 1,
            "table": "Node",
            "embedding_field": "embedding",
            "index_name": "node_embedding_idx"
        }
        response = client.post("/tools/topk", json=payload)
        assert response.status_code == 500
        assert "Top-K query failed" in response.text

def test_topk_with_filters() -> None:
    mock_embedding = [0.1] * 384
    mock_embedding_obj = MagicMock()
    mock_embedding_obj.tolist.return_value = mock_embedding
    mock_rows = [[{"id": "n3", "snippet": "baz"}, 0.03]]
    col_names = ["node", "distance"]
    with patch("server.main.SentenceTransformer") as MockModel, \
         patch("server.main.conn") as mock_conn:
        MockModel.return_value.encode.return_value = mock_embedding_obj
        # SHOW_INDEXES (index exists)
        mock_show_idx = make_mock_query_result_topk([["node_embedding_idx", "Node"]], ["index name", "table name"])
        # Provide 5 side effects: INSTALL VECTOR, LOAD VECTOR, SHOW_INDEXES, PROJECT_GRAPH, QUERY_VECTOR_INDEX
        mock_conn.execute.side_effect = [None, None, mock_show_idx, None, make_mock_query_result_topk(mock_rows, col_names)]
        payload = {
            "query_text": "find baz",
            "k": 1,
            "table": "Node",
            "embedding_field": "embedding",
            "index_name": "node_embedding_idx",
            "filters": {"user_id": "user-1"}
        }
        response = client.post("/tools/topk", json=payload)
        if response.status_code != 200:
            print("test_topk_with_filters error:", response.status_code, response.text)
        assert response.status_code == 200
        data = response.json()
        assert data[0]["node"]["snippet"] == "baz"

def test_ingest_telemetry_readonly(monkeypatch) -> None:
    monkeypatch.setenv("KUZU_READ_ONLY", "true")
    response = client.post("/telemetry/ingest", json=TELEMETRY_EVENT)
    assert response.status_code == 403
    assert "Read-only mode enabled" in response.text

def test_topk_readonly(monkeypatch) -> None:
    monkeypatch.setenv("KUZU_READ_ONLY", "true")
    payload = {
        "query_text": "find foo",
        "k": 2,
        "table": "Node",
        "embedding_field": "embedding",
        "index_name": "node_embedding_idx"
    }
    response = client.post("/tools/topk", json=payload)
    assert response.status_code == 403
    assert "Read-only mode enabled" in response.text

def test_ingest_telemetry_not_readonly(monkeypatch) -> None:
    monkeypatch.setenv("KUZU_READ_ONLY", "false")
    with patch("server.main.conn.execute") as mock_execute:
        mock_execute.return_value = None
        response = client.post("/telemetry/ingest", json=TELEMETRY_EVENT)
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

def test_topk_not_readonly(monkeypatch) -> None:
    monkeypatch.setenv("KUZU_READ_ONLY", "false")
    mock_embedding = [0.1] * 384
    mock_embedding_obj = MagicMock()
    mock_embedding_obj.tolist.return_value = mock_embedding
    mock_rows = [[{"id": "n1", "snippet": "foo"}, 0.01], [{"id": "n2", "snippet": "bar"}, 0.02]]
    col_names = ["node", "distance"]
    with patch("server.main.SentenceTransformer") as MockModel, \
         patch("server.main.conn") as mock_conn:
        MockModel.return_value.encode.return_value = mock_embedding_obj
        mock_show_idx = make_mock_query_result_topk([], ["index name", "table name"])
        mock_conn.execute.side_effect = [None, None, mock_show_idx, None, make_mock_query_result_topk(mock_rows, col_names)]
        payload = {
            "query_text": "find foo",
            "k": 2,
            "table": "Node",
            "embedding_field": "embedding",
            "index_name": "node_embedding_idx"
        }
        response = client.post("/tools/topk", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2 