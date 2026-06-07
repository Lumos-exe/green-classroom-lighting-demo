from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import numpy as np

from .calibration import CalibrationExample, mock_calibrate_demand_coefficients
from .demand import build_lighting_state
from .external import BackendConfig, ExternalDependencyError, backend_record, missing_real_prerequisites
from .gaussian_splatting_adapter import GaussianSplattingBackend
from .geometry import discretize_work_surfaces, mock_lamps, mock_vggt_point_maps
from .lighting_matrix import calibrate_contribution_matrix
from .perception import SwinTinyFPNPerception
from .static_3dgs import StaticGaussianScene
from .types import ACTIVITIES, CameraFrame, PrototypeData, is_board_front_cell
from .vggt_adapter import VGGTBackend


def _mock_frames(seed: int = 3) -> tuple[list[CameraFrame], dict[str, np.ndarray]]:
    rng = np.random.default_rng(seed)
    frames = []
    background = {}
    for idx, camera_id in enumerate(("front_camera", "rear_camera", "side_camera")):
        base = np.full((48, 64, 3), 80 + idx * 8, dtype=np.uint8)
        image = np.clip(base + rng.normal(0, 5, base.shape), 0, 255).astype(np.uint8)
        background[camera_id] = base
        frames.append(
            CameraFrame(
                camera_id=camera_id,
                image=image,
                intrinsics=np.eye(3),
                extrinsics=np.eye(4),
                timestamp_s=0.0,
            )
        )
    return frames, background


def prepare_mock_data() -> PrototypeData:
    clouds = mock_vggt_point_maps()
    cells = discretize_work_surfaces(clouds)
    lamps = mock_lamps()
    frames, background = _mock_frames()
    contribution, _terms = calibrate_contribution_matrix(cells, lamps)
    previous_control = np.full(len(lamps), 0.18, dtype=float)
    return PrototypeData(cells, lamps, frames, contribution, previous_control, background)


def _frames_from_image_dir(image_dir: Path) -> tuple[list[CameraFrame], dict[str, np.ndarray]]:
    try:
        from PIL import Image
    except Exception as exc:
        raise ExternalDependencyError("Pillow is required to read real classroom images.") from exc

    frames: list[CameraFrame] = []
    background: dict[str, np.ndarray] = {}
    for path in sorted(image_dir.iterdir()):
        if path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}:
            continue
        image = np.asarray(Image.open(path).convert("RGB"), dtype=np.uint8)
        camera_id = path.stem
        background[camera_id] = image.copy()
        frames.append(
            CameraFrame(
                camera_id=camera_id,
                image=image,
                intrinsics=np.eye(3),
                extrinsics=np.eye(4),
                timestamp_s=0.0,
            )
        )
    if not frames:
        raise ExternalDependencyError(f"No readable images found in {image_dir}.")
    return frames, background


def prepare_real_data(config: BackendConfig) -> tuple[PrototypeData, object]:
    clouds = VGGTBackend(config).semantic_point_clouds()
    cells = discretize_work_surfaces(clouds)
    assert config.image_dir is not None
    frames, background = _frames_from_image_dir(config.image_dir)
    camera_ids = tuple(frame.camera_id for frame in frames)
    cells = [replace(cell, visible_cameras=camera_ids) for cell in cells]
    lamps = mock_lamps()
    contribution, _terms = calibrate_contribution_matrix(cells, lamps)
    previous_control = np.full(len(lamps), 0.18, dtype=float)
    static_scene = GaussianSplattingBackend(config).scene()
    return PrototypeData(cells, lamps, frames, contribution, previous_control, background), static_scene


