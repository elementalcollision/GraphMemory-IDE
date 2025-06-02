#!/usr/bin/env python3
"""
Database initialization script for GraphMemory-IDE MCP Server.
Sets up the Kuzu database with required node types and schema.
"""

import kuzu
import os

def init_database() -> None:
    """Initialize the Kuzu database with required schema."""
    
    # Get database path
    KUZU_DB_PATH = os.environ.get("KUZU_DB_PATH", "./data")
    
    print(f"Initializing Kuzu database at: {KUZU_DB_PATH}")
    
    # Create database and connection
    db = kuzu.Database(KUZU_DB_PATH)
    conn = kuzu.Connection(db)
    
    try:
        # Create node table for TelemetryEvent if it doesn't exist
        # In Kuzu, we need to create node tables explicitly
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