from __future__ import annotations

import argparse
import csv
import math
import sys
from pathlib import Path

import bpy

sys.path.append(str(Path(__file__).resolve().parent))
import create_realistic_classroom_preview as base


ROOT = Path(__file__).resolve().parents[1]
OUT_VIDEO = ROOT / "outputs" / "videos" / "smart_lighting_demo.mp4"
OUT_KEYFRAMES = ROOT / "outputs" / "videos" / "keyframes"
OUT_BLEND = ROOT / "outputs" / "blender" / "smart_lighting_demo.blend"
OUT_DATA = ROOT / "outputs" / "data"

FPS = 24
DURATION_S = 20.0
FRAME_END = int(FPS * DURATION_S)
CYCLES_LIGHT_GAIN = 1.35
EEVEE_LIGHT_GAIN = 3.0
STUDENT_COUNT = 56
LIGHT_NAMES = [f"ceiling_light_r{r:02d}_c{c:02d}" for r in range(1, 6) for c in range(1, 5)]
LINEAR_NAMES = ["front_linear_light_left", "front_linear_light_right"]
ALL_LIGHT_NAMES = LIGHT_NAMES + LINEAR_NAMES
ACTIVITY_CATEGORIES = ["empty", "listening", "writing", "projection", "blackboard-writing", "discussion", "walking"]

TIMELINE = [
    ("empty_safety", 0.0, 2.2),
    ("class_mode", 2.2, 8.0),
    ("break_mode", 8.0, 10.8),
    ("projection_mode", 10.8, 14.0),
    ("self_study", 14.0, 17.2),
    ("final_self_study", 17.2, 20.0),
]

KEYFRAMES = [
    ("keyframe_01_empty_safety.png", "empty_safety", 1.2),
    ("keyframe_02_class_mode.png", "class_mode", 6.8),
    ("keyframe_03_break_mode.png", "break_mode", 9.2),
    ("keyframe_04_projection_mode.png", "projection_mode", 12.2),
    ("keyframe_05_self_study_mode.png", "self_study", 19.0),
]

PERSON_EVENTS: dict[int, list[tuple[float, tuple[float, float, float], bool, bool]]] = {}
WORK_SURFACE_CELLS: list[dict] = []


def parse_args() -> argparse.Namespace:
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1 :]
    else:
        argv = []
    parser = argparse.ArgumentParser()
    parser.add_argument("--keyframes-only", action="store_true")
    return parser.parse_args(argv)


def frame_at(time_s: float) -> int:
    return max(1, min(FRAME_END, int(round(time_s * FPS))))


def phase_at(time_s: float) -> str:
    for name, start, end in TIMELINE:
        if start <= time_s < end:
            return name
    return TIMELINE[-1][0]


def public_mode(mode: str) -> str:
    return "self_study" if mode == "final_self_study" else mode


def smoothstep(edge0: float, edge1: float, x: float) -> float:
    if edge1 == edge0:
        return 1.0
    t = max(0.0, min(1.0, (x - edge0) / (edge1 - edge0)))
    return t * t * (3.0 - 2.0 * t)


def transition_width(prev_name: str, next_name: str) -> float:
    if next_name == "projection_mode":
        return 0.35
    if prev_name == "projection_mode" and next_name == "self_study":
        return 0.45
    if prev_name == "empty_safety" and next_name == "class_mode":
        return 1.00
    return 0.80


def blend_modes(time_s: float) -> dict[str, float]:
    raw = {name: 1.0 if phase_at(time_s) == name else 0.0 for name, _s, _e in TIMELINE}
    for idx in range(len(TIMELINE) - 1):
        prev_name, _start, end = TIMELINE[idx]
        next_name, next_start, _next_end = TIMELINE[idx + 1]
        transition = transition_width(prev_name, next_name)
        if end <= time_s <= next_start + transition:
            t = smoothstep(end, next_start + transition, time_s)
            raw[prev_name] = 1.0 - t
            raw[next_name] = t
            for name in raw:
                if name not in (prev_name, next_name):
                    raw[name] = 0.0
            break
    total = sum(raw.values()) or 1.0
    return {k: v / total for k, v in raw.items()}


def seating_positions() -> list[tuple[float, float, float]]:
    width = base.P["room_width"]
    start_y = base.seat_start_y()
    center_left = width / 2 - base.P["center_aisle_width"] / 2
    center_right = width / 2 + base.P["center_aisle_width"] / 2
    left_x0 = base.P["left_aisle_width"] + 0.30
    left_w = center_left - left_x0 - 0.30
    right_x0 = center_right + 0.30
    right_w = width - base.P["right_aisle_width"] - right_x0 - 0.30
    seats = []
    for row in range(base.P["desk_row_count"]):
        y = start_y + row * base.P["row_depth"] + 0.15
        z = base.tier_z(y) + 0.04
        for x0, block_w in ((left_x0, left_w), (right_x0, right_w)):
            for slot in (1, 3, 5):
                x = x0 + slot * block_w / base.P["seat_modules_per_block"]
                seats.append((x, y, z))
    return seats


