from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .hardware import HardwareProfile


PROFILE_SCHEMA_VERSION = 1
_PROFILE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def lab_home() -> Path:
    override = os.environ.get("LOCAL_LLM_LAB_HOME")
    if override:
        return Path(override).expanduser().resolve()
    return Path.cwd() / ".local-llm-lab"


def profiles_dir() -> Path:
    return lab_home() / "profiles"


def validate_profile_name(name: str) -> str:
    cleaned = name.strip()
    if not _PROFILE_NAME_RE.match(cleaned):
        raise ValueError("Profile names must be 1-64 characters: letters, numbers, dot, dash, or underscore.")
    return cleaned


def profile_path(name: str) -> Path:
    return profiles_dir() / f"{validate_profile_name(name)}.json"


def _redact_string(value: str) -> str:
    home = str(Path.home())
    if home and home in value:
        value = value.replace(home, "[home]")
    value = re.sub(r"/Users/[^/\s]+", "/Users/[redacted]", value)
    value = re.sub(r"(?i)(serial|uuid|token|password|secret)[^,\n;]*", r"\1=[redacted]", value)
    return value


def sanitized_hardware_dict(profile: HardwareProfile) -> dict[str, Any]:
    data = profile.to_dict()
    backends = data.get("backends")
    if isinstance(backends, dict):
        data["backends"] = {str(key): ("found" if value else None) for key, value in backends.items()}

    probes = data.get("probes")
    if isinstance(probes, dict):
        clean_probes: dict[str, Any] = {}
        for key, value in probes.items():
            if isinstance(value, str):
                clean_probes[str(key)] = "error redacted" if str(key).endswith("_error") else _redact_string(value)
            else:
                clean_probes[str(key)] = value
        data["probes"] = clean_probes

    for key, value in list(data.items()):
        lowered = str(key).lower()
        if any(sensitive in lowered for sensitive in ("serial", "uuid", "token", "password", "secret")):
            data[key] = "[redacted]"
        elif isinstance(value, str):
            data[key] = _redact_string(value)
    return data


def save_profile(name: str, profile: HardwareProfile, *, source: str = "local-detect") -> Path:
    cleaned = validate_profile_name(name)
    target = profile_path(cleaned)
    target.parent.mkdir(parents=True, exist_ok=True)
    document = {
        "schema_version": PROFILE_SCHEMA_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "profile_name": cleaned,
        "source": _redact_string(source),
        "hardware": sanitized_hardware_dict(profile),
    }
    target.write_text(json.dumps(document, indent=2, sort_keys=True), encoding="utf-8")
    return target


def load_profile_document(name: str) -> dict[str, Any]:
    path = profile_path(name)
    if not path.exists():
        available = ", ".join(item["name"] for item in list_profiles()) or "none"
        raise ValueError(f"Unknown hardware profile {name!r}. Saved profiles: {available}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "hardware" not in data:
        raise ValueError(f"Profile {name!r} is not a valid local-llm-lab profile.")
    return data


def load_profile(name: str) -> HardwareProfile:
    document = load_profile_document(name)
    hardware = document["hardware"]
    if not isinstance(hardware, dict):
        raise ValueError(f"Profile {name!r} does not contain hardware data.")
    return HardwareProfile(**hardware)


def list_profiles() -> list[dict[str, Any]]:
    directory = profiles_dir()
    if not directory.exists():
        return []
    profiles: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            hardware = data.get("hardware", {}) if isinstance(data, dict) else {}
            profiles.append(
                {
                    "name": str(data.get("profile_name") or path.stem),
                    "created_at": str(data.get("created_at") or ""),
                    "hardware_name": str(hardware.get("name") or "unknown") if isinstance(hardware, dict) else "unknown",
                    "memory_total_gib": hardware.get("memory_total_gib") if isinstance(hardware, dict) else None,
                    "path": str(path),
                }
            )
        except Exception:
            profiles.append(
                {
                    "name": path.stem,
                    "created_at": "",
                    "hardware_name": "unreadable profile",
                    "memory_total_gib": None,
                    "path": str(path),
                }
            )
    return profiles
