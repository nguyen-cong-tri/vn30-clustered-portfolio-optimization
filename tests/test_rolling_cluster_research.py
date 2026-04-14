from pathlib import Path
import sys

import pytest
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform

ROOT = Path(__file__).resolve().parents[1]
HELPERS_DIR = ROOT / "notebooks" / "helpers"
if str(HELPERS_DIR) not in sys.path:
    sys.path.insert(0, str(HELPERS_DIR))

from rolling_cluster_research import (
    canonicalize_cluster_profiles,
    correlation_to_distance,
    derive_window_cluster_snapshot,
    summarize_aggressive_rebalance_states,
)


WINDOW_RETURNS = pd.DataFrame(
    {
        "AAA": [0.030, 0.025, 0.028, 0.031, 0.029],
        "AAB": [0.027, 0.024, 0.026, 0.029, 0.028],
        "BBB": [0.018, 0.016, 0.020, 0.019, 0.017],
        "BBC": [0.015, 0.014, 0.017, 0.016, 0.013],
        "CCC": [0.004, 0.012, -0.001, 0.010, 0.002],
        "CCD": [0.002, 0.010, -0.003, 0.008, 0.001],
        "DDD": [0.001, 0.000, -0.001, 0.001, 0.000],
        "DDE": [0.000, 0.001, -0.001, 0.000, 0.001],
    }
)


def test_correlation_to_distance_preserves_labels_and_zero_diagonal():
    corr = pd.DataFrame(
        [[1.0, 0.5], [0.5, 1.0]],
        index=["AAA", "BBB"],
        columns=["AAA", "BBB"],
    )
    distance = correlation_to_distance(corr)
    assert distance.index.tolist() == ["AAA", "BBB"]
    assert distance.columns.tolist() == ["AAA", "BBB"]
    assert distance.loc["AAA", "AAA"] == 0.0
    assert round(distance.loc["AAA", "BBB"], 6) == round((2.0 * (1.0 - 0.5)) ** 0.5, 6)


def test_canonicalize_cluster_profiles_is_invariant_to_raw_label_permutation():
    raw_a = pd.Series([11, 11, 7, 7, 3, 3, 5, 5], index=WINDOW_RETURNS.columns)
    raw_b = pd.Series([3, 3, 11, 11, 5, 5, 7, 7], index=WINDOW_RETURNS.columns)

    canonical_a, summary_a = canonicalize_cluster_profiles(WINDOW_RETURNS, raw_a)
    canonical_b, summary_b = canonicalize_cluster_profiles(WINDOW_RETURNS, raw_b)

    expected = {
        "AAA": 1,
        "AAB": 1,
        "BBB": 2,
        "BBC": 2,
        "CCC": 3,
        "CCD": 3,
        "DDD": 4,
        "DDE": 4,
    }

    assert canonical_a.to_dict() == expected
    assert canonical_b.to_dict() == expected
    assert summary_a["cluster_id"].tolist() == [1, 2, 3, 4]
    assert summary_b["cluster_id"].tolist() == [1, 2, 3, 4]


def test_canonicalize_cluster_profiles_uses_content_based_tiebreak_for_tied_profiles():
    tied_window = pd.DataFrame(
        {
            "AAA": [0.020, 0.021, 0.019, 0.020],
            "AAB": [0.020, 0.021, 0.019, 0.020],
            "BBB": [0.020, 0.021, 0.019, 0.020],
            "BBC": [0.020, 0.021, 0.019, 0.020],
            "CCC": [0.030, 0.031, 0.029, 0.030],
            "CCD": [0.030, 0.031, 0.029, 0.030],
            "DDD": [0.000, 0.000, 0.000, 0.000],
            "DDE": [0.000, 0.000, 0.000, 0.000],
        }
    )
    raw_a = pd.Series([11, 11, 7, 7, 3, 3, 5, 5], index=tied_window.columns)
    raw_b = pd.Series([7, 7, 11, 11, 3, 3, 5, 5], index=tied_window.columns)

    canonical_a, summary_a = canonicalize_cluster_profiles(tied_window, raw_a)
    canonical_b, summary_b = canonicalize_cluster_profiles(tied_window, raw_b)

    assert canonical_a.equals(canonical_b)
    pd.testing.assert_frame_equal(
        summary_a.drop(columns=["raw_cluster_id"]),
        summary_b.drop(columns=["raw_cluster_id"]),
    )


def test_canonicalize_cluster_profiles_rejects_non_four_label_universe():
    raw_ids = pd.Series([1, 2, 3, 4, 5, 1, 2, 3], index=WINDOW_RETURNS.columns)

    with pytest.raises(ValueError, match="exactly 4 unique raw cluster labels"):
        canonicalize_cluster_profiles(WINDOW_RETURNS, raw_ids)