CLASS_SEAT_SLOTS_BY_ROW = (
    (0, 2, 3, 5),
    (1, 2, 4, 5),
    (0, 1, 3, 5),
    (0, 2, 3, 4),
    (1, 2, 4, 5),
    (0, 2, 3, 5),
    (0, 1, 4, 5),
    (1, 2, 3, 5),
    (0, 2, 4, 5),
    (0, 1, 3, 4),
    (1, 3, 4, 5),
    (0, 2, 3, 5),
)
CLASS_SEATS = [row * 6 + slot for row, slots in enumerate(CLASS_SEAT_SLOTS_BY_ROW) for slot in slots]
SELF_STUDY_SEATS = [22, 33, 47, 58, 48, 63, 61, 66]
SELF_STUDY_STUDENT_BY_SEAT = {seat_idx: CLASS_SEATS.index(seat_idx) for seat_idx in SELF_STUDY_SEATS}
SELF_STUDY_STUDENTS = set(SELF_STUDY_STUDENT_BY_SEAT.values())
BREAK_STAND_POINTS = [
    (0.58, 2.15), (0.66, 2.85), (0.70, 4.10), (0.72, 5.65),
    (4.92, 5.25), (4.92, 6.55), (4.92, 8.40), (4.92, 10.20),
    (9.08, 5.80), (9.02, 9.20),
]


def work_surface_cells() -> list[dict]:
    if WORK_SURFACE_CELLS:
        return WORK_SURFACE_CELLS
    seats = seating_positions()
    cells: list[dict] = []
    for seat_idx, (x, y, z) in enumerate(seats):
        cells.append({
            "id": f"desk_cell_{seat_idx:02d}",
            "center": (x, y, z + 0.68),
            "normal": (0.0, 0.0, 1.0),
            "label": "desk_work_surface",
            "visible_cameras": "rear_to_front_camera",
            "rho": 0.62,
        })
    for aisle_name, x in (
        ("door_aisle", 0.66),
        ("center_aisle", base.P["room_width"] / 2),
        ("window_aisle", base.P["room_width"] - 0.82),
    ):
        for idx, y in enumerate((2.2, 3.8, 5.4, 7.0, 8.6, 10.2, 11.8, 13.4)):
            cells.append({
                "id": f"{aisle_name}_cell_{idx:02d}",
                "center": (x, y, base.tier_z(y) + 0.03),
                "normal": (0.0, 0.0, 1.0),
                "label": "aisle_floor",
                "visible_cameras": "rear_to_front_camera",
                "rho": 0.42,
            })
    for idx, x in enumerate((3.0, 4.3, 5.6)):
        cells.append({
            "id": f"blackboard_cell_{idx:02d}",
            "center": (x, 0.13, 1.55),
            "normal": (0.0, 1.0, 0.0),
            "label": "blackboard",
            "visible_cameras": "rear_to_front_camera",
            "rho": 0.18,
        })
    for idx, x in enumerate((6.75, 7.28, 7.81)):
        cells.append({
            "id": f"projection_screen_cell_{idx:02d}",
            "center": (x, 0.12, 1.78),
            "normal": (0.0, 1.0, 0.0),
            "label": "projection_screen",
            "visible_cameras": "rear_to_front_camera",
            "rho": 0.72,
        })
    WORK_SURFACE_CELLS.extend(cells)
    return WORK_SURFACE_CELLS


def occupancy_points(mode: str) -> list[tuple[float, float, float, float]]:
    seats = seating_positions()
    if mode == "empty_safety":
        return []
    if mode == "class_mode":
        return [(seats[i][0], seats[i][1], seats[i][2], 1.0) for i in CLASS_SEATS]
    if mode == "break_mode":
        points = [(seats[i][0], seats[i][1], seats[i][2], 0.65) for i in CLASS_SEATS[:24]]
        for x, y in BREAK_STAND_POINTS:
            points.append((x, y, base.tier_z(y) + 0.04, 1.0))
        return points
    if mode == "projection_mode":
        return [(seats[i][0], seats[i][1], seats[i][2], 0.95) for i in CLASS_SEATS[:36]]
    return [(seats[i][0], seats[i][1], seats[i][2], 1.0) for i in SELF_STUDY_SEATS]


def interpolate_path(events: list[tuple[float, tuple[float, float, float], bool, bool]], time_s: float):
    ordered = sorted(events, key=lambda event: event[0])
    prev = ordered[0]
    for current in ordered[1:]:
        if time_s <= current[0]:
            if not prev[2] and not current[2]:
                return prev[1], False, prev[3]
            if not prev[2] and current[2]:
                return prev[1], False, prev[3]
            if prev[2] and not current[2]:
                return prev[1], prev[2], prev[3]
            span = max(0.001, current[0] - prev[0])
            alpha = smoothstep(prev[0], current[0], time_s)
            loc = tuple(prev[1][axis] + (current[1][axis] - prev[1][axis]) * alpha for axis in range(3))
            return loc, True, current[3] if alpha > 0.5 else prev[3]
        prev = current
    return prev[1], prev[2], prev[3]