def _run_from_data(data: PrototypeData, static_scene, scenario: str, backend_info: dict) -> dict:
    visibility_weight = static_scene.visibility_weight(data.cells, data.frames)
    base_reflectance = static_scene.base_reflectance(data.cells)
    dynamic_residual_level = static_scene.dynamic_residual_level(data.frames)
    perception_model = SwinTinyFPNPerception(
        data.cells,
        visibility_weight=visibility_weight,
        base_reflectance=base_reflectance,
    )
    perception = perception_model.infer(
        data.frames,
        scenario=scenario,
        time_s=0.0,
        dynamic_residual_level=dynamic_residual_level,
    )
    lighting_state = build_lighting_state(data.cells, data.contribution, data.previous_control, perception)

    from .controller import solve_control

    control = solve_control(data.cells, data.contribution, lighting_state)
    mock_control_strategy_label = np.clip(control.control * 0.92 + 0.04, 0.0, 1.0)
    calibration = mock_calibrate_demand_coefficients(
        data.cells,
        data.contribution,
        data.previous_control,
        [CalibrationExample(perception=perception, mock_control_strategy_label=mock_control_strategy_label)],
    )
    return {
        "data": data,
        "static_auxiliary": {
            "dynamic_residual_level": dynamic_residual_level,
            "mean_visibility_weight": float(visibility_weight.mean()),
            "mean_base_reflectance": float(base_reflectance.mean()),
        },
        "perception": perception,
        "lighting_state": lighting_state,
        "control": control,
        "calibration": calibration,
        "scenario": scenario,
        "backend": backend_info,
    }


def _default_config(backend: str = "mock") -> BackendConfig:
    return BackendConfig(project_root=Path(__file__).resolve().parents[1], backend=backend)  # type: ignore[arg-type]


def run_mock_pipeline(
    scenario: str = "self_study",
    config: BackendConfig | None = None,
    fallback_reason: str | None = None,
) -> dict:
    config = config or _default_config("mock")
    data = prepare_mock_data()
    static_scene = StaticGaussianScene(data.static_background)
    backend_info = backend_record(
        backend_used="mock",
        config=config,
        fallback_reason=fallback_reason,
        mock_modules_used=[
            "VGGT semantic point maps",
            "3DGS static helper",
            "Swin-Tiny-FPN perception heads",
            "lamp switching experiments",
            "lamp hardware response",
        ],
    )
    return _run_from_data(data, static_scene, scenario, backend_info)


def run_real_pipeline(scenario: str = "self_study", config: BackendConfig | None = None) -> dict:
    config = config or _default_config("real")
    missing = missing_real_prerequisites(config)
    if missing:
        raise ExternalDependencyError("Real backend prerequisites are missing: " + "; ".join(missing))
    data, static_scene = prepare_real_data(config)
    backend_info = backend_record(
        backend_used="real",
        config=config,
        real_modules_enabled=[
            "official VGGT geometry backend",
            "official 3DGS scene adapter",
        ],
        mock_modules_used=[
            "Swin-Tiny-FPN perception heads",
            "lamp contribution calibration observations",
            "lamp hardware response",
        ],
    )
    return _run_from_data(data, static_scene, scenario, backend_info)


def run_pipeline(
    scenario: str = "self_study",
    backend: str = "mock",
    config: BackendConfig | None = None,
) -> dict:
    config = config or _default_config(backend)
    if backend == "mock":
        return run_mock_pipeline(scenario, config=config)
    if backend == "real":
        return run_real_pipeline(scenario, config=config)
    if backend == "auto":
        missing = missing_real_prerequisites(config)
        if missing:
            return run_mock_pipeline(scenario, config=config, fallback_reason="; ".join(missing))
        try:
            return run_real_pipeline(scenario, config=config)
        except ExternalDependencyError as exc:
            return run_mock_pipeline(scenario, config=config, fallback_reason=str(exc))
    raise ValueError(f"Unknown backend: {backend}")


def control_quality_metrics(
    target: np.ndarray,
    high_limit: np.ndarray,
    predicted: np.ndarray,
    control: np.ndarray,
    visual_light: np.ndarray,
) -> dict[str, float]:
    under = np.maximum(0.0, target - predicted)
    over = np.maximum(0.0, predicted - high_limit)
    tolerance = 0.07
    task_mask = target >= 0.35
    if not bool(task_mask.any()):
        task_mask = np.ones_like(target, dtype=bool)
    return {
        "mean_under_light": float(under.mean()),
        "max_under_light": float(under.max()),
        "task_mean_under_light": float(under[task_mask].mean()),
        "task_max_under_light": float(under[task_mask].max()),
        "mean_over_light": float(over.mean()),
        "max_over_light": float(over.max()),
        "mean_energy": float(control.mean()),
        "relative_energy": float(control.mean()),
        "target_satisfaction_rate": float((under <= tolerance).mean()),
        "task_target_satisfaction_rate": float((under[task_mask] <= tolerance).mean()),
        "normalized_target_satisfaction": float((under[task_mask] <= tolerance).mean()),
        "mock_light_estimation_error": float(np.abs(predicted - visual_light).mean()),
    }


