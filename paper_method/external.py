from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


BackendName = Literal["mock", "real", "auto"]


class ExternalDependencyError(RuntimeError):
    """Raised when a requested real research backend is not ready."""


@dataclass(frozen=True)
class BackendConfig:
    """Configuration for switching between mock and real paper-method backends."""

    project_root: Path
    backend: BackendName = "mock"
    image_dir: Path | None = None
    mask_dir: Path | None = None
    vggt_repo: Path | None = None
    vggt_checkpoint: str = "facebook/VGGT-1B"
    gaussian_repo: Path | None = None
    gaussian_scene_dir: Path | None = None
    real_output_dir: Path | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)

    def resolved_vggt_repo(self) -> Path:
        return self.vggt_repo or self.project_root / "third_party" / "vggt"

    def resolved_gaussian_repo(self) -> Path:
        return self.gaussian_repo or self.project_root / "third_party" / "gaussian-splatting"

    def resolved_real_output_dir(self) -> Path:
        return self.real_output_dir or self.project_root / "outputs" / "paper_method_real"


def missing_real_prerequisites(config: BackendConfig) -> list[str]:
    """Return human-readable prerequisites missing for the real backend."""

    missing: list[str] = []
    vggt_repo = config.resolved_vggt_repo()
    gaussian_repo = config.resolved_gaussian_repo()
    if not (vggt_repo / "vggt").exists():
        missing.append(f"VGGT official code not found at {vggt_repo}")
    if not (gaussian_repo / "train.py").exists():
        missing.append(f"3DGS official code not found at {gaussian_repo}")
    if config.image_dir is None or not config.image_dir.exists():
        missing.append("multi-view image directory is required (--image-dir)")
    if config.mask_dir is None or not config.mask_dir.exists():
        missing.append("semantic mask directory is required (--mask-dir)")
    if config.gaussian_scene_dir is None or not config.gaussian_scene_dir.exists():
        missing.append("trained/static 3DGS scene directory is required (--gaussian-scene-dir)")
    return missing


def backend_record(
    *,
    backend_used: str,
    config: BackendConfig,
    fallback_reason: str | None = None,
    real_modules_enabled: list[str] | None = None,
    mock_modules_used: list[str] | None = None,
) -> dict:
    missing = missing_real_prerequisites(config)
    return {
        "backend_used": backend_used,
        "requested_backend": config.backend,
        "external_repos": {
            "vggt": str(config.resolved_vggt_repo()),
            "gaussian_splatting": str(config.resolved_gaussian_repo()),
        },
        "real_modules_enabled": real_modules_enabled or [],
        "mock_modules_used": mock_modules_used or [],
        "missing_prerequisites": missing,
        "fallback_reason": fallback_reason,
        "notes": list(config.notes),
    }
