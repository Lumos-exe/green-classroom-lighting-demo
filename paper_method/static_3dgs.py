from __future__ import annotations

import numpy as np

from .types import CameraFrame, Cell


class StaticGaussianScene:
    """Interface placeholder for the paper's 3DGS static helper.

    The real method trains a static 3D Gaussian scene.  This prototype stores a
    synthetic background and exposes only the helper operations needed by the
    rest of the pipeline.
    """

    def __init__(self, background_by_camera: dict[str, np.ndarray]):
        self.background_by_camera = background_by_camera

    def render_static_reference(self, camera_id: str) -> np.ndarray:
        return self.background_by_camera[camera_id]

    def dynamic_residual(self, frame: CameraFrame) -> np.ndarray:
        """Return dynamic residual used as a mock cue for moving occupants."""

        reference = self.render_static_reference(frame.camera_id)
        return frame.image.astype(float) - reference.astype(float)

    def visible_cells(self, cells: list[Cell], camera_id: str) -> np.ndarray:
        return np.array([camera_id in cell.visible_cameras for cell in cells], dtype=bool)

    def visibility_weight(self, cells: list[Cell], frames: list[CameraFrame]) -> np.ndarray:
        """Return V_i-like multi-camera visibility weights for each cell."""

        camera_ids = {frame.camera_id for frame in frames}
        if not camera_ids:
            return np.zeros(len(cells), dtype=float)
        weights = []
        for cell in cells:
            visible = len(camera_ids.intersection(cell.visible_cameras))
            weights.append(visible / max(1, len(camera_ids)))
        return np.asarray(weights, dtype=float)

    def base_reflectance(self, cells: list[Cell]) -> np.ndarray:
        """Return rho_i, the static base reflectance appearance of each cell."""

        return np.array([cell.rho for cell in cells], dtype=float)

    def dynamic_residual_level(self, frames: list[CameraFrame]) -> float:
        """Compact residual statistic used by the mock perception feature F_i(t)."""

        if not frames:
            return 0.0
        residuals = [np.abs(self.dynamic_residual(frame)).mean() / 255.0 for frame in frames]
        return float(np.mean(residuals))
