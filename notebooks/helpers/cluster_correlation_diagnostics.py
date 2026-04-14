from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd


def build_cluster_correlation_diagnostics(
    corr_matrix: pd.DataFrame,
    cluster_map: Mapping[str, int],
) -> dict[str, object]:
    if corr_matrix.shape[0] != corr_matrix.shape[1]:
        raise ValueError("corr_matrix must be square")

    if corr_matrix.index.tolist() != corr_matrix.columns.tolist():
        raise ValueError(
            "corr_matrix row/column order drifted; "
            "pairwise diagnostics require identical index/column order"
        )

    tickers = corr_matrix.index.tolist()
    missing_cluster_tickers = [ticker for ticker in tickers if ticker not in cluster_map]
    if missing_cluster_tickers:
        raise ValueError(
            "cluster_map is missing tickers required by corr_matrix: "
            f"{missing_cluster_tickers}"
        )

    cluster_ids = sorted({int(cluster_map[ticker]) for ticker in tickers})
    intra_corr: dict[int, list[float]] = {cluster_id: [] for cluster_id in cluster_ids}
    inter_corr: list[float] = []
    corr_values = corr_matrix.values
    n_tickers = len(tickers)

    for i in range(n_tickers):
        for j in range(i + 1, n_tickers):
            left_ticker, right_ticker = tickers[i], tickers[j]
            left_cluster = int(cluster_map[left_ticker])
            right_cluster = int(cluster_map[right_ticker])
            corr_value = float(corr_values[i, j])

            if left_cluster == right_cluster:
                intra_corr[left_cluster].append(corr_value)
            else:
                inter_corr.append(corr_value)

    intra_stats = []
    pooled_intra_corr: list[float] = []
    for cluster_id, values in intra_corr.items():
        arr = np.asarray(values, dtype=float)
        pooled_intra_corr.extend(arr.tolist())
        pair_count_note = "limited pair count" if len(arr) < 5 else ""
        intra_stats.append(
            {
                "cluster_id": cluster_id,
                "n_intra_pairs": int(len(arr)),
                "mean_intra_corr": float(arr.mean()) if arr.size > 0 else np.nan,
                "std_intra_corr": float(arr.std()) if arr.size > 0 else np.nan,
                "min_intra_corr": float(arr.min()) if arr.size > 0 else np.nan,
                "max_intra_corr": float(arr.max()) if arr.size > 0 else np.nan,
                "pair_count_note": pair_count_note,
            }
        )

    intra_stats_df = pd.DataFrame(intra_stats).set_index("cluster_id")
    inter_corr_arr = np.asarray(inter_corr, dtype=float)
    pooled_intra_arr = np.asarray(pooled_intra_corr, dtype=float)

    mean_inter = float(inter_corr_arr.mean()) if inter_corr_arr.size > 0 else np.nan
    mean_intra = float(pooled_intra_arr.mean()) if pooled_intra_arr.size > 0 else np.nan
    if np.isnan(mean_inter) or np.isnan(mean_intra):
        corr_ratio = np.nan
    elif mean_inter == 0:
        corr_ratio = np.inf
    else:
        corr_ratio = float(mean_intra / mean_inter)

    return {
        "intra_stats_df": intra_stats_df,
        "inter_corr": inter_corr_arr,
        "mean_inter": mean_inter,
        "mean_intra": mean_intra,
        "corr_ratio": corr_ratio,
    }
