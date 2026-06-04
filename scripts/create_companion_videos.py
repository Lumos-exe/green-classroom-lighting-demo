from __future__ import annotations

import csv
import math
from collections import Counter
from pathlib import Path

import imageio.v2 as imageio
import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "outputs" / "data"
VIDEO_DIR = ROOT / "outputs" / "videos"
COMPANION_DIR = VIDEO_DIR / "companion"

MAIN_VIDEO = VIDEO_DIR / "smart_lighting_demo.mp4"
PREVIEW_VIDEO = VIDEO_DIR / "smart_lighting_demo_preview.mp4"

ROOM_W = 9.85
ROOM_L = 16.2
FPS_FALLBACK = 8.0
DURATION_FALLBACK = 20.0

LIGHT_NAMES = [f"ceiling_light_r{r:02d}_c{c:02d}" for r in range(1, 6) for c in range(1, 5)]
LINEAR_NAMES = ["front_linear_light_left", "front_linear_light_right"]
ALL_LIGHT_NAMES = LIGHT_NAMES + LINEAR_NAMES

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
MODE_COLORS = {
    "empty_safety": (91, 100, 116),
    "class_mode": (76, 158, 122),
    "break_mode": (205, 130, 86),
    "projection_mode": (91, 141, 186),
    "self_study": (128, 171, 118),
    "self_study_summary": (104, 164, 165),
}

BG = (15, 20, 27)
PANEL = (25, 31, 40)
PANEL_2 = (31, 38, 49)
GRID = (66, 76, 91)
TEXT = (226, 232, 240)
MUTED = (154, 164, 178)
ACCENT = (118, 173, 220)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


FONT_11 = load_font(11)
FONT_12 = load_font(12)
FONT_13 = load_font(13)
FONT_14 = load_font(14)
FONT_16 = load_font(16, True)
FONT_18 = load_font(18, True)
FONT_22 = load_font(22, True)


def main_video_path() -> Path:
    if MAIN_VIDEO.exists():
        return MAIN_VIDEO
    if PREVIEW_VIDEO.exists():
        return PREVIEW_VIDEO
    raise FileNotFoundError("No main animation video found in outputs/videos.")


def video_meta(path: Path) -> tuple[float, float, int, int]:
    reader = imageio.get_reader(path)
    meta = reader.get_meta_data()
    frame0 = reader.get_data(0)
    fps = float(meta.get("fps") or FPS_FALLBACK)
    duration = float(meta.get("duration") or DURATION_FALLBACK)
    reader.close()
    return fps, duration, int(frame0.shape[1]), int(frame0.shape[0])


def nearest(rows: list[dict], time_s: float) -> dict:
    return min(rows, key=lambda row: abs(float(row["time_s"]) - time_s))


def parse_data() -> dict:
    required = [
        "demo_timeline.csv",
        "occupancy_timeseries.csv",
        "activity_cell_timeseries.csv",
        "work_surface_cells.csv",
        "light_brightness_timeseries.csv",
        "energy_summary.csv",
    ]
    missing = [name for name in required if not (DATA_DIR / name).exists()]
    if missing:
        raise FileNotFoundError(f"Missing data files: {missing}")

    timeline = read_csv(DATA_DIR / "demo_timeline.csv")
    occupancy = read_csv(DATA_DIR / "occupancy_timeseries.csv")
    cell_rows = read_csv(DATA_DIR / "work_surface_cells.csv")
    activity_rows = read_csv(DATA_DIR / "activity_cell_timeseries.csv")
    light_rows = read_csv(DATA_DIR / "light_brightness_timeseries.csv")
    energy_rows = read_csv(DATA_DIR / "energy_summary.csv")

    allowed = set(ACTIVITY_ORDER)
    bad_activities = {row["activity"] for row in occupancy} - allowed
    bad_cells = {row["dominant_activity"] for row in activity_rows} - allowed
    if bad_activities or bad_cells:
        raise ValueError(f"Unexpected activity labels: people={bad_activities}, cells={bad_cells}")
    if len([name for name in light_rows[0] if name in ALL_LIGHT_NAMES]) != 22:
        raise ValueError("light_brightness_timeseries.csv must contain 22 lamp columns.")

    occupancy_by_t: dict[float, list[dict]] = {}
    for row in occupancy:
        occupancy_by_t.setdefault(float(row["time_s"]), []).append(row)
    activity_by_t: dict[float, list[dict]] = {}
    for row in activity_rows:
        activity_by_t.setdefault(float(row["time_s"]), []).append(row)

    return {
        "timeline": timeline,
        "occupancy": occupancy,
        "occupancy_times": sorted(occupancy_by_t),
        "occupancy_by_t": occupancy_by_t,
        "cells": cell_rows,
        "activity_times": sorted(activity_by_t),
        "activity_by_t": activity_by_t,
        "lights": light_rows,
        "energy": energy_rows,
    }


