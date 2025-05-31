"""
Main FastAPI application for GraphMemory-IDE with production-ready configuration.
Integrates security middleware, monitoring, and comprehensive configuration management.
"""

import os
import ast
import time
import logging
from typing import Any, List, Optional
from datetime import timedelta

import kuzu
from fastapi import FastAPI, HTTPException, Query, Body, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

# Import configuration and middleware
from core.config import get_settings, Settings
from middleware.security import setup_security_middleware
from monitoring.metrics import (
    setup_metrics_endpoint,
    setup_health_endpoint,
    setup_monitoring_middleware,
    get_metrics_collector
)

# Import models and auth
from models import TelemetryEvent, Token, User
from auth import (
    authenticate_user, 
    create_access_token, 
    ACCESS_TOKEN_EXPIRE_MINUTES, 
    get_optional_current_user
)

# Import routers
from analytics_routes import router as analytics_router, initialize_analytics_engine, shutdown_analytics_engine

# Import streaming analytics
try:
    from streaming import (
        initialize_streaming_analytics, 
        shutdown_streaming_analytics,
        create_analytics_router,
        produce_memory_operation_event,
        produce_user_interaction_event,
        produce_system_metric_event,
        OperationType
    )
    STREAMING_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Streaming analytics not available: {e}")
    STREAMING_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_application() -> FastAPI:
    """Create and configure FastAPI application"""
    settings = get_settings()
    
    # Create FastAPI app with environment-specific settings
    app = FastAPI(
        title=settings.APP_NAME,
        description="Model Context Protocol server for GraphMemory-IDE with enterprise features",
        version=settings.APP_VERSION,
        debug=settings.server.DEBUG,
        docs_url="/docs" if not settings.is_production() else None,
        redoc_url="/redoc" if not settings.is_production() else None,
    )

    # Setup security middleware stack
    setup_security_middleware(
        app=app,
        environment=settings.ENVIRONMENT.value,
        cors_origins=settings.get_cors_origins(),
        allowed_hosts=settings.get_allowed_hosts(),
        rate_limit_per_minute=settings.security.RATE_LIMIT_PER_MINUTE,
        enable_request_logging=settings.is_development()
    )
    
    # Setup monitoring middleware and endpoints
    setup_monitoring_middleware(app)
    setup_metrics_endpoint(app, settings.monitoring.METRICS_ENDPOINT)
    setup_health_endpoint(app, settings.monitoring.HEALTH_ENDPOINT)
    
    # Setup database connection
    setup_database(app, settings)
    
    # Setup routers
    setup_routers(app, settings)
    
    # Setup lifecycle events
    setup_lifecycle_events(app, settings)
    
    logger.info(f"FastAPI application created for {settings.ENVIRONMENT.value} environment")
    return app


def setup_database(app: FastAPI, settings: Settings) -> None:
    """Initialize database connections"""
    # Initialize Kuzu DB connection
    kuzu_db_path = settings.database.KUZU_DB_PATH
    
    try:
        app.state.kuzu_db = kuzu.Database(kuzu_db_path)
        app.state.kuzu_conn = kuzu.Connection(app.state.kuzu_db)
        logger.info(f"Kuzu database initialized at: {kuzu_db_path}")
    except Exception as e:
        logger.error(f"Failed to initialize Kuzu database: {e}")
        raise


def setup_routers(app: FastAPI, settings: Settings) -> None:
    """Setup and include all routers"""
    
    # Include analytics router
    app.include_router(analytics_router, prefix="/api/v1", tags=["analytics"])
    
    # Include streaming analytics router if available
    if STREAMING_AVAILABLE and settings.ENABLE_STREAMING_ANALYTICS:
        try:
            streaming_router = create_analytics_router()
            app.mount("/streaming", streaming_router)
            logger.info("Streaming analytics router mounted")
        except Exception as e:
            logger.warning(f"Failed to mount streaming router: {e}")
    
    # Include dashboard router if available and enabled
    if settings.ENABLE_DASHBOARD:
        try:
            from dashboard.routes import dashboard_router
            app.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])
            logger.info("Dashboard router included")
        except ImportError:
            logger.warning("Dashboard dependencies not available. Install with: pip install sse-starlette streamlit streamlit-echarts")


