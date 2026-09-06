from specpilot.config import ConfigManager, Profile, ProfileStore


def test_profile_creation_and_store(tmp_path):
    config_dir = tmp_path / "specpilot_config"
    mgr = ConfigManager(config_dir=config_dir)

    assert mgr.list_profiles() == []

    p1 = Profile(name="dev", spec_location="./dev.yaml", base_url="http://localhost:8000")
    mgr.add_profile(p1)

    profiles = mgr.list_profiles()
    assert len(profiles) == 1
    assert profiles[0].name == "dev"
    assert mgr.get_active_profile().name == "dev"

    p2 = Profile(name="prod", spec_location="https://api.prod.com/openapi.json", read_only=True)
    mgr.add_profile(p2)

    assert len(mgr.list_profiles()) == 2
    assert mgr.set_active_profile("prod") is True
    assert mgr.get_active_profile().name == "prod"

    assert mgr.remove_profile("dev") is True
    assert len(mgr.list_profiles()) == 1