def nearest_time(times: list[float], time_s: float) -> float:
    return min(times, key=lambda value: abs(value - time_s))


def resize_cover(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    target_w, target_h = size
    scale = max(target_w / image.width, target_h / image.height)
    scaled = image.resize((int(image.width * scale), int(image.height * scale)), Image.Resampling.LANCZOS)
    left = (scaled.width - target_w) // 2
    top = (scaled.height - target_h) // 2
    return scaled.crop((left, top, left + target_w, top + target_h))


def resize_fit(image: Image.Image, size: tuple[int, int], fill: tuple[int, int, int] = PANEL) -> Image.Image:
    target_w, target_h = size
    scale = min(target_w / image.width, target_h / image.height)
    scaled = image.resize((int(image.width * scale), int(image.height * scale)), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, fill)
    canvas.paste(scaled, ((target_w - scaled.width) // 2, (target_h - scaled.height) // 2))
    return canvas


def draw_panel(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], title: str | None = None):
    draw.rounded_rectangle(box, radius=7, fill=PANEL, outline=(45, 55, 68), width=1)
    if title:
        draw.text((box[0] + 14, box[1] + 10), title, fill=TEXT, font=FONT_16)


def room_mapper(box: tuple[int, int, int, int]):
    x0, y0, x1, y1 = box
    pad = 16
    w = x1 - x0 - pad * 2
    h = y1 - y0 - pad * 2

    def map_xy(x: float, y: float) -> tuple[int, int]:
        # Match the rear-to-front camera: world +x appears on the rendered
        # image's left side, so top-down companion maps mirror x.
        px = x0 + pad + int((1.0 - x / ROOM_W) * w)
        py = y0 + pad + int((y / ROOM_L) * h)
        return px, py

    return map_xy


def blend(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def light_color(value: float) -> tuple[int, int, int]:
    if value < 0.35:
        return blend((39, 55, 75), (83, 122, 147), value / 0.35)
    if value < 0.75:
        return blend((83, 122, 147), (190, 160, 82), (value - 0.35) / 0.40)
    return blend((190, 160, 82), (245, 211, 117), (value - 0.75) / 0.43)


def activity_rows_at(data: dict, time_s: float) -> list[dict]:
    key = nearest_time(data["activity_times"], time_s)
    return data["activity_by_t"].get(key, [])


def occupancy_rows_at(data: dict, time_s: float) -> list[dict]:
    if not data["occupancy_times"]:
        return []
    key = nearest_time(data["occupancy_times"], time_s)
    return data["occupancy_by_t"].get(key, [])


def mode_at(data: dict, time_s: float) -> str:
    for row in data["timeline"]:
        if float(row["start_s"]) <= time_s < float(row["end_s"]):
            return row["mode"]
    return data["timeline"][-1]["mode"]


def draw_room_grid(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int]):
    map_xy = room_mapper(box)
    p0 = map_xy(0, 0)
    p1 = map_xy(ROOM_W, ROOM_L)
    left_top = (min(p0[0], p1[0]), min(p0[1], p1[1]))
    right_bottom = (max(p0[0], p1[0]), max(p0[1], p1[1]))
    draw.rectangle([left_top, right_bottom], fill=PANEL_2, outline=(74, 84, 99), width=1)
    for x in np.linspace(0, ROOM_W, 6):
        px0, py0 = map_xy(float(x), 0)
        px1, py1 = map_xy(float(x), ROOM_L)
        draw.line([(px0, py0), (px1, py1)], fill=(43, 51, 62), width=1)
    for y in np.linspace(0, ROOM_L, 9):
        px0, py0 = map_xy(0, float(y))
        px1, py1 = map_xy(ROOM_W, float(y))
        draw.line([(px0, py0), (px1, py1)], fill=(43, 51, 62), width=1)
    draw.text((left_top[0] + 8, left_top[1] + 7), "front board", fill=MUTED, font=FONT_11)
    draw.text((right_bottom[0] - 116, left_top[1] + 7), "door side", fill=MUTED, font=FONT_11)
    draw.text((left_top[0] + 8, left_top[1] + 24), "window side", fill=MUTED, font=FONT_11)
    draw.text((left_top[0] + 8, right_bottom[1] - 20), "rear camera side", fill=MUTED, font=FONT_11)


def draw_activity_legend(draw: ImageDraw.ImageDraw, x: int, y: int, compact: bool = False):
    for idx, activity in enumerate(ACTIVITY_ORDER):
        yy = y + idx * (18 if compact else 22)
        color = ACTIVITY_COLORS[activity]
        draw.rounded_rectangle((x, yy, x + 12, yy + 12), radius=2, fill=color)
        draw.text((x + 18, yy - 2), activity, fill=MUTED, font=FONT_11 if compact else FONT_12)


def draw_mode_timeline(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], data: dict, time_s: float):
    x0, y0, x1, y1 = box
    draw.rounded_rectangle(box, radius=5, fill=(18, 24, 32), outline=(50, 60, 74), width=1)
    total = float(data["timeline"][-1]["end_s"])
    for row in data["timeline"]:
        start = float(row["start_s"])
        end = float(row["end_s"])
        xs = x0 + int((start / total) * (x1 - x0))
        xe = x0 + int((end / total) * (x1 - x0))
        color = MODE_COLORS.get(row["mode"], GRID)
        draw.rectangle((xs, y0, xe, y1), fill=color)
    tx = x0 + int((time_s / total) * (x1 - x0))
    draw.line((tx, y0 - 4, tx, y1 + 4), fill=(245, 248, 252), width=2)


def draw_cell_map(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], data: dict, time_s: float, show_people: bool):
    draw_room_grid(draw, box)
    map_xy = room_mapper(box)
    rows = activity_rows_at(data, time_s)
    by_id = {row["cell_id"]: row for row in rows}
    for cell in data["cells"]:
        row = by_id.get(cell["cell_id"])
        activity = row["dominant_activity"] if row else "empty"
        color = ACTIVITY_COLORS.get(activity, ACTIVITY_COLORS["empty"])
        x, y = float(cell["x_m"]), float(cell["y_m"])
        px, py = map_xy(x, y)
        label = cell["semantic_label"]
        if label == "desk_work_surface":
            size = 8
            draw.rounded_rectangle((px - size, py - 4, px + size, py + 4), radius=2, fill=color, outline=(18, 22, 28))
        elif label == "aisle_floor":
            draw.ellipse((px - 5, py - 5, px + 5, py + 5), fill=color, outline=(18, 22, 28))
        elif label == "blackboard":
            draw.rectangle((px - 10, py - 4, px + 10, py + 4), fill=color, outline=(18, 22, 28))
        else:
            draw.rounded_rectangle((px - 10, py - 5, px + 10, py + 5), radius=2, fill=color, outline=(18, 22, 28))

    if show_people:
        for person in occupancy_rows_at(data, time_s):
            activity = person["activity"]
            color = ACTIVITY_COLORS.get(activity, (230, 230, 230))
            px, py = map_xy(float(person["x_m"]), float(person["y_m"]))
            r = 4 if activity != "walking" else 5
            draw.ellipse((px - r, py - r, px + r, py + r), fill=color, outline=(235, 241, 247))