def setup_lifecycle_events(app: FastAPI, settings: Settings) -> None:
    """Setup application lifecycle events"""
    
    @app.on_event("startup")
    async def startup_event():
        """Initialize services on startup"""
        logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
        logger.info(f"Environment: {settings.ENVIRONMENT.value}")
        
        try:
            # Initialize analytics engine
            await initialize_analytics_engine(
                conn=app.state.kuzu_conn, 
                redis_url=settings.database.REDIS_URL
            )
            logger.info("Analytics engine initialized")
            
            # Initialize streaming analytics pipeline
            if STREAMING_AVAILABLE and settings.ENABLE_STREAMING_ANALYTICS:
                try:
                    await initialize_streaming_analytics()
                    logger.info("🚀 Streaming Analytics Pipeline initialized")
                    
                    # Send startup metrics
                    await produce_system_metric_event(
                        metric_name="server_startup",
                        metric_value=1.0,
                        metric_unit="event",
                        additional_data={
                            "component": "mcp_server",
                            "environment": settings.ENVIRONMENT.value,
                            "version": settings.APP_VERSION
                        }
                    )
                    
                except Exception as e:
                    logger.error(f"Streaming analytics initialization failed: {e}")
            
            # Record startup in metrics
            metrics_collector = get_metrics_collector()
            metrics_collector.record_graph_operation("server_startup")
            
            logger.info("🚀 Application startup complete")
            
        except Exception as e:
            logger.error(f"Startup failed: {e}")
            raise

    @app.on_event("shutdown")
    async def shutdown_event():
        """Cleanup services on shutdown"""
        logger.info("Shutting down services...")
        
        try:
            # Send shutdown metrics before stopping
            if STREAMING_AVAILABLE and settings.ENABLE_STREAMING_ANALYTICS:
                try:
                    await produce_system_metric_event(
                        metric_name="server_shutdown",
                        metric_value=1.0,
                        metric_unit="event",
                        additional_data={"component": "mcp_server"}
                    )
                    
                    await shutdown_streaming_analytics()
                    logger.info("Streaming Analytics Pipeline shutdown complete")
                except Exception as e:
                    logger.warning(f"Streaming analytics shutdown failed: {e}")
            
            await shutdown_analytics_engine()
            logger.info("Analytics engine shutdown complete")
            
            # Record shutdown in metrics
            metrics_collector = get_metrics_collector()
            metrics_collector.record_graph_operation("server_shutdown")
            
        except Exception as e:
            logger.warning(f"Services shutdown failed: {e}")


# Initialize the FastAPI application
app = create_application()


# Request/Response Models
class TopKQueryRequest(BaseModel):
    query_text: str
    k: int
    table: str
    embedding_field: str
    index_name: str
    filters: Optional[dict] = None


def enforce_read_only():
    """Enforce read-only mode if enabled"""
    settings = get_settings()
    if settings.database.KUZU_READ_ONLY:
        raise HTTPException(status_code=403, detail="Read-only mode enabled.")


