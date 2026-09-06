from pathlib import Path
import pytest

from specpilot.openapi.errors import SpecParseError
from specpilot.openapi.loader import SpecLoader
from specpilot.openapi.parser import OpenAPIParser

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_parse_sample_3_0_json() -> None:
    loader = SpecLoader()
    loaded = loader.load(str(FIXTURES_DIR / "sample_3_0.json"))

    parser = OpenAPIParser(loaded)
    spec = parser.parse()

    assert spec.title == "Petstore API"
    assert spec.api_version == "1.0.0"
    assert spec.openapi_version == "3.0.3"
    assert len(spec.servers) == 1
    assert spec.servers[0].url == "https://api.petstore.example.com/v1"
    assert len(spec.tags) == 1
    assert spec.tags[0] == "pets"

    # Operations: GET /pets, POST /pets, GET /pets/{petId}
    assert len(spec.operations) == 3

    op_map = {op.operation_id: op for op in spec.operations}
    assert "listPets" in op_map
    assert "createPet" in op_map
    assert "showPetById" in op_map

    # Inspect listPets operation
    list_pets = op_map["listPets"]
    assert list_pets.method == "GET"
    assert list_pets.path == "/pets"
    assert len(list_pets.parameters) == 1
    assert list_pets.parameters[0].name == "limit"
    assert list_pets.parameters[0].in_location == "query"

    # Inspect showPetById (parameter resolved from $ref)
    show_pet = op_map["showPetById"]
    assert show_pet.method == "GET"
    assert show_pet.path == "/pets/{petId}"
    assert len(show_pet.parameters) == 1
    assert show_pet.parameters[0].name == "petId"
    assert show_pet.parameters[0].in_location == "path"
    assert show_pet.parameters[0].required is True


def test_parse_missing_openapi_version() -> None:
    loader_spec = SpecLoader().load(str(FIXTURES_DIR / "sample_3_0.json"))
    raw_data = dict(loader_spec.data)
    del raw_data["openapi"]

    bad_loaded = loader_spec._replace(data=raw_data)
    parser = OpenAPIParser(bad_loaded)

    with pytest.raises(SpecParseError, match="Missing or invalid 'openapi' version"):
        parser.parse()


def test_parse_unsupported_openapi_v2() -> None:
    loader_spec = SpecLoader().load(str(FIXTURES_DIR / "sample_3_0.json"))
    raw_data = dict(loader_spec.data)
    raw_data["openapi"] = "2.0"

    bad_loaded = loader_spec._replace(data=raw_data)
    parser = OpenAPIParser(bad_loaded)

    with pytest.raises(SpecParseError, match="Unsupported OpenAPI version '2.0'"):
        parser.parse()


def test_auto_generate_operation_id() -> None:
    raw_doc = {
        "openapi": "3.0.0",
        "info": {"title": "Minimal API", "version": "1.0"},
        "paths": {
            "/users/{userId}/posts": {
                "get": {
                    "summary": "Get user posts",
                    "responses": {"200": {"description": "OK"}},
                }
            }
        },
    }
    loaded = SpecLoader().load_from_path(FIXTURES_DIR / "sample_3_0.json")._replace(data=raw_doc)
    parser = OpenAPIParser(loaded)
    spec = parser.parse()

    assert len(spec.operations) == 1
    assert spec.operations[0].operation_id == "get_users_userId_posts"
