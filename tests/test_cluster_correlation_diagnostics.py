from pathlib import Path
import sys

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
HELPERS_DIR = ROOT / "notebooks" / "helpers"
if str(HELPERS_DIR) not in sys.path:
    sys.path.insert(0, str(HELPERS_DIR))

from cluster_correlation_diagnostics import build_cluster_correlation_diagnostics


def test_build_cluster_correlation_diagnostics_uses_pooled_intra_mean():
    tickers = ["A", "B", "C", "D", "E", "F"]
    corr_matrix = pd.DataFrame(0.2, index=tickers, columns=tickers, dtype=float)
    for ticker in tickers:
        corr_matrix.loc[ticker, ticker] = 1.0

    cluster_one_pairs = [("A", "B"), ("A", "C"), ("A", "D"), ("B", "C"), ("B", "D"), ("C", "D")]
    for left, right in cluster_one_pairs:
        corr_matrix.loc[left, right] = 0.6
        corr_matrix.loc[right, left] = 0.6

    corr_matrix.loc["E", "F"] = 0.1
    corr_matrix.loc["F", "E"] = 0.1

    cluster_map = {"A": 1, "B": 1, "C": 1, "D": 1, "E": 2, "F": 2}

    diagnostics = build_cluster_correlation_diagnostics(corr_matrix, cluster_map)

    assert diagnostics["intra_stats_df"].loc[1, "n_intra_pairs"] == 6
    assert diagnostics["intra_stats_df"].loc[2, "n_intra_pairs"] == 1
    assert diagnostics["intra_stats_df"].loc[1, "mean_intra_corr"] == 0.6
    assert diagnostics["intra_stats_df"].loc[2, "mean_intra_corr"] == 0.1
    assert diagnostics["mean_inter"] == 0.2
    assert diagnostics["mean_intra"] == 3.7 / 7
    assert diagnostics["mean_intra"] != 0.35
    assert diagnostics["corr_ratio"] == (3.7 / 7) / 0.2


def test_build_cluster_correlation_diagnostics_rejects_row_column_order_drift():
    corr_matrix = pd.DataFrame(
        [
            [1.0, 0.40, 0.20],
            [0.40, 1.0, 0.30],
            [0.20, 0.30, 1.0],
        ],
        index=["AAA", "BBB", "CCC"],
        columns=["BBB", "AAA", "CCC"],
        dtype=float,
    )
    cluster_map = {"AAA": 1, "BBB": 1, "CCC": 2}

    with pytest.raises(ValueError, match="row/column order drifted"):
        build_cluster_correlation_diagnostics(corr_matrix, cluster_map)
