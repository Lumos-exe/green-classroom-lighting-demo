from __future__ import annotations

import math
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
OUT_BLEND = ROOT / "outputs" / "blender" / "showcase_classroom_scene.blend"
OUT_REAR = ROOT / "outputs" / "videos" / "classroom_model_rear_to_front.png"
OUT_LOW = ROOT / "outputs" / "videos" / "classroom_model_lighting_low.png"
OUT_COMPARE = ROOT / "outputs" / "videos" / "classroom_model_lighting_compare.png"

P = {
    "room_length": 16.20,
    "room_width": 9.85,
    "room_height": 3.72,
    "tile_size": 0.60,
    "front_platform_depth": 2.95,
    "flat_rows": 6,
    "step_height": 0.105,
    "max_step_count": 6,
    "row_depth": 0.90,
    "desk_row_count": 12,
    "left_aisle_width": 0.72,
    "center_aisle_width": 1.00,
    "right_aisle_width": 0.86,
    "seat_modules_per_block": 7,
    "window_count": 4,
    "window_width": 1.95,
    "window_height": 1.95,
    "window_sill_z": 1.05,
    "ceiling_light_rows": 5,
    "ceiling_lights_per_row": 4,
}

M: dict[str, bpy.types.Material] = {}


def clear():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def mat(name, color, rough=0.65, emission=None):
    material = bpy.data.materials.new(name)
    material.diffuse_color = color
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = rough
        if emission:
            bsdf.inputs["Emission"].default_value = emission[0]
            bsdf.inputs["Emission Strength"].default_value = emission[1]
    return material


def set_emit(material, color, strength, frame):
    bsdf = material.node_tree.nodes.get("Principled BSDF") if material.use_nodes else None
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Emission"].default_value = color
        bsdf.inputs["Emission Strength"].default_value = strength
        bsdf.inputs["Base Color"].keyframe_insert("default_value", frame=frame)
        bsdf.inputs["Emission"].keyframe_insert("default_value", frame=frame)
        bsdf.inputs["Emission Strength"].keyframe_insert("default_value", frame=frame)
    material.diffuse_color = color
    material.keyframe_insert("diffuse_color", frame=frame)


def set_lamp_cover_strength(obj, scale):
    material = obj.data.materials[0]
    bsdf = material.node_tree.nodes.get("Principled BSDF") if material.use_nodes else None
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.72, 0.72, 0.68, 1)
        bsdf.inputs["Emission"].default_value = (0.92, 0.95, 0.98, 1)
        bsdf.inputs["Emission Strength"].default_value = 0.02 + scale * 0.72


def lamp_cover_material(name, base_material):
    material = base_material.copy()
    material.name = name
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.72, 0.72, 0.68, 1)
        bsdf.inputs["Emission"].default_value = (0.92, 0.95, 0.98, 1)
        bsdf.inputs["Emission Strength"].default_value = 0.02
    return material


def camera_only_glow(obj):
    obj.visible_diffuse = False
    obj.visible_glossy = False
    obj.visible_transmission = False
    obj.visible_shadow = False


