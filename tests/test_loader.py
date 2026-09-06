from pathlib import Path
import pytest
import respx
from httpx import Response, TimeoutException

from specpilot.openapi.errors import SpecLoaderError
from specpilot.openapi.loader import SpecLoader

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_load_local_json() -> None:
    loader = SpecLoader()
    json_path = FIXTURES_DIR / "sample_3_0.json"
    spec = loader.load(str(json_path))

    assert spec.format == "json"
    assert spec.source == str(json_path)
    assert spec.data["info"]["title"] == "Petstore API"


def test_load_local_yaml() -> None:
    loader = SpecLoader()
    yaml_path = FIXTURES_DIR / "sample_3_0.yaml"
    spec = loader.load(str(yaml_path))

    assert spec.format == "yaml"
    assert spec.source == str(yaml_path)
    assert spec.data["info"]["title"] == "Petstore YAML API"


def test_load_nonexistent_file() -> None:
    loader = SpecLoader()
    with pytest.raises(SpecLoaderError, match="Local file does not exist"):
        loader.load("non_existent_file.yaml")


def test_load_malformed_json(tmp_path: Path) -> None:
    bad_json = tmp_path / "bad.json"
    bad_json.write_text("{ invalid json ", encoding="utf-8")

    loader = SpecLoader()
    with pytest.raises(SpecLoaderError, match="Malformed JSON"):
        loader.load(str(bad_json))


def test_load_malformed_yaml(tmp_path: Path) -> None:
    bad_yaml = tmp_path / "bad.yaml"
    bad_yaml.write_text("info:\n  title: [unclosed list", encoding="utf-8")

    loader = SpecLoader()
    with pytest.raises(SpecLoaderError, match="Malformed YAML"):
        loader.load(str(bad_yaml))


@respx.mock
def test_load_remote_url_success() -> None:
    url = "https://example.com/openapi.json"
    respx.get(url).mock(
        return_value=Response(
            200,
            json={"openapi": "3.0.0", "info": {"title": "Remote API", "version": "1.0.0"}, "paths": {}},
            headers={"Content-Type": "application/json"},
        )
    )

    loader = SpecLoader()
    spec = loader.load(url)

    assert spec.source == url
    assert spec.format == "json"
    assert spec.data["info"]["title"] == "Remote API"


@respx.mock
def test_load_remote_url_404() -> None:
    url = "https://example.com/missing.json"
    respx.get(url).mock(return_value=Response(404))

    loader = SpecLoader()
    with pytest.raises(SpecLoaderError, match="failed with status code 404"):
        loader.load(url)


@respx.mock
def test_load_remote_url_timeout() -> None:
    url = "https://example.com/timeout.json"
    respx.get(url).side_effect = TimeoutException("Connection timed out")

    loader = SpecLoader()
    with pytest.raises(SpecLoaderError, match="timed out"):
        loader.load(url)