def draw_light_matrix(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], data: dict, time_s: float, labels: bool = True):
    row = nearest(data["lights"], time_s)
    x0, y0, x1, y1 = box
    w = (x1 - x0 - 26) // 4
    h = (y1 - y0 - 56) // 5
    visual_cols = [4, 3, 2, 1]
    for r in range(5):
        for visual_c, physical_c in enumerate(visual_cols):
            name = f"ceiling_light_r{r+1:02d}_c{physical_c:02d}"
            val = float(row[name])
            x = x0 + 10 + visual_c * w
            y = y0 + 10 + r * h
            color = light_color(val)
            draw.rounded_rectangle((x, y, x + w - 8, y + h - 8), radius=5, fill=color, outline=(20, 25, 32), width=1)
            if labels:
                draw.text((x + 9, y + 7), f"{val:.2f}", fill=(9, 13, 18), font=FONT_12)
                draw.text((x + 9, y + h - 23), f"R{r+1}C{physical_c}", fill=(18, 24, 30), font=FONT_11)
    bar_y = y1 - 32
    for idx, name in enumerate(LINEAR_NAMES):
        val = float(row[name])
        bx = x0 + 12 + idx * ((x1 - x0 - 36) // 2)
        bw = (x1 - x0 - 48) // 2
        draw.rounded_rectangle((bx, bar_y, bx + bw, bar_y + 14), radius=3, fill=(33, 41, 53), outline=(66, 76, 91))
        draw.rounded_rectangle((bx, bar_y, bx + int(bw * min(1, val / 1.18)), bar_y + 14), radius=3, fill=light_color(val))
        draw.text((bx, bar_y + 17), f"{name.replace('front_linear_light_', 'linear ')} {val:.2f}", fill=MUTED, font=FONT_11)


def draw_activity_stats(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], data: dict, time_s: float):
    rows = activity_rows_at(data, time_s)
    counts = Counter(row["dominant_activity"] for row in rows)
    total = max(1, sum(counts.values()))
    x0, y0, x1, _y1 = box
    y = y0
    for activity in ACTIVITY_ORDER:
        frac = counts[activity] / total
        color = ACTIVITY_COLORS[activity]
        draw.text((x0, y), activity, fill=MUTED, font=FONT_11)
        bx = x0 + 118
        bw = x1 - bx
        draw.rounded_rectangle((bx, y + 2, bx + bw, y + 12), radius=3, fill=(35, 43, 55))
        draw.rounded_rectangle((bx, y + 2, bx + int(bw * frac), y + 12), radius=3, fill=color)
        draw.text((x1 + 8, y - 1), f"{counts[activity]:02d}", fill=TEXT, font=FONT_11)
        y += 19


