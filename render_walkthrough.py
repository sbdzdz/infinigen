import argparse
import os
import sys
from datetime import datetime

import bpy
import numpy as np

from infinigen.core.placement.animation_policy import animate_trajectory
from infinigen.core.placement.camera import camera_selection_preprocessing
from infinigen.core.util.rrt import (
    RRT,
    AnimPolicyRRT,
    validate_cam_pose_rrt,
    validate_node_indoors,
)

SETTINGS = {
    "quick": {
        "label": "Quick Test",
        "frame_end": 72,
        "samples": 32,
        "resolution": (480, 270),
        "output_prefix": "quick_test",
        "ffmpeg_crf_arg": "-crf 23",
        "estimate_seconds_per_frame": 0.10,
        "fallback_yaw_mid_deg": 18,
        "fallback_yaw_end_deg": -12,
        "rrt_step_range": (0.8, 1.6),
        "rrt_stride_range": (24, 48),
        "rrt_max_iter": 3000,
        "speed": ("uniform", 0.9, 1.7),
        "rot": ("normal", 0, [8, 0, 10], 3),
        "min_pixels_check": 120,
        "max_step_tries": 35,
        "max_full_retries": 6,
    },
    "full": {
        "label": "Full Quality",
        "frame_end": 120,
        "samples": 256,
        "resolution": (1280, 720),
        "output_prefix": "video",
        "ffmpeg_crf_arg": "",
        "estimate_seconds_per_frame": 0.75,
        "fallback_yaw_mid_deg": 24,
        "fallback_yaw_end_deg": -16,
        "rrt_step_range": (0.9, 1.8),
        "rrt_stride_range": (40, 70),
        "rrt_max_iter": 4000,
        "speed": ("uniform", 0.8, 1.5),
        "rot": ("normal", 0, [7, 0, 9], 3),
        "min_pixels_check": 160,
        "max_step_tries": 40,
        "max_full_retries": 8,
    },
}


def parse_mode():
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument(
        "--quick", action="store_true", help="Use quick/test render settings"
    )
    parser.add_argument("--test", action="store_true", help="Alias for --quick")
    parser.add_argument(
        "--full", action="store_true", help="Use full-quality render settings"
    )
    args = parser.parse_args(argv)

    if args.quick or args.test:
        return "quick"
    if args.full:
        return "full"
    return "full"


def estimate_volume(obj):
    d = obj.dimensions
    return float(max(d.x, 0.01) * max(d.y, 0.01) * max(d.z, 0.01))