def interpolate_activity_path(events: list[tuple[float, tuple[float, float, float], bool, bool]], time_s: float):
    ordered = sorted(events, key=lambda event: event[0])
    prev = ordered[0]
    for current in ordered[1:]:
        if time_s <= current[0]:
            if not prev[2] and not current[2]:
                return prev[1], False, prev[3], 0.0
            if not prev[2] and current[2]:
                return prev[1], False, prev[3], 0.0
            span = max(0.001, current[0] - prev[0])
            distance = math.dist(prev[1], current[1])
            speed = distance / span
            alpha = smoothstep(prev[0], current[0], time_s)
            loc = tuple(prev[1][axis] + (current[1][axis] - prev[1][axis]) * alpha for axis in range(3))
            return loc, prev[2], current[3] if alpha > 0.5 else prev[3], speed
        prev = current
    return prev[1], prev[2], prev[3], 0.0


def activity_for_person(idx: int, sitting: bool, speed: float, time_s: float) -> str:
    mode = phase_at(time_s)
    if idx == STUDENT_COUNT:
        return "walking" if speed > 0.12 else "blackboard-writing"
    if speed > 0.12 and not sitting:
        return "walking"
    if sitting and mode in ("self_study", "final_self_study") and idx in SELF_STUDY_STUDENTS:
        return "writing"
    if sitting and mode == "self_study":
        return "writing"
    if sitting and mode == "projection_mode":
        return "projection"
    if sitting and mode == "break_mode":
        return "discussion"
    if sitting:
        return "writing"
    return "discussion"


def animated_activity_points(time_s: float) -> list[tuple[float, float, float, str, float]]:
    points = []
    for idx, events in PERSON_EVENTS.items():
        loc, visible, sitting, speed = interpolate_activity_path(events, time_s)
        if visible:
            activity = activity_for_person(idx, sitting, speed, time_s)
            weight = 0.65 if idx == STUDENT_COUNT else 1.0
            points.append((loc[0], loc[1], loc[2], activity, weight))
    return points


def animated_occupancy_points(time_s: float) -> list[tuple[float, float, float, float]]:
    if not PERSON_EVENTS:
        return weighted_occupancy_by_mode(time_s)
    points = []
    for x, y, z, activity, weight in animated_activity_points(time_s):
        points.append((x, y, z, weight if activity in ("listening", "writing", "projection") else 0.85 * weight))
    return points


def weighted_occupancy_by_mode(time_s: float) -> list[tuple[float, float, float, float]]:
    result: list[tuple[float, float, float, float]] = []
    for mode, weight in blend_modes(time_s).items():
        if weight <= 0.001:
            continue
        for x, y, z, point_weight in occupancy_points(mode):
            result.append((x, y, z, point_weight * weight))
    return result


def light_level(name: str, loc: tuple[float, float, float], time_s: float) -> float:
    x, y, _z = loc
    weights = blend_modes(time_s)
    activity_points = animated_activity_points(time_s)
    person_load = min(1.0, sum(weight for *_xyz, _activity, weight in activity_points) / 40.0)
    aisle_boost = math.exp(-((x - base.P["room_width"] / 2) / 1.35) ** 2)
    door_boost = math.exp(-((x - 0.4) / 1.2) ** 2) * math.exp(-((y - 2.0) / 2.2) ** 2)
    rear = max(0.0, (y - 8.5) / 6.0)
    front_projection_zone = smoothstep(6.0, 1.8, y)

    seated_task = walking_task = standing_task = presenter_task = projection_note_task = 0.0
    for cell in work_surface_cells():
        cx, cy, _cz = cell["center"]
        cell_scores = cell_activity_scores(cell, time_s)
        radius_x, radius_y = (1.65, 2.15) if weights.get("final_self_study", 0.0) > 0.5 else (2.10, 2.55)
        influence = math.exp(-((x - cx) / radius_x) ** 2 - ((y - cy) / radius_y) ** 2)
        if cell["label"] in ("blackboard", "projection_screen"):
            influence *= 0.65
        seated_task = max(seated_task, influence * (0.96 * cell_scores["writing"] + 0.34 * cell_scores["listening"]))
        walking_task = max(walking_task, influence * 0.95 * cell_scores["walking"])
        standing_task = max(standing_task, influence * 0.54 * cell_scores["discussion"])
        presenter_task = max(presenter_task, influence * 0.56 * cell_scores["blackboard-writing"])
        projection_note_task = max(projection_note_task, influence * (0.25 + 0.35 * smoothstep(5.0, 13.2, cy)) * cell_scores["projection"])

    seated_task = min(1.12, seated_task * (1.56 if weights.get("final_self_study", 0.0) > 0.5 else 1.18))
    walking_task = min(1.00, walking_task * 1.16)
    standing_task = min(0.78, standing_task * 1.12)
    presenter_task = min(0.50, presenter_task * 1.10)
    projection_note_task = min(0.68, projection_note_task * 1.10)

    activity_level = 0.055
    activity_level += 0.86 * seated_task
    activity_level += 0.74 * walking_task
    activity_level += 0.48 * standing_task
    activity_level += 0.55 * presenter_task
    activity_level += 0.60 * projection_note_task
    activity_level += 0.10 * aisle_boost * smoothstep(0.05, 0.35, walking_task)
    activity_level += 0.12 * door_boost * smoothstep(0.05, 0.35, walking_task)

    level = weights.get("empty_safety", 0.0) * (0.11 + 0.02 * rear)
    active_weight = 1.0 - weights.get("empty_safety", 0.0)
    level += active_weight * activity_level
    level += weights.get("class_mode", 0.0) * (0.08 * person_load)
    level += weights.get("break_mode", 0.0) * (0.04 * person_load)
    level += weights.get("projection_mode", 0.0) * (0.05 + 0.09 * rear - 0.36 * front_projection_zone)
    level += weights.get("self_study", 0.0) * (0.06 * smoothstep(0.25, 0.9, person_load))

    if name in LINEAR_NAMES:
        level = 0.10
        level += 0.62 * presenter_task
        level += 0.38 * walking_task * door_boost
        level += 0.22 * weights.get("class_mode", 0.0) * person_load
        level += 0.18 * weights.get("break_mode", 0.0) * smoothstep(0.05, 0.35, walking_task)
        level += weights.get("projection_mode", 0.0) * -0.07
    return max(0.035, min(1.18, level))


