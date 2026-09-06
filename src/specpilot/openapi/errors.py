class SpecPilotError(Exception):
    """Base exception for all SpecPilot errors."""
    pass


class SpecLoaderError(SpecPilotError):
    """Raised when loading an OpenAPI specification fails."""
    pass


class SpecParseError(SpecPilotError):
    """Raised when parsing or validating an OpenAPI specification fails."""
    pass


class RefResolutionError(SpecParseError):
    """Raised when resolving a JSON Pointer $ref fails."""
    pass
