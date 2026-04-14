from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
HELPERS_DIR = ROOT / "notebooks" / "helpers"
if str(HELPERS_DIR) not in sys.path:
    sys.path.insert(0, str(HELPERS_DIR))

from static_aggressive_targets import build_aggressive_target_shortlist, choose_highest_feasible_target


def test_build_aggressive_target_shortlist_returns_sorted_unique_values():
    shortlist = build_aggressive_target_shortlist([0.0008, 0.0010, 0.0008, float("nan"), 0.0012])
    assert shortlist == [0.0008, 0.001, 0.0012]


def test_choose_highest_feasible_target_returns_highest_feasible_value():
    target = choose_highest_feasible_target([
        {"target_return": 0.0007, "feasible": True, "solver_status": "optimal"},
        {"target_return": 0.0009, "feasible": False, "solver_status": "optimal_inaccurate"},
        {"target_return": 0.0008, "feasible": True, "solver_status": "optimal_inaccurate"},
    ])
    assert target == 0.0008


def test_choose_highest_feasible_target_ignores_non_finite_values():
    target = choose_highest_feasible_target([
        {"target_return": float("nan"), "feasible": True, "solver_status": "optimal"},
        {"target_return": float("inf"), "feasible": True, "solver_status": "optimal_inaccurate"},
        {"target_return": 0.0006, "feasible": True, "solver_status": "optimal"},
    ])
    assert target == 0.0006


def test_choose_highest_feasible_target_returns_none_when_nothing_is_feasible():
    target = choose_highest_feasible_target([
        {"target_return": 0.0007, "feasible": False, "solver_status": "optimal"},
        {"target_return": 0.0008, "feasible": False, "solver_status": "infeasible"},
    ])
    assert target is None