def make_person_materials() -> dict[str, bpy.types.Material]:
    return {
        "blue": base.M["clothes_a"],
        "gray": base.M["clothes_b"],
        "teacher": base.M["teacher"],
        "skin": base.M["skin"],
        "metal": base.M["dark_metal"],
    }


def make_projection_screen() -> bpy.types.Material:
    material = base.mat("active projection screen glow", (0.18, 0.22, 0.26, 1), 0.38, ((0.65, 0.85, 1.0, 1), 0.02))
    base.cube("active_projection_screen_panel", (7.28, 0.082, 1.78), (2.05, 0.036, 1.16), material, 0.006)
    base.cube("active_projection_screen_top_bar", (7.28, 0.105, 2.40), (2.18, 0.052, 0.045), base.M["dark_metal"], 0.004)
    return material


def set_projection_screen_strength(material: bpy.types.Material, strength: float, frame: int):
    color = (0.76, 0.88, 1.0, 1) if strength > 0.2 else (0.18, 0.22, 0.26, 1)
    bsdf = material.node_tree.nodes.get("Principled BSDF") if material.use_nodes else None
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Emission"].default_value = (0.70, 0.88, 1.0, 1)
        bsdf.inputs["Emission Strength"].default_value = strength
        bsdf.inputs["Base Color"].keyframe_insert("default_value", frame=frame)
        bsdf.inputs["Emission"].keyframe_insert("default_value", frame=frame)
        bsdf.inputs["Emission Strength"].keyframe_insert("default_value", frame=frame)
    material.diffuse_color = color
    material.keyframe_insert("diffuse_color", frame=frame)


def animate_projection_screen(material: bpy.types.Material):
    for time_s, strength in (
        (0.0, 0.02),
        (10.5, 0.02),
        (11.1, 2.4),
        (14.0, 2.4),
        (14.8, 0.02),
        (20.0, 0.02),
    ):
        set_projection_screen_strength(material, strength, frame_at(time_s))


def make_demo_person(name: str, material: bpy.types.Material) -> list[bpy.types.Object]:
    parts = []
    parts.append(base.cyl(name + "_torso", (0, 0, 0.8), 0.105, 0.56, material, 12))
    parts.append(base.sphere(name + "_head", (0, 0, 1.18), 0.105, base.M["skin"]))
    parts.append(base.cube(name + "_left_leg", (-0.055, 0, 0.34), (0.055, 0.055, 0.42), material, 0.008))
    parts.append(base.cube(name + "_right_leg", (0.055, 0, 0.34), (0.055, 0.055, 0.42), material, 0.008))
    parts.append(base.cube(name + "_shoulders", (0, 0, 0.90), (0.28, 0.055, 0.065), material, 0.008))
    return parts


def set_person_state(parts: list[bpy.types.Object], loc: tuple[float, float, float], visible: bool, sitting: bool, frame: int):
    x, y, z = loc
    offsets = [
        (0.0, 0.0, 0.63 if sitting else 0.78),
        (0.0, 0.0, 0.98 if sitting else 1.16),
        (-0.055, 0.04 if sitting else 0.0, 0.32 if sitting else 0.36),
        (0.055, 0.04 if sitting else 0.0, 0.32 if sitting else 0.36),
        (0.0, 0.0, 0.78 if sitting else 0.90),
    ]
    for obj, (ox, oy, oz) in zip(parts, offsets):
        obj.hide_viewport = not visible
        obj.hide_render = not visible
        obj.location = (x + ox, y + oy, z + oz)
        obj.scale = (1.0, 1.0, 0.78 if sitting and "torso" in obj.name else 1.0)
        obj.keyframe_insert("hide_viewport", frame=frame)
        obj.keyframe_insert("hide_render", frame=frame)
        obj.keyframe_insert("location", frame=frame)
        obj.keyframe_insert("scale", frame=frame)


