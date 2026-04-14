from __future__ import annotations

import math
from typing import Iterable, Sequence


def build_aggressive_target_shortlist(frontier_returns: Sequence[float], *, decimals: int = 10) -> list[float]:
    cleaned: list[float] = []
    for value in frontier_returns:
        value = float(value)
        if not math.isfinite(value):
            continue
        cleaned.append(round(value, decimals))
    return sorted(dict.fromkeys(cleaned))


def choose_highest_feasible_target(results: Iterable[dict]) -> float | None:
    feasible: list[float] = []
    for item in results:
        if not item.get("feasible") or item.get("solver_status") not in {"optimal", "optimal_inaccurate"}:
            continue
        target_return = float(item["target_return"])
        if not math.isfinite(target_return):
            continue
        feasible.append(target_return)
    return max(feasible) if feasible else None