def cube(name, loc, scale, material, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(material)
    repeated_preview_part = any(token in name for token in (
        "_row_",
        "_frame_",
        "_rail_",
        "_basket_",
        "_divider_",
        "seat_floor_platform",
        "stair_nosing",
        "tile_grout",
        "ceiling_grid",
        "rear_acoustic_rib",
    ))
    if bevel and not repeated_preview_part:
        obj.data.use_auto_smooth = True
        mod = obj.modifiers.new("small_radius_edges", "BEVEL")
        mod.width = bevel
        mod.segments = 2
        obj.modifiers.new("weighted_normals", "WEIGHTED_NORMAL")
    return obj


def cyl(name, loc, radius, depth, material, vertices=24, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=loc, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    try:
        bpy.ops.object.shade_smooth()
    except Exception:
        pass
    return obj


def sphere(name, loc, radius, material):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=radius, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    bpy.ops.object.shade_smooth()
    return obj


def look_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def seat_start_y():
    return P["front_platform_depth"] + 0.55


def stepped_start_y():
    return seat_start_y() + (P["flat_rows"] - 0.5) * P["row_depth"]


def tier_z(y):
    start = stepped_start_y()
    if y < start:
        return 0.0
    row = max(0, int((y - start) / P["row_depth"]) + 1)
    return min(row, P["max_step_count"]) * P["step_height"]


def make_materials():
    M.clear()
    M.update({
        "floor": mat("cool gray ceramic tile", (0.32, 0.33, 0.32, 1), 0.82),
        "tile_line": mat("dark tile grout", (0.22, 0.22, 0.20, 1), 0.9),
        "wall": mat("matte classroom warm white wall", (0.46, 0.46, 0.43, 1), 0.78),
        "back_acoustic": mat("rear beige acoustic ribbed wall", (0.54, 0.50, 0.42, 1), 0.86),
        "ceiling": mat("warm segmented suspended ceiling", (0.52, 0.51, 0.47, 1), 0.86),
        "ceiling_grid": mat("ceiling trim and beams", (0.37, 0.37, 0.35, 1), 0.80),
        "platform": mat("raised front platform gray tile", (0.30, 0.31, 0.30, 1), 0.76),
        "hazard_yellow": mat("yellow black platform warning tape yellow", (0.95, 0.73, 0.06, 1), 0.58),
        "wood": mat("light maple desk board", (0.76, 0.55, 0.30, 1), 0.48),
        "wood_edge": mat("orange-brown seat side panel", (0.58, 0.32, 0.12, 1), 0.52),
        "metal": mat("pale gray aluminum frames", (0.46, 0.47, 0.44, 1), 0.48),
        "dark_metal": mat("black equipment metal", (0.025, 0.028, 0.03, 1), 0.42),
        "board": mat("deep green chalkboard", (0.015, 0.11, 0.07, 1), 0.9),
        "whiteboard": mat("slightly worn whiteboard", (0.52, 0.53, 0.50, 1), 0.60),
        "rail": mat("blackboard silver rails", (0.50, 0.50, 0.46, 1), 0.40),
        "podium": mat("white teaching podium", (0.54, 0.54, 0.50, 1), 0.58),
        "screen": mat("front display black glass", (0.014, 0.016, 0.018, 1), 0.2, ((0.03, 0.05, 0.08, 1), 0.05)),
        "door": mat("right wall pale door panel", (0.62, 0.60, 0.55, 1), 0.62),
        "window": mat("dark gray framed glass panes", (0.055, 0.070, 0.080, 1), 0.34),
        "curtain": mat("open gray fabric curtain panels", (0.30, 0.30, 0.28, 1), 0.94),
        "curtain_shadow": mat("curtain fold shadow fabric", (0.20, 0.20, 0.19, 1), 0.96),
        "window_backing": mat("flat dark backing behind windows", (0.025, 0.030, 0.034, 1), 0.72),
        "light_diffuser": mat("matte square light diffuser", (0.80, 0.78, 0.62, 1), 0.56),
        "linear_light": mat("matte front linear lamp diffuser", (0.88, 0.84, 0.66, 1), 0.56),
        "blue_bin": mat("blue trash bin", (0.03, 0.18, 0.55, 1), 0.5),
        "black_bin": mat("black trash bin", (0.015, 0.015, 0.018, 1), 0.5),
        "skin": mat("simple skin", (0.65, 0.48, 0.36, 1), 0.7),
        "clothes_a": mat("student muted blue clothing", (0.05, 0.16, 0.32, 1), 0.72),
        "clothes_b": mat("student gray clothing", (0.21, 0.23, 0.25, 1), 0.72),
        "teacher": mat("teacher dark red clothing", (0.38, 0.08, 0.06, 1), 0.72),
    })


def build_room():
    length, width, height = P["room_length"], P["room_width"], P["room_height"]
    cube("floor_slab", (width / 2, length / 2, -0.035), (width, length, 0.07), M["floor"], 0.004)
    tile = P["tile_size"]
    x = 0.0
    while x <= width + 0.01:
        cube(f"tile_grout_x_{x:.1f}", (x, length / 2, 0.003), (0.010, length, 0.006), M["tile_line"])
        x += tile
    y = 0.0
    while y <= length + 0.01:
        cube(f"tile_grout_y_{y:.1f}", (width / 2, y, 0.004), (width, 0.010, 0.006), M["tile_line"])
        y += tile

    cube("front_teaching_wall", (width / 2, -0.045, height / 2), (width, 0.09, height), M["wall"], 0.003)
    cube("window_side_long_wall", (width + 0.045, length / 2, height / 2), (0.09, length, height), M["wall"], 0.003)
    cube("door_side_long_wall", (-0.045, length / 2, height / 2), (0.09, length, height), M["wall"], 0.003)
    cube("rear_acoustic_wall", (width / 2, length + 0.045, height / 2), (width, 0.09, height), M["back_acoustic"], 0.003)
    cube("segmented_ceiling", (width / 2, length / 2, height + 0.025), (width, length, 0.05), M["ceiling"], 0.002)

    x = 1.2
    while x < width:
        cube(f"ceiling_grid_x_{x:.1f}", (x, length / 2, height - 0.018), (0.018, length, 0.025), M["ceiling_grid"])
        x += 1.2
    y = 1.2
    while y < length:
        cube(f"ceiling_grid_y_{y:.1f}", (width / 2, y, height - 0.018), (width, 0.018, 0.025), M["ceiling_grid"])
        y += 1.2

    for y in (3.0, 6.4, 9.8, 13.2, 15.0):
        cube(f"wide_ceiling_beam_{y:.1f}", (width / 2, y, height - 0.16), (width, 0.18, 0.16), M["ceiling_grid"], 0.006)
    for x in (4.70, 7.10):
        cube(f"longitudinal_ceiling_drop_beam_{x:.1f}", (x, length / 2, height - 0.18), (0.16, length, 0.20), M["ceiling_grid"], 0.006)

    cube("window_side_gray_baseboard", (width + 0.000, length / 2, 0.12), (0.055, length, 0.24), M["tile_line"], 0.003)
    cube("door_side_gray_baseboard", (0.000, length / 2, 0.12), (0.055, length, 0.24), M["tile_line"], 0.003)


def build_windows_and_rear():
    length, height = P["room_length"], P["room_height"]
    width = P["room_width"]
    y0 = 2.45
    gap = 0.48
    for i in range(P["window_count"]):
        y = y0 + i * (P["window_width"] + gap)
        yc = y + P["window_width"] / 2
        zc = P["window_sill_z"] + P["window_height"] / 2
        sill = P["window_sill_z"]
        top = sill + P["window_height"]
        mid_z = sill + 1.28
        cube(f"window_dark_backing_{i+1}", (width + 0.060, yc, zc), (0.020, P["window_width"] - 0.08, P["window_height"] - 0.10), M["window_backing"], 0.003)
        # In the rear-to-front camera, the visually left pane maps to the
        # rear side of this side-wall window. Keep the rendered image left
        # pane larger and right pane narrower, matching the reference photo.
        split_y = y + 0.74
        left_center_y = y + 1.33
        right_center_y = y + 0.28
        left_w = 1.14
        right_w = 0.54
        cube(f"window_glass_upper_left_{i+1}", (width + 0.026, left_center_y, (mid_z + top) / 2), (0.025, left_w, top - mid_z - 0.060), M["window"], 0.004)
        cube(f"window_glass_upper_right_{i+1}", (width + 0.026, right_center_y, (mid_z + top) / 2), (0.025, right_w, top - mid_z - 0.060), M["window"], 0.004)
        cube(f"window_glass_lower_left_{i+1}", (width + 0.026, left_center_y, (sill + mid_z) / 2), (0.025, left_w, mid_z - sill - 0.060), M["window"], 0.004)
        cube(f"window_glass_lower_right_{i+1}", (width + 0.026, right_center_y, (sill + mid_z) / 2), (0.025, right_w, mid_z - sill - 0.060), M["window"], 0.004)
        cube(f"window_frame_top_{i+1}", (width - 0.010, yc, top), (0.055, P["window_width"] + 0.10, 0.055), M["dark_metal"], 0.003)
        cube(f"window_frame_bottom_{i+1}", (width - 0.010, yc, sill), (0.055, P["window_width"] + 0.10, 0.055), M["dark_metal"], 0.003)
        cube(f"window_frame_front_{i+1}", (width - 0.010, y - 0.03, zc), (0.055, 0.050, P["window_height"] + 0.10), M["dark_metal"], 0.003)
        cube(f"window_frame_back_{i+1}", (width - 0.010, y + P["window_width"] + 0.03, zc), (0.055, 0.050, P["window_height"] + 0.10), M["dark_metal"], 0.003)
        cube(f"window_horizontal_mid_rail_{i+1}", (width - 0.012, yc, mid_z), (0.055, P["window_width"] + 0.05, 0.050), M["dark_metal"], 0.003)
        cube(f"window_center_vertical_rail_{i+1}", (width - 0.012, split_y, zc), (0.055, 0.055, P["window_height"] + 0.05), M["dark_metal"], 0.003)
        cube(f"open_curtain_top_rail_{i+1}", (width - 0.050, yc, P["window_sill_z"] + P["window_height"] + 0.16), (0.065, P["window_width"] + 0.36, 0.050), M["metal"], 0.006)
        for side, panel_y in (("front", y + 0.16), ("back", y + P["window_width"] - 0.16)):
            cube(f"open_curtain_panel_{i+1}_{side}", (width - 0.060, panel_y, zc + 0.03), (0.070, 0.36, P["window_height"] + 0.42), M["curtain"], 0.014)
            for fold_idx, offset in enumerate((-0.10, 0.09)):
                cube(f"open_curtain_soft_fold_{i+1}_{side}_{fold_idx}", (width - 0.100, panel_y + offset, zc + 0.03), (0.020, 0.040, P["window_height"] + 0.36), M["curtain_shadow"], 0.004)
            cube(f"open_curtain_outer_edge_{i+1}_{side}", (width - 0.108, panel_y + (0.18 if side == "front" else -0.18), zc + 0.03), (0.018, 0.055, P["window_height"] + 0.40), M["curtain_shadow"], 0.004)
        cube(f"window_sill_{i+1}", (width - 0.12, yc, P["window_sill_z"] - 0.07), (0.20, P["window_width"] + 0.20, 0.08), M["wall"], 0.006)

    # Rear wall ribbed acoustic panels and speakers.
    panel_count = 8
    panel_w = P["room_width"] / panel_count
    for idx in range(panel_count):
        x = panel_w * (idx + 0.5)
        cube(f"rear_acoustic_panel_{idx+1}", (x, length + 0.004, 1.82), (panel_w - 0.04, 0.030, 3.20), M["back_acoustic"], 0.006)
        for stripe in range(6):
            sx = x - panel_w / 2 + 0.12 + stripe * (panel_w - 0.24) / 5
            cube(f"rear_acoustic_rib_{idx+1}_{stripe}", (sx, length - 0.010, 1.82), (0.010, 0.035, 3.15), M["ceiling_grid"])
    for x in (1.25, P["room_width"] - 1.25):
        cube(f"rear_black_speaker_{x:.1f}", (x, length - 0.055, 2.65), (0.38, 0.18, 0.70), M["dark_metal"], 0.035)

    # Window-side guard rails visible around the stepped rear landing.
    for y in (8.15, 11.35):
        cube(f"window_side_guardrail_top_{y:.1f}", (width - 0.72, y, 1.14), (0.10, 1.50, 0.055), M["metal"], 0.010)
        cube(f"window_side_guardrail_mid_{y:.1f}", (width - 0.72, y, 0.88), (0.075, 1.50, 0.040), M["metal"], 0.008)
        for py in (-0.65, 0.0, 0.65):
            cube(f"window_side_guardrail_post_{y:.1f}_{py:.1f}", (width - 0.72, y + py, 0.67), (0.075, 0.050, 0.72), M["metal"], 0.006)


def build_hazard_tape(prefix, x0, x1, y, z, along_x=True):
    count = max(8, int(abs(x1 - x0) / 0.18))
    for idx in range(count):
        x = x0 + (idx + 0.5) * (x1 - x0) / count
        material = M["hazard_yellow"] if idx % 2 == 0 else M["dark_metal"]
        if along_x:
            cube(f"{prefix}_{idx:02d}", (x, y, z), ((x1 - x0) / count * 0.86, 0.055, 0.030), material, 0.002)
        else:
            cube(f"{prefix}_{idx:02d}", (y, x, z), (0.055, (x1 - x0) / count * 0.86, 0.030), material, 0.002)


def build_tile_grout_region(prefix, x0, x1, y0, y1, z, include_y=True):
    tile = P["tile_size"]
    eps = 0.006
    x = math.ceil(x0 / tile) * tile
    while x <= x1 + 0.001:
        cube(f"{prefix}_grout_x_{x:.1f}", (x, (y0 + y1) / 2, z), (0.012, y1 - y0, eps), M["tile_line"])
        x += tile
    if include_y:
        y = math.ceil(y0 / tile) * tile
        while y <= y1 + 0.001:
            cube(f"{prefix}_grout_y_{y:.1f}", ((x0 + x1) / 2, y, z + 0.001), (x1 - x0, 0.012, eps), M["tile_line"])
            y += tile


def build_terrace_grout_region(prefix, x0, x1, y0, y1, z):
    build_tile_grout_region(prefix, x0, x1, y0, y1, z, include_y=False)
    inner_y = y0 + P["tile_size"]
    if inner_y < y1 - 0.10:
        cube(f"{prefix}_grout_y_inner", ((x0 + x1) / 2, inner_y, z + 0.001), (x1 - x0, 0.012, 0.006), M["tile_line"])


def build_front_teaching_area():
    width = P["room_width"]
    platform_z = 0.12
    cube("raised_front_teaching_platform", (width / 2 + 0.52, 1.36, platform_z / 2), (7.65, 2.45, platform_z), M["platform"], 0.010)
    cube("front_center_floor_fill_tile", (width / 2, 2.96, 0.018), (1.55, 0.76, 0.036), M["floor"], 0.004)
    cube("front_platform_front_riser", (width / 2 + 0.52, 2.58, platform_z / 2), (7.65, 0.070, platform_z), M["tile_line"], 0.003)
    cube("front_platform_right_riser", (9.57, 1.36, platform_z / 2), (0.070, 2.45, platform_z), M["tile_line"], 0.003)
    build_hazard_tape("front_platform_warning_front", 1.72, 9.38, 2.63, platform_z + 0.018)
    build_hazard_tape("front_platform_warning_right", 0.18, 2.45, 9.62, platform_z + 0.018, along_x=False)

    # Wide multi-panel board wall, matching white/green/green-board composition.
    cube("front_board_upper_rail", (width / 2, 0.052, 2.70), (7.85, 0.07, 0.055), M["rail"], 0.004)
    cube("front_board_lower_rail", (width / 2, 0.070, 0.98), (7.85, 0.09, 0.055), M["rail"], 0.004)
    cube("front_left_greenboard_top", (2.70, 0.015, 2.17), (2.15, 0.055, 0.86), M["board"], 0.010)
    cube("front_left_dark_screen_panel", (2.70, 0.018, 1.28), (2.15, 0.055, 0.80), M["screen"], 0.010)
    cube("front_center_greenboard_top", (5.05, 0.015, 2.17), (1.95, 0.055, 0.86), M["board"], 0.010)
    cube("front_center_greenboard_bottom", (5.05, 0.018, 1.28), (1.95, 0.055, 0.80), M["board"], 0.010)
    cube("front_right_whiteboard_panel", (7.28, 0.015, 1.85), (2.10, 0.055, 1.55), M["whiteboard"], 0.010)
    for x in (1.62, 3.78, 6.08, 8.45):
        cube(f"front_board_vertical_frame_{x:.1f}", (x, 0.065, 1.85), (0.055, 0.08, 1.76), M["rail"], 0.004)

    cube("white_teacher_podium_body", (width / 2, 1.28, 0.52 + platform_z), (1.24, 0.66, 1.02), M["podium"], 0.035)
    cube("white_teacher_podium_top", (width / 2, 1.16, 1.06 + platform_z), (1.55, 0.82, 0.08), M["podium"], 0.025)
    cyl("podium_round_logo", (width / 2, 0.94, 0.62 + platform_z), 0.17, 0.025, M["rail"], 32, (math.pi / 2, 0, 0))
    cube("podium_dark_red_top_inset", (width / 2, 1.15, 1.115 + platform_z), (1.24, 0.58, 0.025), M["wood_edge"], 0.012)

    cube("front_window_side_large_display", (9.05, 0.40, 1.45), (1.55, 0.075, 0.90), M["screen"], 0.020)
    cube("display_vertical_stand", (9.05, 0.62, 0.72), (0.12, 0.10, 1.05), M["dark_metal"], 0.010)
    cube("display_wheeled_base", (9.05, 0.72, 0.07), (0.95, 0.48, 0.08), M["dark_metal"], 0.010)

    cube("opposite_side_front_door_panel", (-0.020, 1.55, 1.03), (0.070, 0.92, 2.06), M["door"], 0.012)
    cube("opposite_side_front_door_window", (0.040, 1.55, 1.48), (0.025, 0.42, 0.52), M["window"], 0.006)
    cube("opposite_side_door_dark_frame_top", (0.030, 1.55, 2.08), (0.060, 1.04, 0.055), M["dark_metal"], 0.004)
    cube("opposite_side_door_dark_frame_front", (0.030, 1.02, 1.05), (0.060, 0.055, 2.10), M["dark_metal"], 0.004)
    cube("opposite_side_door_dark_frame_back", (0.030, 2.08, 1.05), (0.060, 0.055, 2.10), M["dark_metal"], 0.004)
    cube("front_notice_posters", (8.75, 0.050, 1.70), (0.64, 0.035, 0.48), M["whiteboard"], 0.004)
    cube("front_electric_box", (9.35, 0.045, 1.58), (0.42, 0.060, 0.46), M["metal"], 0.004)
    cube("front_left_speaker", (1.05, 0.060, 2.35), (0.34, 0.13, 0.58), M["dark_metal"], 0.030)
    cube("front_right_speaker", (9.28, 0.060, 2.35), (0.34, 0.13, 0.58), M["dark_metal"], 0.030)
    cyl("opposite_side_black_trash_bin", (0.45, 2.35, 0.30), 0.17, 0.55, M["black_bin"], 20)
    cyl("opposite_side_blue_trash_bin", (0.45, 2.78, 0.30), 0.17, 0.55, M["blue_bin"], 20)


def build_tiers_and_benches():
    width = P["room_width"]
    start_y = seat_start_y()
    center_left = width / 2 - P["center_aisle_width"] / 2
    center_right = width / 2 + P["center_aisle_width"] / 2
    left_x0 = P["left_aisle_width"] + 0.12
    left_w = center_left - left_x0 - 0.12
    right_x0 = center_right + 0.12
    right_w = width - P["right_aisle_width"] - right_x0 - 0.12

    # Build six clean, full-width terraces. The front half is one flat slab;
    # the rear half rises in equal row-depth steps and then stays high to the rear wall.
    flat_start = start_y - P["row_depth"] / 2
    step_start = stepped_start_y()
    floor_skin = 0.024
    cube("front_flat_seating_floor", (width / 2, (flat_start + step_start) / 2, floor_skin / 2), (width, step_start - flat_start, floor_skin), M["floor"], 0.003)
    build_tile_grout_region("front_flat_seating_floor", 0.0, width, flat_start, step_start, floor_skin + 0.006)
    for step in range(1, P["max_step_count"] + 1):
        y0 = step_start + (step - 1) * P["row_depth"]
        y1 = step_start + step * P["row_depth"]
        z = step * P["step_height"]
        cube(f"rear_terrace_floor_{step:02d}", (width / 2, (y0 + y1) / 2, z + floor_skin / 2), (width, P["row_depth"], floor_skin), M["floor"], 0.003)
        build_terrace_grout_region(f"rear_terrace_floor_{step:02d}", 0.0, width, y0, y1, z + floor_skin + 0.006)
        cube(f"rear_terrace_riser_{step:02d}", (width / 2, y0, z - P["step_height"] / 2), (width, 0.040, P["step_height"]), M["platform"], 0.002)
        cube(f"rear_terrace_nosing_{step:02d}", (width / 2, y0 + 0.018, z + floor_skin + 0.003), (width, 0.032, 0.006), M["tile_line"], 0.001)
    rear_y0 = step_start + P["max_step_count"] * P["row_depth"]
    rear_z = P["max_step_count"] * P["step_height"]
    rear_depth = max(0.4, P["room_length"] - rear_y0)
    cube("rear_high_landing_floor", (width / 2, rear_y0 + rear_depth / 2, rear_z + floor_skin / 2), (width, rear_depth, floor_skin), M["floor"], 0.003)
    build_tile_grout_region("rear_high_landing_floor", 0.0, width, rear_y0, P["room_length"], rear_z + floor_skin + 0.006)

    for row in range(P["desk_row_count"]):
        y = start_y + row * P["row_depth"]
        z = tier_z(y)
        for block, x0, block_w in (("left", left_x0, left_w), ("right", right_x0, right_w)):
            bench_y = y + 0.18
            desk_y = y - 0.18
            cube(f"{block}_long_desk_row_{row+1:02d}", (x0 + block_w / 2, desk_y, z + 0.75), (block_w, 0.30, 0.060), M["wood"], 0.018)
            cube(f"{block}_desk_front_edge_row_{row+1:02d}", (x0 + block_w / 2, desk_y - 0.17, z + 0.70), (block_w, 0.055, 0.12), M["wood_edge"], 0.012)
            cube(f"{block}_seat_plank_row_{row+1:02d}", (x0 + block_w / 2, bench_y, z + 0.42), (block_w, 0.28, 0.065), M["wood"], 0.018)
            cube(f"{block}_back_low_wood_panel_row_{row+1:02d}", (x0 + block_w / 2, bench_y + 0.36, z + 0.64), (block_w, 0.070, 0.35), M["wood_edge"], 0.018)
            for rail_idx, rail_z in enumerate((0.78, 0.90, 1.02)):
                cube(f"{block}_back_silver_rail_{row+1:02d}_{rail_idx}", (x0 + block_w / 2, bench_y + 0.45, z + rail_z), (block_w, 0.040, 0.045), M["metal"], 0.008)

            modules = P["seat_modules_per_block"]
            support_indices = [0, 2, 4, 6, modules]
            for c in support_indices:
                x = x0 + c * block_w / modules
                cube(f"{block}_desk_metal_frame_{row+1:02d}_{c:02d}", (x, desk_y, z + 0.42), (0.035, 0.060, 0.62), M["metal"], 0.004)
                cube(f"{block}_seat_metal_frame_{row+1:02d}_{c:02d}", (x, bench_y + 0.20, z + 0.35), (0.050, 0.070, 0.70), M["metal"], 0.004)
                cube(f"{block}_floor_foot_{row+1:02d}_{c:02d}", (x, bench_y + 0.08, z + 0.035), (0.34, 0.080, 0.035), M["metal"], 0.004)
            cube(f"{block}_continuous_wire_basket_row_{row+1:02d}", (x0 + block_w / 2, desk_y + 0.10, z + 0.48), (block_w - 0.28, 0.15, 0.045), M["metal"], 0.003)
            for c in (1, 3, 5):
                x = x0 + c * block_w / modules
                cube(f"{block}_seat_divider_{row+1:02d}_{c:02d}", (x, bench_y + 0.34, z + 0.67), (0.030, 0.080, 0.32), M["metal"], 0.004)


def _make_square_light(name, x, y, z):
    cover_mat = lamp_cover_material(name + "_visible_glow", M["light_diffuser"])
    cover = cube(name + "_diffuser", (x, y, z), (0.72, 0.54, 0.035), cover_mat, 0.010)
    camera_only_glow(cover)
    cube(name + "_trim", (x, y, z + 0.026), (0.84, 0.64, 0.025), M["rail"], 0.006)
    bpy.ops.object.light_add(type="AREA", location=(x, y, z - 0.08))
    lamp = bpy.context.object
    lamp.name = name
    lamp.data.shape = "RECTANGLE"
    lamp.data.size = 0.95
    lamp.data.size_y = 0.70
    lamp.data.energy = 420
    return lamp, cover


def _make_linear_light(name, x, y, z, width):
    cover_mat = lamp_cover_material(name + "_visible_glow", M["linear_light"])
    cover = cube(name + "_diffuser", (x, y, z), (width, 0.10, 0.035), cover_mat, 0.008)
    camera_only_glow(cover)
    bpy.ops.object.light_add(type="AREA", location=(x, y, z - 0.06))
    lamp = bpy.context.object
    lamp.name = name
    lamp.data.shape = "RECTANGLE"
    lamp.data.size = width
    lamp.data.size_y = 0.12
    lamp.data.energy = 600
    return lamp, cover


def build_ceiling_equipment():
    width, height = P["room_width"], P["room_height"]
    lights = []
    x_cols = [1.30, 3.60, 6.25, 8.50]
    y_rows = [2.35, 5.20, 8.05, 10.90, 13.75]
    for ri, y in enumerate(y_rows, start=1):
        for ci, x in enumerate(x_cols, start=1):
            lamp, cover = _make_square_light(f"ceiling_light_r{ri:02d}_c{ci:02d}", x, y, height - 0.055)
            lights.append((lamp, cover, 18, ri - 1, ci - 1))

    front_left, front_left_cover = _make_linear_light("front_linear_light_left", 3.35, 0.78, height - 0.070, 3.15)
    front_right, front_right_cover = _make_linear_light("front_linear_light_right", 6.35, 0.78, height - 0.070, 3.15)
    lights.append((front_left, front_left_cover, 30, -1, 0))
    lights.append((front_right, front_right_cover, 30, -1, 1))

    vent_positions = [(2.45, 3.55), (4.90, 4.20), (7.65, 4.65), (3.55, 7.70), (6.00, 9.20), (7.85, 12.90)]
    for idx, (x, y) in enumerate(vent_positions, start=1):
        cube(f"ceiling_air_vent_{idx}", (x, y, height - 0.045), (0.72, 0.42, 0.030), M["metal"], 0.006)
        for slit in range(5):
            cube(f"ceiling_air_vent_{idx}_slit_{slit}", (x - 0.24 + slit * 0.12, y, height - 0.066), (0.020, 0.40, 0.014), M["dark_metal"])

    cube("ceiling_projector_body", (width / 2, 3.15, height - 0.45), (0.52, 0.36, 0.18), M["podium"], 0.022)
    cyl("projector_lens", (width / 2, 2.95, height - 0.45), 0.075, 0.055, M["dark_metal"], 24, (math.pi / 2, 0, 0))
    cube("projector_mount", (width / 2, 3.15, height - 0.25), (0.07, 0.07, 0.30), M["dark_metal"], 0.006)
    cube("ceiling_small_camera_front", (5.25, 5.70, height - 0.26), (0.20, 0.12, 0.10), M["dark_metal"], 0.012)
    return lights


def person(name, loc, material):
    x, y, z = loc
    body = cyl(name + "_body", (x, y, z + 0.72), 0.13, 0.78, material, 18)
    head = sphere(name + "_head", (x, y, z + 1.22), 0.15, M["skin"])
    return body, head


def set_person(body, head, loc, visible, sitting, frame):
    x, y, z = loc
    body.hide_viewport = not visible
    body.hide_render = not visible
    head.hide_viewport = not visible
    head.hide_render = not visible
    body.location = (x, y, z + (0.52 if sitting else 0.72))
    head.location = (x, y, z + (0.96 if sitting else 1.22))
    for obj in (body, head):
        obj.keyframe_insert("hide_viewport", frame=frame)
        obj.keyframe_insert("hide_render", frame=frame)
        obj.keyframe_insert("location", frame=frame)


def animate_people_and_lights(light_mats):
    # Static model phase intentionally leaves the room empty; kept for API compatibility.
    for lamp, cover, base_energy, _ri, _ci in light_mats:
        lamp.data.energy = base_energy
        set_lamp_cover_strength(cover, 1.0)


def apply_lighting_state(light_mats, scale):
    for lamp, cover, base_energy, _ri, _ci in light_mats:
        lamp.data.energy = base_energy * scale
        set_lamp_cover_strength(cover, scale)


def setup_camera_and_render():
    width, length, height = P["room_width"], P["room_length"], P["room_height"]
    bpy.ops.object.camera_add(location=(5.05, length - 0.12, 2.46))
    rear = bpy.context.object
    rear.name = "rear_to_front_camera"
    rear.data.lens = 20
    rear.data.angle = math.radians(78)
    rear.data.clip_end = 90
    look_at(rear, (4.95, 1.28, 1.22))

    bpy.ops.object.camera_add(location=(1.15, 2.10, 2.38))
    front = bpy.context.object
    front.name = "front_to_back_camera"
    front.data.lens = 20
    front.data.angle = math.radians(74)
    front.data.clip_end = 90
    look_at(front, (6.00, length - 2.20, 1.45))
    bpy.context.scene.camera = rear

    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = 1
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 128
    scene.cycles.use_denoising = False
    scene.cycles.max_bounces = 4
    scene.cycles.diffuse_bounces = 2
    scene.cycles.glossy_bounces = 2
    scene.cycles.transparent_max_bounces = 2
    scene.world.color = (0.002, 0.0022, 0.0025)
    scene.view_settings.view_transform = "Filmic"
    scene.view_settings.look = "Medium High Contrast"
    scene.view_settings.exposure = -0.25
    scene.view_settings.gamma = 1.0
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.image_settings.file_format = "PNG"


def make_image_material(name, filepath):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    nodes.clear()
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(str(filepath), check_existing=False)
    emission = nodes.new("ShaderNodeEmission")
    output = nodes.new("ShaderNodeOutputMaterial")
    material.node_tree.links.new(tex.outputs["Color"], emission.inputs["Color"])
    material.node_tree.links.new(emission.outputs["Emission"], output.inputs["Surface"])
    return material


def render_lighting_compare():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    low_mat = make_image_material("compare_low_image", OUT_LOW)
    on_mat = make_image_material("compare_on_image", OUT_REAR)
    for name, x, material in (("compare_low_panel", -3.24, low_mat), ("compare_on_panel", 3.24, on_mat)):
        bpy.ops.mesh.primitive_plane_add(size=1, location=(x, 0, 0))
        obj = bpy.context.object
        obj.name = name
        obj.dimensions = (6.30, 3.55, 1)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        obj.data.materials.append(material)
    cube("compare_center_separator", (0, 0, 0.002), (0.035, 3.70, 0.01), mat("compare separator black", (0, 0, 0, 1), 0.5))
    bpy.ops.object.camera_add(location=(0, 0, 7.5))
    camera = bpy.context.object
    camera.name = "lighting_compare_camera"
    look_at(camera, (0, 0, 0))
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 7.25
    scene = bpy.context.scene
    scene.camera = camera
    scene.render.engine = "BLENDER_EEVEE"
    scene.world.color = (0, 0, 0)
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "Medium High Contrast"
    scene.view_settings.exposure = 0
    scene.render.filepath = str(OUT_COMPARE)
    bpy.ops.render.render(write_still=True)


def render_static_previews(light_mats):
    scene = bpy.context.scene
    rear = bpy.data.objects["rear_to_front_camera"]
    apply_lighting_state(light_mats, 1.0)
    scene.camera = rear
    scene.render.filepath = str(OUT_REAR)
    bpy.ops.render.render(write_still=True)
    apply_lighting_state(light_mats, 0.045)
    scene.camera = rear
    scene.render.filepath = str(OUT_LOW)
    bpy.ops.render.render(write_still=True)
    render_lighting_compare()


def main():
    clear()
    OUT_BLEND.parent.mkdir(parents=True, exist_ok=True)
    OUT_REAR.parent.mkdir(parents=True, exist_ok=True)
    make_materials()
    build_room()
    build_windows_and_rear()
    build_front_teaching_area()
    build_tiers_and_benches()
    lights = build_ceiling_equipment()
    animate_people_and_lights(lights)
    setup_camera_and_render()
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT_BLEND))
    render_static_previews(lights)


if __name__ == "__main__":
    main()