def hidden_staging(idx: int) -> tuple[float, float, float]:
    return (0.28, 1.08 + (idx % 10) * 0.045, 0.04)


def front_door_point(idx: int) -> tuple[float, float, float]:
    return (0.34, 1.48 + (idx % 5) * 0.07, 0.04)


def door_side_aisle_point(y: float) -> tuple[float, float, float]:
    return (0.62, y, base.tier_z(y) + 0.04)


def window_side_aisle_point(y: float) -> tuple[float, float, float]:
    return (base.P["room_width"] - 0.82, y, base.tier_z(y) + 0.04)


def front_open_walkway_point(x: float) -> tuple[float, float, float]:
    return (x, 2.72, base.tier_z(2.72) + 0.04)


def center_aisle_point(y: float) -> tuple[float, float, float]:
    return (base.P["room_width"] / 2, y, base.tier_z(y) + 0.04)


def aisle_point_for_x(x: float, y: float) -> tuple[float, float, float]:
    if x < 1.4:
        return door_side_aisle_point(y)
    if x > base.P["room_width"] - 1.4:
        return window_side_aisle_point(y)
    return center_aisle_point(y)


def seat_access_point(seat_idx: int) -> tuple[float, float, float]:
    seats = seating_positions()
    _sx, sy, _sz = seats[seat_idx]
    slot = seat_idx % 6
    center_left = base.P["room_width"] / 2 - base.P["center_aisle_width"] / 2
    center_right = base.P["room_width"] / 2 + base.P["center_aisle_width"] / 2
    if slot in (0, 1):
        x = 0.72
    elif slot == 2:
        x = center_left - 0.18
    elif slot == 3:
        x = center_right + 0.18
    else:
        x = base.P["room_width"] - 0.82
    return (x, sy, base.tier_z(sy) + 0.04)


def set_person_linear_interpolation(parts: list[bpy.types.Object]):
    for obj in parts:
        if not obj.animation_data or not obj.animation_data.action:
            continue
        for fcurve in obj.animation_data.action.fcurves:
            for keyframe in fcurve.keyframe_points:
                keyframe.interpolation = "LINEAR"


def set_person_path(parts: list[bpy.types.Object], events: list[tuple[float, tuple[float, float, float], bool, bool]]):
    person_idx = len(PERSON_EVENTS)
    PERSON_EVENTS[person_idx] = sorted(events, key=lambda event: event[0])
    last_frame = -1
    for time_s, loc, visible, sitting in sorted(events, key=lambda event: event[0]):
        frame = frame_at(time_s)
        if frame == last_frame:
            frame += 1
        last_frame = frame
        set_person_state(parts, loc, visible, sitting, frame)
    set_person_linear_interpolation(parts)


def add_people() -> list[list[bpy.types.Object]]:
    mats = make_person_materials()
    people = []
    for idx in range(STUDENT_COUNT):
        material = mats["blue"] if idx % 3 else mats["gray"]
        people.append(make_demo_person(f"student_{idx+1:02d}", material))
    people.append(make_demo_person("teacher_01", mats["teacher"]))
    return people


def person_target(idx: int, mode: str) -> tuple[tuple[float, float, float], bool, bool]:
    seats = seating_positions()
    if idx == STUDENT_COUNT:
        if mode == "empty_safety":
            return ((base.P["room_width"] / 2, 1.2, 0.16), False, False)
        if mode in ("self_study", "final_self_study"):
            return ((base.P["room_width"] / 2, 1.2, 0.16), False, False)
        return ((base.P["room_width"] / 2 - 0.9, 1.35, 0.16), True, False)
    if mode == "empty_safety":
        return ((0.45, 1.35 + idx * 0.03, 0.04), False, False)
    if mode == "class_mode":
        seat_idx = CLASS_SEATS[idx % len(CLASS_SEATS)]
        visible = idx < len(CLASS_SEATS)
        return (seats[seat_idx], visible, True)
    if mode == "break_mode":
        if idx < len(BREAK_STAND_POINTS):
            x, y = BREAK_STAND_POINTS[idx]
            return ((x, y, base.tier_z(y) + 0.04), True, False)
        if idx < 34:
            seat_idx = CLASS_SEATS[idx % len(CLASS_SEATS)]
            return (seats[seat_idx], True, True)
        return ((0.55, 2.1, 0.04), False, False)
    if mode == "projection_mode":
        if idx < 36 or idx in SELF_STUDY_STUDENTS:
            seat_idx = CLASS_SEATS[idx % len(CLASS_SEATS)]
            return (seats[seat_idx], True, True)
        return ((0.55, 2.1, 0.04), False, False)
    if idx in SELF_STUDY_STUDENTS:
        return (seats[CLASS_SEATS[idx]], True, True)
    return ((0.45, 2.0 + idx * 0.04, 0.04), False, False)


