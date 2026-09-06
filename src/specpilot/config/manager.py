import json
import os
from pathlib import Path
from typing import List, Optional

from specpilot.config.models import Profile, ProfileStore


class ConfigManager:
    """Manages persistent profile storage and retrieval in user configuration directory."""

    def __init__(self, config_dir: Optional[Path] = None) -> None:
        if config_dir:
            self.config_dir = config_dir
        else:
            # OS-appropriate config directory location (~/.config/specpilot or APPDATA/specpilot)
            if os.name == "nt":
                app_data = os.environ.get("APPDATA")
                base = Path(app_data) if app_data else Path.home() / ".config"
            else:
                base = Path.home() / ".config"
            self.config_dir = base / "specpilot"

        self.config_path = self.config_dir / "profiles.json"

    def ensure_config_dir(self) -> None:
        """Ensure the configuration directory exists."""
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def load_store(self) -> ProfileStore:
        """Load profile store from disk, returning empty store if file missing or corrupt."""
        if not self.config_path.exists():
            return ProfileStore()

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return ProfileStore.model_validate(data)
        except Exception:
            return ProfileStore()

    def save_store(self, store: ProfileStore) -> None:
        """Save profile store to disk."""
        self.ensure_config_dir()
        data = store.model_dump()
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def add_profile(self, profile: Profile) -> None:
        """Add or update a profile."""
        store = self.load_store()
        store.profiles[profile.name] = profile
        if not store.active_profile:
            store.active_profile = profile.name
        self.save_store(store)

    def remove_profile(self, name: str) -> bool:
        """Remove a profile by name."""
        store = self.load_store()
        if name in store.profiles:
            del store.profiles[name]
            if store.active_profile == name:
                store.active_profile = next(iter(store.profiles.keys()), None)
            self.save_store(store)
            return True
        return False

    def get_profile(self, name: str) -> Optional[Profile]:
        """Get a profile by name."""
        store = self.load_store()
        return store.profiles.get(name)

    def set_active_profile(self, name: str) -> bool:
        """Set the active profile."""
        store = self.load_store()
        if name in store.profiles:
            store.active_profile = name
            self.save_store(store)
            return True
        return False

    def get_active_profile(self) -> Optional[Profile]:
        """Get the currently active profile."""
        store = self.load_store()
        if store.active_profile and store.active_profile in store.profiles:
            return store.profiles[store.active_profile]
        return None

    def list_profiles(self) -> List[Profile]:
        """List all saved profiles."""
        store = self.load_store()
        return list(store.profiles.values())