def draw_activity_chips(draw: ImageDraw.ImageDraw, x: int, y: int, data: dict, time_s: float):
    rows = activity_rows_at(data, time_s)
    counts = Counter(row["dominant_activity"] for row in rows)
    x_cursor = x
    for activity, count in counts.most_common(5):
        color = ACTIVITY_COLORS.get(activity, MUTED)
        label = f"{activity} {count}"
        text_w = int(draw.textlength(label, font=FONT_12))
        draw.rounded_rectangle((x_cursor, y, x_cursor + text_w + 28, y + 24), radius=5, fill=(31, 38, 49), outline=(54, 64, 78))
        draw.rounded_rectangle((x_cursor + 8, y + 7, x_cursor + 18, y + 17), radius=2, fill=color)
        draw.text((x_cursor + 23, y + 4), label, fill=TEXT, font=FONT_12)
        x_cursor += text_w + 38


def draw_energy_curve(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], data: dict, time_s: float):
    x0, y0, x1, y1 = box
    light_rows = data["lights"]
    times = np.array([float(row["time_s"]) for row in light_rows])
    values = np.array([np.mean([float(row[name]) for name in ALL_LIGHT_NAMES]) for row in light_rows])
    accum = np.cumsum(values)
    accum = accum / max(0.001, accum[-1])
    draw.rounded_rectangle(box, radius=5, fill=(18, 24, 32), outline=(50, 60, 74))
    prev = None
    for t, value in zip(times, accum):
        px = x0 + int((t / 20.0) * (x1 - x0))
        py = y1 - int(value * (y1 - y0 - 12)) - 6
        if prev:
            draw.line((prev[0], prev[1], px, py), fill=ACCENT, width=2)
        prev = (px, py)
    tx = x0 + int((time_s / 20.0) * (x1 - x0))
    draw.line((tx, y0, tx, y1), fill=(245, 248, 252), width=1)
    row = nearest(light_rows, time_s)
    avg = np.mean([float(row[name]) for name in ALL_LIGHT_NAMES])
    draw.text((x0 + 10, y0 + 8), f"mean lamp level {avg:.2f}", fill=TEXT, font=FONT_12)


def title_bar(draw: ImageDraw.ImageDraw, title: str, time_s: float, mode: str, width: int):
    draw.text((28, 22), title, fill=TEXT, font=FONT_22)
    draw.text((width - 230, 24), f"t = {time_s:05.2f}s", fill=TEXT, font=FONT_18)
    draw.rounded_rectangle((width - 420, 22, width - 250, 48), radius=5, fill=MODE_COLORS.get(mode, GRID))
    draw.text((width - 410, 27), mode.replace("_", " "), fill=(8, 12, 16), font=FONT_13)


def frame_from_reader(reader, index: int, total_frames: int) -> Image.Image:
    idx = max(0, min(total_frames - 1, index))
    arr = reader.get_data(idx)
    return Image.fromarray(arr).convert("RGB")


