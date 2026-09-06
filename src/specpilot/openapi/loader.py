import json
from pathlib import Path
from typing import Any, Dict, NamedTuple, Union
import urllib.parse

import httpx
import yaml

from specpilot.openapi.errors import SpecLoaderError


class LoadedSpec(NamedTuple):
    data: Dict[str, Any]
    source: str
    format: str  # "json" or "yaml"


class SpecLoader:
    """Loads OpenAPI specifications from local file paths or HTTP/HTTPS URLs."""

    def __init__(self, default_timeout: float = 10.0) -> None:
        self.default_timeout = default_timeout

    def load(self, location: str) -> LoadedSpec:
        """Load spec from path or URL based on location format."""
        parsed = urllib.parse.urlparse(location)
        if parsed.scheme in ("http", "https"):
            return self.load_from_url(location)
        return self.load_from_path(location)

    def load_from_path(self, file_path: Union[str, Path]) -> LoadedSpec:
        """Load specification from a local file path (JSON or YAML)."""
        path = Path(file_path)
        if not path.exists():
            raise SpecLoaderError(f"Local file does not exist: {path}")

        if not path.is_file():
            raise SpecLoaderError(f"Specified path is not a file: {path}")

        try:
            content = path.read_text(encoding="utf-8")
        except Exception as err:
            raise SpecLoaderError(f"Failed to read file '{path}': {err}") from err

        suffix = path.suffix.lower()
        if suffix == ".json":
            return LoadedSpec(data=self._parse_json(content, str(path)), source=str(path), format="json")
        elif suffix in (".yaml", ".yml"):
            return LoadedSpec(data=self._parse_yaml(content, str(path)), source=str(path), format="yaml")

        # Fallback: try parsing JSON first, then YAML
        try:
            data = self._parse_json(content, str(path))
            return LoadedSpec(data=data, source=str(path), format="json")
        except SpecLoaderError:
            try:
                data = self._parse_yaml(content, str(path))
                return LoadedSpec(data=data, source=str(path), format="yaml")
            except SpecLoaderError:
                raise SpecLoaderError(
                    f"Unsupported file format for '{path}'. File must be valid JSON or YAML."
                )

    def load_from_url(self, url: str, timeout: Union[float, None] = None) -> LoadedSpec:
        """Load specification from remote HTTP/HTTPS URL."""
        req_timeout = timeout if timeout is not None else self.default_timeout

        try:
            response = httpx.get(url, timeout=req_timeout, follow_redirects=True)
        except httpx.TimeoutException as err:
            raise SpecLoaderError(f"Request timed out while accessing URL '{url}' after {req_timeout}s.") from err
        except httpx.RequestError as err:
            raise SpecLoaderError(f"Failed to connect to URL '{url}': {err}") from err

        if response.status_code != 200:
            raise SpecLoaderError(
                f"HTTP request to '{url}' failed with status code {response.status_code}."
            )

        content = response.text
        content_type = response.headers.get("content-type", "").lower()

        if "json" in content_type:
            return LoadedSpec(data=self._parse_json(content, url), source=url, format="json")
        elif "yaml" in content_type or "yml" in content_type:
            return LoadedSpec(data=self._parse_yaml(content, url), source=url, format="yaml")

        # Deduce from URL extension or try JSON -> YAML
        parsed_url = urllib.parse.urlparse(url)
        url_path = parsed_url.path.lower()
        if url_path.endswith(".json"):
            return LoadedSpec(data=self._parse_json(content, url), source=url, format="json")
        elif url_path.endswith((".yaml", ".yml")):
            return LoadedSpec(data=self._parse_yaml(content, url), source=url, format="yaml")

        try:
            data = self._parse_json(content, url)
            return LoadedSpec(data=data, source=url, format="json")
        except SpecLoaderError:
            try:
                data = self._parse_yaml(content, url)
                return LoadedSpec(data=data, source=url, format="yaml")
            except SpecLoaderError:
                raise SpecLoaderError(
                    f"Unable to parse OpenAPI specification from remote URL '{url}'. Content is not valid JSON or YAML."
                )

    def _parse_json(self, content: str, source: str) -> Dict[str, Any]:
        try:
            data = json.loads(content)
            if not isinstance(data, dict):
                raise SpecLoaderError(f"Specification in '{source}' must be a JSON object, not {type(data).__name__}.")
            return data
        except json.JSONDecodeError as err:
            raise SpecLoaderError(f"Malformed JSON in '{source}': line {err.lineno}, col {err.colno}.") from err

    def _parse_yaml(self, content: str, source: str) -> Dict[str, Any]:
        try:
            data = yaml.safe_load(content)
            if not isinstance(data, dict):
                raise SpecLoaderError(f"Specification in '{source}' must be a YAML mapping, not {type(data).__name__}.")
            return data
        except yaml.YAMLError as err:
            raise SpecLoaderError(f"Malformed YAML in '{source}': {err}") from err
