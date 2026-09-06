from specpilot.safety.redactor import SecretRedactor


def test_secret_redactor_text() -> None:
    text1 = '{"api_key": "secret_abc_123", "user": "alice"}'
    redacted1 = SecretRedactor.redact(text1)
    assert "secret_abc_123" not in redacted1
    assert "[REDACTED]" in redacted1
    assert "alice" in redacted1

    text2 = "Authorization: Bearer my_secret_bearer_token"
    redacted2 = SecretRedactor.redact(text2)
    assert "my_secret_bearer_token" not in redacted2
    assert "Bearer [REDACTED]" in redacted2 or "[REDACTED]" in redacted2


def test_secret_redactor_dict() -> None:
    data = {
        "api_key": "key_xyz_999",
        "nested": {
            "password": "my_password_123",
            "normal_field": "public_data",
        },
        "headers": ["Authorization: Bearer token_abc"],
        "count": 42,
    }

    redacted = SecretRedactor.redact_dict(data)

    assert redacted["api_key"] == "[REDACTED]"
    assert redacted["nested"]["password"] == "[REDACTED]"
    assert redacted["nested"]["normal_field"] == "public_data"
    assert redacted["count"] == 42
    assert "token_abc" not in str(redacted["headers"])
