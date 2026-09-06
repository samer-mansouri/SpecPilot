from typing import Any, Dict, Set, Union
from specpilot.openapi.errors import RefResolutionError


class RefResolver:
    """Resolves local JSON Pointer references (e.g. #/components/schemas/Pet)."""

    def __init__(self, root_doc: Dict[str, Any]) -> None:
        self.root_doc = root_doc

    def resolve(self, ref_uri: str, visited: Union[Set[str], None] = None) -> Dict[str, Any]:
        """Resolve a JSON Pointer URI against root_doc."""
        if not isinstance(ref_uri, str) or not ref_uri.startswith("#/"):
            raise RefResolutionError(
                f"Unsupported or invalid $ref format '{ref_uri}'. Only local references starting with '#/' are supported."
            )

        if visited is None:
            visited = set()

        if ref_uri in visited:
            raise RefResolutionError(f"Circular reference detected while resolving $ref '{ref_uri}'.")

        visited.add(ref_uri)

        parts = ref_uri[2:].split("/")
        current: Any = self.root_doc

        for part in parts:
            # Unescape JSON pointer characters (~1 -> /, ~0 -> ~)
            part = part.replace("~1", "/").replace("~0", "~")
            if isinstance(current, dict) and part in current:
                current = current[part]
            elif isinstance(current, list) and part.isdigit():
                idx = int(part)
                if 0 <= idx < len(current):
                    current = current[idx]
                else:
                    raise RefResolutionError(
                        f"Ref index '{part}' out of range when resolving $ref '{ref_uri}'."
                    )
            else:
                raise RefResolutionError(
                    f"Ref path segment '{part}' not found when resolving $ref '{ref_uri}'."
                )

        if not isinstance(current, dict):
            raise RefResolutionError(
                f"Resolved target for $ref '{ref_uri}' must be a dictionary, got {type(current).__name__}."
            )

        # If resolved target contains another $ref, resolve recursively
        if "$ref" in current and isinstance(current["$ref"], str):
            return self.resolve(current["$ref"], visited)

        return current

    def resolve_deep(self, item: Any, visited: Union[Set[str], None] = None) -> Any:
        """Recursively resolve all $ref pointers inside a dict or list structure."""
        if isinstance(item, dict):
            if "$ref" in item and isinstance(item["$ref"], str):
                resolved = self.resolve(item["$ref"], visited)
                # Merge any sibling keys in item with the resolved target
                extra = {k: v for k, v in item.items() if k != "$ref"}
                if extra:
                    merged = dict(resolved)
                    merged.update(self.resolve_deep(extra, visited))
                    return merged
                return self.resolve_deep(resolved, visited)
            return {k: self.resolve_deep(v, visited) for k, v in item.items()}
        elif isinstance(item, list):
            return [self.resolve_deep(v, visited) for v in item]
        return item