def method_alignment_summary() -> dict:
    return {
        "closed_variable_chain": [
            "VGGT semantic point maps or mock VGGT-like semantic point maps",
            "work-surface cells C={cell_i}",
            "3DGS helper outputs: dynamic_residual, visibility_weight, base_reflectance",
            "F_i(t), O_t(i), A_t(i,k), L_t(i)",
            "L_day,t(i), R_t(i), M(i,g)",
            "optimized lamp control vector c_t",
        ],
        "real_backend_interfaces": [
            "facebookresearch/vggt adapter",
            "graphdeco-inria/gaussian-splatting adapter",
        ],
        "default_mock_modules": [
            "VGGT geometry reconstruction",
            "3DGS static scene",
            "Swin-Tiny-FPN perception heads",
            "indirect supervision labels",
            "lamp hardware response",
        ],
        "not_claimed": [
            "real model training",
            "real multi-camera calibration",
            "real illuminance-meter validation",
            "deployable classroom control system",
        ],
        "cell_index_note": "Lamps may be localized by semantic masks, but lamps are not work-surface cells and are stored separately from Cell.",
    }


def _perception_header(prefix: list[str]) -> list[str]:
    return [
        *prefix,
        "O_t_i",
        "L_t_i",
        "F_visibility_weight",
        "F_base_reflectance",
        "F_dynamic_residual",
        "is_board_front",
        *[f"A_t_{name}" for name in ACTIVITIES],
    ]


def _perception_row(prefix: list[str], cell, occ: float, light: float, feature: np.ndarray, act: np.ndarray) -> list:
    return [
        *prefix,
        round(float(occ), 4),
        round(float(light), 4),
        round(float(feature[4]), 4),
        round(float(feature[3]), 4),
        round(float(feature[6]), 4),
        int(is_board_front_cell(cell)),
        *[round(float(v), 4) for v in act],
    ]


