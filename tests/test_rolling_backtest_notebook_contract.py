import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_PATH = ROOT / "notebooks" / "08_backtest_rolling_markowitz.ipynb"


def _load_notebook_cell_sources() -> list[str]:
    notebook = json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))
    return ["".join(cell.get("source", [])) for cell in notebook["cells"]]


def _load_notebook() -> dict:
    return json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))


def _full_source_text() -> str:
    return "\n\n".join(_load_notebook_cell_sources())


def _cell_containing(fragment: str) -> str:
    for source in _load_notebook_cell_sources():
        if fragment in source:
            return source
    raise AssertionError(f"Could not find notebook cell containing {fragment!r}")


def _slice_between(source: str, start: str, end: str) -> str:
    start_index = source.index(start)
    end_index = source.index(end, start_index)
    return source[start_index:end_index]


def test_notebook_08_uses_notebook_cell_sources_not_raw_ipynb_text():
    cell_sources = _load_notebook_cell_sources()

    assert cell_sources
    assert all(isinstance(source, str) for source in cell_sources)
    assert any("ROLLING_CLUSTER_COUNT = 4" in source for source in cell_sources)


def test_notebook_08_rebuilds_window_clusters_and_uses_them_for_both_optimizers():
    source = _full_source_text()
    walk_forward_source = _cell_containing("for rebalance_number, t in enumerate(rebalance_points, start=1):")

    assert "from rolling_cluster_research import (\n    derive_window_cluster_snapshot,\n    summarize_aggressive_rebalance_states,\n)" in source
    assert "ticker_clusters_enriched.csv" not in source
    assert "ROLLING_CLUSTER_COUNT = 4" in source
    assert "CLUSTER_CAPS_DEFENSIVE = {1: 0.50, 2: 0.40, 3: 0.20, 4: 0.50}" in source
    assert "CLUSTER_CAPS_AGGRESSIVE = {1: 0.60, 2: 0.60, 3: 0.30, 4: 0.25}" in source
    assert "cluster_snapshot = derive_window_cluster_snapshot(window_data, cluster_count=ROLLING_CLUSTER_COUNT)" in walk_forward_source

    match = re.search(
        r"(?P<var>\w+)\s*=\s*cluster_snapshot\.cluster_ids\.reindex\(window_data\.columns\)\.to_numpy\(dtype=int\)",
        walk_forward_source,
    )
    assert match, "Derived rolling cluster ids must be materialized from the window snapshot before optimization"
    cluster_ids_var = match.group("var")

    assert (
        f"result_def = solve_markowitz_defensive(mu_t, Sigma_t, {cluster_ids_var}, CLUSTER_CAPS_DEFENSIVE)"
        in walk_forward_source
    )
    assert (
        f"result_agg = solve_markowitz_aggressive(mu_t, Sigma_t, {cluster_ids_var}, CLUSTER_CAPS_AGGRESSIVE, target_daily_return)"
        in walk_forward_source
    )


def test_notebook_08_preserves_pure_hybrid_split_semantics_and_diagnostics():
    source = _full_source_text()
    walk_forward_source = _cell_containing("aggressive_used_fallback = False")
    returns_source = _cell_containing("ret_agg_pure = pd.Series(rolling_ret_agg_pure")

    assert "rolling_ret_agg_pure = []" in walk_forward_source
    assert "rolling_ret_agg_hybrid = []" in walk_forward_source
    assert 'aggressive_state = "fallback_used"' in walk_forward_source
    assert 'aggressive_state = "pure_feasible"' in walk_forward_source
    assert "aggressive_used_fallback = True" in walk_forward_source
    assert "final_w_agg_pure = np.full(len(" in walk_forward_source
    assert "ret_agg_pure_period = np.full(len(future_simple), np.nan, dtype=float)" in walk_forward_source
    assert "if aggressive_state == \"pure_feasible\":" in walk_forward_source
    assert "build_aggressive_fallback(cluster_ids_t, CLUSTER_CAPS_AGGRESSIVE)" in walk_forward_source
    assert "if final_feasible_agg:" in walk_forward_source
    assert "ret_agg_hybrid_period = future_simple.to_numpy() @ final_w_agg_hybrid" in walk_forward_source
    assert "ret_agg_hybrid_period = np.full(len(future_simple), np.nan, dtype=float)" in walk_forward_source
    assert "\"aggressive_state\": aggressive_state" in walk_forward_source
    assert "\"aggressive_used_fallback\": aggressive_used_fallback" in walk_forward_source

    assert "ret_agg_pure = pd.Series(rolling_ret_agg_pure, index=rolling_dates, name=\"Rolling_Aggressive_Pure\")" in returns_source
    assert "ret_agg_hybrid = pd.Series(rolling_ret_agg_hybrid, index=rolling_dates, name=\"Rolling_Aggressive_Hybrid\")" in returns_source
    assert "pure_active_oos_days = int(ret_agg_pure.notna().sum())" in returns_source
    assert "pure_coverage_ratio = pure_active_oos_days / len(ret_agg_pure) if len(ret_agg_pure) else np.nan" in returns_source
    assert "hybrid_active_oos_days = int(ret_agg_hybrid.notna().sum())" in returns_source
    assert "hybrid_coverage_ratio = hybrid_active_oos_days / len(ret_agg_hybrid) if len(ret_agg_hybrid) else np.nan" in returns_source
    assert "Rolling Aggressive (Pure) active OOS days" in source
    assert "Rolling Aggressive Hybrid active OOS days" in source
    assert "Aggressive fallback rebalances (Hybrid path)" in source
    assert "summarize_aggressive_rebalance_states(rebalance_info)" in source


