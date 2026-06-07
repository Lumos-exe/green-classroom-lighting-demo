from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import PowerNorm


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "outputs" / "paper_method_demo"
FIG_DIR = ROOT / "paper" / "figures"

LABEL_COLORS = {
    "student_desk": "#4C78A8",
    "teacher_desk": "#72B7B2",
    "board": "#F2CF5B",
    "screen": "#B279A2",
    "aisle": "#59A14F",
    "podium": "#E15759",
}
SCENARIO_LABELS = {
    "class_writing": "class writing",
    "break_discussion": "break discussion",
    "projection": "projection",
    "board_writing": "board writing",
    "self_study": "self study",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def ensure_dirs() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)


def setup_style() -> None:
    plt.rcParams.update(
        {
            "figure.dpi": 150,
            "savefig.dpi": 300,
            "font.size": 9,
            "axes.titlesize": 11,
            "axes.labelsize": 9,
            "legend.fontsize": 8,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "axes.edgecolor": "#333333",
            "axes.linewidth": 0.8,
            "grid.color": "#CBD5E1",
            "grid.alpha": 0.36,
        }
    )


def save(fig: plt.Figure, name: str) -> None:
    fig.savefig(FIG_DIR / name, bbox_inches="tight")
    plt.close(fig)


def plot_method_flow() -> None:
    fig, ax = plt.subplots(figsize=(12, 4.8))
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    rows = [
        (
            "Offline preparation",
            0.68,
            "#E9F2FA",
            [
                ("Empty classroom", "multi-view images"),
                ("VGGT + masks", "point maps and\nsemantic surfaces"),
                ("Work-surface\ncells", "$X_i,n_i,\\ell_i,\\mathcal{V}_i,\\rho_i$"),
                ("3DGS helper", "residual, visibility,\nreflectance"),
                ("Lamp matrix", "$M(i,g)$ calibration"),
            ],
        ),
        (
            "Online control",
            0.30,
            "#EEF6EF",
            [
                ("Live images", "$I_t^1,\\ldots,I_t^N$"),
                ("Cell feature", "$F_i(t)$"),
                ("Visual heads", "$O_t(i),A_t(i,k),L_t(i)$"),
                ("Demand", "$L_{day,t}(i),R_t(i)$"),
                ("Optimization", "$c_t$"),
            ],
        ),
    ]
    x_positions = np.linspace(0.10, 0.90, 5)
    for row_title, y, fill, steps in rows:
        ax.text(0.50, y + 0.155, row_title, ha="center", va="center", weight="bold", color="#1F2933", fontsize=10.5)
        ax.plot([0.08, 0.92], [y, y], color="#A7B1BD", lw=0.9, zorder=0)
        for idx, ((title, subtitle), x) in enumerate(zip(steps, x_positions)):
            box_w = 0.145
            box_h = 0.18
            rect = plt.Rectangle(
                (x - box_w / 2, y - box_h / 2),
                box_w,
                box_h,
                fc=fill,
                ec="#2E4057",
                lw=1.1,
                zorder=2,
            )
            ax.add_patch(rect)
            ax.text(x, y + 0.038, title, ha="center", va="center", weight="bold", color="#1F2933", fontsize=8.0)
            ax.text(x, y - 0.044, subtitle, ha="center", va="center", color="#364152", fontsize=7.4)
            if idx < len(steps) - 1:
                ax.annotate(
                    "",
                    xy=(x_positions[idx + 1] - 0.081, y),
                    xytext=(x + 0.081, y),
                    arrowprops=dict(arrowstyle="->", lw=1.25, color="#2E4057"),
                    zorder=3,
                )
    ax.annotate(
        "",
        xy=(0.90, 0.405),
        xytext=(0.90, 0.595),
        arrowprops=dict(arrowstyle="->", lw=1.2, color="#596B7A", linestyle="--"),
    )
    ax.text(0.5, 0.08, "Unified work-surface cells connect visual perception, demand generation and lamp control.", ha="center", color="#52606D")
    save(fig, "method_flow.png")