def animate_people(people: list[list[bpy.types.Object]]):
    PERSON_EVENTS.clear()
    seats = seating_positions()
    teacher_idx = STUDENT_COUNT
    for idx, parts in enumerate(people):
        if idx == teacher_idx:
            teacher_hidden = hidden_staging(teacher_idx)
            teacher_front = (base.P["room_width"] / 2 - 0.9, 1.35, 0.16)
            teacher_walkway = front_open_walkway_point(teacher_front[0])
            teacher_door_aisle = door_side_aisle_point(2.18)
            teacher_door = front_door_point(teacher_idx)
            set_person_path(parts, [
                (0.0, teacher_hidden, False, False),
                (2.20, teacher_hidden, False, False),
                (2.32, teacher_door, True, False),
                (2.56, teacher_door_aisle, True, False),
                (2.84, teacher_walkway, True, False),
                (3.14, teacher_front, True, False),
                (16.55, teacher_front, True, False),
                (16.85, teacher_walkway, True, False),
                (17.10, teacher_door_aisle, True, False),
                (17.34, teacher_door, True, False),
                (17.62, teacher_hidden, False, False),
                (20.0, teacher_hidden, False, False),
            ])
            continue

        events: list[tuple[float, tuple[float, float, float], bool, bool]] = [
            (0.0, hidden_staging(idx), False, False),
            (2.4, hidden_staging(idx), False, False),
        ]

        if idx < len(CLASS_SEATS):
            class_seat_idx = CLASS_SEATS[idx]
            class_seat = seats[class_seat_idx]
            class_access = seat_access_point(class_seat_idx)
            class_aisle = aisle_point_for_x(class_access[0], class_seat[1])
            entry_delay = (idx % 16) * 0.080 + (idx // 16) * 0.180
            events.extend([
                (2.25 + entry_delay, front_door_point(idx), True, False),
                (2.48 + entry_delay, door_side_aisle_point(2.18), True, False),
                (2.86 + entry_delay, front_open_walkway_point(class_access[0]), True, False),
                (3.34 + entry_delay, class_aisle, True, False),
                (3.78 + entry_delay, class_access, True, False),
                (4.20 + entry_delay, class_seat, True, True),
                (8.00, class_seat, True, True),
            ])

            projection_visible = True
            if idx < len(BREAK_STAND_POINTS):
                bx, by = BREAK_STAND_POINTS[idx]
                break_point = (bx, by, base.tier_z(by) + 0.04)
                break_delay = (idx % 5) * 0.045
                break_route = aisle_point_for_x(bx, by)
                wander_y_a = max(2.15, min(base.P["room_length"] - 2.8, by + (0.55 if idx % 2 == 0 else -0.45)))
                wander_y_b = max(2.15, min(base.P["room_length"] - 2.8, by + (-0.35 if idx % 2 == 0 else 0.50)))
                wander_a = aisle_point_for_x(bx, wander_y_a)
                wander_b = aisle_point_for_x(bx, wander_y_b)
                events.extend([
                    (8.10 + break_delay, class_access, True, False),
                    (8.38 + break_delay, class_aisle, True, False),
                    (8.58 + break_delay, break_route, True, False),
                    (8.82 + break_delay, break_point, True, False),
                    (9.24 + break_delay, wander_a, True, False),
                    (9.62 + break_delay, break_point, True, False),
                    (9.96 + break_delay, wander_b, True, False),
                ])
                if projection_visible:
                    events.extend([
                        (10.22 + break_delay, break_route, True, False),
                        (10.38 + break_delay, class_aisle, True, False),
                        (10.52 + break_delay, class_access, True, False),
                        (10.68 + break_delay, class_seat, True, True),
                        (14.00, class_seat, True, True),
                    ])
            elif projection_visible:
                events.extend([
                    (8.40, class_seat, True, True),
                    (10.80, class_seat, True, True),
                    (14.00, class_seat, True, True),
                ])

            if idx in SELF_STUDY_STUDENTS:
                events.extend([
                    (14.00, class_seat, True, True),
                    (20.00, class_seat, True, True),
                ])
            elif projection_visible:
                leave_start = 14.05 + (idx % 24) * 0.040 + (idx // 24) * 0.120
                events.extend([
                    (leave_start - 0.12, class_seat, True, True),
                    (leave_start, class_access, True, False),
                    (leave_start + 0.45, class_aisle, True, False),
                    (leave_start + 0.92, front_open_walkway_point(class_access[0]), True, False),
                    (leave_start + 1.35, door_side_aisle_point(2.18), True, False),
                    (leave_start + 1.72, front_door_point(idx), True, False),
                    (leave_start + 2.02, hidden_staging(idx), False, False),
                    (20.00, hidden_staging(idx), False, False),
                ])
            else:
                events.append((20.00, hidden_staging(idx), False, False))
        else:
            events.append((20.00, hidden_staging(idx), False, False))

        set_person_path(parts, events)


def configure_render(keyframes_only: bool):
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = FRAME_END
    scene.frame_set(1)
    scene.render.fps = FPS
    scene.frame_step = 1
    if keyframes_only:
        scene.render.engine = "CYCLES"
        scene.cycles.samples = 72
        scene.cycles.use_denoising = True
        scene.cycles.denoiser = "OPENIMAGEDENOISE"
        scene.cycles.max_bounces = 4
        scene.cycles.diffuse_bounces = 2
        scene.cycles.glossy_bounces = 2
    else:
        scene.render.engine = "CYCLES"
        scene.cycles.samples = 48
        scene.cycles.use_denoising = True
        scene.cycles.denoiser = "OPENIMAGEDENOISE"
        scene.cycles.max_bounces = 4
        scene.cycles.diffuse_bounces = 2
        scene.cycles.glossy_bounces = 2
    scene.world.color = (0.002, 0.0022, 0.0025)
    scene.view_settings.view_transform = "Filmic"
    scene.view_settings.look = "Medium High Contrast"
    scene.view_settings.exposure = -0.15
    scene.view_settings.gamma = 1.0
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.image_settings.file_format = "PNG"


def index_lights(light_mats):
    return {lamp.name: (lamp, cover, float(base_energy), (float(lamp.location.x), float(lamp.location.y), float(lamp.location.z))) for lamp, cover, base_energy, _ri, _ci in light_mats}


def apply_light_levels(light_map, time_s: float, frame: int | None = None):
    gain = CYCLES_LIGHT_GAIN if bpy.context.scene.render.engine == "CYCLES" else EEVEE_LIGHT_GAIN
    for name, (lamp, cover, base_energy, loc) in light_map.items():
        level = light_level(name, loc, time_s)
        lamp.data.energy = base_energy * level * gain
        base.set_lamp_cover_strength(cover, level)
        if frame is not None:
            lamp.data.keyframe_insert("energy", frame=frame)
            material = cover.data.materials[0]
            bsdf = material.node_tree.nodes.get("Principled BSDF")
            if bsdf:
                bsdf.inputs["Emission Strength"].keyframe_insert("default_value", frame=frame)


def cell_activity_scores(cell: dict, time_s: float) -> dict[str, float]:
    x, y, _z = cell["center"]
    scores = {activity: 0.0 for activity in ACTIVITY_CATEGORIES}
    for px, py, _pz, activity, weight in animated_activity_points(time_s):
        if activity == "walking":
            rx, ry = 1.45, 1.95
        elif activity == "blackboard-writing":
            rx, ry = 1.85, 1.70
        elif activity == "projection":
            rx, ry = 1.45, 1.90
        elif activity == "discussion":
            rx, ry = 1.20, 1.55
        elif activity == "listening":
            rx, ry = 1.20, 1.55
        else:
            rx, ry = 0.82, 1.05
        dist = math.hypot((x - px) / rx, (y - py) / ry)
        scores[activity] += weight * math.exp(-(dist * dist))
    if cell["label"] == "blackboard" and phase_at(time_s) in ("class_mode", "break_mode"):
        scores["blackboard-writing"] = max(scores["blackboard-writing"], 0.35)
    if cell["label"] == "projection_screen" and phase_at(time_s) == "projection_mode":
        scores["projection"] = max(scores["projection"], 0.85)
    for activity in scores:
        scores[activity] = min(1.0, scores[activity])
    active_max = max(scores[activity] for activity in ACTIVITY_CATEGORIES if activity != "empty")
    if active_max < 0.45:
        for activity in ACTIVITY_CATEGORIES:
            scores[activity] = 0.0
        scores["empty"] = 1.0
    else:
        scores["empty"] = max(0.0, 1.0 - smoothstep(0.35, 0.55, active_max))
    return scores


def animate_lights(light_map):
    for frame in range(1, FRAME_END + 1, 8):
        time_s = (frame - 1) / FPS
        apply_light_levels(light_map, time_s, frame)
    apply_light_levels(light_map, DURATION_S, FRAME_END)


def export_data(light_map):
    OUT_DATA.mkdir(parents=True, exist_ok=True)
    with (OUT_DATA / "demo_timeline.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["mode", "start_s", "end_s", "description"])
        writer.writerows([
            ("empty_safety", 0.0, 2.2, "Low readable safety lighting, no occupants."),
            ("class_mode", 2.2, 8.0, "Students enter from the front door, settle, then remain in a stable class segment."),
            ("break_mode", 8.0, 10.8, "Aisles and door circulation get priority lighting while students walk and return."),
            ("projection_mode", 10.8, 14.0, "Front board area dims for projection while students remain seated."),
            ("self_study", 14.0, 20.0, "Dismissal finishes in about three seconds, then sparse occupants remain for stable self-study lighting."),
        ])

    samples = [round(i * 0.25, 2) for i in range(int(DURATION_S / 0.25) + 1)]
    with (OUT_DATA / "light_brightness_timeseries.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["time_s", "mode", *ALL_LIGHT_NAMES])
        for time_s in samples:
            row = [time_s, public_mode(phase_at(time_s))]
            for name in ALL_LIGHT_NAMES:
                _lamp, _cover, _base_energy, loc = light_map[name]
                row.append(round(light_level(name, loc, time_s), 4))
            writer.writerow(row)

    with (OUT_DATA / "occupancy_timeseries.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["time_s", "mode", "person_id", "x_m", "y_m", "z_m", "state", "activity"])
        for time_s in samples:
            mode = public_mode(phase_at(time_s))
            for idx in sorted(PERSON_EVENTS):
                loc, visible, sitting, speed = interpolate_activity_path(PERSON_EVENTS[idx], time_s)
                if visible:
                    activity = activity_for_person(idx, sitting, speed, time_s)
                    writer.writerow([time_s, mode, idx + 1, round(loc[0], 3), round(loc[1], 3), round(loc[2], 3), "sitting" if sitting else "standing", activity])

    with (OUT_DATA / "work_surface_cells.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["cell_id", "x_m", "y_m", "z_m", "normal_x", "normal_y", "normal_z", "semantic_label", "visible_cameras", "rho"])
        for cell in work_surface_cells():
            x, y, z = cell["center"]
            nx, ny, nz = cell["normal"]
            writer.writerow([cell["id"], round(x, 3), round(y, 3), round(z, 3), nx, ny, nz, cell["label"], cell["visible_cameras"], cell["rho"]])

    with (OUT_DATA / "activity_cell_timeseries.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["time_s", "mode", "cell_id", "x_m", "y_m", "dominant_activity", *ACTIVITY_CATEGORIES])
        for time_s in samples:
            mode = public_mode(phase_at(time_s))
            for cell in work_surface_cells():
                x, y, _z = cell["center"]
                scores = cell_activity_scores(cell, time_s)
                dominant = max(ACTIVITY_CATEGORIES, key=lambda activity: scores[activity])
                writer.writerow([
                    time_s,
                    mode,
                    cell["id"],
                    round(x, 3),
                    round(y, 3),
                    dominant,
                    *[round(scores[activity], 4) for activity in ACTIVITY_CATEGORIES],
                ])

    full_on = len(LIGHT_NAMES) * 1.0 * len(samples) + len(LINEAR_NAMES) * 1.0 * len(samples)
    smart = 0.0
    for time_s in samples:
        for name in ALL_LIGHT_NAMES:
            _lamp, _cover, _base_energy, loc = light_map[name]
            smart += light_level(name, loc, time_s)
    with (OUT_DATA / "energy_summary.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["strategy", "relative_energy", "saving_vs_full_on"])
        for strategy, value in (("full_on", full_on), ("smart_per_lamp_dimming", smart)):
            writer.writerow([strategy, round(value / full_on, 4), round(1.0 - value / full_on, 4)])


def build_scene(keyframes_only: bool):
    base.clear()
    OUT_KEYFRAMES.mkdir(parents=True, exist_ok=True)
    OUT_VIDEO.parent.mkdir(parents=True, exist_ok=True)
    OUT_BLEND.parent.mkdir(parents=True, exist_ok=True)
    base.make_materials()
    base.build_room()
    base.build_windows_and_rear()
    base.build_front_teaching_area()
    projection_material = make_projection_screen()
    base.build_tiers_and_benches()
    light_mats = base.build_ceiling_equipment()
    base.setup_camera_and_render()
    configure_render(keyframes_only)
    light_map = index_lights(light_mats)
    people = add_people()
    animate_people(people)
    animate_lights(light_map)
    animate_projection_screen(projection_material)
    export_data(light_map)
    return light_map


def render_keyframes(light_map):
    scene = bpy.context.scene
    scene.camera = bpy.data.objects["rear_to_front_camera"]
    for filename, _mode, time_s in KEYFRAMES:
        frame = frame_at(time_s)
        scene.frame_set(frame)
        apply_light_levels(light_map, time_s)
        scene.render.filepath = str(OUT_KEYFRAMES / filename)
        bpy.ops.render.render(write_still=True)


def render_video():
    scene = bpy.context.scene
    scene.camera = bpy.data.objects["rear_to_front_camera"]
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "MEDIUM"
    scene.render.ffmpeg.ffmpeg_preset = "GOOD"
    scene.render.filepath = str(OUT_VIDEO)
    bpy.ops.render.render(animation=True)


def main():
    args = parse_args()
    light_map = build_scene(args.keyframes_only)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT_BLEND))
    render_keyframes(light_map)
    if not args.keyframes_only:
        render_video()


if __name__ == "__main__":
    main()