def test_notebook_08_keeps_gmv_and_benchmark_outputs_and_avoids_ambiguous_aggressive_label():
    source = _full_source_text()
    notebook = _load_notebook()
    comparison_cell = _cell_containing("comparison = pd.DataFrame(")
    metrics_chart_cell = _cell_containing("strategy_colors = {")
    equity_plot_source = _cell_containing("# Equity curves")
    drawdown_plot_source = _cell_containing("# Drawdown curves")
    equity_curve_source = _cell_containing('label="Rolling Aggressive (Pure)"')
    drawdown_source = _cell_containing('label="Rolling Aggressive Hybrid"')
    diagnostics_source = _cell_containing("Rolling Aggressive (Pure) active OOS days")
    summary_cell = _cell_containing("Notebook 08 role:")

    comparison_source = _slice_between(comparison_cell, "comparison_data = {", 'print("Rebalance quality summary:")')
    metrics_chart_source = _slice_between(metrics_chart_cell, "strategies = list(comparison.columns)", "metric_plot_map = [")
    summary_source = _slice_between(summary_cell, 'print("Notebook 08 role:")', 'print("Feasibility and fallback reporting:")')
    diagnostics_summary_source = _slice_between(
        summary_cell,
        'print("Feasibility and fallback reporting:")',
        'print("Methodological note:")',
    )
    ranking_source = _slice_between(
        summary_cell,
        'best_sharpe_strategy = comparison.loc["Sharpe Ratio (Rf=0)"].idxmax()',
        'print("Notebook outputs:")',
    )

    assert "Rolling Defensive" in source
    assert "Equal-Weight Benchmark" in source
    assert "metrics_def = calculate_metrics(ret_def)" in source
    assert "metrics_bench = calculate_metrics(ret_bench)" in source
    assert "w_eq = np.ones(returns.shape[1], dtype=float) / returns.shape[1]" in source
    assert "strategies = list(comparison.columns)" in metrics_chart_source
    assert "strategy_colors = {" in metrics_chart_source
    assert "colors = [strategy_colors[strategy] for strategy in strategies]" in metrics_chart_source
    assert 'strategies = ["Equal-Weight Benchmark", "Rolling Defensive", "Rolling Aggressive Hybrid"]' not in metrics_chart_source
    assert 'pure_nav_plot = metrics_agg_pure["NAV"].reindex(ret_def.index)' in equity_plot_source
    assert 'hybrid_nav_plot = metrics_agg_hybrid["NAV"].reindex(ret_def.index)' in equity_plot_source
    assert 'pure_drawdown_plot = metrics_agg_pure["Drawdown"].reindex(ret_def.index)' in drawdown_plot_source
    assert 'hybrid_drawdown_plot = metrics_agg_hybrid["Drawdown"].reindex(ret_def.index)' in drawdown_plot_source
    assert 'metrics_agg_pure["NAV"].index' not in equity_plot_source
    assert 'metrics_agg_hybrid["NAV"].index' not in equity_plot_source
    assert 'metrics_agg_pure["Drawdown"].index' not in drawdown_plot_source
    assert 'metrics_agg_hybrid["Drawdown"].index' not in drawdown_plot_source
    assert "hybrid_included_in_main_comparison = np.isclose(hybrid_coverage_ratio, 1.0)" in comparison_source
    assert "if hybrid_included_in_main_comparison:" in comparison_source
    assert '"Rolling Aggressive Hybrid"] = [' in comparison_source
    assert "Rolling Aggressive Hybrid is excluded from the main like-for-like comparison because coverage is incomplete." in comparison_source
    assert '"Rolling Aggressive (Pure)"' not in metrics_chart_source
    assert "Rolling Aggressive Hybrid" in metrics_chart_source
    assert 'label="Rolling Aggressive (Pure)"' in equity_curve_source
    assert 'label="Rolling Aggressive Hybrid"' in equity_curve_source
    assert 'label="Rolling Aggressive (Pure)"' in drawdown_source
    assert 'label="Rolling Aggressive Hybrid"' in drawdown_source
    assert "Rolling Aggressive (Pure)" in diagnostics_source
    assert "Rolling Aggressive (Pure) active OOS days" in diagnostics_summary_source
    assert "Rolling Aggressive Hybrid is reported separately as a coverage-aware diagnostic because its OOS coverage is incomplete" in summary_source
    assert "Rolling Aggressive Hybrid is not included in the main comparison/ranking block because coverage is incomplete" in summary_source
    assert "Rolling Aggressive (Pure)" not in summary_source
    assert "Rolling Aggressive (Pure)" not in ranking_source
    assert "if not hybrid_included_in_main_comparison:" in ranking_source
    assert "Rolling Aggressive Hybrid is excluded from the main ranking when coverage is incomplete." in ranking_source
    assert 'label="Rolling Aggressive"' not in source
    assert '"Rolling Aggressive": [' not in source
    assert 'print(f"Rolling Aggressive length:' not in source

    code_cells = [cell for cell in notebook["cells"] if cell.get("cell_type") == "code"]
    assert code_cells
    assert all(cell.get("execution_count") is None for cell in code_cells)
    assert all(cell.get("outputs") == [] for cell in code_cells)


def test_notebook_08_drawdown_chart_uses_lighter_fill_opacity():
    drawdown_source = _cell_containing("# Drawdown curves")

    assert 'ax.fill_between(metrics_def["Drawdown"].index, metrics_def["Drawdown"].values * 100, 0, alpha=0.08, color="steelblue")' in drawdown_source
    assert 'ax.fill_between(pure_drawdown_plot.index, pure_drawdown_plot.values * 100, 0, alpha=0.06, color="darkorange")' in drawdown_source
    assert 'ax.fill_between(hybrid_drawdown_plot.index, hybrid_drawdown_plot.values * 100, 0, alpha=0.04, color="firebrick")' in drawdown_source