def draw_preview(image: Image.Image, frame: Image.Image, box: tuple[int, int, int, int], label: str = "animation frame"):
    preview = resize_cover(frame, (box[2] - box[0], box[3] - box[1]))
    image.paste(preview, (box[0], box[1]))
    draw = ImageDraw.Draw(image)
    draw.rectangle(box, outline=(71, 83, 100), width=1)
    draw.text((box[0] + 8, box[1] + 8), label, fill=TEXT, font=FONT_12)


def activity_heatmap_frame(data: dict, frame: Image.Image, time_s: float) -> Image.Image:
    image = Image.new("RGB", (1280, 720), BG)
    draw = ImageDraw.Draw(image)
    mode = mode_at(data, time_s)
    title_bar(draw, "Real-time Occupant Activity and Work-surface Response", time_s, mode, 1280)
    draw_panel(draw, (28, 70, 770, 540), "synchronized animation")
    draw_preview(image, frame, (44, 112, 754, 511))
    draw_panel(draw, (790, 70, 1252, 650), "activity heatmap on work-surface cells")
    draw_cell_map(draw, (808, 112, 1128, 616), data, time_s, show_people=True)
    draw_activity_legend(draw, 1142, 122, compact=True)
    draw_panel(draw, (28, 560, 770, 650), "dominant activity counts")
    draw_activity_chips(draw, 50, 602, data, time_s)
    draw_mode_timeline(draw, (48, 668, 1232, 690), data, time_s)
    return image


def cell_activity_frame(data: dict, frame: Image.Image, time_s: float) -> Image.Image:
    image = Image.new("RGB", (1280, 720), BG)
    draw = ImageDraw.Draw(image)
    mode = mode_at(data, time_s)
    title_bar(draw, "Cell-level Activity State A_t(i,k)", time_s, mode, 1280)
    draw_panel(draw, (28, 70, 872, 650), "discretized physical work-surface cells")
    draw_cell_map(draw, (54, 112, 695, 628), data, time_s, show_people=False)
    draw.text((720, 112), "cell_i = {X_i, n_i, l_i, V_i, rho_i}", fill=TEXT, font=FONT_16)
    draw.text((720, 144), "Cells are desk, aisle floor, blackboard, and projection-screen surfaces.", fill=MUTED, font=FONT_12)
    draw.text((720, 170), "Color encodes dominant A_t(i,k), not lamp identity.", fill=MUTED, font=FONT_12)
    draw_activity_legend(draw, 720, 220)
    draw_panel(draw, (900, 70, 1252, 340), "animation reference")
    draw_preview(image, frame, (922, 116, 1230, 332))
    draw_panel(draw, (900, 365, 1252, 650), "cell activity distribution")
    draw_activity_stats(draw, (922, 410, 1168, 616), data, time_s)
    draw_mode_timeline(draw, (48, 668, 1232, 690), data, time_s)
    return image


def light_matrix_frame(data: dict, frame: Image.Image, time_s: float) -> Image.Image:
    image = Image.new("RGB", (1280, 720), BG)
    draw = ImageDraw.Draw(image)
    mode = mode_at(data, time_s)
    title_bar(draw, "Per-lamp Brightness Control from Cell Demand", time_s, mode, 1280)
    draw_panel(draw, (28, 70, 770, 540), "synchronized animation")
    draw_preview(image, frame, (44, 112, 754, 511))
    draw_panel(draw, (790, 70, 1252, 650), "5x4 ceiling light matrix")
    draw_light_matrix(draw, (818, 118, 1228, 558), data, time_s)
    draw_panel(draw, (28, 560, 770, 650), "cell-to-lamp response")
    draw.text((50, 590), "Lamp levels are generated from work-surface cell activity through M(i,g).", fill=TEXT, font=FONT_14)
    draw.text((50, 618), "Self-study keeps writing cells bright and empty cells dark.", fill=MUTED, font=FONT_12)
    draw_mode_timeline(draw, (48, 668, 1232, 690), data, time_s)
    return image