def plot_cell_distribution(cells: list[dict[str, str]]) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11.6, 4.5), gridspec_kw={"width_ratios": [1.22, 1.02]})
    fig.subplots_adjust(wspace=0.30)
    ax = axes[0]
    for label, color in LABEL_COLORS.items():
        pts = [(float(row["x"]), float(row["y"])) for row in cells if row["label"] == label]
        if not pts:
            continue
        x, y = np.array(pts).T
        ax.scatter(x, y, s=30, label=label.replace("_", " "), color=color, edgecolor="white", linewidth=0.35)
    ax.set_title("Work-surface cell layout")
    ax.set_xlabel("room x / m")
    ax.set_ylabel("room y / m")
    ax.set_xlim(0, 10)
    ax.set_ylim(14.5, 0)
    ax.grid(True)
    ax.legend(ncol=3, loc="lower center", bbox_to_anchor=(0.5, -0.33), frameon=False, columnspacing=1.0, handletextpad=0.35)

    counts = Counter(row["label"] for row in cells)
    labels = list(LABEL_COLORS)
    values = [counts[label] for label in labels]
    short_labels = ["student desk", "teacher desk", "board", "screen", "aisle", "podium"]
    axes[1].barh(short_labels, values, color=[LABEL_COLORS[label] for label in labels])
    axes[1].set_title("Cell count by semantic surface")
    axes[1].set_xlabel("number of cells")
    axes[1].tick_params(axis="y", pad=3)
    axes[1].grid(axis="x")
    save(fig, "cell_semantic_distribution.png")


def plot_contribution_matrix(rows: list[dict[str, str]]) -> None:
    lamp_names = [name for name in rows[0] if name != "cell_id"]
    matrix = np.array([[float(row[name]) for name in lamp_names] for row in rows], dtype=float)
    fig, ax = plt.subplots(figsize=(12, 5.0))
    display_vmax = max(1e-9, float(np.quantile(matrix, 0.985)))
    im = ax.imshow(matrix, aspect="auto", cmap="magma", norm=PowerNorm(gamma=0.45, vmin=0, vmax=display_vmax))
    ax.set_title("Calibrated lamp contribution matrix $M(i,g)$")
    ax.set_xlabel("lamp group g")
    ax.set_ylabel("work-surface cell i")
    step = max(1, len(lamp_names) // 8)
    ax.set_xticks(range(0, len(lamp_names), step), [name.replace("ceiling_", "c_").replace("front_linear_", "linear_") for name in lamp_names[::step]], rotation=35, ha="right")
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("normalized contribution, power-scaled")
    save(fig, "contribution_matrix.png")


def plot_demand_prediction(rows: list[dict[str, str]]) -> None:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row["scenario"]].append(row)
    scenarios = list(SCENARIO_LABELS)
    x = np.arange(len(scenarios))
    relevant: dict[str, list[dict[str, str]]] = {}
    for scenario in scenarios:
        high_demand = [r for r in grouped[scenario] if float(r["target_demand"]) >= 0.35]
        relevant[scenario] = high_demand or grouped[scenario]
    demand = [np.mean([float(r["target_demand"]) for r in relevant[s]]) for s in scenarios]
    pred = [np.mean([float(r["predicted_light"]) for r in relevant[s]]) for s in scenarios]
    under = [np.mean([float(r["under_light"]) for r in relevant[s]]) for s in scenarios]
    over = [np.mean([float(r["over_light"]) for r in relevant[s]]) for s in scenarios]

    fig, ax = plt.subplots(figsize=(10.5, 4.5))
    width = 0.34
    ax.bar(x - width / 2, demand, width, label="target demand", color="#0057FF", alpha=1.0)
    ax.bar(x + width / 2, pred, width, label="predicted light", color="#00B8D9", alpha=1.0)
    ax.plot(x, under, marker="o", color="#FF8C00", label="mean under-light", linewidth=1.9)
    ax.plot(x, over, marker="s", color="#D81B60", label="over high-limit", linewidth=1.7)
    ax.set_xticks(x, [SCENARIO_LABELS[s] for s in scenarios], rotation=18, ha="right")
    ax.set_ylabel("normalized visual lighting")
    ax.set_title("Task-relevant cell demand and optimized predicted lighting")
    ax.set_ylim(0, max(max(demand), max(pred)) * 1.25)
    ax.grid(axis="y")
    ax.legend(ncol=2, frameon=False)
    save(fig, "demand_prediction_by_scenario.png")


