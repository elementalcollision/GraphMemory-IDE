from fastapi import FastAPI, HTTPException, Query, Body, Depends
from server.models import TelemetryEvent
from typing import Any, List, Optional
import kuzu
import os
import ast
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

app = FastAPI(title="MCP Server", description="Model Context Protocol server for GraphMemory-IDE")

# Initialize Kuzu DB connection on startup
KUZU_DB_PATH = os.environ.get("KUZU_DB_PATH", "./data")
db = kuzu.Database(KUZU_DB_PATH)
conn = kuzu.Connection(db)

class TopKQueryRequest(BaseModel):
    query_text: str
    k: int
    table: str
    embedding_field: str
    index_name: str
    filters: Optional[dict] = None

def enforce_read_only():
    if os.environ.get("KUZU_READ_ONLY", "false").lower() == "true":
        raise HTTPException(status_code=403, detail="Read-only mode enabled.")

@app.post("/telemetry/ingest", summary="Ingest IDE telemetry event", response_model=dict)
async def ingest_telemetry(event: TelemetryEvent, _: Any = Depends(enforce_read_only)) -> Any:
    """
    Ingest a telemetry event from an IDE plugin.
    Validates and stores the event in the Kuzu database.
    """
    try:
        query = (
            "CREATE (e:TelemetryEvent {event_type: $event_type, timestamp: $timestamp, "
            "user_id: $user_id, session_id: $session_id, data: $data})"
        )
        params = {
            "event_type": event.event_type,
            "timestamp": event.timestamp,
            "user_id": event.user_id,
            "session_id": event.session_id,
            "data": str(event.data),  # Serialize dict to string for storage
        }
        conn.execute(query, params)
        return {"status": "ok", "message": "Event ingested"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store event: {e}")

@app.get("/telemetry/list", summary="List all telemetry events", response_model=List[dict])
async def list_telemetry_events() -> Any:
    """
    List all telemetry events stored in the Kuzu database.
    """
    try:
        query = "MATCH (e:TelemetryEvent) RETURN e"
        result = conn.execute(query)
        if isinstance(result, list):
            result = result[0]
        events = []
        col_names = []
        while result.has_next():
            row = result.get_next()
            if not col_names:
                col_names = result.get_column_names()
            event = dict(zip(col_names, row))
            try:
                event["e"]["data"] = ast.literal_eval(event["e"]["data"])
            except Exception:
                pass
            events.append(event["e"])
        return events
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list events: {e}")

@app.get("/telemetry/query", summary="Query telemetry events", response_model=List[dict])
async def query_telemetry_events(
    event_type: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    session_id: Optional[str] = Query(None),
) -> Any:
    """
    Query telemetry events by event_type, user_id, or session_id.
    """
    try:
        filters = []
        params = {}
        if event_type:
            filters.append("e.event_type = $event_type")
            params["event_type"] = event_type
        if user_id:
            filters.append("e.user_id = $user_id")
            params["user_id"] = user_id
        if session_id:
            filters.append("e.session_id = $session_id")
            params["session_id"] = session_id
        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
        query = f"MATCH (e:TelemetryEvent) {where_clause} RETURN e"
        result = conn.execute(query, params)
        if isinstance(result, list):
            result = result[0]
        events = []
        col_names = []
        while result.has_next():
            row = result.get_next()
            if not col_names:
                col_names = result.get_column_names()
            event = dict(zip(col_names, row))
            try:
                event["e"]["data"] = ast.literal_eval(event["e"]["data"])
            except Exception:
                pass
            events.append(event["e"])
        return events
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query events: {e}")

@app.post("/tools/topk", summary="Top-K relevant node/snippet query", response_model=list)
async def topk_query(
    req: TopKQueryRequest = Body(...),
    _: Any = Depends(enforce_read_only)
):
    """
    Retrieve the top-K relevant nodes/snippets using Kuzu's native vector search.
    Accepts query_text, k, table, embedding_field, index_name, and optional filters.
    Auto-creates the vector index if it does not exist.
    """
    try:
        # Load embedding model
        model = SentenceTransformer("all-MiniLM-L6-v2")
        query_vector = model.encode(req.query_text).tolist()
        # Ensure VECTOR extension is loaded
        conn.execute("INSTALL VECTOR;")
        conn.execute("LOAD VECTOR;")
        # Check if vector index exists, create if missing
        idx_result = conn.execute("CALL SHOW_INDEXES() RETURN *;")
        if isinstance(idx_result, list):
            idx_result = idx_result[0]
        found = False
        while idx_result.has_next():
            row = idx_result.get_next()
            col_names = idx_result.get_column_names()
            idx_info = dict(zip(col_names, row))
            if idx_info.get("index name") == req.index_name and idx_info.get("table name") == req.table:
                found = True
                break
        if not found:
            # Create the vector index
            conn.execute(f"CALL CREATE_VECTOR_INDEX('{req.table}', '{req.index_name}', '{req.embedding_field}');")
        # Build Cypher
        params = {"query_vector": query_vector, "k": req.k}
        if req.filters:
            # Create projected graph for filtered search
            proj_name = f"filtered_{req.table.lower()}"
            filter_str = ' AND '.join([f"n.{k} = '{v}'" for k, v in req.filters.items()])
            conn.execute(f"CALL PROJECT_GRAPH('{proj_name}', '{{\"{req.table}\": {{\"filter\": \"{filter_str}\"}}}}', []);")
            cypher = f"""
            CALL QUERY_VECTOR_INDEX('{proj_name}', '{req.index_name}', $query_vector, $k)
            RETURN node, distance
            ORDER BY distance
            """
        else:
            cypher = f"""
            CALL QUERY_VECTOR_INDEX('{req.table}', '{req.index_name}', $query_vector, $k)
            RETURN node, distance
            ORDER BY distance
            """
        result = conn.execute(cypher, params)
        if isinstance(result, list):
            result = result[0]
        col_names = []
        topk = []
        while result.has_next():
            row = result.get_next()
            if not col_names:
                col_names = result.get_column_names()
            item = dict(zip(col_names, row))
            topk.append(item)
        return topk
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Top-K query failed: {e}") 