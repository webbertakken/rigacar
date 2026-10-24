"""Captures the rigged test sedan in the 3D viewport, for documentation and pull requests.

Run from the repository root, under a virtual display when headless:
    xvfb-run -a blender --factory-startup --python tests/screenshot.py -- out.png
Pass --steer to turn the front wheels, and --rig-only to hide the car.
"""
import os
import sys

import bpy
import gpu
from mathutils import Euler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import e2e  # noqa: E402

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = os.path.abspath(next((a for a in ARGS if not a.startswith('--')), 'rigacar.png'))


def stage(area):
    e2e.reset_scene()
    body, wheels = e2e.import_sedan()
    e2e.select_only([body, *wheels], body)
    e2e.invoke_in_viewport(bpy.ops.object.armature_car_deformation_rig)
    rig = bpy.context.object
    bpy.ops.pose.car_animation_rig_generate()
    rig.show_in_front = True
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.pose.select_all(action='DESELECT')
    if '--steer' in ARGS:
        rig.pose.bones['Steering'].location.x = .25
    if '--rig-only' in ARGS:
        for obj in (body, *wheels):
            obj.hide_set(True)
    space = area.spaces[0]
    space.shading.type = 'MATERIAL'
    space.overlay.show_floor = True
    view = space.region_3d
    view.view_perspective = 'PERSP'
    view.view_rotation = Euler((1.15, 0, -0.75)).to_quaternion()
    view.view_location = (0, 0, .45)
    view.view_distance = 4.2


def capture(window, area, region):
    view = area.spaces[0].region_3d
    width, height = region.width, region.height
    offscreen = gpu.types.GPUOffScreen(width, height)
    with bpy.context.temp_override(window=window, area=area, region=region):
        offscreen.draw_view3d(bpy.context.scene, bpy.context.view_layer, area.spaces[0], region,
                              view.view_matrix, view.window_matrix, do_color_management=True, draw_background=True)
        with offscreen.bind():
            pixels = gpu.state.active_framebuffer_get().read_color(0, 0, width, height, 4, 0, 'FLOAT')
    offscreen.free()
    pixels.dimensions = width * height * 4
    image = bpy.data.images.new('rigacar-screenshot', width, height)
    image.pixels.foreach_set(pixels)
    image.filepath_raw = OUT
    image.file_format = 'PNG'
    image.save()
    print(f'[screenshot] saved {OUT}', flush=True)
    os._exit(0)


def run():
    e2e.import_addon()
    window = bpy.context.window_manager.windows[0]
    area = max((a for a in window.screen.areas if a.type == 'VIEW_3D'), key=lambda a: a.width * a.height)
    region = next(r for r in area.regions if r.type == 'WINDOW')
    with bpy.context.temp_override(window=window, area=area, region=region):
        stage(area)
    bpy.app.timers.register(lambda: capture(window, area, region), first_interval=1.0)


if bpy.app.background:
    print('[screenshot] needs a window: run under xvfb-run without --background', flush=True)
    os._exit(2)
bpy.app.timers.register(run, first_interval=.5)
