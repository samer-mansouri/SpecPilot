from enum import Enum
from typing import Optional


class OperationRisk(str, Enum):
    """Risk classification level for OpenAPI HTTP operations."""

    READ_ONLY = "read_only"
    MUTATING = "mutating"
    DESTRUCTIVE = "destructive"


class SafetyPolicy:
    """Policy engine for classifying and evaluating operation risk and safety constraints."""

    READ_METHODS = {"GET", "HEAD", "OPTIONS"}
    MUTATING_METHODS = {"POST", "PUT", "PATCH"}
    DESTRUCTIVE_METHODS = {"DELETE"}

    def __init__(self, read_only_mode: bool = False) -> None:
        self.read_only_mode = read_only_mode

    def classify_method(self, method: str) -> OperationRisk:
        """Classify HTTP method into an OperationRisk category."""
        m_upper = method.upper().strip()
        if m_upper in self.READ_METHODS:
            return OperationRisk.READ_ONLY
        elif m_upper in self.DESTRUCTIVE_METHODS:
            return OperationRisk.DESTRUCTIVE
        elif m_upper in self.MUTATING_METHODS:
            return OperationRisk.MUTATING
        # Default fallback for unknown methods
        return OperationRisk.MUTATING

    def is_allowed(self, method: str, read_only_override: Optional[bool] = None) -> bool:
        """Return True if the operation is permitted under current safety constraints."""
        is_read_only = self.read_only_mode if read_only_override is None else read_only_override
        risk = self.classify_method(method)

        if is_read_only and risk != OperationRisk.READ_ONLY:
            return False
        return True

    def requires_approval(self, method: str, read_only_override: Optional[bool] = None) -> bool:
        """Return True if the operation requires human approval before network execution."""
        is_read_only = self.read_only_mode if read_only_override is None else read_only_override

        # If read-only mode is active, non-read operations are blocked outright, not approved
        if is_read_only:
            return False

        risk = self.classify_method(method)
        return risk in (OperationRisk.MUTATING, OperationRisk.DESTRUCTIVE)
