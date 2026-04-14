from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def migrate_existing_aggressive_snapshot_once(canonical_path: Path, legacy_path: Path) -> bool:
    legacy_path.parent.mkdir(parents=True, exist_ok=True)
    if legacy_path.exists() or not canonical_path.exists():
        return False
    canonical_path.replace(legacy_path)
    return True


def clear_canonical_if_present(path: Path) -> bool:
    if not path.exists():
        return False
    path.unlink()
    return True


def build_static_artifact_status(*, gmv: dict[str, Any], aggressive: dict[str, Any]) -> dict[str, Any]:
    return {"version": 1, "run_timestamp": _utc_now_iso(), "gmv": gmv, "aggressive": aggressive}


def write_static_artifact_status(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def load_static_artifact_status(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, IsADirectoryError, UnicodeDecodeError, json.JSONDecodeError, OSError):
        return None
    return payload if isinstance(payload, dict) else None


def aggressive_canonical_available(status: dict[str, Any] | None, canonical_path: Path) -> bool:
    if not isinstance(status, dict):
        return False
    aggressive = status.get("aggressive")
    if not isinstance(aggressive, dict):
        return False
    return aggressive.get("canonical") is True and canonical_path.is_file()


def resolve_aggressive_input(
    *,
    status: dict[str, Any] | None,
    canonical_path: Path,
    legacy_path: Path,
    allow_legacy: bool,
) -> tuple[Path | None, str, str]:
    if aggressive_canonical_available(status, canonical_path):
        return canonical_path, "Canonical aggressive artifact", "canonical"

    aggressive = status.get("aggressive") if isinstance(status, dict) else None
    if allow_legacy and isinstance(aggressive, dict) and aggressive.get("canonical") is False and legacy_path.is_file():
        return legacy_path, "LEGACY / non-canonical reference", "legacy"

    return None, "Aggressive unavailable", "unavailable"