def dashboard_frame(data: dict, frame: Image.Image, time_s: float, size: tuple[int, int] = (1280, 720)) -> Image.Image:
    width, height = size
    image = Image.new("RGB", size, BG)
    draw = ImageDraw.Draw(image)
    mode = mode_at(data, time_s)
    title_bar(draw, "Synchronized Smart-lighting Analysis", time_s, mode, width)
    draw_panel(draw, (24, 70, 470, 398), "animation reference")
    draw_preview(image, frame, (42, 112, 452, 344))
    draw_mode_timeline(draw, (42, 366, 452, 384), data, time_s)
    draw_panel(draw, (494, 70, 888, 398), "cell activity")
    draw_cell_map(draw, (510, 112, 770, 378), data, time_s, show_people=False)
    draw_activity_legend(draw, 790, 118, compact=True)
    draw_panel(draw, (912, 70, 1256, 398), "lamp brightness")
    draw_light_matrix(draw, (930, 112, 1240, 374), data, time_s, labels=False)
    draw_panel(draw, (24, 420, 470, 674), "activity distribution")
    draw_activity_stats(draw, (46, 465, 338, 634), data, time_s)
    draw_panel(draw, (494, 420, 888, 674), "energy trajectory")
    draw_energy_curve(draw, (520, 472, 862, 626), data, time_s)
    draw_panel(draw, (912, 420, 1256, 674), "current control state")
    row = nearest(data["lights"], time_s)
    light_vals = np.array([float(row[name]) for name in ALL_LIGHT_NAMES])
    draw.text((934, 470), f"active cells: {sum(1 for r in activity_rows_at(data, time_s) if r['dominant_activity'] != 'empty')}", fill=TEXT, font=FONT_16)
    draw.text((934, 502), f"mean lamp level: {light_vals.mean():.2f}", fill=TEXT, font=FONT_16)
    draw.text((934, 534), f"min / max: {light_vals.min():.2f} / {light_vals.max():.2f}", fill=TEXT, font=FONT_16)
    draw.text((934, 580), "Inputs: animation frame + cell activity + lamp data", fill=MUTED, font=FONT_12)
    return image


def compact_dashboard_frame(data: dict, frame: Image.Image, time_s: float) -> Image.Image:
    full = dashboard_frame(data, frame, time_s, size=(1280, 720))
    return full.resize((640, 720), Image.Resampling.LANCZOS)


def iter_video_frames(path: Path, fps: float, duration: float):
    reader = imageio.get_reader(path)
    total_frames = max(1, int(round(fps * duration)))
    for idx in range(total_frames):
        time_s = min(duration, idx / fps)
        yield idx, time_s, frame_from_reader(reader, idx, total_frames)
    reader.close()


def write_video(path: Path, fps: float, frame_iter):
    path.parent.mkdir(parents=True, exist_ok=True)
    with imageio.get_writer(path, fps=fps, codec="libx264", quality=8, macro_block_size=16) as writer:
        for frame in frame_iter:
            writer.append_data(np.asarray(frame))


def make_standalone_videos(data: dict, video_path: Path, fps: float, duration: float):
    renderers = [
        ("activity_heatmap_video.mp4", activity_heatmap_frame),
        ("light_matrix_video.mp4", light_matrix_frame),
        ("lighting_dashboard_video.mp4", dashboard_frame),
    ]
    for filename, renderer in renderers:
        def frames(renderer=renderer):
            for _idx, time_s, frame in iter_video_frames(video_path, fps, duration):
                yield renderer(data, frame, time_s)

        write_video(COMPANION_DIR / filename, fps, frames())
        print(f"created {COMPANION_DIR / filename}")


def make_combined_video(data: dict, video_path: Path, fps: float, duration: float):
    def frames():
        for _idx, time_s, frame in iter_video_frames(video_path, fps, duration):
            left = resize_cover(frame, (1280, 720))
            right = compact_dashboard_frame(data, frame, time_s)
            canvas = Image.new("RGB", (1920, 720), BG)
            canvas.paste(left, (0, 0))
            canvas.paste(right, (1280, 0))
            draw = ImageDraw.Draw(canvas)
            draw.line((1280, 0, 1280, 720), fill=(42, 50, 62), width=2)
            yield canvas

    write_video(VIDEO_DIR / "smart_lighting_demo_with_dashboard.mp4", fps, frames())
    print(f"created {VIDEO_DIR / 'smart_lighting_demo_with_dashboard.mp4'}")


def main():
    COMPANION_DIR.mkdir(parents=True, exist_ok=True)
    video_path = main_video_path()
    fps, duration, width, height = video_meta(video_path)
    data = parse_data()
    print(f"source video: {video_path} ({width}x{height}, {fps:.3f} fps, {duration:.3f}s)")
    make_standalone_videos(data, video_path, fps, duration)


if __name__ == "__main__":
    main()
