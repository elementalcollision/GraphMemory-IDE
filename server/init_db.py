#!/usr/bin/env python3
"""
Database initialization script for GraphMemory-IDE MCP Server.
Sets up the LadybugDB database with required node types and schema.
"""

import ladybug as lb
import os

def init_database() -> None:
    """Initialize the LadybugDB database with required schema."""

    # Get database path (LADYBUG_DB_PATH preferred; KUZU_DB_PATH kept as a
    # deprecated fallback for existing deployments mid-migration)
    LADYBUG_DB_PATH = os.environ.get("LADYBUG_DB_PATH") or os.environ.get("KUZU_DB_PATH", "./data")

    print(f"Initializing LadybugDB database at: {LADYBUG_DB_PATH}")

    # LadybugDB does not create parent directories (Kuzu did) — ensure they exist
    from pathlib import Path
    Path(LADYBUG_DB_PATH).parent.mkdir(parents=True, exist_ok=True)

    # Create database and connection
    db = lb.Database(LADYBUG_DB_PATH)
    conn = lb.Connection(db)

    try:
        # Create node table for TelemetryEvent if it doesn't exist
        # In LadybugDB, we need to create node tables explicitly
        print("Creating TelemetryEvent node table...")
        conn.execute("""
            CREATE NODE TABLE IF NOT EXISTS TelemetryEvent(
                event_type STRING,
                timestamp STRING,
                user_id STRING,
                session_id STRING,
                data STRING,
                PRIMARY KEY(timestamp)
            )
        """)

        # Create a simple test node to verify the table works
        print("Creating test TelemetryEvent node...")
        conn.execute("""
            CREATE (e:TelemetryEvent {
                event_type: 'init_test',
                timestamp: '2025-01-27T12:41:19',
                user_id: 'system',
                session_id: 'init',
                data: '{"action": "database_initialization"}'
            })
        """)

        # Verify the node was created
        result = conn.execute("MATCH (e:TelemetryEvent) WHERE e.event_type = 'init_test' RETURN e")
        if isinstance(result, list):
            result = result[0]

        count = 0
        while result.has_next():
            result.get_next()
            count += 1

        print(f"Database initialization successful! Created {count} test node(s).")

        # Clean up test node
        conn.execute("MATCH (e:TelemetryEvent) WHERE e.event_type = 'init_test' DELETE e")
        print("Cleaned up test node.")

    except Exception as e:
        print(f"Error during database initialization: {e}")
        raise

    finally:
        # Close connection
        conn.close()
        print("Database initialization complete.")

if __name__ == "__main__":
    init_database()
