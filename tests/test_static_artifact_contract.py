from contextlib import contextmanager
from pathlib import Path
import shutil
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
HELPERS_DIR = ROOT / "notebooks" / "helpers"
SANDBOX_ROOT = ROOT / "tests" / "_sandbox" / "artifact_contract"
if str(HELPERS_DIR) not in sys.path:
    sys.path.insert(0, str(HELPERS_DIR))

from static_artifact_contract import (
    aggressive_canonical_available,
    build_static_artifact_status,
    clear_canonical_if_present,
    load_static_artifact_status,
    migrate_existing_aggressive_snapshot_once,
    resolve_aggressive_input,
    write_static_artifact_status,
)


@contextmanager
def sandbox(name: str):
    path = SANDBOX_ROOT / f"{name}_{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)
        for cleanup_target in (SANDBOX_ROOT, SANDBOX_ROOT.parent):
            try:
                cleanup_target.rmdir()
            except OSError:
                pass


def test_migrate_existing_aggressive_snapshot_once_moves_only_once():
    with sandbox("migrate_once") as tmp_path:
        canonical = tmp_path / "portfolio_weights_aggressive.csv"
        legacy = tmp_path / "legacy" / "portfolio_weights_aggressive_prefeasibility.csv"
        canonical.write_text("ticker,weight\nAAA,1.0\n", encoding="utf-8")
        assert migrate_existing_aggressive_snapshot_once(canonical, legacy) is True
        assert canonical.exists() is False
        assert legacy.exists() is True
        assert migrate_existing_aggressive_snapshot_once(canonical, legacy) is False


def test_clear_canonical_if_present_is_idempotent():
    with sandbox("clear_canonical") as tmp_path:
        path = tmp_path / "portfolio_weights_aggressive.csv"
        path.write_text("ticker,weight\nAAA,1.0\n", encoding="utf-8")
        assert clear_canonical_if_present(path) is True
        assert path.exists() is False
        assert clear_canonical_if_present(path) is False


def test_manifest_round_trip_and_canonical_check():
    with sandbox("manifest_round_trip") as tmp_path:
        status_path = tmp_path / "static_artifact_status.json"
        canonical = tmp_path / "portfolio_weights_aggressive.csv"
        canonical.write_text("ticker,weight\nAAA,1.0\n", encoding="utf-8")
        status = build_static_artifact_status(
            gmv={"solver_status": "optimal", "feasible": True, "exported": True, "canonical_path": "static.csv"},
            aggressive={
                "solver_status": "optimal",
                "feasible": True,
                "exported": True,
                "canonical": True,
                "canonical_path": str(canonical),
                "legacy_path": "legacy.csv",
                "reason_if_not_canonical": None,
            },
        )
        write_static_artifact_status(status_path, status)
        loaded = load_static_artifact_status(status_path)
        assert loaded is not None
        assert loaded["version"] == 1
        assert "run_timestamp" in loaded
        assert loaded["gmv"] == {
            "solver_status": "optimal",
            "feasible": True,
            "exported": True,
            "canonical_path": "static.csv",
        }
        assert loaded["aggressive"] == {
            "solver_status": "optimal",
            "feasible": True,
            "exported": True,
            "canonical": True,
            "canonical_path": str(canonical),
            "legacy_path": "legacy.csv",
            "reason_if_not_canonical": None,
        }
        assert aggressive_canonical_available(loaded, canonical) is True


def test_load_manifest_returns_none_for_missing_or_invalid_json(monkeypatch):
    with sandbox("manifest_invalid") as tmp_path:
        missing = tmp_path / "missing.json"
        assert load_static_artifact_status(missing) is None

        broken = tmp_path / "broken.json"
        broken.write_text("{not-json", encoding="utf-8")
        assert load_static_artifact_status(broken) is None

        not_an_object = tmp_path / "list.json"
        not_an_object.write_text("[]", encoding="utf-8")
        assert load_static_artifact_status(not_an_object) is None

        bad_bytes = tmp_path / "bad_bytes.json"
        bad_bytes.write_bytes(b"\xff\xfe\x00\x00")
        assert load_static_artifact_status(bad_bytes) is None

        def raise_permission_error(self, *args, **kwargs):
            raise PermissionError("denied")

        monkeypatch.setattr(Path, "read_text", raise_permission_error)
        assert load_static_artifact_status(tmp_path / "permission.json") is None


def test_resolve_aggressive_input_prefers_canonical_then_legacy_then_unavailable():
    with sandbox("resolve_input") as tmp_path:
        canonical = tmp_path / "portfolio_weights_aggressive.csv"
        legacy = tmp_path / "legacy" / "portfolio_weights_aggressive_prefeasibility.csv"
        canonical.write_text("ticker,weight\nAAA,1.0\n", encoding="utf-8")
        legacy.parent.mkdir(parents=True, exist_ok=True)
        legacy.write_text("ticker,weight\nBBB,1.0\n", encoding="utf-8")

        selected_path, artifact_status, mode = resolve_aggressive_input(
            status={"aggressive": {"canonical": True}},
            canonical_path=canonical,
            legacy_path=legacy,
            allow_legacy=True,
        )
        assert selected_path == canonical
        assert artifact_status == "Canonical aggressive artifact"
        assert mode == "canonical"

        selected_path, artifact_status, mode = resolve_aggressive_input(
            status={"aggressive": {"canonical": "false"}},
            canonical_path=canonical,
            legacy_path=legacy,
            allow_legacy=False,
        )
        assert selected_path is None
        assert artifact_status == "Aggressive unavailable"
        assert mode == "unavailable"

        selected_path, artifact_status, mode = resolve_aggressive_input(
            status={"aggressive": {"canonical": False}},
            canonical_path=canonical,
            legacy_path=legacy,
            allow_legacy=True,
        )
        assert selected_path == legacy
        assert artifact_status == "LEGACY / non-canonical reference"
        assert mode == "legacy"

        selected_path, artifact_status, mode = resolve_aggressive_input(
            status={"aggressive": None},
            canonical_path=canonical,
            legacy_path=legacy,
            allow_legacy=False,
        )
        assert selected_path is None
        assert artifact_status == "Aggressive unavailable"
        assert mode == "unavailable"

        selected_path, artifact_status, mode = resolve_aggressive_input(
            status=None,
            canonical_path=canonical,
            legacy_path=legacy,
            allow_legacy=True,
        )
        assert selected_path is None
        assert artifact_status == "Aggressive unavailable"
        assert mode == "unavailable"


def test_resolve_aggressive_input_rejects_directory_paths():
    with sandbox("directory_paths") as tmp_path:
        canonical_dir = tmp_path / "portfolio_weights_aggressive.csv"
        legacy_dir = tmp_path / "legacy" / "portfolio_weights_aggressive_prefeasibility.csv"
        canonical_dir.mkdir(parents=True)
        legacy_dir.mkdir(parents=True)

        selected_path, artifact_status, mode = resolve_aggressive_input(
            status={"aggressive": {"canonical": True}},
            canonical_path=canonical_dir,
            legacy_path=legacy_dir,
            allow_legacy=True,
        )
        assert selected_path is None
        assert artifact_status == "Aggressive unavailable"
        assert mode == "unavailable"

        selected_path, artifact_status, mode = resolve_aggressive_input(
            status={"aggressive": {"canonical": False}},
            canonical_path=tmp_path / "missing.csv",
            legacy_path=legacy_dir,
            allow_legacy=True,
        )
        assert selected_path is None
        assert artifact_status == "Aggressive unavailable"
        assert mode == "unavailable"
