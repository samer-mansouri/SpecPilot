from specpilot.safety.policy import OperationRisk, SafetyPolicy


def test_operation_risk_classification() -> None:
    policy = SafetyPolicy()

    assert policy.classify_method("GET") == OperationRisk.READ_ONLY
    assert policy.classify_method("head") == OperationRisk.READ_ONLY
    assert policy.classify_method("OPTIONS") == OperationRisk.READ_ONLY

    assert policy.classify_method("POST") == OperationRisk.MUTATING
    assert policy.classify_method("put") == OperationRisk.MUTATING
    assert policy.classify_method("PATCH") == OperationRisk.MUTATING

    assert policy.classify_method("DELETE") == OperationRisk.DESTRUCTIVE
    assert policy.classify_method("delete") == OperationRisk.DESTRUCTIVE


def test_safety_policy_read_only_mode() -> None:
    read_only_policy = SafetyPolicy(read_only_mode=True)

    # Allowed in read-only
    assert read_only_policy.is_allowed("GET") is True
    assert read_only_policy.is_allowed("HEAD") is True

    # Blocked in read-only
    assert read_only_policy.is_allowed("POST") is False
    assert read_only_policy.is_allowed("PUT") is False
    assert read_only_policy.is_allowed("PATCH") is False
    assert read_only_policy.is_allowed("DELETE") is False


def test_safety_policy_interactive_mode() -> None:
    interactive_policy = SafetyPolicy(read_only_mode=False)

    # All allowed, but mutating/destructive require approval
    assert interactive_policy.is_allowed("GET") is True
    assert interactive_policy.is_allowed("POST") is True
    assert interactive_policy.is_allowed("DELETE") is True

    assert interactive_policy.requires_approval("GET") is False
    assert interactive_policy.requires_approval("POST") is True
    assert interactive_policy.requires_approval("PUT") is True
    assert interactive_policy.requires_approval("PATCH") is True
    assert interactive_policy.requires_approval("DELETE") is True