def write_outputs(result: dict, out_dir: Path) -> None:
    import csv

    out_dir.mkdir(parents=True, exist_ok=True)
    data = result["data"]
    perception = result["perception"]
    state = result["lighting_state"]
    control = result["control"]

    with (out_dir / "cells.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["cell_id", "x", "y", "z", "normal_x", "normal_y", "normal_z", "label", "visible_cameras", "rho"])
        for cell in data.cells:
            writer.writerow([cell.cell_id, *cell.center.round(4), *cell.normal.round(4), cell.label, "|".join(cell.visible_cameras), round(cell.rho, 4)])

    with (out_dir / "perception_state.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(_perception_header(["cell_id"]))
        for cell, occ, light, feature, act in zip(
            data.cells,
            perception.occupancy,
            perception.visual_light,
            perception.feature,
            perception.activity,
        ):
            writer.writerow(_perception_row([cell.cell_id], cell, occ, light, feature, act))

    with (out_dir / "contribution_matrix.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["cell_id", *[lamp.lamp_id for lamp in data.lamps]])
        for cell, row in zip(data.cells, data.contribution):
            writer.writerow([cell.cell_id, *[round(float(v), 5) for v in row]])

    with (out_dir / "target_demand.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["cell_id", "label", "day_light", "target_demand", "high_limit", "predicted_light", "under_light", "over_light"])
        for cell, day, demand, high, predicted in zip(data.cells, state.day_light, state.target_demand, state.high_limit, control.predicted_light):
            under = max(0.0, float(demand - predicted))
            over = max(0.0, float(predicted - high))
            writer.writerow([cell.cell_id, cell.label, round(float(day), 4), round(float(demand), 4), round(float(high), 4), round(float(predicted), 4), round(under, 4), round(over, 4)])

    with (out_dir / "control_result.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["lamp_id", "x", "y", "z", "group", "c_t"])
        for lamp, value in zip(data.lamps, control.control):
            writer.writerow([lamp.lamp_id, *lamp.position.round(4), lamp.group, round(float(value), 4)])

    summary = {
        "scenario": result["scenario"],
        "cell_count": len(data.cells),
        "lamp_count": len(data.lamps),
        "solver": control.solver_name,
        "solver_success": control.success,
        "iterations": control.iterations,
        "objective": control.objective,
        "mean_control": float(control.control.mean()),
        "max_control": float(control.control.max()),
        "quality": control_quality_metrics(
            state.target_demand,
            state.high_limit,
            control.predicted_light,
            control.control,
            perception.visual_light,
        ),
        "static_auxiliary": result["static_auxiliary"],
        "calibration": result["calibration"],
        "method_alignment": method_alignment_summary(),
        "backend": result.get("backend", {}),
        "solver_success_note": "solver_success only means the optimizer converged; it does not mean every cell demand is fully satisfied.",
        "disclaimer": "Code reproduction framework with real VGGT/3DGS adapters; public demo outputs use mock or fallback modules unless backend_used is real.",
    }
    (out_dir / "run_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")


def write_multi_outputs(results: list[dict], out_dir: Path) -> None:
    """Write one public demo folder covering all representative scenarios."""

    import csv

    if not results:
        raise ValueError("At least one pipeline result is required.")
    out_dir.mkdir(parents=True, exist_ok=True)
    first = results[0]
    data = first["data"]

    with (out_dir / "cells.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["cell_id", "x", "y", "z", "normal_x", "normal_y", "normal_z", "label", "visible_cameras", "rho"])
        for cell in data.cells:
            writer.writerow([cell.cell_id, *cell.center.round(4), *cell.normal.round(4), cell.label, "|".join(cell.visible_cameras), round(cell.rho, 4)])

    with (out_dir / "contribution_matrix.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["cell_id", *[lamp.lamp_id for lamp in data.lamps]])
        for cell, row in zip(data.cells, data.contribution):
            writer.writerow([cell.cell_id, *[round(float(v), 5) for v in row]])

    with (out_dir / "perception_state.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(_perception_header(["scenario", "cell_id"]))
        for result in results:
            perception = result["perception"]
            for cell, occ, light, feature, act in zip(
                result["data"].cells,
                perception.occupancy,
                perception.visual_light,
                perception.feature,
                perception.activity,
            ):
                writer.writerow(_perception_row([result["scenario"], cell.cell_id], cell, occ, light, feature, act))

    with (out_dir / "target_demand.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["scenario", "cell_id", "label", "day_light", "target_demand", "high_limit", "predicted_light", "under_light", "over_light"])
        for result in results:
            state = result["lighting_state"]
            control = result["control"]
            for cell, day, demand, high, predicted in zip(result["data"].cells, state.day_light, state.target_demand, state.high_limit, control.predicted_light):
                under = max(0.0, float(demand - predicted))
                over = max(0.0, float(predicted - high))
                writer.writerow([result["scenario"], cell.cell_id, cell.label, round(float(day), 4), round(float(demand), 4), round(float(high), 4), round(float(predicted), 4), round(under, 4), round(over, 4)])

    with (out_dir / "control_result.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["scenario", "lamp_id", "x", "y", "z", "group", "c_t"])
        for result in results:
            for lamp, value in zip(result["data"].lamps, result["control"].control):
                writer.writerow([result["scenario"], lamp.lamp_id, *lamp.position.round(4), lamp.group, round(float(value), 4)])

    summary = {
        "scenarios": [result["scenario"] for result in results],
        "cell_count": len(data.cells),
        "lamp_count": len(data.lamps),
        "solvers": sorted({result["control"].solver_name for result in results}),
        "all_solver_success": all(result["control"].success for result in results),
        "mean_control_by_scenario": {
            result["scenario"]: float(result["control"].control.mean()) for result in results
        },
        "quality_by_scenario": {
            result["scenario"]: control_quality_metrics(
                result["lighting_state"].target_demand,
                result["lighting_state"].high_limit,
                result["control"].predicted_light,
                result["control"].control,
                result["perception"].visual_light,
            )
            for result in results
        },
        "static_auxiliary_by_scenario": {
            result["scenario"]: result["static_auxiliary"] for result in results
        },
        "calibration": {result["scenario"]: result["calibration"] for result in results},
        "method_alignment": method_alignment_summary(),
        "backend": first.get("backend", {}),
        "solver_success_note": "solver_success only means the optimizer converged; it does not mean every cell demand is fully satisfied.",
        "disclaimer": "Code reproduction framework with real VGGT/3DGS adapters; public demo outputs use mock or fallback modules unless backend_used is real.",
    }
    (out_dir / "run_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
