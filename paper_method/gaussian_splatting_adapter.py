from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np

from .external import BackendConfig, ExternalDependencyError
from .types import CameraFrame, Cell


class RealGaussianScene:
    """3DGS helper backed by an existing official gaussian-splatting scene."""

    def __init__(self, scene_dir: Path):
        self.scene_dir = scene_dir

    def render_static_reference(self, camera_id: str) -> np.ndarray:
        candidates = [
            self.scene_dir / "renders" / f"{camera_id}.png",
            self.scene_dir / "render" / f"{camera_id}.png",
            self.scene_dir / "static_reference" / f"{camera_id}.png",
        ]
        for path in candidates:
            if path.exists():
                try:
                    from PIL import Image
                except Exception as exc:
                    raise ExternalDependencyError("Pillow is required to read 3DGS reference renders.") from exc
                return np.asarray(Image.open(path).convert("RGB"), dtype=np.uint8)
        raise ExternalDependencyError(
            f"No rendered static reference found for {camera_id}. Expected one of: "
            + ", ".join(str(path) for path in candidates)
        )

    def dynamic_residual(self, frame: CameraFrame) -> np.ndarray:
        reference = self.render_static_reference(frame.camera_id)
        if reference.shape != frame.image.shape:
            reference = self._resize_nearest(reference, frame.image.shape[:2])
        return frame.image.astype(float) - reference.astype(float)

    def visibility_weight(self, cells: list[Cell], frames: list[CameraFrame]) -> np.ndarray:
        """Use cell camera visibility as the real-backend fallback visibility cue.

        A fully rendered visibility pass can replace this method once a project
        has exported depth/alpha maps from the official 3DGS renderer.
        """

        camera_ids = {frame.camera_id for frame in frames}
        return np.asarray(
            [len(camera_ids.intersection(cell.visible_cameras)) / max(1, len(camera_ids)) for cell in cells],
            dtype=float,
        )

    def base_reflectance(self, cells: list[Cell]) -> np.ndarray:
        return np.asarray([cell.rho for cell in cells], dtype=float)

    def dynamic_residual_level(self, frames: list[CameraFrame]) -> float:
        if not frames:
            return 0.0
        residuals = [np.abs(self.dynamic_residual(frame)).mean() / 255.0 for frame in frames]
        return float(np.mean(residuals))

    @staticmethod
    def _resize_nearest(image: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
        y_idx = np.linspace(0, image.shape[0] - 1, shape[0]).round().astype(int)
        x_idx = np.linspace(0, image.shape[1] - 1, shape[1]).round().astype(int)
        return image[np.ix_(y_idx, x_idx)]


class GaussianSplattingBackend:
    """Adapter for graphdeco-inria/gaussian-splatting."""

    def __init__(self, config: BackendConfig):
        self.config = config
        self.repo = config.resolved_gaussian_repo()

    def validate(self) -> None:
        if not (self.repo / "train.py").exists():
            raise ExternalDependencyError(
                f"3DGS code is missing at {self.repo}. Run scripts/install_paper_method_repos.sh first."
            )
        if self.config.gaussian_scene_dir is None or not self.config.gaussian_scene_dir.exists():
            raise ExternalDependencyError("Real 3DGS backend requires --gaussian-scene-dir with a trained/static scene.")

    def scene(self) -> RealGaussianScene:
        self.validate()
        assert self.config.gaussian_scene_dir is not None
        return RealGaussianScene(self.config.gaussian_scene_dir)

    def train_command(self, source_scene_dir: Path, model_dir: Path | None = None) -> list[str]:
        model_dir = model_dir or self.config.resolved_real_output_dir() / "3dgs_model"
        return [
            "python3",
            str(self.repo / "train.py"),
            "-s",
            str(source_scene_dir),
            "-m",
            str(model_dir),
        ]

    def render_command(self, model_dir: Path) -> list[str]:
        return [
            "python3",
            str(self.repo / "render.py"),
            "-m",
            str(model_dir),
        ]

    def run_training(self, source_scene_dir: Path, model_dir: Path | None = None) -> None:
        command = self.train_command(source_scene_dir, model_dir)
        subprocess.run(command, cwd=self.repo, check=True)
