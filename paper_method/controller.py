from __future__ import annotations

import numpy as np

from .types import Cell, ControlResult, LightingState


def _objective(
    control: np.ndarray,
    cells: list[Cell],
    contribution: np.ndarray,
    state: LightingState,
    previous: np.ndarray,
) -> float:
    predicted = state.day_light + contribution @ control
    under = np.maximum(0.0, state.target_demand - predicted)
    over = np.maximum(0.0, predicted - state.high_limit)
    task_weight = 1.0 + 15.0 * (state.target_demand >= 0.35).astype(float) + 3.0 * state.target_demand
    over_weight = 1.0 + 12.0 * (state.high_limit < 0.7).astype(float)
    energy = control.mean()
    smooth = np.square(control - previous).mean()
    local_uniformity = 0.0
    for label in ("student_desk", "teacher_desk", "aisle", "board", "screen", "podium"):
        idx = [i for i, cell in enumerate(cells) if cell.label == label and state.target_demand[i] > 0.35]
        if len(idx) > 1:
            local_uniformity += float(np.var(predicted[idx]))
    return float(
        0.006 * energy
        + 520.0 * np.average(np.square(under), weights=task_weight)
        + 130.0 * np.average(np.square(over), weights=over_weight)
        + 0.06 * smooth
        + 0.35 * local_uniformity
    )


def _projected_gradient(
    cells: list[Cell],
    contribution: np.ndarray,
    state: LightingState,
    iterations: int = 220,
    step: float = 0.16,
) -> ControlResult:
    previous = state.current_control.copy()
    control = previous.copy()
    eps = 1e-4
    for _ in range(iterations):
        grad = np.zeros_like(control)
        for g in range(len(control)):
            plus = control.copy()
            minus = control.copy()
            plus[g] = min(1.0, plus[g] + eps)
            minus[g] = max(0.0, minus[g] - eps)
            grad[g] = (
                _objective(plus, cells, contribution, state, previous)
                - _objective(minus, cells, contribution, state, previous)
            ) / max(eps, plus[g] - minus[g])
        control = np.clip(control - step * grad, 0.0, 1.0)
    predicted = state.day_light + contribution @ control
    return ControlResult(control, predicted, _objective(control, cells, contribution, state, previous), "projected-gradient", True, iterations)


def solve_control(cells: list[Cell], contribution: np.ndarray, state: LightingState) -> ControlResult:
    """Solve c_t with L-BFGS-B when SciPy is available, otherwise fallback."""

    previous = state.current_control.copy()
    try:
        from scipy.optimize import minimize
    except Exception:
        return _projected_gradient(cells, contribution, state)

    result = minimize(
        lambda c: _objective(c, cells, contribution, state, previous),
        previous,
        method="L-BFGS-B",
        bounds=[(0.0, 1.0)] * len(previous),
        options={"maxiter": 200, "ftol": 1e-9},
    )
    control = np.clip(result.x, 0.0, 1.0)
    predicted = state.day_light + contribution @ control
    return ControlResult(
        control=control,
        predicted_light=predicted,
        objective=float(result.fun),
        solver_name="L-BFGS-B",
        success=bool(result.success),
        iterations=int(getattr(result, "nit", 0)),
    )
