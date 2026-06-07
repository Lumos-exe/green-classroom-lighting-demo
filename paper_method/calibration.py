from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .controller import solve_control
from .demand import build_lighting_state
from .types import Cell, PerceptionState


@dataclass(frozen=True)
class CalibrationExample:
    perception: PerceptionState
    mock_control_strategy_label: np.ndarray


def control_strategy_loss(
    predicted: np.ndarray,
    target: np.ndarray,
    contribution: np.ndarray,
    theta_regularization: float = 0.0,
) -> tuple[float, dict[str, float]]:
    control_error = np.square(predicted - target).mean()
    light_error = np.square(contribution @ predicted - contribution @ target).mean()
    theta_penalty = float(theta_regularization)
    total = float(control_error + 0.4 * light_error + 0.05 * theta_penalty)
    return total, {
        "control_error": float(control_error),
        "light_error": float(light_error),
        "theta_regularization": theta_penalty,
    }


def mock_calibrate_demand_coefficients(
    cells: list[Cell],
    contribution: np.ndarray,
    previous_control: np.ndarray,
    examples: list[CalibrationExample],
) -> dict[str, float]:
    """Demonstrate indirect calibration with c_t^gt.

    This does not train a neural network.  It reports the control-strategy loss
    that a real differentiable unrolled controller would backpropagate through.
    """

    losses = []
    terms = []
    for example in examples:
        state = build_lighting_state(cells, contribution, previous_control, example.perception)
        result = solve_control(cells, contribution, state)
        loss, term = control_strategy_loss(
            result.control,
            example.mock_control_strategy_label,
            contribution,
            theta_regularization=0.0,
        )
        losses.append(loss)
        terms.append(term)
    return {
        "kind": "mock_indirect_supervision_demo",
        "label_field": "mock_control_strategy_label",
        "examples": float(len(examples)),
        "mean_control_strategy_loss": float(np.mean(losses)) if losses else 0.0,
        "mean_control_error": float(np.mean([term["control_error"] for term in terms])) if terms else 0.0,
        "mean_light_error": float(np.mean([term["light_error"] for term in terms])) if terms else 0.0,
        "mean_theta_regularization": float(np.mean([term["theta_regularization"] for term in terms])) if terms else 0.0,
        "note": "mock report only; labels are synthetic control-strategy examples, not real human annotations or trained coefficients",
    }
