from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class Server(BaseModel):
    """OpenAPI Server object representation."""

    url: str
    description: Optional[str] = None


class Parameter(BaseModel):
    """OpenAPI Parameter object (path, query, header, cookie)."""

    model_config = ConfigDict(populate_by_name=True)

    name: str
    in_location: str = Field(alias="in")
    required: bool = False
    description: Optional[str] = None
    schema_def: Optional[Dict[str, Any]] = None


class RequestBody(BaseModel):
    """OpenAPI RequestBody object."""

    description: Optional[str] = None
    required: bool = False
    content_types: Dict[str, Any] = Field(default_factory=dict)


class Response(BaseModel):
    """OpenAPI Response object."""

    status_code: str
    description: Optional[str] = None
    content_types: Dict[str, Any] = Field(default_factory=dict)


class SecurityScheme(BaseModel):
    """OpenAPI SecurityScheme object."""

    model_config = ConfigDict(populate_by_name=True)

    type: str
    description: Optional[str] = None
    name: Optional[str] = None
    in_location: Optional[str] = Field(default=None, alias="in")
    scheme: Optional[str] = None


class Operation(BaseModel):
    """Normalized API operation definition."""

    operation_id: str
    method: str
    path: str
    tags: List[str] = Field(default_factory=list)
    summary: Optional[str] = None
    description: Optional[str] = None
    parameters: List[Parameter] = Field(default_factory=list)
    request_body: Optional[RequestBody] = None
    responses: List[Response] = Field(default_factory=list)
    security: List[Dict[str, List[str]]] = Field(default_factory=list)


class NormalizedSpec(BaseModel):
    """Fully normalized OpenAPI 3.x specification."""

    title: str
    api_version: str
    openapi_version: str
    source: str
    description: Optional[str] = None
    servers: List[Server] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    operations: List[Operation] = Field(default_factory=list)
    components_schemas: Dict[str, Any] = Field(default_factory=dict)
    security_schemes: Dict[str, SecurityScheme] = Field(default_factory=dict)
