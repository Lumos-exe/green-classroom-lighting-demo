from __future__ import annotations

import numpy as np

from .types import ACTIVITIES, Cell, LightingState, PerceptionState, is_board_front_cell


BASE_BY_SEMANTIC = {
    "student_desk": 0.24,
    "teacher_desk": 0.25,
    "board": 0.20,
    "screen": 0.12,
    "aisle": 0.16,
    "podium": 0.20,
}
OCC_BY_SEMANTIC = {
    "student_desk": 0.18,
    "teacher_desk": 0.16,
    "board": 0.06,
    "screen": 0.04,
    "aisle": 0.16,
    "podium": 0.18,
}
ACTIVITY_GAIN_BY_SEMANTIC = {
    "student_desk": {
        "empty": 0.00,
        "listening": 0.24,
        "writing": 0.68,
        "projection": 0.12,
        "blackboard-writing": 0.10,
        "discussion": 0.22,
        "walking": 0.18,
    },
    "teacher_desk": {
        "empty": 0.00,
        "listening": 0.28,
        "writing": 0.56,
        "projection": 0.08,
        "blackboard-writing": 0.44,
        "discussion": 0.24,
        "walking": 0.22,
    },
    "board": {
        "empty": 0.00,
        "listening": 0.08,
        "writing": 0.08,
        "projection": 0.04,
        "blackboard-writing": 0.50,
        "discussion": 0.04,
        "walking": 0.02,
    },
    "screen": {
        "empty": 0.00,
        "listening": 0.04,
        "writing": 0.04,
        "projection": 0.12,
        "blackboard-writing": 0.02,
        "discussion": 0.04,
        "walking": 0.02,
    },
    "aisle": {
        "empty": 0.00,
        "listening": 0.06,
        "writing": 0.18,
        "projection": 0.04,
        "blackboard-writing": 0.04,
        "discussion": 0.28,
        "walking": 0.30,
    },
    "podium": {
        "empty": 0.00,
        "listening": 0.30,
        "writing": 0.56,
        "projection": 0.06,
        "blackboard-writing": 0.50,
        "discussion": 0.28,
        "walking": 0.30,
    },
}


def estimate_day_light(visual_light: np.ndarray, contribution: np.ndarray, previous_control: np.ndarray) -> np.ndarray:
    artificial = contribution @ previous_control
    return np.maximum(0.0, visual_light - artificial)


def target_demand(cells: list[Cell], perception: PerceptionState) -> tuple[np.ndarray, np.ndarray]:
    """Compute R_t(i) with semantic base, occupancy, activity and board propagation terms."""

    activity_gain = np.array(
        [[ACTIVITY_GAIN_BY_SEMANTIC[cell.label][name] for name in ACTIVITIES] for cell in cells],
        dtype=float,
    )
    local_activity = perception.occupancy * np.sum(perception.activity * activity_gain, axis=1)
    base = np.array([BASE_BY_SEMANTIC[cell.label] for cell in cells], dtype=float)
    occ = np.array([OCC_BY_SEMANTIC[cell.label] for cell in cells], dtype=float) * perception.occupancy
    demand = base + occ + local_activity

    board_idx = [i for i, cell in enumerate(cells) if cell.label == "board"]
    board_front_idx = [i for i, cell in enumerate(cells) if is_board_front_cell(cell)]
    blackboard_col = ACTIVITIES.index("blackboard-writing")
    board_signal = float(perception.activity[board_front_idx, blackboard_col].max()) if board_front_idx else 0.0
    if board_idx:
        demand[board_idx] += board_signal * 0.28

    high_limit = np.ones(len(cells), dtype=float) * 0.92
    screen_idx = [i for i, cell in enumerate(cells) if cell.label == "screen"]
    if screen_idx:
        projection_col = ACTIVITIES.index("projection")
        projection_signal = perception.activity[screen_idx, projection_col].max()
        high_limit[screen_idx] = 0.56 if projection_signal > 0.5 else 0.92
        demand[screen_idx] = np.maximum(demand[screen_idx], 0.48 * projection_signal)
    return np.clip(demand, 0.0, high_limit), high_limit


def build_lighting_state(
    cells: list[Cell],
    contribution: np.ndarray,
    previous_control: np.ndarray,
    perception: PerceptionState,
) -> LightingState:
    day_light = estimate_day_light(perception.visual_light, contribution, previous_control)
    demand, high_limit = target_demand(cells, perception)
    return LightingState(
        current_control=previous_control.copy(),
        day_light=day_light,
        target_demand=demand,
        high_limit=high_limit,
    )
