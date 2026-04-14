import importlib.util
import shutil
from pathlib import Path
from uuid import uuid4

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
HELPER_PATH = ROOT / "notebooks" / "helpers" / "optimal_portfolio_composition_report.py"


def _load_helper_module():
    spec = importlib.util.spec_from_file_location("optimal_portfolio_composition_report", HELPER_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def report_helper():
    return _load_helper_module()


@pytest.fixture
def workspace_tmp_path(request) -> Path:
    tmp_root = ROOT / ".tmp_pytest_report_figure_language_consistency"
    tmp_root.mkdir(parents=True, exist_ok=True)
    path = tmp_root / f"{request.node.name}-{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    try:
        yield path
    finally:
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)


def test_build_top_n_with_remainder_keeps_top_n_and_balances_to_one(report_helper):
    weights = pd.DataFrame(
        {
            "ticker": ["DDD", "EEE", "BBB", "CCC", "AAA"],
            "cluster_id": [2, 3, 1, 2, 1],
            "weight": [0.10, 0.10, 0.25, 0.15, 0.40],
        }
    )

    summary = report_helper.build_top_n_with_remainder(weights, top_n=3, remainder_label="Còn lại")

    assert list(summary["ticker"]) == ["AAA", "BBB", "CCC", "Còn lại"]
    assert summary.loc[summary["ticker"] == "Còn lại", "weight"].iloc[0] == pytest.approx(0.20)
    assert summary["weight"].sum() == pytest.approx(1.0)


def test_build_scope_label_returns_positive_weight_count_when_summary_has_no_remainder_bucket(report_helper):
    summary = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB", "CCC", "DDD"],
            "cluster_id": [1, 2, 3, 4],
            "weight": [0.40, 0.30, 0.20, 0.10],
        }
    )

    assert report_helper.build_scope_label(summary, top_n=8) == "4 mã có tỷ trọng dương"


def test_build_scope_label_returns_top_n_plus_remainder_when_summary_has_remainder_bucket(report_helper):
    summary = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB", "Còn lại"],
            "cluster_id": [1, 2, ""],
            "weight": [0.55, 0.25, 0.20],
        }
    )

    assert report_helper.build_scope_label(summary, top_n=8) == "Top 8 + Còn lại"


def test_generate_optimal_portfolio_report_writes_markdown_and_two_figures(
    report_helper, workspace_tmp_path: Path
):
    gmv_csv = workspace_tmp_path / "portfolio_weights_static.csv"
    agg_csv = workspace_tmp_path / "portfolio_weights_aggressive.csv"

    pd.DataFrame(
        {
            "ticker": ["AAA", "BBB", "CCC", "DDD"],
            "cluster_id": [1, 1, 2, 3],
            "weight": [0.45, 0.30, 0.15, 0.10],
        }
    ).to_csv(gmv_csv, index=False)

    pd.DataFrame(
        {
            "ticker": ["EEE", "FFF", "GGG", "HHH"],
            "cluster_id": [1, 2, 2, 4],
            "weight": [0.60, 0.20, 0.10, 0.10],
        }
    ).to_csv(agg_csv, index=False)

    out_dir = workspace_tmp_path / "report_draft"
    markdown_path, figure_paths = report_helper.generate_optimal_portfolio_report(
        gmv_path=gmv_csv,
        aggressive_path=agg_csv,
        output_dir=out_dir,
        top_n=3,
    )

    assert markdown_path.exists()
    assert markdown_path.resolve().is_relative_to(out_dir.resolve())
    text = markdown_path.read_text(encoding="utf-8")

    headings = [
        "# Danh mục tối ưu đại diện trong đề tài",
        "## 1. Danh mục tối ưu được hiểu như thế nào trong đề tài",
        "## 2. Thành phần hai danh mục tối ưu đại diện",
        "## 3. Ghi chú về vai trò của rolling",
    ]
    for heading in headings:
        assert heading in text

    assert "GMV Defensive" in text
    assert "Aggressive" in text
    assert "rolling" in text.lower()
    assert "AAA" in text
    assert "EEE" in text
    assert "DDD" not in text
    assert "HHH" not in text
    assert "figures/optimal_gmv_defensive_top3.png" in text
    assert "figures/optimal_aggressive_top3.png" in text
    assert ":\\" not in text
    assert ":/" not in text

    assert len(figure_paths) == 2
    assert all(path.exists() for path in figure_paths)
    expected_paths = {
        (out_dir / "figures" / "optimal_gmv_defensive_top3.png").resolve(),
        (out_dir / "figures" / "optimal_aggressive_top3.png").resolve(),
    }
    assert {path.resolve() for path in figure_paths} == expected_paths


def test_generate_optimal_portfolio_report_skips_markdown_when_disabled(
    report_helper, workspace_tmp_path: Path
):
    gmv_csv = workspace_tmp_path / "portfolio_weights_static.csv"
    agg_csv = workspace_tmp_path / "portfolio_weights_aggressive.csv"

    pd.DataFrame(
        {
            "ticker": ["AAA", "BBB", "CCC", "DDD"],
            "cluster_id": [1, 1, 2, 3],
            "weight": [0.45, 0.30, 0.15, 0.10],
        }
    ).to_csv(gmv_csv, index=False)

    pd.DataFrame(
        {
            "ticker": ["EEE", "FFF", "GGG", "HHH"],
            "cluster_id": [1, 2, 2, 4],
            "weight": [0.60, 0.20, 0.10, 0.10],
        }
    ).to_csv(agg_csv, index=False)

    out_dir = workspace_tmp_path / "chapter_5"
    markdown_path, figure_paths = report_helper.generate_optimal_portfolio_report(
        gmv_path=gmv_csv,
        aggressive_path=agg_csv,
        output_dir=out_dir,
        top_n=3,
        write_markdown=False,
    )

    assert markdown_path is None
    assert not (out_dir / "optimal_portfolio_composition.md").exists()
    assert len(figure_paths) == 2
    assert all(path.exists() for path in figure_paths)
    assert all(path.resolve().is_relative_to((out_dir / "figures").resolve()) for path in figure_paths)
    assert not any(path.resolve().is_relative_to(out_dir.resolve()) and path.name == "optimal_portfolio_composition.md" for path in out_dir.rglob("*"))
