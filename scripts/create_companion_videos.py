from __future__ import annotations

import csv
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
}
MODE_LABELS = {
    "empty_safety": "empty safety",
    "class_mode": "class mode",
    "break_mode": "break mode",
    "projection_mode": "projection mode",
    "self_study": "self study",
}

BG = (15, 20, 27)
PANEL = (25, 31, 40)
PANEL_2 = (31, 38, 49)
GRID = (66, 76, 91)
TEXT = (226, 232, 240)
MUTED = (154, 164, 178)


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
FONT_26 = load_font(26, True)
FONT_32 = load_font(32, True)
FONT_48 = load_font(48, True)


def main_video_path() -> Path:
    if MAIN_VIDEO.exists():
        return MAIN_VIDEO
    raise FileNotFoundError(f"Main animation video not found: {MAIN_VIDEO}")


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
    ]
    missing = [name for name in required if not (DATA_DIR / name).exists()]
    if missing:
        raise FileNotFoundError(f"Missing data files: {missing}")

    timeline = read_csv(DATA_DIR / "demo_timeline.csv")
    occupancy = read_csv(DATA_DIR / "occupancy_timeseries.csv")
    cell_rows = read_csv(DATA_DIR / "work_surface_cells.csv")
    activity_rows = read_csv(DATA_DIR / "activity_cell_timeseries.csv")
    light_rows = read_csv(DATA_DIR / "light_brightness_timeseries.csv")

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


def light_percent(value: float) -> int:
    return int(round(max(0.0, min(1.0, value / 1.18)) * 100))


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


def draw_room_grid(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], text_labels: bool = True):
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
    if text_labels:
        draw.text((left_top[0] + 8, left_top[1] + 7), "front board", fill=MUTED, font=FONT_11)
        draw.text((right_bottom[0] - 116, left_top[1] + 7), "door side", fill=MUTED, font=FONT_11)
        draw.text((left_top[0] + 8, left_top[1] + 24), "window side", fill=MUTED, font=FONT_11)
        draw.text((left_top[0] + 8, right_bottom[1] - 20), "rear camera side", fill=MUTED, font=FONT_11)
        return

    board_y = left_top[1] + 8
    draw.rounded_rectangle((left_top[0] + 34, board_y, right_bottom[0] - 34, board_y + 5), radius=2, fill=(88, 100, 116))
    door_x = right_bottom[0] - 7
    door_y = left_top[1] + 42
    draw.line((door_x, door_y, door_x, door_y + 52), fill=(138, 153, 170), width=3)
    cam_y = right_bottom[1] - 14
    cam_x = (left_top[0] + right_bottom[0]) // 2
    draw.polygon([(cam_x, cam_y), (cam_x - 8, cam_y + 10), (cam_x + 8, cam_y + 10)], fill=(118, 173, 220))


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


def draw_cell_map(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    data: dict,
    time_s: float,
    show_people: bool,
    room_text_labels: bool = True,
):
    draw_room_grid(draw, box, text_labels=room_text_labels)
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


