import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_PATH = ROOT / "notebooks" / "03_returns_and_validation.ipynb"


def _load_notebook() -> dict:
    return json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))


def _cell_containing(fragment: str) -> dict:
    for cell in _load_notebook()["cells"]:
        source = "".join(cell.get("source", []))
        if fragment in source:
            return cell
    raise AssertionError(f"Could not find notebook cell containing {fragment!r}")


def test_notebook_03_source_enforces_balanced_panel_contract_and_clear_tail_labels():
    load_cell = _cell_containing("# Load clean_ohlcv.csv")
    validation_cell = _cell_containing("VALIDATE CLEAN INPUT PANEL")
    tail_plot_cell = _cell_containing("# Diagnostic plots for log_return")

    load_source = "".join(load_cell.get("source", []))
    validation_source = "".join(validation_cell.get("source", []))
    tail_plot_source = "".join(tail_plot_cell.get("source", []))

    assert "REQUIRED_PREPROCESS_COLS" in load_source
    assert "range_ratio" in load_source
    assert "is_range_outlier" in load_source
    assert "is_volume_outlier" in load_source
    assert "missing_required_preprocess" in validation_source
    assert re.search(r"missing_required_preprocess[\s\S]{0,300}(?:raise|assert)", validation_source)
    assert "Notebook 03 expects the balanced-panel clean_ohlcv.csv exported by notebook 02" in validation_source
    assert "Notebook 02 handoff note:" in validation_source
    assert "derived preprocessing columns are part of the contract for notebook 03 diagnostics" in validation_source
    assert 'label="P1 (1st percentile)"' in tail_plot_source
    assert 'label="Q1%"' not in tail_plot_source
