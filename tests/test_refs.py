import pytest
from specpilot.openapi.errors import RefResolutionError
from specpilot.openapi.refs import RefResolver


def test_ref_resolution_success() -> None:
    doc = {
        "components": {
            "schemas": {
                "Pet": {"type": "object", "properties": {"name": {"type": "string"}}}
            }
        }
    }
    resolver = RefResolver(doc)
    resolved = resolver.resolve("#/components/schemas/Pet")
    assert resolved == {"type": "object", "properties": {"name": {"type": "string"}}}


def test_ref_resolution_missing_path() -> None:
    doc = {"components": {}}
    resolver = RefResolver(doc)
    with pytest.raises(RefResolutionError, match="Ref path segment 'schemas' not found"):
        resolver.resolve("#/components/schemas/Missing")


def test_circular_ref_detection() -> None:
    doc = {
        "components": {
            "schemas": {
                "NodeA": {"$ref": "#/components/schemas/NodeB"},
                "NodeB": {"$ref": "#/components/schemas/NodeA"},
            }
        }
    }
    resolver = RefResolver(doc)
    with pytest.raises(RefResolutionError, match="Circular reference detected"):
        resolver.resolve("#/components/schemas/NodeA")


def test_deep_resolution() -> None:
    doc = {
        "components": {
            "schemas": {
                "Category": {"type": "object", "properties": {"id": {"type": "integer"}}},
                "Pet": {
                    "type": "object",
                    "properties": {
                        "category": {"$ref": "#/components/schemas/Category"}
                    },
                },
            }
        }
    }
    resolver = RefResolver(doc)
    resolved = resolver.resolve_deep(doc["components"]["schemas"]["Pet"])
    assert resolved["properties"]["category"]["properties"]["id"]["type"] == "integer"
