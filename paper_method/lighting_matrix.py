from __future__ import annotations

import numpy as np

from .geometry import geometric_contribution_prior
from .types import Cell, Lamp


def simulate_switching_experiments(cells: list[Cell], lamps: list[Lamp], seed: int = 19) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Synthetic lamp-switching observations for calibrating M(i,g)."""

    rng = np.random.default_rng(seed)
    true_m = geometric_contribution_prior(cells, lamps)
    controls = [np.zeros(len(lamps), dtype=float)]
    controls.extend(np.eye(len(lamps), dtype=float))
    controls.extend(rng.uniform(0.0, 1.0, size=(12, len(lamps))))
    control_matrix = np.vstack(controls)
    background = 0.08 + 0.12 * np.array([cell.rho for cell in cells], dtype=float)
    observed = background[None, :] + control_matrix @ true_m.T
    observed += rng.normal(0.0, 0.01, observed.shape)
    return control_matrix, observed, background


def matrix_regularization_terms(m: np.ndarray, prior: np.ndarray) -> dict[str, float]:
    nonneg = float(np.square(np.minimum(m, 0.0)).mean())
    smooth = float(np.square(np.diff(m, axis=0)).mean()) if len(m) > 1 else 0.0
    sparse = float(np.abs(m).mean())
    geo = float(np.square(m - prior).mean())
    return {"nonnegative": nonneg, "smooth": smooth, "sparse": sparse, "geometry": geo}


def calibrate_contribution_matrix(cells: list[Cell], lamps: list[Lamp]) -> tuple[np.ndarray, dict[str, float]]:
    """Estimate M(i,g) from synthetic switching experiments.

    The closed-form least-squares estimate is used for the runnable prototype;
    the returned regularization terms mirror the paper's full loss.
    """

    controls, observed, background = simulate_switching_experiments(cells, lamps)
    y = observed - background[None, :]
    estimate_g_by_i, *_ = np.linalg.lstsq(controls, y, rcond=None)
    m = np.clip(estimate_g_by_i.T, 0.0, None)
    prior = geometric_contribution_prior(cells, lamps)
    m = 0.85 * m + 0.15 * prior
    m /= max(1e-9, float(m.max()))
    terms = matrix_regularization_terms(m, prior)
    terms["reconstruction"] = float(np.square(controls @ m.T - y).mean())
    return m, terms
