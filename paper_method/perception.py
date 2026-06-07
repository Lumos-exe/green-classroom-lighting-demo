from __future__ import annotations

import numpy as np

from .types import ACTIVITIES, CameraFrame, Cell, PerceptionState, is_board_front_cell


class SwinTinyFPNPerception:
    """Paper-shaped perception module with mock heads.

    In the paper this module contains a shared Swin-Tiny-FPN backbone and three
    heads.  Here it produces deterministic cell-indexed outputs so the remaining
    method can be inspected without training data or model weights.
    """

    def __init__(
        self,
        cells: list[Cell],
        visibility_weight: np.ndarray | None = None,
        base_reflectance: np.ndarray | None = None,
    ):
        self.cells = cells
        self.visibility_weight = (
            np.asarray(visibility_weight, dtype=float)
            if visibility_weight is not None
            else np.ones(len(cells), dtype=float)
        )
        self.base_reflectance = (
            np.asarray(base_reflectance, dtype=float)
            if base_reflectance is not None
            else np.array([cell.rho for cell in cells], dtype=float)
        )
        self.activity_to_idx = {activity: idx for idx, activity in enumerate(ACTIVITIES)}

    def fuse_cell_features(self, frames: list[CameraFrame], dynamic_residual_level: float = 0.0) -> np.ndarray:
        """Build F_i(t) from geometry, 3DGS helper cues and frame-level light."""

        frame_level = np.array([frame.image.mean() / 255.0 for frame in frames], dtype=float)
        mean_light = float(frame_level.mean()) if len(frame_level) else 0.35
        feature = np.zeros((len(self.cells), 10), dtype=float)
        for i, cell in enumerate(self.cells):
            x, y, z = cell.center
            semantic_code = (
                ["student_desk", "teacher_desk", "board", "screen", "aisle", "podium"].index(cell.label) / 5.0
            )
            feature[i] = np.array(
                [
                    x / 10.0,
                    y / 14.0,
                    z / 3.0,
                    self.base_reflectance[i],
                    self.visibility_weight[i],
                    mean_light,
                    dynamic_residual_level,
                    semantic_code,
                    1.0 if is_board_front_cell(cell) else 0.0,
                    1.0,
                ]
            )
        return feature

    def infer(
        self,
        frames: list[CameraFrame],
        scenario: str,
        time_s: float = 0.0,
        dynamic_residual_level: float = 0.0,
    ) -> PerceptionState:
        feature = self.fuse_cell_features(frames, dynamic_residual_level=dynamic_residual_level)
        occupancy = np.zeros(len(self.cells), dtype=float)
        activity = np.zeros((len(self.cells), len(ACTIVITIES)), dtype=float)
        visual_light = 0.20 + 0.28 * self.base_reflectance + 0.03 * self.visibility_weight

        for i, cell in enumerate(self.cells):
            x, y, _z = cell.center
            scores = {name: 0.0 for name in ACTIVITIES}
            scores["empty"] = 1.0
            if scenario == "class_writing" and cell.label == "student_desk" and 3.0 <= y <= 13.5:
                scores.update(empty=0.02, listening=0.60, writing=1.50)
            elif scenario == "class_writing" and cell.label in ("teacher_desk", "podium"):
                scores.update(empty=0.04, listening=0.80, writing=0.55)
            elif scenario == "break_discussion" and cell.label == "aisle":
                near_center = np.exp(-((x - 4.9) / 1.8) ** 2 - ((y - 7.2) / 4.0) ** 2)
                scores.update(empty=max(0.10, 1.0 - 0.95 * near_center), walking=0.65 * near_center, discussion=0.55 * near_center)
            elif scenario == "break_discussion" and cell.label == "podium":
                near_front = np.exp(-((x - 4.9) / 2.6) ** 2 - ((y - 1.4) / 1.2) ** 2)
                scores.update(empty=max(0.18, 1.0 - 0.70 * near_front), walking=0.32 * near_front, discussion=0.30 * near_front)
            elif scenario == "projection" and cell.label == "screen":
                scores.update(empty=0.02, projection=0.98)
            elif scenario == "projection" and cell.label == "student_desk" and y > 5.0:
                scores.update(empty=0.05, projection=0.75, listening=0.35)
            elif scenario == "board_writing" and is_board_front_cell(cell):
                scores.update(empty=0.02, **{"blackboard-writing": 0.92})
            elif scenario == "self_study" and cell.label == "student_desk":
                active = (
                    np.exp(-((x - 7.0) / 1.2) ** 2 - ((y - 6.5) / 1.3) ** 2)
                    + np.exp(-((x - 2.2) / 1.2) ** 2 - ((y - 11.5) / 1.5) ** 2)
                )
                if active > 0.25:
                    scores.update(empty=max(0.0, 1.0 - active), writing=min(1.0, active))

            total = sum(scores.values()) or 1.0
            for name, value in scores.items():
                activity[i, self.activity_to_idx[name]] = value / total
            occupancy[i] = min(1.0, 1.0 - activity[i, self.activity_to_idx["empty"]])
            visual_light[i] += 0.08 * occupancy[i]

        return PerceptionState(time_s=time_s, occupancy=occupancy, activity=activity, visual_light=visual_light, feature=feature)
