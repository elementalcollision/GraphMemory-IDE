from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

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

# JWT Authentication Models
class Token(BaseModel):
    """JWT access token response model"""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")

class TokenData(BaseModel):
    """JWT token payload data"""
    username: Optional[str] = Field(None, description="Username from token subject")
    scopes: List[str] = Field(default_factory=list, description="Token scopes for RBAC")

class User(BaseModel):
    """User model for authentication"""
    username: str = Field(..., description="Unique username")
    email: Optional[str] = Field(None, description="User email address")
    full_name: Optional[str] = Field(None, description="User's full name")
    disabled: bool = Field(default=False, description="Whether user account is disabled")

class UserInDB(User):
    """User model with hashed password for database storage"""
    hashed_password: str = Field(..., description="Bcrypt hashed password")

# Example for future extensibility:
# class FileOpenData(BaseModel):
#     filename: str
#     project: Optional[str]
#
# class FileOpenEvent(TelemetryEvent):
#     data: FileOpenData 