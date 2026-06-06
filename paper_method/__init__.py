"""Research prototype for the VGGT-3DGS-BEV lighting-control method.

This package is independent from the Blender animation demo.  It exposes the
paper's data flow with runnable mock data, but it does not include trained VGGT,
3DGS, Swin-Tiny-FPN models, real camera calibration, or lamp hardware drivers.
"""

from .pipeline import run_mock_pipeline

__all__ = ["run_mock_pipeline"]
