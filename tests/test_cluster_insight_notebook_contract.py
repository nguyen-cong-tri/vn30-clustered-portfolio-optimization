import json
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_PATH = ROOT / "notebooks" / "05_cluster_insight.ipynb"
DATA_PROCESSED = ROOT / "data" / "processed"
HELPERS_DIR = ROOT / "notebooks" / "helpers"
if str(HELPERS_DIR) not in sys.path:
    sys.path.insert(0, str(HELPERS_DIR))

from cluster_correlation_diagnostics import build_cluster_correlation_diagnostics


def _load_notebook() -> dict:
    return json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))


def _cell_containing(fragment: str) -> dict:
    for cell in _load_notebook()["cells"]:
        source = "".join(cell.get("source", []))
        if fragment in source:
            return cell
    raise AssertionError(f"Could not find notebook cell containing {fragment!r}")


def _stream_text(cell: dict) -> str:
    chunks: list[str] = []
    for output in cell.get("outputs", []):
        if output.get("output_type") == "stream":
            chunks.append("".join(output.get("text", [])))
    return "".join(chunks)


def _normalize_path_text(text: str) -> str:
    return text.lower().replace("\\", "/")


def _output_contains_relative_path(output_text: str, relative_path: str) -> bool:
    normalized_relative_path = _normalize_path_text(relative_path)
    relative_parts = [part for part in normalized_relative_path.split("/") if part]

    return any(
        any(
            line_parts[start : start + len(relative_parts)] == relative_parts
            for start in range(len(line_parts) - len(relative_parts) + 1)
        )
        for line_parts in (
            [part for part in _normalize_path_text(line).split("/") if part]
            for line in output_text.splitlines()
        )
    )


def _expected_diagnostics() -> dict[str, str]:
    corr_matrix = pd.read_csv(DATA_PROCESSED / "corr_matrix.csv", index_col=0)
    clusters = pd.read_csv(DATA_PROCESSED / "ticker_clusters.csv")
    clusters["ticker"] = clusters["ticker"].astype(str).str.upper().str.strip()
    clusters["cluster_id"] = clusters["cluster_id"].astype(int)
    cluster_map = dict(zip(clusters["ticker"], clusters["cluster_id"]))
    diagnostics = build_cluster_correlation_diagnostics(corr_matrix, cluster_map)

    return {
        "mean_intra": f"{diagnostics['mean_intra']:.4f}",
        "mean_inter": f"{diagnostics['mean_inter']:.4f}",
        "corr_ratio": f"{diagnostics['corr_ratio']:.2f}x",
    }


def test_output_path_assertions_are_portable_across_checkout_roots():
    sample_output = "\n".join(
        [
            r"[OK] Saved figure: D:\alt-checkout\reports\cluster_insight\figures\mean_correlation_by_cluster.png",
            r"2. Exported file: D:\alt-checkout\data\processed\ticker_clusters_enriched.csv",
        ]
    )
    false_positive_output = "\n".join(
        [
            r"[OK] Saved figure: D:\tmp\myreports\cluster_insight\figures\mean_correlation_by_cluster.png",
            r"2. Exported file: D:\tmp\mydata\processed\ticker_clusters_enriched.csv",
        ]
    )

    assert _output_contains_relative_path(
        sample_output, "reports/cluster_insight/figures/mean_correlation_by_cluster.png"
    )
    assert _output_contains_relative_path(sample_output, "data/processed/ticker_clusters_enriched.csv")
    assert not _output_contains_relative_path(
        false_positive_output, "reports/cluster_insight/figures/mean_correlation_by_cluster.png"
    )
    assert not _output_contains_relative_path(
        false_positive_output, "data/processed/ticker_clusters_enriched.csv"
    )


def test_notebook_05_committed_outputs_match_pooled_correlation_diagnostics():
    diagnostics = _expected_diagnostics()
    correlation_cell = _cell_containing("INTRA-CLUSTER VS INTER-CLUSTER CORRELATION")
    final_summary_cell = _cell_containing("FINAL SUMMARY - CLUSTER DIAGNOSTIC AND METADATA ENRICHMENT")

    correlation_source = "".join(correlation_cell.get("source", []))
    correlation_output = _stream_text(correlation_cell)
    final_summary_output = _stream_text(final_summary_cell)

    assert "mean_intra_corr is pooled across all intra-cluster pairs" in correlation_source
    assert f"   - mean_intra_corr: {diagnostics['mean_intra']}" in correlation_output
    assert f"   - mean_inter_corr: {diagnostics['mean_inter']}" in correlation_output
    assert f"   - intra/inter ratio: {diagnostics['corr_ratio']}" in correlation_output

    assert f"   - mean_intra_corr: {diagnostics['mean_intra']}" in final_summary_output
    assert f"   - mean_inter_corr: {diagnostics['mean_inter']}" in final_summary_output
    assert f"   - intra/inter ratio: {diagnostics['corr_ratio']}" in final_summary_output
    assert _output_contains_relative_path(final_summary_output, "data/processed/ticker_clusters_enriched.csv")
    assert _output_contains_relative_path(
        final_summary_output, "reports/cluster_insight/figures/mean_correlation_by_cluster.png"
    )
    assert _output_contains_relative_path(
        final_summary_output, "reports/cluster_insight/figures/cluster_mean_return_and_volatility.png"
    )
    assert _output_contains_relative_path(
        final_summary_output, "reports/cluster_insight/figures/correlation_heatmap_reordered_by_cluster.png"
    )


def test_notebook_05_source_enforces_matrix_order_alignment_contract():
    validation_cell = _cell_containing("INPUT VALIDATION - CLUSTER INSIGHT")
    validation_source = "".join(validation_cell.get("source", []))

    assert 'corr_matrix.index.tolist() == corr_matrix.columns.tolist()' in validation_source
    assert 'cov_matrix.index.tolist() == cov_matrix.columns.tolist()' in validation_source
    assert 'corr_matrix row/column order drifted' in validation_source
    assert 'cov_matrix row/column order drifted' in validation_source


def test_notebook_05_mean_correlation_chart_uses_external_legend_layout():
    chart_cell = _cell_containing("Mean Intra-Cluster Correlation by Cluster")
    chart_source = "".join(chart_cell.get("source", []))

    assert 'ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1.0), framealpha=0.95, borderaxespad=0.0)' in chart_source
    assert "plt.tight_layout(rect=(0, 0, 0.84, 1))" in chart_source
