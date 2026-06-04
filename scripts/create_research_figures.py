from __future__ import annotations

import csv
from pathlib import Path

import imageio.v2 as imageio
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "outputs" / "data"
FIG_DIR = ROOT / "outputs" / "figures"
VIDEO_DIR = ROOT / "outputs" / "videos"

LIGHT_NAMES = [f"ceiling_light_r{r:02d}_c{c:02d}" for r in range(1, 6) for c in range(1, 5)]
LINEAR_NAMES = ["front_linear_light_left", "front_linear_light_right"]
ALL_LIGHT_NAMES = LIGHT_NAMES + LINEAR_NAMES
MODE_COLORS = {
    "empty_safety": "#4c566a",
    "class_mode": "#2f7d6b",
    "break_mode": "#d08770",
    "projection_mode": "#5e81ac",
    "self_study": "#a3be8c",
    "self_study_summary": "#8fbcbb",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def ensure_dirs():
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)


def load_light_rows():
    rows = read_csv(DATA_DIR / "light_brightness_timeseries.csv")
    for row in rows:
        row["time_s"] = float(row["time_s"])
        for name in ALL_LIGHT_NAMES:
            row[name] = float(row[name])
    return rows


def plot_timeline():
    rows = read_csv(DATA_DIR / "demo_timeline.csv")
    fig, ax = plt.subplots(figsize=(12, 2.8))
    for row in rows:
        start = float(row["start_s"])
        end = float(row["end_s"])
        mode = row["mode"]
        ax.barh([0], [end - start], left=start, height=0.45, color=MODE_COLORS.get(mode, "#999999"), edgecolor="white")
        ax.text((start + end) / 2, 0, mode.replace("_", "\n"), ha="center", va="center", fontsize=9, color="white")
    ax.set_xlim(0, 20)
    ax.set_ylim(-0.55, 0.55)
    ax.set_yticks([])
    ax.set_xlabel("Time (s)")
    ax.set_title("Smart Lighting Demonstration Timeline")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "mode_timeline.png", dpi=180)
    plt.close(fig)


def plot_light_curves(rows):
    times = np.array([row["time_s"] for row in rows])
    front = np.mean([[row[f"ceiling_light_r{r:02d}_c{c:02d}"] for r in (1, 2) for c in range(1, 5)] for row in rows], axis=1)
    middle = np.mean([[row[f"ceiling_light_r{r:02d}_c{c:02d}"] for r in (3,) for c in range(1, 5)] for row in rows], axis=1)
    rear = np.mean([[row[f"ceiling_light_r{r:02d}_c{c:02d}"] for r in (4, 5) for c in range(1, 5)] for row in rows], axis=1)
    linears = np.mean([[row[name] for name in LINEAR_NAMES] for row in rows], axis=1)
    fig, ax = plt.subplots(figsize=(11, 4.5))
    ax.plot(times, front, label="Front ceiling lights", linewidth=2)
    ax.plot(times, middle, label="Middle ceiling lights", linewidth=2)
    ax.plot(times, rear, label="Rear ceiling lights", linewidth=2)
    ax.plot(times, linears, label="Front linear lights", linewidth=2)
    ax.set_xlim(0, 20)
    ax.set_ylim(0, 1.15)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Relative brightness")
    ax.set_title("Per-Lamp Dimming Curves by Area")
    ax.grid(alpha=0.25)
    ax.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "light_brightness_curves.png", dpi=180)
    plt.close(fig)


def nearest_row(rows, time_s):
    return min(rows, key=lambda row: abs(row["time_s"] - time_s))


def light_matrix(row):
    values = [row[name] for name in LIGHT_NAMES]
    return np.array(values).reshape(5, 4)


def plot_light_heatmaps(rows):
    samples = [
        ("Empty safety", 1.25),
        ("Class mode", 5.25),
        ("Break mode", 8.0),
        ("Projection", 11.25),
        ("Self-study", 19.0),
    ]
    fig, axes = plt.subplots(1, len(samples), figsize=(14, 3.4), constrained_layout=True)
    for ax, (title, time_s) in zip(axes, samples):
        mat = light_matrix(nearest_row(rows, time_s))
        im = ax.imshow(mat, cmap="YlOrRd", vmin=0, vmax=1.1)
        ax.set_title(title, fontsize=10)
        ax.set_xticks(range(4), labels=["c1", "c2", "c3", "c4"])
        ax.set_yticks(range(5), labels=["r1", "r2", "r3", "r4", "r5"])
        for y in range(5):
            for x in range(4):
                ax.text(x, y, f"{mat[y, x]:.2f}", ha="center", va="center", fontsize=7)
    fig.colorbar(im, ax=axes, shrink=0.75, label="Relative brightness")
    fig.suptitle("5x4 Ceiling Light Brightness Heatmaps")
    fig.savefig(FIG_DIR / "light_heatmaps_by_mode.png", dpi=180)
    plt.close(fig)


