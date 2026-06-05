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
ROOM_W = 9.85
ROOM_L = 16.2
MODE_COLORS = {
    "empty_safety": "#4c566a",
    "class_mode": "#2f7d6b",
    "break_mode": "#d08770",
    "projection_mode": "#5e81ac",
    "self_study": "#a3be8c",
}
MODE_LABELS = {
    "empty_safety": "empty safety",
    "class_mode": "class mode",
    "break_mode": "break mode",
    "projection_mode": "projection mode",
    "self_study": "self study",
}
ACTIVITY_COLORS = {
    "empty": (68, 76, 86),
    "listening": (91, 141, 186),
    "writing": (76, 158, 122),
    "projection": (111, 101, 177),
    "blackboard-writing": (210, 176, 79),
    "discussion": (205, 130, 86),
    "walking": (194, 84, 87),
}
ACTIVITY_ORDER = ["empty", "listening", "writing", "projection", "blackboard-writing", "discussion", "walking"]


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


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


FONT_12 = load_font(12)
FONT_13 = load_font(13)
FONT_14 = load_font(14, True)
FONT_16 = load_font(16, True)
FONT_18 = load_font(18)
FONT_20_REG = load_font(20)
FONT_20 = load_font(20, True)
FONT_24 = load_font(24, True)
FONT_28 = load_font(28, True)


def plot_timeline():
    rows = read_csv(DATA_DIR / "demo_timeline.csv")
    fig, ax = plt.subplots(figsize=(12, 2.8))
    for row in rows:
        start = float(row["start_s"])
        end = float(row["end_s"])
        mode = row["mode"]
        ax.barh([0], [end - start], left=start, height=0.45, color=MODE_COLORS.get(mode, "#999999"), edgecolor="white")
        ax.text((start + end) / 2, 0, MODE_LABELS.get(mode, mode.replace("_", " ")).replace(" ", "\n"), ha="center", va="center", fontsize=9, color="white")
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


def mode_at(timeline: list[dict[str, str]], time_s: float) -> str:
    for row in timeline:
        if float(row["start_s"]) <= time_s < float(row["end_s"]):
            return row["mode"]
    return timeline[-1]["mode"]


def light_matrix(row):
    values = [[row[f"ceiling_light_r{r:02d}_c{c:02d}"] for c in (4, 3, 2, 1)] for r in range(1, 6)]
    return np.array(values)


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
        ax.set_xticks(range(4), labels=["c4", "c3", "c2", "c1"])
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
    modes = [("class_mode", 5.25), ("break_mode", 9.0), ("self_study", 19.0)]
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
        ax.set_title(MODE_LABELS.get(mode, mode.replace("_", " ")))
        ax.set_xlabel("Room x (m)")
        ax.set_ylabel("Room y (m)")
        ax.grid(alpha=0.18)
    fig.suptitle("Occupancy Density Heatmaps")
    fig.savefig(FIG_DIR / "occupancy_heatmaps.png", dpi=180)
    plt.close(fig)


def plot_energy():
    label_map = {"full_on": "full-on\nbaseline", "smart_per_lamp_dimming": "smart\nper-lamp"}
    rows = [row for row in read_csv(DATA_DIR / "energy_summary.csv") if row["strategy"] in label_map]
    labels = [label_map[row["strategy"]] for row in rows]
    energy = [float(row["relative_energy"]) for row in rows]
    savings = [float(row["saving_vs_full_on"]) for row in rows]
    fig, ax = plt.subplots(figsize=(8, 4.6))
    bars = ax.bar(labels, energy, color=["#7b8794", "#2f7d6b"])
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
        labels.append(MODE_LABELS.get(mode, mode.replace("_", " ")).replace(" ", "\n"))
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


def light_color(value: float) -> tuple[int, int, int]:
    color = plt.cm.YlOrRd(min(1.0, max(0.0, value / 1.1)))
    return tuple(int(255 * ch) for ch in color[:3])


def draw_centered_text(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], text: str, fill, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = box[0] + (box[2] - box[0] - tw) // 2
    y = box[1] + (box[3] - box[1] - th) // 2 - 1
    draw.text((x, y), text, fill=fill, font=font)