# Authentication Endpoints
@app.post("/auth/token", response_model=Token, summary="Generate JWT access token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()) -> Token:
    """
    Generate a JWT access token for authentication.
    
    Use this endpoint to obtain a token for accessing protected endpoints.
    The token should be included in the Authorization header as 'Bearer <token>'.
    
    Default test credentials:
    - Username: testuser, Password: testpassword
    - Username: admin, Password: adminpassword
    """
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        # Record authentication failure
        metrics_collector = get_metrics_collector()
        metrics_collector.record_error("authentication_failed", "auth_endpoint")
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    # Record successful authentication
    metrics_collector = get_metrics_collector()
    metrics_collector.record_graph_operation("user_authentication")
    
    return Token(access_token=access_token, token_type="bearer")


@app.post("/telemetry/ingest", summary="Ingest IDE telemetry event", response_model=dict)
async def ingest_telemetry(
    event: TelemetryEvent, 
    current_user: Optional[User] = Depends(get_optional_current_user),
    _: Any = Depends(enforce_read_only)
) -> Any:
    """
    Ingest a telemetry event from an IDE plugin.
    Validates and stores the event in the Kuzu database.
    
    Authentication: Optional (respects JWT_ENABLED setting)
    - If JWT_ENABLED=false: No authentication required
    - If JWT_ENABLED=true: Optional Bearer token authentication
    """
    start_time = time.time()
    
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
        app.state.kuzu_conn.execute(query, params)
        
        processing_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        # Record metrics
        metrics_collector = get_metrics_collector()
        metrics_collector.record_database_query("CREATE", "TelemetryEvent", processing_time / 1000)
        
        # Stream telemetry event to analytics pipeline
        settings = get_settings()
        if STREAMING_AVAILABLE and settings.ENABLE_STREAMING_ANALYTICS:
            try:
                # Map telemetry event to user interaction
                await produce_user_interaction_event(
                    interaction_type=event.event_type,
                    target_resource="telemetry_endpoint",
                    user_id=event.user_id,
                    session_id=event.session_id,
                    duration_ms=processing_time,
                    additional_data={
                        "event_data": event.data,
                        "timestamp": event.timestamp
                    }
                )
                
                # Track processing performance
                await produce_system_metric_event(
                    metric_name="telemetry_processing_time",
                    metric_value=processing_time,
                    metric_unit="milliseconds",
                    additional_data={"event_type": event.event_type}
                )
                
            except Exception as streaming_error:
                logger.warning(f"Failed to stream telemetry event: {streaming_error}")
                metrics_collector.record_error("streaming_failed", "telemetry_endpoint")
        
        return {
            "status": "success",
            "message": "Telemetry event ingested successfully",
            "processing_time_ms": processing_time,
            "event_id": f"{event.user_id}_{event.session_id}_{event.timestamp}"
        }
        
    except Exception as e:
        logger.error(f"Failed to ingest telemetry event: {e}")
        metrics_collector = get_metrics_collector()
        metrics_collector.record_error("database_error", "telemetry_endpoint")
        
        raise HTTPException(
            status_code=500,
            detail=f"Failed to ingest telemetry event: {str(e)}"
        )


@app.get("/telemetry/list", summary="List all telemetry events", response_model=List[dict])
async def list_telemetry_events(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: Optional[User] = Depends(get_optional_current_user)
) -> Any:
    """
    List all telemetry events with pagination.
    
    Authentication: Optional (respects JWT_ENABLED setting)
    """
    start_time = time.time()
    
    try:
        query = (
            "MATCH (e:TelemetryEvent) "
            "RETURN e.event_type, e.timestamp, e.user_id, e.session_id, e.data "
            f"SKIP {offset} LIMIT {limit}"
        )
        result = app.state.kuzu_conn.execute(query)
        
        events = []
        while result.hasNext():
            row = result.getNext()
            events.append({
                "event_type": row[0],
                "timestamp": row[1],
                "user_id": row[2],
                "session_id": row[3],
                "data": ast.literal_eval(row[4]) if row[4] else {}
            })
        
        # Record metrics
        processing_time = (time.time() - start_time) * 1000
        metrics_collector = get_metrics_collector()
        metrics_collector.record_database_query("MATCH", "TelemetryEvent", processing_time / 1000)
        
        return events
        
    except Exception as e:
        logger.error(f"Failed to list telemetry events: {e}")
        metrics_collector = get_metrics_collector()
        metrics_collector.record_error("database_error", "telemetry_list")
        
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve telemetry events: {str(e)}"
        )