def _expected_snapshot(window_returns: pd.DataFrame) -> tuple[pd.Series, pd.DataFrame]:
    corr = window_returns.corr()
    distance = correlation_to_distance(corr)
    condensed = squareform(distance.to_numpy(dtype=float), checks=False)
    raw_cluster_ids = pd.Series(
        fcluster(linkage(condensed, method="ward"), t=4, criterion="maxclust"),
        index=window_returns.columns,
        name="raw_cluster_id",
    )

    rows: list[dict[str, float | int]] = []
    for raw_cluster_id in sorted(pd.unique(raw_cluster_ids)):
        tickers = raw_cluster_ids.index[raw_cluster_ids == raw_cluster_id]
        cluster_block = window_returns.loc[:, tickers]
        rows.append(
            {
                "raw_cluster_id": int(raw_cluster_id),
                "ticker_count": int(len(tickers)),
                "mean_return": float(cluster_block.mean().mean()),
                "mean_volatility": float(cluster_block.std(ddof=1).mean()),
            }
        )

    summary = pd.DataFrame(rows)
    defensive_raw = int(
        summary.sort_values(
            ["mean_volatility", "mean_return", "raw_cluster_id"],
            ascending=[True, True, True],
        ).iloc[0]["raw_cluster_id"]
    )
    growth_like = summary[summary["raw_cluster_id"] != defensive_raw].sort_values(
        ["mean_return", "mean_volatility", "ticker_count", "raw_cluster_id"],
        ascending=[False, False, False, True],
    )

    label_map = {defensive_raw: 4}
    for canonical_id, raw_cluster_id in enumerate(growth_like["raw_cluster_id"].tolist(), start=1):
        label_map[int(raw_cluster_id)] = canonical_id

    expected_ids = raw_cluster_ids.map(label_map).astype(int).rename("cluster_id")
    expected_summary = (
        summary.assign(cluster_id=summary["raw_cluster_id"].map(label_map).astype(int))
        .sort_values("cluster_id")
        .reset_index(drop=True)[
            ["cluster_id", "raw_cluster_id", "ticker_count", "mean_return", "mean_volatility"]
        ]
    )
    return expected_ids, expected_summary


def test_derive_window_cluster_snapshot_defaults_to_four_clusters_and_matches_ward_assignment():
    snapshot = derive_window_cluster_snapshot(WINDOW_RETURNS)
    expected_ids, expected_summary = _expected_snapshot(WINDOW_RETURNS)

    assert snapshot.cluster_ids.index.tolist() == WINDOW_RETURNS.columns.tolist()
    assert snapshot.cluster_ids.equals(expected_ids)
    pd.testing.assert_frame_equal(snapshot.cluster_summary, expected_summary)
    assert set(snapshot.cluster_ids.unique()) == {1, 2, 3, 4}
    assert snapshot.cluster_summary["ticker_count"].sum() == WINDOW_RETURNS.shape[1]


def test_derive_window_cluster_snapshot_rejects_three_asset_window():
    three_asset_window = pd.DataFrame(
        {
            "AAA": [0.01, 0.02, 0.03, 0.02],
            "AAB": [0.01, 0.02, 0.03, 0.02],
            "BBB": [0.02, 0.01, 0.02, 0.01],
        }
    )

    with pytest.raises(ValueError, match="at least 4 assets"):
        derive_window_cluster_snapshot(three_asset_window)


def test_derive_window_cluster_snapshot_rejects_degenerate_flat_window():
    flat_window = pd.DataFrame(
        {
            "AAA": [0.0, 0.0, 0.0, 0.0],
            "AAB": [0.0, 0.0, 0.0, 0.0],
            "BBB": [0.0, 0.0, 0.0, 0.0],
            "BBC": [0.0, 0.0, 0.0, 0.0],
            "CCC": [0.0, 0.0, 0.0, 0.0],
        }
    )

    with pytest.raises(ValueError, match="realized clusters"):
        derive_window_cluster_snapshot(flat_window)


def test_derive_window_cluster_snapshot_rejects_unsupported_cluster_count():
    with pytest.raises(ValueError, match="cluster_count must be 4"):
        derive_window_cluster_snapshot(WINDOW_RETURNS, cluster_count=3)


def test_summarize_aggressive_rebalance_states_reports_pure_and_fallback_counts():
    summary = summarize_aggressive_rebalance_states(
        [
            {"aggressive_state": "pure_feasible", "aggressive_used_fallback": False},
            {"aggressive_state": "fallback_used", "aggressive_used_fallback": True},
            {"aggressive_state": "pure_unavailable", "aggressive_used_fallback": False},
        ]
    )
    assert summary["total_rebalances"] == 3
    assert summary["pure_feasible_rebalances"] == 1
    assert summary["pure_unavailable_rebalances"] == 2
    assert summary["fallback_rebalances"] == 1
    assert round(summary["pure_feasible_ratio"], 6) == round(1 / 3, 6)