def make_matrix_gif(rows):
    frames = []
    for time_s in np.linspace(0, 20, 41):
        row = nearest_row(rows, float(time_s))
        mat = light_matrix(row)
        image = Image.new("RGB", (800, 600), "#151b24")
        draw = ImageDraw.Draw(image)
        mode = MODE_LABELS.get(row["mode"], row["mode"].replace("_", " "))
        draw.text((40, 28), "Per-lamp Brightness Matrix", fill="#e5e7eb", font=FONT_20)
        draw.text((560, 32), f"t={time_s:04.1f}s  {mode}", fill="#cbd5e1", font=FONT_13)

        panel = (44, 82, 756, 560)
        draw.rounded_rectangle(panel, radius=8, fill="#202938", outline="#475569", width=1)
        draw.rounded_rectangle((184, 114, 616, 154), radius=6, fill="#111827", outline="#475569", width=1)
        bar_w, bar_h = 196, 24
        bar_gap = 24
        bar_total = bar_w * 2 + bar_gap
        bar_x0 = 400 - bar_total // 2
        for idx, name in enumerate(LINEAR_NAMES):
            val = float(row[name])
            x = bar_x0 + idx * (bar_w + bar_gap)
            box = (x, 122, x + bar_w, 146)
            draw.rounded_rectangle(box, radius=4, fill=light_color(val), outline="#111827")
            draw_centered_text(draw, box, f"line {idx + 1}  {int(round(val / 1.18 * 100)):02d}%", "#101010", FONT_12)

        cell_w, cell_h = 138, 56
        gap = 10
        grid_w = cell_w * 4 + gap * 3
        x0, y0 = 400 - grid_w // 2, 178
        for r in range(5):
            for c in range(4):
                val = float(mat[r, c])
                x = x0 + c * (cell_w + gap)
                y = y0 + r * (cell_h + gap)
                box = (x, y, x + cell_w, y + cell_h)
                draw.rounded_rectangle(box, radius=6, fill=light_color(val), outline="#111827", width=1)
                draw.text((x + 10, y + 8), f"R{r+1}C{[4,3,2,1][c]}", fill="#111827", font=FONT_12)
                draw.text((x + 70, y + 25), f"{int(round(val / 1.18 * 100)):02d}%", fill="#111827", font=FONT_18)
        frames.append(np.array(image))
    imageio.mimsave(VIDEO_DIR / "light_control_matrix.gif", frames, duration=0.12)


def room_mapper(box: tuple[int, int, int, int]):
    x0, y0, x1, y1 = box
    pad = 18
    w = x1 - x0 - pad * 2
    h = y1 - y0 - pad * 2

    def map_xy(x: float, y: float) -> tuple[int, int]:
        px = x0 + pad + int((1.0 - x / ROOM_W) * w)
        py = y0 + pad + int((y / ROOM_L) * h)
        return px, py

    return map_xy


def rows_by_time(rows: list[dict[str, str]]) -> dict[float, list[dict[str, str]]]:
    result: dict[float, list[dict[str, str]]] = {}
    for row in rows:
        result.setdefault(float(row["time_s"]), []).append(row)
    return result


def nearest_time(times: list[float], time_s: float) -> float:
    return min(times, key=lambda value: abs(value - time_s))


def rows_at_time(groups: dict[float, list[dict[str, str]]], times: list[float], time_s: float, tolerance: float = 0.13) -> list[dict[str, str]]:
    if not times:
        return []
    key = nearest_time(times, time_s)
    if abs(key - time_s) > tolerance:
        return []
    return groups.get(key, [])


