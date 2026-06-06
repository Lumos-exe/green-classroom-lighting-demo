from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from paper_method.pipeline import run_mock_pipeline, write_multi_outputs, write_outputs

OUT_DIR = ROOT / "outputs" / "paper_method_demo"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the standalone paper-method mock prototype.")
    parser.add_argument(
        "--scenario",
        choices=["all", "class_writing", "break_discussion", "projection", "board_writing", "self_study"],
        default="all",
        help="Synthetic classroom state used by the mock perception heads.",
    )
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.scenario == "all":
        scenarios = ["class_writing", "break_discussion", "projection", "board_writing", "self_study"]
        results = [run_mock_pipeline(scenario=scenario) for scenario in scenarios]
        write_multi_outputs(results, args.out_dir)
    else:
        result = run_mock_pipeline(scenario=args.scenario)
        write_outputs(result, args.out_dir)
    print(f"paper method mock outputs written to {args.out_dir}")


if __name__ == "__main__":
    main()