def draw_light_matrix(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    data: dict,
    time_s: float,
    labels: bool = True,
    large_labels: bool = False,
):
    row = nearest(data["lights"], time_s)
    x0, y0, x1, y1 = box
    w = (x1 - x0 - 26) // 4
    linear_h = 22 if labels else 16
    bar_y = y0 + 8
    line_font = FONT_16 if large_labels else FONT_13
    percent_font = FONT_32 if large_labels else FONT_18
    position_font = FONT_16 if large_labels else FONT_12
    for idx, name in enumerate(LINEAR_NAMES):
        val = float(row[name])
        bx = x0 + 12 + idx * ((x1 - x0 - 36) // 2)
        bw = (x1 - x0 - 48) // 2
        draw.rounded_rectangle((bx, bar_y, bx + bw, bar_y + linear_h), radius=4, fill=(33, 41, 53), outline=(66, 76, 91))
        draw.rounded_rectangle(
            (bx, bar_y, bx + int(bw * min(1, val / 1.18)), bar_y + linear_h),
            radius=4,
            fill=light_color(val),
        )
        if labels:
            draw.text((bx + 8, bar_y + 2), f"line light {idx + 1}: {light_percent(val)}%", fill=TEXT, font=line_font)

    grid_y0 = y0 + linear_h + (42 if labels else 30)
    h = (y1 - grid_y0 - 10) // 5
    visual_cols = [4, 3, 2, 1]
    for r in range(5):
        for visual_c, physical_c in enumerate(visual_cols):
            name = f"ceiling_light_r{r+1:02d}_c{physical_c:02d}"
            val = float(row[name])
            x = x0 + 10 + visual_c * w
            y = grid_y0 + r * h
            color = light_color(val)
            draw.rounded_rectangle((x, y, x + w - 8, y + h - 8), radius=5, fill=color, outline=(20, 25, 32), width=1)
            if labels:
                draw.text((x + 12, y + 10), f"{light_percent(val)}%", fill=(9, 13, 18), font=percent_font)
                draw.text((x + 12, y + h - (32 if large_labels else 25)), f"R{r+1}C{physical_c}", fill=(18, 24, 30), font=position_font)


def draw_activity_stats(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], data: dict, time_s: float):
    rows = activity_rows_at(data, time_s)
    counts = Counter(row["dominant_activity"] for row in rows)
    total = max(1, sum(counts.values()))
    x0, y0, x1, _y1 = box
    y = y0
    for activity in ACTIVITY_ORDER:
        frac = counts[activity] / total
        color = ACTIVITY_COLORS[activity]
        draw.text((x0, y), activity, fill=MUTED, font=FONT_12)
        bx = x0 + 128
        bw = x1 - bx
        draw.rounded_rectangle((bx, y + 3, bx + bw, y + 14), radius=3, fill=(35, 43, 55))
        draw.rounded_rectangle((bx, y + 3, bx + int(bw * frac), y + 14), radius=3, fill=color)
        draw.text((x1 + 8, y - 1), f"{counts[activity]:02d}", fill=TEXT, font=FONT_12)
        y += 20


def energy_profiles(data: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    light_rows = data["lights"]
    times = np.array([float(row["time_s"]) for row in light_rows])
    smart_values = np.array([np.mean([float(row[name]) for name in ALL_LIGHT_NAMES]) for row in light_rows])
    sample_count = max(1, len(smart_values))
    full = np.arange(1, sample_count + 1, dtype=float) / sample_count
    smart = np.cumsum(smart_values) / sample_count
    return times, full, smart


def energy_at(data: dict, time_s: float) -> tuple[float, float, float]:
    times, full, smart = energy_profiles(data)
    idx = int(np.argmin(np.abs(times - time_s)))
    live_saving = 1.0 - smart[idx] / max(0.001, full[idx])
    return full[idx], smart[idx], max(0.0, min(1.0, live_saving))


def draw_energy_saved_chart(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], data: dict, time_s: float):
    x0, y0, x1, y1 = box
    times, full, smart = energy_profiles(data)
    total = max(0.001, float(data["timeline"][-1]["end_s"]))
    max_y = 1.0
    plot = (x0 + 12, y0 + 16, x1 - 12, y1 - 28)
    px0, py0, px1, py1 = plot
    draw.rounded_rectangle(box, radius=5, fill=(18, 24, 32), outline=(50, 60, 74))
    for frac in (0.25, 0.5, 0.75):
        yy = py1 - int(frac * (py1 - py0))
        draw.line((px0, yy, px1, yy), fill=(35, 43, 55), width=1)

    def points(values: np.ndarray) -> list[tuple[int, int]]:
        return [
            (px0 + int((float(t) / total) * (px1 - px0)), py1 - int((float(v) / max_y) * (py1 - py0)))
            for t, v in zip(times, values)
        ]

    full_pts = points(full)
    smart_pts = points(smart)
    current_idx = int(np.argmin(np.abs(times - time_s)))
    if current_idx > 1:
        fill_poly = full_pts[: current_idx + 1] + list(reversed(smart_pts[: current_idx + 1]))
        draw.polygon(fill_poly, fill=(44, 77, 63))
    for pts, color, width in [
        (full_pts, (136, 145, 158), 2),
        (smart_pts, (92, 179, 132), 3),
    ]:
        for a, b in zip(pts, pts[1:]):
            draw.line((a[0], a[1], b[0], b[1]), fill=color, width=width)

    tx = px0 + int((time_s / total) * (px1 - px0))
    draw.line((tx, py0 - 3, tx, py1 + 3), fill=(245, 248, 252), width=1)
    legend = [("full-on baseline", (136, 145, 158)), ("smart per-lamp", (92, 179, 132))]
    lx = px0
    for label, color in legend:
        draw.rounded_rectangle((lx, y1 - 19, lx + 14, y1 - 9), radius=2, fill=color)
        draw.text((lx + 19, y1 - 23), label, fill=MUTED, font=FONT_11)
        lx += 152


