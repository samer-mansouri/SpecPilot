from typing import Dict, Optional
from pydantic import BaseModel, Field
from specpilot.auth.models import AuthConfig


class Profile(BaseModel):
    """Configuration profile for API targets and model settings."""

    __test__ = False
    name: str
    spec_location: Optional[str] = None
    base_url: Optional[str] = None
    model_provider: str = "openai"
    model_name: str = "gpt-4o-mini"
    timeout: float = 30.0
    read_only: bool = False
    headers: Dict[str, str] = Field(default_factory=dict)
    auth: Optional[AuthConfig] = None



class ProfileStore(BaseModel):
    """Persistent storage schema for user profiles."""

    __test__ = False
    active_profile: Optional[str] = None
    profiles: Dict[str, Profile] = Field(default_factory=dict)