def plot_control_vectors(rows: list[dict[str, str]]) -> None:
    scenarios = list(SCENARIO_LABELS)
    lamp_order = []
    by_scenario: dict[str, dict[str, float]] = defaultdict(dict)
    for row in rows:
        lamp_id = row["lamp_id"]
        if lamp_id not in lamp_order:
            lamp_order.append(lamp_id)
        by_scenario[row["scenario"]][lamp_id] = float(row["c_t"])
    mat = np.array([[by_scenario[s][lamp] for lamp in lamp_order] for s in scenarios], dtype=float)
    fig, ax = plt.subplots(figsize=(12, 4.4))
    im = ax.imshow(mat, cmap="YlOrRd", aspect="auto", vmin=0, vmax=max(0.5, mat.max()))
    ax.set_yticks(range(len(scenarios)), [SCENARIO_LABELS[s] for s in scenarios])
    ax.set_xticks(range(len(lamp_order)), [lamp.replace("ceiling_", "c_").replace("front_linear_", "linear_") for lamp in lamp_order], rotation=55, ha="right")
    ax.set_title("Optimized lamp control vector $c_t$ by scenario")
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("control value")
    save(fig, "control_vectors.png")


def plot_quality_metrics(summary: dict) -> None:
    scenarios = list(SCENARIO_LABELS)
    quality = summary["quality_by_scenario"]
    metrics = [
        ("task_mean_under_light", "task under-light", "#FF8C00"),
        ("mean_over_light", "over high-limit", "#D81B60"),
        ("relative_energy", "relative energy", "#0057FF"),
        ("normalized_target_satisfaction", "task satisfaction", "#00A878"),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(10.5, 6.2), sharex=True)
    for ax, (key, title, color) in zip(axes.ravel(), metrics):
        values = [float(quality[s][key]) for s in scenarios]
        ax.bar(range(len(scenarios)), values, color=color, alpha=1.0)
        ax.set_title(title)
        ax.grid(axis="y")
        if "satisfaction" in key:
            ax.set_ylim(0, 1.05)
        else:
            ax.set_ylim(0, max(values) * 1.35 + 1e-6)
    for ax in axes[-1]:
        ax.set_xticks(range(len(scenarios)), [SCENARIO_LABELS[s] for s in scenarios], rotation=22, ha="right")
    fig.suptitle("Prototype control quality metrics", y=1.02)
    save(fig, "prototype_quality_metrics.png")


def main() -> None:
    ensure_dirs()
    setup_style()
    cells = read_csv(DATA_DIR / "cells.csv")
    contribution = read_csv(DATA_DIR / "contribution_matrix.csv")
    target = read_csv(DATA_DIR / "target_demand.csv")
    control = read_csv(DATA_DIR / "control_result.csv")
    summary = json.loads((DATA_DIR / "run_summary.json").read_text(encoding="utf-8"))
    plot_method_flow()
    plot_cell_distribution(cells)
    plot_contribution_matrix(contribution)
    plot_demand_prediction(target)
    plot_control_vectors(control)
    plot_quality_metrics(summary)
    print(f"paper figures written to {FIG_DIR}")


if __name__ == "__main__":
    main()
