"""Research prototype for the VGGT-3DGS-BEV lighting-control method.

This package is independent from the Blender animation demo.  It exposes the
paper's data flow with a runnable mock backend and optional adapters for the
official VGGT and 3D Gaussian Splatting repositories.
"""

from .pipeline import run_mock_pipeline, run_pipeline, run_real_pipeline

__all__ = ["run_pipeline", "run_mock_pipeline", "run_real_pipeline"]
