from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np


Activity = Literal[
    "empty",
    "listening",
    "writing",
    "projection",
    "blackboard-writing",
    "discussion",
    "walking",
]
SurfaceLabel = Literal[
    "student_desk",
    "teacher_desk",
    "board",
    "screen",
    "aisle",
    "podium",
]

ACTIVITIES: tuple[Activity, ...] = (
    "empty",
    "listening",
    "writing",
    "projection",
    "blackboard-writing",
    "discussion",
    "walking",
)


@dataclass(frozen=True)
class Cell:
    """A physical work-surface unit, not an image pixel or lamp."""

    cell_id: str
    center: np.ndarray
    normal: np.ndarray
    label: SurfaceLabel
    visible_cameras: tuple[str, ...]
    rho: float


@dataclass(frozen=True)
class Lamp:
    lamp_id: str
    position: np.ndarray
    group: str


@dataclass(frozen=True)
class CameraFrame:
    camera_id: str
    image: np.ndarray
    intrinsics: np.ndarray
    extrinsics: np.ndarray
    timestamp_s: float


@dataclass(frozen=True)
class PerceptionState:
    """Cell-indexed outputs of the paper's three visual heads."""

    time_s: float
    occupancy: np.ndarray
    activity: np.ndarray
    visual_light: np.ndarray
    feature: np.ndarray


@dataclass(frozen=True)
class LightingState:
    """Cell-indexed lighting state before control optimization."""

    current_control: np.ndarray
    day_light: np.ndarray
    target_demand: np.ndarray
    high_limit: np.ndarray


@dataclass(frozen=True)
class ControlResult:
    control: np.ndarray
    predicted_light: np.ndarray
    objective: float
    solver_name: str
    success: bool
    iterations: int


@dataclass(frozen=True)
class PrototypeData:
    cells: list[Cell]
    lamps: list[Lamp]
    frames: list[CameraFrame]
    contribution: np.ndarray
    previous_control: np.ndarray
    static_background: dict[str, np.ndarray]


def is_board_front_cell(cell: Cell) -> bool:
    """Cells in Omega_board_front: the physical area where board writing occurs."""

    _x, y, _z = cell.center
    return cell.label in ("teacher_desk", "podium") and y <= 1.9