def draw_live_saving(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], data: dict, time_s: float):
    x0, y0, x1, y1 = box
    _full, _smart, saving = energy_at(data, time_s)
    pct = int(round(saving * 100))
    draw.text((x0, y0), f"{pct:02d}%", fill=(118, 217, 157), font=FONT_48)
    draw.text((x0, y0 + 62), "cumulative saving", fill=TEXT, font=FONT_16)
    draw.text((x0, y0 + 90), "vs full-on baseline", fill=MUTED, font=FONT_12)
    bar_y = y1 - 18
    draw.rounded_rectangle((x0, bar_y, x1, bar_y + 12), radius=4, fill=(35, 43, 55))
    draw.rounded_rectangle((x0, bar_y, x0 + int((x1 - x0) * saving), bar_y + 12), radius=4, fill=(92, 179, 132))


def draw_energy_numbers(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], data: dict, time_s: float):
    x0, y0, x1, y1 = box
    full, smart, saving = energy_at(data, time_s)
    rows = [
        ("baseline", full, (136, 145, 158)),
        ("smart", smart, (92, 179, 132)),
        ("saved", full - smart, (118, 217, 157)),
    ]
    draw.text((x0, y0), "relative energy", fill=MUTED, font=FONT_11)
    max_value = max(0.001, full)
    bar_x = x0 + 78
    bar_w = x1 - bar_x
    for idx, (label, value, color) in enumerate(rows):
        yy = y0 + 24 + idx * 23
        draw.text((x0, yy - 2), label, fill=MUTED, font=FONT_11)
        draw.rounded_rectangle((bar_x, yy, bar_x + bar_w, yy + 10), radius=3, fill=(35, 43, 55))
        draw.rounded_rectangle((bar_x, yy, bar_x + int(bar_w * max(0.0, value) / max_value), yy + 10), radius=3, fill=color)
        draw.text((bar_x + bar_w - 42, yy - 4), f"{value:.2f}", fill=TEXT, font=FONT_11)


def title_bar(draw: ImageDraw.ImageDraw, title: str, time_s: float, mode: str, width: int):
    draw.text((28, 22), title, fill=TEXT, font=FONT_22)
    draw.text((width - 230, 24), f"t = {time_s:05.2f}s", fill=TEXT, font=FONT_18)
    draw.rounded_rectangle((width - 420, 22, width - 250, 48), radius=5, fill=MODE_COLORS.get(mode, GRID))
    draw.text((width - 410, 27), MODE_LABELS.get(mode, mode.replace("_", " ")), fill=(8, 12, 16), font=FONT_13)


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


def activity_heatmap_frame(data: dict, frame: Image.Image, time_s: float, size: tuple[int, int] = (1920, 1080)) -> Image.Image:
    width, height = size
    image = Image.new("RGB", size, BG)
    draw = ImageDraw.Draw(image)
    mode = mode_at(data, time_s)
    title_bar(draw, "Real-time Occupant Activity and Work-surface Response", time_s, mode, width)
    draw_panel(draw, (36, 90, 1208, 792), "Synchronized Animation")
    draw_preview(image, frame, (60, 140, 1184, 772), label="source frame")
    draw_panel(draw, (1236, 90, 1884, 792), "Work-surface Activity Field")
    draw_cell_map(draw, (1280, 132, 1840, 760), data, time_s, show_people=True, room_text_labels=False)
    people = occupancy_rows_at(data, time_s)
    active_cells = sum(1 for r in activity_rows_at(data, time_s) if r["dominant_activity"] != "empty")
    walking = sum(1 for p in people if p["activity"] == "walking")
    draw_panel(draw, (36, 816, 1884, 1016), "Dominant Activity Counts")
    draw_activity_stats(draw, (64, 860, 870, 992), data, time_s)
    draw_activity_legend(draw, 930, 862, compact=False)
    draw.text((1240, 858), f"people {len(people)}", fill=TEXT, font=FONT_22)
    draw.text((1240, 898), f"active cells {active_cells}", fill=TEXT, font=FONT_22)
    draw.text((1240, 938), f"walking {walking}", fill=MUTED, font=FONT_16)
    draw.text((1510, 866), "white rings mark occupant locations", fill=TEXT, font=FONT_16)
    draw.text((1510, 906), "cell color encodes dominant A_t(i,k)", fill=MUTED, font=FONT_14)
    draw.text((1510, 946), "same rear-to-front orientation", fill=MUTED, font=FONT_14)
    draw_mode_timeline(draw, (72, 1038, 1848, 1058), data, time_s)
    return image


