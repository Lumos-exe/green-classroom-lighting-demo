from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from paper_method.external import BackendConfig, ExternalDependencyError
from paper_method.pipeline import run_pipeline, write_multi_outputs, write_outputs

OUT_DIR = ROOT / "outputs" / "paper_method_demo"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the standalone paper-method reproduction framework.")
    parser.add_argument(
        "--backend",
        choices=["mock", "real", "auto"],
        default="mock",
        help="mock runs the synthetic demo; real requires official VGGT/3DGS code and real inputs; auto falls back to mock.",
    )
    parser.add_argument(
        "--scenario",
        choices=["all", "class_writing", "break_discussion", "projection", "board_writing", "self_study"],
        default="all",
        help="Classroom state used by the cell-level perception/control pipeline.",
    )
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--image-dir", type=Path, help="Real backend: multi-view classroom image directory.")
    parser.add_argument("--mask-dir", type=Path, help="Real backend: semantic masks arranged as mask_dir/<label>/<image_stem>.npy or .png.")
    parser.add_argument("--vggt-repo", type=Path, help="Real backend: path to facebookresearch/vggt.")
    parser.add_argument("--vggt-checkpoint", default="facebook/VGGT-1B", help="VGGT checkpoint id or local checkpoint path.")
    parser.add_argument("--gaussian-repo", type=Path, help="Real backend: path to graphdeco-inria/gaussian-splatting.")
    parser.add_argument("--gaussian-scene-dir", type=Path, help="Real backend: trained/static 3DGS scene directory.")
    parser.add_argument("--real-output-dir", type=Path, help="Real backend: folder for intermediate geometry/3DGS outputs.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = BackendConfig(
        project_root=ROOT,
        backend=args.backend,
        image_dir=args.image_dir,
        mask_dir=args.mask_dir,
        vggt_repo=args.vggt_repo,
        vggt_checkpoint=args.vggt_checkpoint,
        gaussian_repo=args.gaussian_repo,
        gaussian_scene_dir=args.gaussian_scene_dir,
        real_output_dir=args.real_output_dir,
    )
    if args.scenario == "all":
        scenarios = ["class_writing", "break_discussion", "projection", "board_writing", "self_study"]
        results = [run_pipeline(scenario=scenario, backend=args.backend, config=config) for scenario in scenarios]
        write_multi_outputs(results, args.out_dir)
    else:
        result = run_pipeline(scenario=args.scenario, backend=args.backend, config=config)
        write_outputs(result, args.out_dir)
    print(f"paper method outputs written to {args.out_dir} using backend={args.backend}")


if __name__ == "__main__":
    try:
        main()
    except ExternalDependencyError as exc:
        print(f"paper method real backend is not ready: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
