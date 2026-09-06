import specpilot


def test_package_version() -> None:
    assert hasattr(specpilot, "__version__")
    assert isinstance(specpilot.__version__, str)
    assert len(specpilot.__version__) > 0
