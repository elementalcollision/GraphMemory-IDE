from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class TelemetryEvent(BaseModel):
    """
    Schema for IDE telemetry events ingested by the MCP server.
    Extensible for future event types.
    """
    event_type: str = Field(..., description="Type of event (e.g., file_open, file_save, symbol_index, test_run, user_chat)")
    timestamp: str = Field(..., description="ISO 8601 timestamp of the event")
    user_id: Optional[str] = Field(None, description="User identifier")
    session_id: Optional[str] = Field(None, description="Session identifier")
    data: Dict[str, Any] = Field(..., description="Event-specific payload")

# Example for future extensibility:
# class FileOpenData(BaseModel):
#     filename: str
#     project: Optional[str]
#
# class FileOpenEvent(TelemetryEvent):
#     data: FileOpenData 