from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform


@dataclass(frozen=True)
class RollingClusterSnapshot:
    cluster_ids: pd.Series
    cluster_summary: pd.DataFrame


def correlation_to_distance(corr: pd.DataFrame) -> pd.DataFrame:
    ordered = corr.loc[corr.index, corr.index].astype(float)
    values = ordered.to_numpy(copy=True)
    values = np.where(np.isfinite(values), values, 0.0)
    np.fill_diagonal(values, 1.0)
    distance = np.sqrt(np.clip(2.0 * (1.0 - values), 0.0, None))
    np.fill_diagonal(distance, 0.0)
    return pd.DataFrame(distance, index=ordered.index, columns=ordered.columns)


def canonicalize_cluster_profiles(
    window_returns: pd.DataFrame, raw_cluster_ids: pd.Series
) -> tuple[pd.Series, pd.DataFrame]:
    if not raw_cluster_ids.index.equals(window_returns.columns):
        raw_cluster_ids = raw_cluster_ids.reindex(window_returns.columns)
    if raw_cluster_ids.isna().any():
        missing = raw_cluster_ids[raw_cluster_ids.isna()].index.tolist()
        raise ValueError(f"Missing raw cluster ids for tickers: {missing}")
    unique_raw_cluster_count = int(raw_cluster_ids.nunique(dropna=False))
    if unique_raw_cluster_count != 4:
        raise ValueError(
            f"raw_cluster_ids must contain exactly 4 unique raw cluster labels; "
            f"got {unique_raw_cluster_count}"
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
                "ticker_signature": "|".join(map(str, tickers.tolist())),
            }
        )

    summary = pd.DataFrame(rows)

    defensive_raw = int(
        summary.sort_values(
            ["mean_volatility", "mean_return", "ticker_signature"],
            ascending=[True, True, True],
        ).iloc[0]["raw_cluster_id"]
    )

    growth_like = summary[summary["raw_cluster_id"] != defensive_raw].sort_values(
        ["mean_return", "mean_volatility", "ticker_count", "ticker_signature"],
        ascending=[False, False, False, True],
    )

    label_map = {defensive_raw: 4}
    for canonical_id, raw_cluster_id in enumerate(growth_like["raw_cluster_id"].tolist(), start=1):
        label_map[int(raw_cluster_id)] = canonical_id

    canonical_ids = raw_cluster_ids.map(label_map).astype(int).rename("cluster_id")
    canonical_summary = (
        summary.assign(cluster_id=summary["raw_cluster_id"].map(label_map).astype(int))
        .sort_values("cluster_id")
        .reset_index(drop=True)
    )
    return canonical_ids, canonical_summary[
        ["cluster_id", "raw_cluster_id", "ticker_count", "mean_return", "mean_volatility"]
    ]


def derive_window_cluster_snapshot(
    window_returns: pd.DataFrame, *, cluster_count: int = 4
) -> RollingClusterSnapshot:
    if window_returns.empty:
        raise ValueError("window_returns must be non-empty")
    if window_returns.columns.duplicated().any():
        raise ValueError("window_returns columns must be unique")
    if window_returns.shape[1] < 4:
        raise ValueError("window_returns must contain at least 4 assets")
    if cluster_count != 4:
        raise ValueError("cluster_count must be 4 for rolling cluster methodology")

    corr = window_returns.corr()
    distance = correlation_to_distance(corr)
    condensed = squareform(distance.to_numpy(dtype=float), checks=False)
    linkage_matrix = linkage(condensed, method="ward")
    raw_cluster_ids = pd.Series(
        fcluster(linkage_matrix, t=cluster_count, criterion="maxclust"),
        index=window_returns.columns,
        name="raw_cluster_id",
    )
    realized_raw_cluster_count = int(raw_cluster_ids.nunique(dropna=False))
    if realized_raw_cluster_count != 4:
        raise ValueError(
            "derive_window_cluster_snapshot realized clusters must be exactly 4; "
            f"got {realized_raw_cluster_count}"
        )
    cluster_ids, cluster_summary = canonicalize_cluster_profiles(window_returns, raw_cluster_ids)
    return RollingClusterSnapshot(cluster_ids=cluster_ids, cluster_summary=cluster_summary)


def summarize_aggressive_rebalance_states(rebalance_info: list[dict]) -> dict[str, float]:
    total = len(rebalance_info)
    pure_feasible = sum(item.get("aggressive_state") == "pure_feasible" for item in rebalance_info)
    fallback_used = sum(bool(item.get("aggressive_used_fallback")) for item in rebalance_info)
    pure_unavailable = total - pure_feasible
    return {
        "total_rebalances": total,
        "pure_feasible_rebalances": pure_feasible,
        "pure_unavailable_rebalances": pure_unavailable,
        "fallback_rebalances": fallback_used,
        "pure_feasible_ratio": pure_feasible / total if total else math.nan,
    }