def light_matrix_frame(data: dict, frame: Image.Image, time_s: float, size: tuple[int, int] = (1920, 1080)) -> Image.Image:
    width, height = size
    image = Image.new("RGB", size, BG)
    draw = ImageDraw.Draw(image)
    mode = mode_at(data, time_s)
    title_bar(draw, "Per-lamp Brightness Control from Cell Demand", time_s, mode, width)
    draw_panel(draw, (36, 90, 1208, 792), "Synchronized Animation")
    draw_preview(image, frame, (60, 140, 1184, 772), label="source frame")
    draw_panel(draw, (1236, 90, 1884, 792), "Ceiling + Front Linear Lights")
    draw_light_matrix(draw, (1260, 138, 1860, 748), data, time_s, labels=True, large_labels=True)
    row = nearest(data["lights"], time_s)
    vals = np.array([float(row[name]) for name in ALL_LIGHT_NAMES])
    draw_panel(draw, (36, 816, 1884, 1016), "Cell-to-lamp Response")
    draw.text((64, 866), "Brightness is shown as percent of controllable maximum.", fill=TEXT, font=FONT_18)
    draw.text((64, 912), "Lamp levels are generated from work-surface cell activity through M(i,g).", fill=MUTED, font=FONT_16)
    draw.text((64, 956), "Top bars are the two front line lights; grid cells are ceiling lights.", fill=MUTED, font=FONT_16)
    metric_x = 1280
    draw.text((metric_x, 858), f"mean {light_percent(float(vals.mean()))}%", fill=TEXT, font=FONT_32)
    draw.text((metric_x, 908), f"active lamps {int(np.sum(vals > 0.35))}/22", fill=TEXT, font=FONT_22)
    draw.text((metric_x, 948), f"min {light_percent(float(vals.min()))}%   max {light_percent(float(vals.max()))}%", fill=MUTED, font=FONT_18)
    draw.text((metric_x, 982), f"brightness range {light_percent(float(vals.max() - vals.min()))}%", fill=MUTED, font=FONT_18)
    draw_mode_timeline(draw, (72, 1038, 1848, 1058), data, time_s)
    return image


