from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

from .external import BackendConfig, ExternalDependencyError
from .geometry import SemanticPointCloud
from .types import SurfaceLabel


SURFACE_LABELS: tuple[SurfaceLabel, ...] = (
    "student_desk",
    "teacher_desk",
    "board",
    "screen",
    "aisle",
    "podium",
)


class VGGTBackend:
    """Adapter for the official facebookresearch/vggt implementation.

    The adapter keeps the project code independent from VGGT at import time.
    It loads the official package only when the real backend is requested.
    """

    def __init__(self, config: BackendConfig):
        self.config = config
        self.repo = config.resolved_vggt_repo()

    def validate(self) -> None:
        if not (self.repo / "vggt").exists():
            raise ExternalDependencyError(
                f"VGGT code is missing at {self.repo}. Run scripts/install_paper_method_repos.sh first."
            )
        if self.config.image_dir is None or not self.config.image_dir.exists():
            raise ExternalDependencyError("Real VGGT backend requires --image-dir with classroom images.")
        if self.config.mask_dir is None or not self.config.mask_dir.exists():
            raise ExternalDependencyError("Real VGGT backend requires --mask-dir with semantic masks.")

    def image_paths(self) -> list[Path]:
        assert self.config.image_dir is not None
        paths = sorted(
            p for p in self.config.image_dir.iterdir()
            if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
        )
        if not paths:
            raise ExternalDependencyError(f"No images found in {self.config.image_dir}.")
        return paths

    def infer_predictions(self) -> dict:
        """Run VGGT and return the raw prediction dictionary.

        This follows the public VGGT API shape.  The exact prediction keys may
        change upstream, so downstream extraction checks several common aliases
        and reports available keys when conversion is not possible.
        """

        self.validate()
        sys.path.insert(0, str(self.repo))
        try:
            import torch
            from vggt.models.vggt import VGGT
            from vggt.utils.load_fn import load_and_preprocess_images
        except Exception as exc:
            raise ExternalDependencyError(
                "VGGT Python dependencies are not importable. Install the official VGGT requirements first."
            ) from exc

        device = "cuda" if torch.cuda.is_available() else "cpu"
        image_names = [str(path) for path in self.image_paths()]
        try:
            model = VGGT.from_pretrained(self.config.vggt_checkpoint).to(device)
            model.eval()
            images = load_and_preprocess_images(image_names).to(device)
            with torch.no_grad():
                if device == "cuda":
                    dtype = torch.bfloat16 if torch.cuda.get_device_capability()[0] >= 8 else torch.float16
                    with torch.cuda.amp.autocast(dtype=dtype):
                        predictions = model(images)
                else:
                    predictions = model(images)
        except Exception as exc:
            raise ExternalDependencyError(
                "VGGT inference failed. Check checkpoint access, image format and CUDA/PyTorch compatibility."
            ) from exc
        return {key: self._to_numpy(value) for key, value in dict(predictions).items()}

    def semantic_point_clouds(self) -> list[SemanticPointCloud]:
        """Lift semantic masks to 3D point clouds using VGGT point-map output."""

        predictions = self.infer_predictions()
        point_map = self._pick_point_map(predictions)
        if point_map.ndim == 5:
            point_map = point_map[0]
        if point_map.ndim != 4 or point_map.shape[-1] != 3:
            raise ExternalDependencyError(
                f"Unsupported VGGT point-map shape {point_map.shape}; expected [views,H,W,3]."
            )

        clouds: list[SemanticPointCloud] = []
        image_paths = self.image_paths()
        for label in SURFACE_LABELS:
            points_for_label = []
            for view_idx, image_path in enumerate(image_paths[: point_map.shape[0]]):
                mask = self._load_mask(label, image_path.stem)
                if mask is None:
                    continue
                mask = self._resize_nearest(mask, point_map.shape[1:3])
                points = point_map[view_idx][mask > 0.5]
                if len(points) > 2500:
                    step = max(1, len(points) // 2500)
                    points = points[::step]
                points_for_label.append(points)
            if points_for_label:
                merged = np.concatenate(points_for_label, axis=0)
                if len(merged) >= 3:
                    clouds.append(SemanticPointCloud(label, merged.astype(float)))
        if not clouds:
            raise ExternalDependencyError(
                "No semantic point clouds were produced. Check mask layout: mask_dir/<label>/<image_stem>.npy or .png."
            )
        return clouds

    def _load_mask(self, label: SurfaceLabel, image_stem: str) -> np.ndarray | None:
        assert self.config.mask_dir is not None
        base = self.config.mask_dir / label / image_stem
        if (base.with_suffix(".npy")).exists():
            return np.load(base.with_suffix(".npy")).astype(float)
        png = base.with_suffix(".png")
        if png.exists():
            try:
                from PIL import Image
            except Exception as exc:
                raise ExternalDependencyError("Pillow is required to read PNG semantic masks.") from exc
            return np.asarray(Image.open(png).convert("L"), dtype=float) / 255.0
        return None

    @staticmethod
    def _pick_point_map(predictions: dict) -> np.ndarray:
        for key in ("world_points", "point_map", "point_maps", "points3D", "points"):
            if key in predictions:
                return np.asarray(predictions[key])
        keys = ", ".join(sorted(predictions))
        raise ExternalDependencyError(f"VGGT predictions do not contain a point-map key. Available keys: {keys}")

    @staticmethod
    def _resize_nearest(mask: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
        if mask.shape[:2] == shape:
            return mask
        y_idx = np.linspace(0, mask.shape[0] - 1, shape[0]).round().astype(int)
        x_idx = np.linspace(0, mask.shape[1] - 1, shape[1]).round().astype(int)
        return mask[np.ix_(y_idx, x_idx)]

    @staticmethod
    def _to_numpy(value):
        if hasattr(value, "detach"):
            return value.detach().cpu().numpy()
        if isinstance(value, (list, tuple)):
            return np.asarray([VGGTBackend._to_numpy(item) for item in value], dtype=object)
        return value
