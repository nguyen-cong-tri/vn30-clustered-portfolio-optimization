import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_PATH = ROOT / "notebooks" / "01_eda.ipynb"
REPORT_PATH = ROOT / "reports" / "eda" / "EDA_REPORT.md"
FIGURES_DIR = ROOT / "reports" / "eda" / "figures"


def _load_notebook_source() -> str:
    notebook = json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))
    return "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))


def test_eda_chart_artifacts_match_current_snapshot():
    notebook_source = _load_notebook_source()
    report_text = REPORT_PATH.read_text(encoding="utf-8")

    assert "normalized_price_growth.png" in notebook_source
    assert "vn30_cumulative_growth_all_tickers.png" not in notebook_source

    assert "normalized_price_growth.png" in report_text
    assert "missing_by_column.png" not in report_text

    assert (FIGURES_DIR / "normalized_price_growth.png").exists()
    assert not (FIGURES_DIR / "vn30_cumulative_growth_all_tickers.png").exists()