def dashboard_frame(data: dict, frame: Image.Image, time_s: float, size: tuple[int, int] = (1920, 1080)) -> Image.Image:
    width, height = size
    image = Image.new("RGB", size, BG)
    draw = ImageDraw.Draw(image)
    mode = mode_at(data, time_s)
    title_bar(draw, "Real-time Lighting Control Dashboard", time_s, mode, width)

    left = (36, 90, 944, 1038)
    right = (976, 90, 1884, 1038)

    draw_panel(draw, (left[0], left[1], left[2], 655), "Animation Reference")
    draw_preview(image, frame, (60, 140, 920, 624), label="source frame")

    draw_panel(draw, (left[0], 675, left[2], left[3]), "Energy Saved So Far")
    draw_energy_saved_chart(draw, (60, 730, 640, 1008), data, time_s)
    draw_live_saving(draw, (684, 718, 920, 858), data, time_s)
    draw.text((684, 884), "smart per-lamp vs full-on", fill=MUTED, font=FONT_12)
    draw_energy_numbers(draw, (684, 916, 920, 1014), data, time_s)

    draw_panel(draw, (right[0], right[1], right[2], 560), "Work-surface Activity Field")
    draw_cell_map(draw, (1000, 140, 1556, 526), data, time_s, show_people=True, room_text_labels=False)
    draw_activity_legend(draw, 1586, 145, compact=False)
    people = occupancy_rows_at(data, time_s)
    active_cells = sum(1 for r in activity_rows_at(data, time_s) if r["dominant_activity"] != "empty")
    draw.text((1586, 330), f"people {len(people)}", fill=TEXT, font=FONT_16)
    draw.text((1586, 360), f"active cells {active_cells}", fill=TEXT, font=FONT_16)
    draw_activity_stats(draw, (1586, 402, 1808, 540), data, time_s)

    draw_panel(draw, (right[0], 580, right[2], right[3]), "Lamp Brightness Matrix")
    draw_light_matrix(draw, (1002, 632, 1652, 1012), data, time_s, labels=True)
    row = nearest(data["lights"], time_s)
    light_vals = np.array([float(row[name]) for name in ALL_LIGHT_NAMES])
    draw.text((1690, 650), f"mean {light_percent(float(light_vals.mean()))}%", fill=TEXT, font=FONT_18)
    draw.text((1690, 690), f"min {light_percent(float(light_vals.min()))}%", fill=MUTED, font=FONT_14)
    draw.text((1690, 720), f"max {light_percent(float(light_vals.max()))}%", fill=MUTED, font=FONT_14)
    draw.text((1690, 770), f"active {int(np.sum(light_vals > 0.35))}/22", fill=TEXT, font=FONT_16)
    front_vals = [float(row[name]) for name in LINEAR_NAMES]
    draw.text((1690, 820), f"linear avg {light_percent(float(np.mean(front_vals)))}%", fill=MUTED, font=FONT_14)
    draw.text((1690, 856), f"brightness range {light_percent(float(light_vals.max() - light_vals.min()))}%", fill=MUTED, font=FONT_14)
    draw_mode_timeline(draw, (72, 1050, 1848, 1066), data, time_s)
    return image


def iter_video_frames(path: Path, fps: float, duration: float):
    reader = imageio.get_reader(path)
    total_frames = max(1, int(round(fps * duration)))
    for idx in range(total_frames):
        time_s = min(duration, idx / fps)
        yield idx, time_s, frame_from_reader(reader, idx, total_frames)
    reader.close()


def write_video(path: Path, fps: float, frame_iter):
    path.parent.mkdir(parents=True, exist_ok=True)
    with imageio.get_writer(path, fps=fps, codec="libx264", quality=8, macro_block_size=1) as writer:
        for frame in frame_iter:
            writer.append_data(np.asarray(frame))


def make_dashboard_video(data: dict, video_path: Path, fps: float, duration: float):
    def frames():
        for _idx, time_s, frame in iter_video_frames(video_path, fps, duration):
            yield dashboard_frame(data, frame, time_s)

    output = COMPANION_DIR / "lighting_dashboard_video.mp4"
    write_video(output, fps, frames())
    print(f"created {output}")


def make_light_matrix_video(data: dict, video_path: Path, fps: float, duration: float):
    def frames():
        for _idx, time_s, frame in iter_video_frames(video_path, fps, duration):
            yield light_matrix_frame(data, frame, time_s)

    output = COMPANION_DIR / "light_matrix_video.mp4"
    write_video(output, fps, frames())
    print(f"created {output}")


def make_activity_heatmap_video(data: dict, video_path: Path, fps: float, duration: float):
    def frames():
        for _idx, time_s, frame in iter_video_frames(video_path, fps, duration):
            yield activity_heatmap_frame(data, frame, time_s)

    output = COMPANION_DIR / "activity_heatmap_video.mp4"
    write_video(output, fps, frames())
    print(f"created {output}")


def main():
    COMPANION_DIR.mkdir(parents=True, exist_ok=True)
    video_path = main_video_path()
    fps, duration, width, height = video_meta(video_path)
    data = parse_data()
    print(f"source video: {video_path} ({width}x{height}, {fps:.3f} fps, {duration:.3f}s)")
    make_activity_heatmap_video(data, video_path, fps, duration)
    make_light_matrix_video(data, video_path, fps, duration)
    make_dashboard_video(data, video_path, fps, duration)


if __name__ == "__main__":
    main()