@app.get("/telemetry/query", summary="Query telemetry events", response_model=List[dict])
async def query_telemetry_events(
    event_type: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    session_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    current_user: Optional[User] = Depends(get_optional_current_user)
) -> Any:
    """
    Query telemetry events with filters.
    
    Authentication: Optional (respects JWT_ENABLED setting)
    """
    start_time = time.time()
    
    try:
        # Build dynamic query based on filters
        where_conditions = []
        params = {}
        
        if event_type:
            where_conditions.append("e.event_type = $event_type")
            params["event_type"] = event_type
        
        if user_id:
            where_conditions.append("e.user_id = $user_id")
            params["user_id"] = user_id
        
        if session_id:
            where_conditions.append("e.session_id = $session_id")
            params["session_id"] = session_id
        
        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
        
        query = (
            f"MATCH (e:TelemetryEvent) WHERE {where_clause} "
            "RETURN e.event_type, e.timestamp, e.user_id, e.session_id, e.data "
            f"LIMIT {limit}"
        )
        
        result = app.state.kuzu_conn.execute(query, params)
        
        events = []
        while result.hasNext():
            row = result.getNext()
            events.append({
                "event_type": row[0],
                "timestamp": row[1],
                "user_id": row[2],
                "session_id": row[3],
                "data": ast.literal_eval(row[4]) if row[4] else {}
            })
        
        # Record metrics
        processing_time = (time.time() - start_time) * 1000
        metrics_collector = get_metrics_collector()
        metrics_collector.record_database_query("MATCH", "TelemetryEvent", processing_time / 1000)
        
        return events
        
    except Exception as e:
        logger.error(f"Failed to query telemetry events: {e}")
        metrics_collector = get_metrics_collector()
        metrics_collector.record_error("database_error", "telemetry_query")
        
        raise HTTPException(
            status_code=500,
            detail=f"Failed to query telemetry events: {str(e)}"
        )


@app.post("/tools/topk", summary="Top-K relevant node/snippet query", response_model=list)
async def topk_query(
    req: TopKQueryRequest = Body(...),
    current_user: Optional[User] = Depends(get_optional_current_user),
    _: Any = Depends(enforce_read_only)
):
    """
    Top-K query for finding relevant nodes/snippets using vector similarity.
    
    Authentication: Optional (respects JWT_ENABLED setting)
    """
    start_time = time.time()
    
    try:
        # Initialize sentence transformer for embeddings
        model = SentenceTransformer('all-MiniLM-L6-v2')
        query_embedding = model.encode([req.query_text])[0].tolist()
        
        # Build Kuzu query for vector similarity search
        query = f"""
        MATCH (n:{req.table})
        WHERE n.{req.embedding_field} IS NOT NULL
        RETURN n, 
               list_cosine_similarity(n.{req.embedding_field}, $query_embedding) AS similarity
        ORDER BY similarity DESC
        LIMIT $k
        """
        
        params = {
            "query_embedding": query_embedding,
            "k": req.k
        }
        
        result = app.state.kuzu_conn.execute(query, params)
        
        results = []
        while result.hasNext():
            row = result.getNext()
            node_data = row[0]
            similarity = row[1]
            
            results.append({
                "node": node_data,
                "similarity": similarity,
                "query": req.query_text
            })
        
        # Record metrics
        processing_time = (time.time() - start_time) * 1000
        metrics_collector = get_metrics_collector()
        metrics_collector.record_database_query("VECTOR_SEARCH", req.table, processing_time / 1000)
        
        return results
        
    except Exception as e:
        logger.error(f"Top-K query failed: {e}")
        metrics_collector = get_metrics_collector()
        metrics_collector.record_error("vector_search_error", "topk_endpoint")
        
        raise HTTPException(
            status_code=500,
            detail=f"Top-K query failed: {str(e)}"
        )


# Additional utility endpoints for production monitoring
@app.get("/api/v1/status", summary="Application status", response_model=dict)
async def get_application_status():
    """Get comprehensive application status"""
    settings = get_settings()
    metrics_collector = get_metrics_collector()
    
    return {
        "application": {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT.value,
        },
        "features": {
            "collaboration": settings.ENABLE_COLLABORATION,
            "streaming_analytics": settings.ENABLE_STREAMING_ANALYTICS and STREAMING_AVAILABLE,
            "dashboard": settings.ENABLE_DASHBOARD,
            "jwt_auth": settings.ENABLE_JWT_AUTH,
        },
        "database": {
            "kuzu_path": settings.database.KUZU_DB_PATH,
            "read_only": settings.database.KUZU_READ_ONLY,
        },
        "security": {
            "cors_enabled": bool(settings.get_cors_origins()),
            "rate_limiting": settings.security.RATE_LIMIT_PER_MINUTE,
        }
    }


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    
    uvicorn.run(
        "main:app",
        host=settings.server.HOST,
        port=settings.server.PORT,
        log_level=settings.get_log_level().lower(),
        reload=settings.is_development(),
        workers=1 if settings.is_development() else settings.server.WORKERS
    ) 