def split_room_and_nonroom(mesh_objs):
    room_name_tokens = ("room", "wall", "floor", "ceiling", "ceil")
    room_objs = [
        obj
        for obj in mesh_objs
        if any(token in obj.name.lower() for token in room_name_tokens)
    ]
    if len(room_objs) < 2:
        by_size = sorted(mesh_objs, key=estimate_volume, reverse=True)
        count = min(len(mesh_objs), max(2, len(mesh_objs) // 8))
        room_objs = by_size[:count]
    room_set = set(room_objs)
    nonroom_objs = [obj for obj in mesh_objs if obj not in room_set]
    return room_objs, nonroom_objs


def smooth_keyframes(obj):
    if not obj.animation_data or not obj.animation_data.action:
        return
    action = obj.animation_data.action
    if not hasattr(action, "fcurves"):
        return
    for fcurve in action.fcurves:
        for keyframe in fcurve.keyframe_points:
            keyframe.interpolation = "BEZIER"
            keyframe.handle_left_type = "AUTO_CLAMPED"
            keyframe.handle_right_type = "AUTO_CLAMPED"


def fallback_pan(scene, rig, cfg):
    if rig.animation_data:
        rig.animation_data_clear()
    start = scene.frame_start
    mid = (scene.frame_start + scene.frame_end) // 2
    end = scene.frame_end
    yaw = float(rig.rotation_euler.z)
    base_rot = np.array((np.deg2rad(90), 0.0, yaw))
    loc = np.array((rig.location.x, rig.location.y, 1.65))
    for frame_num, yaw_offset in (
        (start, 0.0),
        (mid, np.deg2rad(cfg["fallback_yaw_mid_deg"])),
        (end, np.deg2rad(cfg["fallback_yaw_end_deg"])),
    ):
        scene.frame_set(frame_num)
        rig.location = loc
        rig.rotation_euler = base_rot + np.array((0.0, 0.0, yaw_offset))
        rig.keyframe_insert(data_path="location", frame=frame_num)
        rig.keyframe_insert(data_path="rotation_euler", frame=frame_num)
    smooth_keyframes(rig)


def animate_rrt(scene, rig, cfg):
    mesh_objs = [
        obj for obj in bpy.data.objects if obj.type == "MESH" and not obj.hide_render
    ]
    if len(mesh_objs) < 2:
        raise ValueError("Not enough renderable mesh objects for RRT")
    room_objs, nonroom_objs = split_room_and_nonroom(mesh_objs)
    if len(room_objs) == 0:
        raise ValueError("Unable to infer room geometry for RRT")

    if rig.animation_data:
        rig.animation_data_clear()
    rig.location = (rig.location.x, rig.location.y, 1.65)
    rig.rotation_euler = (np.deg2rad(90), 0.0, rig.rotation_euler.z)

    scene_preprocessed = camera_selection_preprocessing(
        terrain=None, scene_objs=mesh_objs
    )
    policy = AnimPolicyRRT(
        rrt=RRT(
            obj_groups=[room_objs, nonroom_objs],
            validate_node=validate_node_indoors,
            step_range=cfg["rrt_step_range"],
            stride_range=cfg["rrt_stride_range"],
            min_node_dist_to_obstacle=0.35,
            max_iter=cfg["rrt_max_iter"],
        ),
        obj_groups=[room_objs, nonroom_objs],
        speed=cfg["speed"],
        rot=cfg["rot"],
    )

    animate_trajectory(
        obj=rig,
        bvh=scene_preprocessed["scene_bvh"],
        policy_func=policy,
        validate_pose_func=lambda cam: validate_cam_pose_rrt(
            cam,
            max_sky_percent=1.0,
            max_proxim_percent=0.5,
            min_obj_dist=0.9,
            min_pixels_check=cfg["min_pixels_check"],
        ),
        max_step_tries=cfg["max_step_tries"],
        max_full_retries=cfg["max_full_retries"],
        fatal=True,
        verbose=False,
    )
    smooth_keyframes(rig)
    return len(room_objs), len(nonroom_objs)


def apply_render_settings(scene, cfg):
    scene.view_settings.exposure = 3.0
    scene.frame_start = 1
    scene.frame_end = cfg["frame_end"]
    scene.render.fps = 24
    scene.cycles.samples = cfg["samples"]
    scene.render.resolution_x, scene.render.resolution_y = cfg["resolution"]
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"


def main():
    mode = parse_mode()
    cfg = SETTINGS[mode]

    scene = bpy.context.scene
    camera = scene.camera
    apply_render_settings(scene, cfg)

    if not (camera and camera.parent):
        print("ERROR: No camera or camera rig found!")
        return

    rig = camera.parent
    total_frames = scene.frame_end - scene.frame_start + 1
    print(f"\n=== Creating {cfg['label']} Walkthrough Video ===")
    print(f"Mode: {mode}")
    print(f"Resolution: {scene.render.resolution_x}x{scene.render.resolution_y}")
    print(f"Samples: {scene.cycles.samples}")
    print(f"Frames: {scene.frame_start} to {scene.frame_end} ({total_frames} frames)")
    print(
        f"Duration: {total_frames / scene.render.fps:.1f} seconds at {scene.render.fps} fps"
    )
    print(
        f"Estimated time: ~{total_frames * cfg['estimate_seconds_per_frame']:.0f} seconds"
    )

    try:
        room_count, nonroom_count = animate_rrt(scene, rig, cfg)
        print(
            f"Camera trajectory mode: RRT (room objs: {room_count}, non-room objs: {nonroom_count})"
        )
    except Exception as err:
        print(f"RRT animation failed: {err}")
        print("Falling back to stationary pan animation.")
        fallback_pan(scene, rig, cfg)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = (
        f"/Users/sebastian/repos/infinigen/outputs/{cfg['output_prefix']}_{timestamp}"
    )
    os.makedirs(output_dir, exist_ok=True)

    print("\n=== Rendering All Frames ===")
    print(f"Output directory: {output_dir}")
    scene.render.filepath = os.path.join(output_dir, "frame_")
    bpy.ops.render.render(animation=True)

    print("\n=== Rendering Complete ===")
    print(f"Frames saved to: {output_dir}")
    ffmpeg_cmd = (
        (
            f"ffmpeg -framerate 24 -i {output_dir}/frame_%04d.png "
            f"-c:v libx264 -pix_fmt yuv420p {cfg['ffmpeg_crf_arg']} {output_dir}/walkthrough.mp4"
        )
        .replace("  ", " ")
        .strip()
    )
    print("\nTo create video, run:")
    print(ffmpeg_cmd)


if __name__ == "__main__":
    main()
