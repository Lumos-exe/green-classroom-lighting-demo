from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .types import Cell, Lamp, SurfaceLabel


@dataclass(frozen=True)
class SemanticPointCloud:
    label: SurfaceLabel
    points: np.ndarray


def mock_vggt_point_maps(seed: int = 7) -> list[SemanticPointCloud]:
    """Return synthetic VGGT-like semantic point clouds for a classroom."""

    rng = np.random.default_rng(seed)
    clouds: list[SemanticPointCloud] = []

    def plane_points(label: SurfaceLabel, xs, ys, z, noise=0.015):
        grid = np.array([(x, y, z) for x in xs for y in ys], dtype=float)
        grid += rng.normal(0.0, noise, grid.shape)
        clouds.append(SemanticPointCloud(label, grid))

    plane_points("student_desk", np.linspace(1.2, 8.4, 9), np.linspace(3.0, 13.5, 9), 0.74)
    plane_points("teacher_desk", np.linspace(3.0, 6.8, 6), np.linspace(1.15, 1.85, 3), 0.82)
    plane_points("aisle", np.array([0.65, 4.9, 9.05]), np.linspace(2.0, 13.8, 16), 0.04)
    plane_points("board", np.linspace(2.5, 5.8, 12), np.array([0.12]), 1.55)
    plane_points("screen", np.linspace(6.5, 8.1, 8), np.array([0.11]), 1.75)
    plane_points("podium", np.linspace(2.2, 7.9, 9), np.linspace(0.7, 1.7, 4), 0.18)
    return clouds


def fit_plane_least_squares(points: np.ndarray) -> tuple[np.ndarray, float]:
    """Least-squares plane fit used after RANSAC in the paper."""

    centroid = points.mean(axis=0)
    _, _, vh = np.linalg.svd(points - centroid, full_matrices=False)
    normal = vh[-1]
    normal = normal / max(1e-9, np.linalg.norm(normal))
    offset = -float(normal @ centroid)
    return normal, offset


def ransac_plane(points: np.ndarray, iterations: int = 80, threshold: float = 0.05) -> tuple[np.ndarray, float, np.ndarray]:
    """Small RANSAC implementation for showing the paper's surface fitting step."""

    if len(points) < 3:
        raise ValueError("At least three points are required for plane fitting.")
    rng = np.random.default_rng(11)
    best_mask = np.ones(len(points), dtype=bool)
    best_count = -1
    for _ in range(iterations):
        sample = points[rng.choice(len(points), 3, replace=False)]
        normal = np.cross(sample[1] - sample[0], sample[2] - sample[0])
        norm = np.linalg.norm(normal)
        if norm < 1e-8:
            continue
        normal /= norm
        offset = -float(normal @ sample[0])
        distance = np.abs(points @ normal + offset)
        mask = distance < threshold
        if int(mask.sum()) > best_count:
            best_mask = mask
            best_count = int(mask.sum())
    normal, offset = fit_plane_least_squares(points[best_mask])
    return normal, offset, best_mask


def discretize_work_surfaces(clouds: list[SemanticPointCloud]) -> list[Cell]:
    """Create cell_i units from fitted work-surface geometry."""

    cells: list[Cell] = []
    camera_set = ("front_camera", "rear_camera", "side_camera")
    rho_by_label = {
        "student_desk": 0.62,
        "teacher_desk": 0.58,
        "board": 0.18,
        "screen": 0.72,
        "aisle": 0.42,
        "podium": 0.50,
    }
    for cloud in clouds:
        normal, _offset, mask = ransac_plane(cloud.points)
        clean = cloud.points[mask]
        if cloud.label == "student_desk":
            xs = np.linspace(1.35, 8.25, 6)
            ys = np.linspace(3.2, 13.2, 8)
            centers = [(x, y, float(clean[:, 2].mean())) for y in ys for x in xs]
        elif cloud.label == "aisle":
            centers = [(x, y, 0.04) for x in (0.65, 4.9, 9.05) for y in np.linspace(2.2, 13.4, 8)]
        elif cloud.label == "board":
            centers = [(x, 0.12, 1.55) for x in np.linspace(2.7, 5.6, 4)]
        elif cloud.label == "screen":
            centers = [(x, 0.11, 1.75) for x in np.linspace(6.55, 8.05, 3)]
        elif cloud.label == "teacher_desk":
            centers = [(x, y, float(clean[:, 2].mean())) for x in np.linspace(3.2, 6.6, 3) for y in np.linspace(1.2, 1.8, 2)]
        else:
            centers = [(x, y, float(clean[:, 2].mean())) for x in np.linspace(2.4, 7.6, 4) for y in np.linspace(0.8, 1.6, 2)]
        for idx, center in enumerate(centers):
            cells.append(
                Cell(
                    cell_id=f"{cloud.label}_{idx:03d}",
                    center=np.asarray(center, dtype=float),
                    normal=normal.astype(float),
                    label=cloud.label,
                    visible_cameras=camera_set,
                    rho=rho_by_label[cloud.label],
                )
            )
    return cells


def mock_lamps() -> list[Lamp]:
    """Twenty ceiling lamps plus two front line-light groups.

    The paper's semantic masks may include lamps for localization, but lamps are
    controlled devices rather than work-surface cells.  Keep them separate from
    the Cell index used by O_t(i), A_t(i,k), L_t(i), R_t(i) and M(i,g).
    """

    lamps: list[Lamp] = []
    for row, y in enumerate(np.linspace(2.2, 13.0, 5), start=1):
        for col, x in enumerate(np.linspace(1.4, 8.4, 4), start=1):
            lamps.append(Lamp(f"ceiling_r{row:02d}_c{col:02d}", np.array([x, y, 3.0]), "ceiling"))
    lamps.append(Lamp("front_linear_left", np.array([3.3, 0.8, 2.8]), "front_linear"))
    lamps.append(Lamp("front_linear_right", np.array([6.7, 0.8, 2.8]), "front_linear"))
    return lamps


def geometric_contribution_prior(cells: list[Cell], lamps: list[Lamp]) -> np.ndarray:
    """Distance, incidence and surface-reflectance prior for M(i,g)."""

    m = np.zeros((len(cells), len(lamps)), dtype=float)
    for i, cell in enumerate(cells):
        for g, lamp in enumerate(lamps):
            vector = lamp.position - cell.center
            distance = max(0.5, float(np.linalg.norm(vector)))
            incoming = vector / distance
            incidence = max(0.08, float(cell.normal @ incoming))
            if cell.label in ("board", "screen"):
                incidence = max(0.15, abs(float(cell.normal @ incoming)))
            spread = math.exp(-0.018 * distance * distance)
            m[i, g] = incidence * spread * (0.65 + 0.35 * cell.rho) / (distance**1.25)
    m /= max(1e-9, float(m.max()))
    return m