def make_activity_heatmap_gif():
    timeline = read_csv(DATA_DIR / "demo_timeline.csv")
    cells = read_csv(DATA_DIR / "work_surface_cells.csv")
    activity_by_time = rows_by_time(read_csv(DATA_DIR / "activity_cell_timeseries.csv"))
    occupancy_by_time = rows_by_time(read_csv(DATA_DIR / "occupancy_timeseries.csv"))
    activity_times = sorted(activity_by_time)
    occupancy_times = sorted(occupancy_by_time)
    frames = []
    for time_s in np.linspace(0, 20, 41):
        mode = mode_at(timeline, float(time_s))
        activity_rows = rows_at_time(activity_by_time, activity_times, float(time_s))
        occupancy_rows = rows_at_time(occupancy_by_time, occupancy_times, float(time_s))
        by_id = {row["cell_id"]: row for row in activity_rows}
        image = Image.new("RGB", (800, 600), "#151b24")
        draw = ImageDraw.Draw(image)
        draw.text((40, 28), "Work-surface Activity Heatmap", fill="#e5e7eb", font=FONT_20)
        draw.text((560, 32), f"t={time_s:04.1f}s  {MODE_LABELS.get(mode, mode)}", fill="#cbd5e1", font=FONT_13)

        room = (56, 82, 520, 520)
        draw.rounded_rectangle(room, radius=8, fill="#202938", outline="#475569", width=1)
        map_xy = room_mapper(room)
        left_top = map_xy(ROOM_W, 0)
        right_bottom = map_xy(0, ROOM_L)
        for x in np.linspace(0, ROOM_W, 6):
            p0 = map_xy(float(x), 0)
            p1 = map_xy(float(x), ROOM_L)
            draw.line((p0, p1), fill="#334155", width=1)
        for y in np.linspace(0, ROOM_L, 9):
            p0 = map_xy(0, float(y))
            p1 = map_xy(ROOM_W, float(y))
            draw.line((p0, p1), fill="#334155", width=1)
        draw.rounded_rectangle((left_top[0] + 26, left_top[1] + 9, right_bottom[0] - 26, left_top[1] + 15), radius=2, fill="#94a3b8")
        draw.line((right_bottom[0] - 8, left_top[1] + 46, right_bottom[0] - 8, left_top[1] + 94), fill="#cbd5e1", width=3)
        cam_x = (left_top[0] + right_bottom[0]) // 2
        draw.polygon([(cam_x, right_bottom[1] - 14), (cam_x - 8, right_bottom[1] - 4), (cam_x + 8, right_bottom[1] - 4)], fill="#7dd3fc")

        for cell in cells:
            row = by_id.get(cell["cell_id"])
            activity = row["dominant_activity"] if row else "empty"
            color = ACTIVITY_COLORS.get(activity, ACTIVITY_COLORS["empty"])
            px, py = map_xy(float(cell["x_m"]), float(cell["y_m"]))
            label = cell["semantic_label"]
            if label == "desk_work_surface":
                draw.rounded_rectangle((px - 8, py - 5, px + 8, py + 5), radius=3, fill=color, outline="#111827")
            elif label == "aisle_floor":
                draw.ellipse((px - 6, py - 6, px + 6, py + 6), fill=color, outline="#111827")
            else:
                draw.rounded_rectangle((px - 12, py - 6, px + 12, py + 6), radius=3, fill=color, outline="#111827")
        for person in occupancy_rows:
            px, py = map_xy(float(person["x_m"]), float(person["y_m"]))
            color = ACTIVITY_COLORS.get(person["activity"], "#f8fafc")
            draw.ellipse((px - 7, py - 7, px + 7, py + 7), fill=color, outline="#f8fafc", width=2)

        counts = {activity: 0 for activity in ACTIVITY_ORDER}
        for row in activity_rows:
            counts[row["dominant_activity"]] += 1
        x, y = 548, 98
        draw.text((x, y), "cell activity", fill="#e5e7eb", font=FONT_18)
        y += 36
        total = max(1, sum(counts.values()))
        for activity in ACTIVITY_ORDER:
            color = ACTIVITY_COLORS[activity]
            draw.rounded_rectangle((x, y + 4, x + 16, y + 20), radius=3, fill=color)
            draw.text((x + 24, y), activity, fill="#cbd5e1", font=FONT_12)
            bar_x, bar_w = x + 150, 44
            draw.rounded_rectangle((bar_x, y + 6, bar_x + bar_w, y + 18), radius=3, fill="#334155")
            draw.rounded_rectangle((bar_x, y + 6, bar_x + int(bar_w * counts[activity] / total), y + 18), radius=3, fill=color)
            draw.text((bar_x + bar_w + 8, y), str(counts[activity]), fill="#e5e7eb", font=FONT_12)
            y += 30
        draw.text((548, 402), f"people {len(occupancy_rows)}", fill="#e5e7eb", font=FONT_18)
        walking = sum(1 for row in occupancy_rows if row["activity"] == "walking")
        draw.text((548, 436), f"walking {walking}", fill="#cbd5e1", font=FONT_14)
        draw.text((548, 492), "white rings: occupants", fill="#94a3b8", font=FONT_13)
        frames.append(np.array(image))
    imageio.mimsave(VIDEO_DIR / "activity_heatmap.gif", frames, duration=0.12)


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
    make_activity_heatmap_gif()
    print("created figures, light_control_matrix.gif, and activity_heatmap.gif")


if __name__ == "__main__":
    main()