def plot_occupancy_heatmaps():
    rows = read_csv(DATA_DIR / "occupancy_timeseries.csv")
    modes = [("class_mode", 5.25), ("break_mode", 8.0), ("self_study_summary", 19.0)]
    fig, axes = plt.subplots(1, 3, figsize=(12, 4), constrained_layout=True)
    for ax, (mode, time_s) in zip(axes, modes):
        pts = []
        for row in rows:
            if abs(float(row["time_s"]) - time_s) < 0.01:
                pts.append((float(row["x_m"]), float(row["y_m"])))
        if pts:
            x, y = np.array(pts).T
            ax.hist2d(x, y, bins=[np.linspace(0, 9.85, 16), np.linspace(0, 16.2, 22)], cmap="Greens")
            ax.scatter(x, y, s=14, c="black", alpha=0.55)
        ax.set_xlim(0, 9.85)
        ax.set_ylim(16.2, 0)
        ax.set_title(mode.replace("_", " "))
        ax.set_xlabel("Room x (m)")
        ax.set_ylabel("Room y (m)")
        ax.grid(alpha=0.18)
    fig.suptitle("Occupancy Density Heatmaps")
    fig.savefig(FIG_DIR / "occupancy_heatmaps.png", dpi=180)
    plt.close(fig)


def plot_energy():
    rows = read_csv(DATA_DIR / "energy_summary.csv")
    labels = [row["strategy"].replace("_", "\n") for row in rows]
    energy = [float(row["relative_energy"]) for row in rows]
    savings = [float(row["saving_vs_full_on"]) for row in rows]
    fig, ax = plt.subplots(figsize=(8, 4.6))
    bars = ax.bar(labels, energy, color=["#7b8794", "#5e81ac", "#2f7d6b"])
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Relative energy")
    ax.set_title("Estimated Energy Comparison")
    ax.grid(axis="y", alpha=0.25)
    for bar, saving in zip(bars, savings):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.025, f"{saving:.0%} saved", ha="center", fontsize=9)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "energy_comparison.png", dpi=180)
    plt.close(fig)


def plot_quality_metrics(rows):
    mode_times = [("empty_safety", 1.25), ("class_mode", 5.25), ("break_mode", 8.0), ("projection_mode", 11.25), ("self_study", 19.0)]
    labels = []
    satisfaction = []
    overlight = []
    for mode, time_s in mode_times:
        row = nearest_row(rows, time_s)
        vals = np.array([row[name] for name in LIGHT_NAMES])
        labels.append(mode.replace("_", "\n"))
        if mode == "self_study":
            satisfaction.append(min(1.0, vals.max() / 0.82))
            overlight.append(float(np.mean(vals < 0.35)))
        elif mode == "projection_mode":
            front_vals = np.array([row[f"ceiling_light_r{r:02d}_c{c:02d}"] for r in (1, 2) for c in range(1, 5)])
            satisfaction.append(1.0 - max(0.0, float(front_vals.mean()) - 0.48))
            overlight.append(max(0.0, float(front_vals.mean()) - 0.35))
        else:
            satisfaction.append(min(1.0, float(vals.mean()) / (0.18 if mode == "empty_safety" else 0.70)))
            overlight.append(max(0.0, float(vals.mean()) - 0.65))
    x = np.arange(len(labels))
    width = 0.36
    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.bar(x - width / 2, satisfaction, width, label="Lighting satisfaction", color="#2f7d6b")
    ax.bar(x + width / 2, overlight, width, label="Over-lighting risk control", color="#d08770")
    ax.set_ylim(0, 1.15)
    ax.set_xticks(x, labels)
    ax.set_ylabel("Score")
    ax.set_title("Simplified Lighting Quality Metrics")
    ax.legend()
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "lighting_quality_metrics.png", dpi=180)
    plt.close(fig)


def make_matrix_gif(rows):
    font = ImageFont.load_default()
    frames = []
    for time_s in np.linspace(0, 20, 41):
        row = nearest_row(rows, float(time_s))
        mat = light_matrix(row)
        image = Image.new("RGB", (440, 360), "#20242a")
        draw = ImageDraw.Draw(image)
        draw.text((18, 14), f"t = {time_s:04.1f}s   {row['mode']}", fill="white", font=font)
        cell_w, cell_h = 82, 48
        x0, y0 = 55, 62
        for r in range(5):
            for c in range(4):
                val = float(mat[r, c])
                color = plt.cm.YlOrRd(min(1.0, val / 1.1))
                rgb = tuple(int(255 * ch) for ch in color[:3])
                x = x0 + c * cell_w
                y = y0 + r * cell_h
                draw.rectangle([x, y, x + cell_w - 8, y + cell_h - 8], fill=rgb, outline="#111111")
                draw.text((x + 20, y + 15), f"{val:.2f}", fill="#101010", font=font)
        frames.append(np.array(image))
    imageio.mimsave(VIDEO_DIR / "light_control_matrix.gif", frames, duration=0.12)


def main():
    ensure_dirs()
    rows = load_light_rows()
    plot_timeline()
    plot_light_curves(rows)
    plot_light_heatmaps(rows)
    plot_occupancy_heatmaps()
    plot_energy()
    plot_quality_metrics(rows)
    make_matrix_gif(rows)
    print("created figures and light_control_matrix.gif")


if __name__ == "__main__":
    main()
