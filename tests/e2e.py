"""End-to-end check of the add-on inside Blender.

Operators only run their invoke step with a window, so run Blender with a UI,
under a virtual display when headless, from the repository root:
    xvfb-run -a blender --factory-startup --python tests/e2e.py
Exits non-zero when any check fails.
"""
import os
import sys
import tempfile
import traceback

import bpy

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADDON_NAME = 'rigacar'

failures = []
# The generated suspension settles the body by about a millimetre at rest.
SETTLE = 2e-3


def check(condition, message):
    status = 'PASS' if condition else 'FAIL'
    print(f'[e2e] {status} {message}', flush=True)
    if not condition:
        failures.append(message)


def import_addon():
    link_dir = tempfile.mkdtemp(prefix='rigacar-e2e-')
    os.symlink(REPO, os.path.join(link_dir, ADDON_NAME))
    sys.path.insert(0, link_dir)
    import rigacar
    rigacar.register()
    return rigacar


def reset_scene():
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    for collection in (bpy.data.objects, bpy.data.collections, bpy.data.armatures, bpy.data.meshes,
                       bpy.data.actions, bpy.data.curves):
        for datablock in list(collection):
            collection.remove(datablock)
    view_layer = bpy.context.view_layer
    view_layer.active_layer_collection = view_layer.layer_collection
    bpy.context.scene.cursor.location = (0, 0, 0)


def add_cube(name, location, scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_cube_add(location=location, scale=scale)
    obj = bpy.context.object
    obj.name = name
    return obj


def add_wheel(name, location, scale=1.0):
    bpy.ops.mesh.primitive_cylinder_add(radius=.35 / scale, depth=.25 / scale, location=location,
                                        rotation=(0, 1.5708, 0))
    obj = bpy.context.object
    obj.name = name
    obj.scale = (scale, scale, scale)
    return obj


def parent_keeping_transform(child, parent):
    world = child.matrix_world.copy()
    child.parent = parent
    child.matrix_world = world


def build_scaled_parented_car():
    """The same world geometry as build_car, from scaled wheels inside a moved, scaled parent."""
    group = bpy.data.objects.new('CarGroup', None)
    bpy.context.scene.collection.objects.link(group)
    group.location = (3, -2, .5)
    group.scale = (.5, .5, .5)
    bpy.context.view_layer.update()
    body, roof, wheels, brake = build_car(wheel_scale=2.0)
    for obj in (body, *wheels, brake):
        parent_keeping_transform(obj, group)
    bpy.context.view_layer.update()
    return body, roof, wheels, brake


def build_car(wheel_scale=1.0):
    body = add_cube('Body', (0, 0, .9), scale=(.9, 2.2, .45))
    # A transformed child must not be transformed twice when sizing the body.
    roof = add_cube('Roof', (0, .3, 1.6), scale=(.7, 1, .2))
    roof.parent = body
    roof.matrix_parent_inverse = body.matrix_world.inverted()
    wheels = [
        add_wheel('Wheel.Ft.L', (.85, -1.4, .35), wheel_scale),
        add_wheel('Wheel.Ft.R', (-.85, -1.4, .35), wheel_scale),
        add_wheel('Wheel.Bk.L', (.85, 1.4, .35), wheel_scale),
        add_wheel('Wheel.Bk.R', (-.85, 1.4, .35), wheel_scale),
    ]
    brake = add_cube('WheelBrake.Ft.L', (.7, -1.4, .35), scale=(.05, .2, .2))
    bpy.context.view_layer.update()
    return body, roof, wheels, brake


def select_pose_bone(rig, name):
    pose_bone = rig.pose.bones[name]
    if hasattr(pose_bone, 'select'):
        pose_bone.select = True
    else:
        rig.data.bones[name].select = True


def viewport():
    window = bpy.context.window_manager.windows[0]
    area = next(a for a in window.screen.areas if a.type == 'VIEW_3D')
    region = next(r for r in area.regions if r.type == 'WINDOW')
    return bpy.context.temp_override(window=window, area=area, region=region)


def invoke_in_viewport(operator):
    return operator('INVOKE_DEFAULT')


def select_only(objs, active):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objs:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = active


def test_bounds(car_rig):
    reset_scene()
    body, roof, _, _ = build_car()
    xyz = car_rig.object_bounds_xyz(body)
    # Body spans y in [-2.2, 2.2] and z up to 1.35; the roof reaches z = 1.8.
    expected = [-.9, .9, -2.2, 2.2, .45, 1.8]
    check(all(abs(a - b) < 1e-4 for a, b in zip(xyz, expected)),
          f'bounds include a transformed child exactly once: {[round(v, 3) for v in xyz]}')

    coll = bpy.data.collections.new('CarParts')
    part = bpy.data.objects.new('Part', bpy.data.meshes['Cube'] if 'Cube' in bpy.data.meshes else body.data)
    coll.objects.link(part)
    bpy.ops.object.collection_instance_add(collection=coll.name, location=(10, 0, 0))
    instance = bpy.context.object
    bpy.context.view_layer.update()
    ixyz = car_rig.object_bounds_xyz(instance)
    check(ixyz is not None and abs((ixyz[0] + ixyz[1]) / 2 - 10) < 1e-4,
          f'collection instance bounds follow the instancer: {ixyz and [round(v, 3) for v in ixyz]}')

    empty = bpy.data.objects.new('LonelyEmpty', None)
    bpy.context.scene.collection.objects.link(empty)
    check(car_rig.object_bounds_xyz(empty) is None, 'an empty without geometry has no bounds')


def test_deformation_rig_without_invoke():
    reset_scene()
    result = bpy.ops.object.armature_car_deformation_rig('EXEC_DEFAULT')
    check(result == {'FINISHED'}, f'deformation rig executes without invoke: {result}')
    check('DEF-Body' in bpy.context.object.data.bones, 'exec-only rig has DEF-Body')


def test_hidden_collection_still_rigs():
    reset_scene()
    hidden = bpy.data.collections.new('Hidden')
    bpy.context.scene.collection.children.link(hidden)
    layer_coll = bpy.context.view_layer.layer_collection.children['Hidden']
    bpy.context.view_layer.active_layer_collection = layer_coll
    layer_coll.hide_viewport = True
    result = bpy.ops.object.armature_car_deformation_rig('EXEC_DEFAULT')
    check(result == {'FINISHED'} and 'DEF-Body' in bpy.context.object.data.bones,
          f'hidden active collection still rigs: {result}')


def test_edit_mode_failure_is_reported():
    reset_scene()
    # Without a window, entering edit mode fails with RuntimeError.
    with bpy.context.temp_override(window=None, area=None, region=None):
        try:
            result = bpy.ops.object.armature_car_deformation_rig('EXEC_DEFAULT')
            check(result == {'CANCELLED'}, f'edit mode failure cancels: {result}')
        except RuntimeError as error:
            # bpy.ops raises the operator's error report; it must be ours, not a traceback.
            message = str(error)
            check('Cannot edit the new armature' in message and 'Traceback' not in message,
                  f'edit mode failure is reported: {message.splitlines()[0]}')


def test_full_pipeline():
    reset_scene()
    body, roof, wheels, brake = build_car()
    select_only([body, *wheels, brake], body)
    result = invoke_in_viewport(bpy.ops.object.armature_car_deformation_rig)
    check(result == {'FINISHED'}, f'deformation rig from selection: {result}')
    rig = bpy.context.object
    bones = rig.data.bones
    for name in ('DEF-Body', 'DEF-Wheel.Ft.L', 'DEF-Wheel.Bk.R', 'DEF-WheelBrake.Ft.L'):
        check(name in bones, f'{name} created')
    check(body.parent == rig and body.parent_bone == 'DEF-Body', 'body parented to DEF-Body')
    body_bone = bones['DEF-Body']
    check(abs(body_bone.length - 2.2) < 1e-3, f'DEF-Body length is half the body: {body_bone.length:.3f}')

    result = bpy.ops.pose.car_animation_rig_generate()
    check(result == {'FINISHED'}, f'animation rig generated: {result}')
    check(rig.data['Car Rig'], 'armature flagged as generated')

    collections = {c.name: c for c in rig.data.collections}
    expected_visibility = {
        'CarRig_Default_Ctrls': True,
        'CarRig_Custom_Ctrls': False,
        'CarRig_Def_Bone': False,
        'CarRig_MCH_Bone': False,
        'CarRig_MCH_Bone_Ext': False,
    }
    for name, visible in expected_visibility.items():
        check(name in collections and collections[name].is_visible == visible,
              f'bone collection {name} exists, visible={visible}')
    check('Root' in collections['CarRig_Default_Ctrls'].bones, 'Root in default controls')
    check('DEF-Body' in collections['CarRig_Def_Bone'].bones, 'DEF-Body in deformation collection')
    check(rig.pose.bones['Root'].color.palette == 'THEME04', 'Root uses the direction palette')
    check(rig.pose.bones['Wheel.Ft.L'].color.palette == 'THEME03', 'wheel uses the wheel palette')

    brake_bone = bones.get('WheelBrake.Ft.L')
    check(brake_bone is not None, 'WheelBrake.Ft.L control created')
    wheel_colls = {c.name for c in bones['Wheel.Ft.L'].collections}
    brake_colls = {c.name for c in brake_bone.collections} if brake_bone else set()
    check(wheel_colls and wheel_colls <= brake_colls, f'brake shares wheel collections: {brake_colls}')

    missing_brake = bones.get('WheelBrake.Ft.R')
    check(missing_brake is None, 'no WheelBrake.Ft.R before adding missing brakes')
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.pose.select_all(action='DESELECT')
    select_pose_bone(rig, 'Wheel.Ft.R')
    result = bpy.ops.pose.car_animation_add_brake_wheel_bones()
    check(result == {'FINISHED'}, f'missing brake bones added: {result}')
    added = rig.data.bones.get('WheelBrake.Ft.R')
    check(added is not None, 'WheelBrake.Ft.R added')
    if added:
        added_colls = {c.name for c in added.collections}
        right_colls = {c.name for c in rig.data.bones['Wheel.Ft.R'].collections}
        check(right_colls <= added_colls, f'added brake shares wheel collections: {added_colls}')
    bpy.ops.object.mode_set(mode='OBJECT')

    drivers = rig.animation_data.drivers if rig.animation_data else []
    scaled = [d for d in drivers if d.modifiers and d.modifiers[0].type == 'GENERATOR'
              and tuple(d.modifiers[0].coefficients)[1] != 1.0]
    check(len(scaled) > 0, f'influence drivers carry generator modifiers: {len(scaled)}')

    root = rig.pose.bones['Root']
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 1, 24
    root.location = (0, 0, 0)
    root.keyframe_insert('location', frame=1)
    root.location = (0, -5, 0)
    root.keyframe_insert('location', frame=12)
    root.location = (4, -10, 0)
    root.keyframe_insert('location', frame=24)

    result = bpy.ops.anim.car_wheels_rotation_bake('EXEC_DEFAULT', frame_start=1, frame_end=24)
    check(result == {'FINISHED'}, f'wheels rotation baked: {result}')
    scene.frame_set(24)
    check(abs(rig.get('Wheel.rotation.Ft.L', 0)) > 1, f'wheel rotated: {rig.get("Wheel.rotation.Ft.L")}')
    bake_operators = sys.modules[ADDON_NAME].bake_operators
    animation_data = rig.animation_data
    fcurves = bake_operators.action_fcurves(animation_data.action, getattr(animation_data, 'action_slot', None))
    wheel_curve = fcurves.find('["Wheel.rotation.Ft.L"]') if fcurves is not None else None
    check(wheel_curve is not None and wheel_curve.group and wheel_curve.group.name == 'Wheels rotation',
          'baked wheel curve sits in the Wheels rotation group of the rig slot')

    result = bpy.ops.anim.car_steering_bake('EXEC_DEFAULT', frame_start=1, frame_end=24)
    check(result == {'FINISHED'}, f'steering baked: {result}')
    steering = [abs(scene.frame_set(f) or rig.get('Steering.rotation', 0)) for f in range(1, 25)]
    check(max(steering) > .01, f'steering follows the turn: max {max(steering):.3f}')

    result = bpy.ops.anim.car_clear_steering_wheels_rotation('EXEC_DEFAULT')
    check(result == {'FINISHED'}, f'steering and wheels cleared: {result}')
    scene.frame_set(24)
    check(rig.get('Wheel.rotation.Ft.L') == 0 and rig.get('Steering.rotation') == 0,
          'cleared rotations stay at rest')


def rig_car(body, wheels, brake):
    select_only([body, *wheels, brake], body)
    invoke_in_viewport(bpy.ops.object.armature_car_deformation_rig)
    rig = bpy.context.object
    bpy.ops.pose.car_animation_rig_generate()
    bpy.context.view_layer.update()
    return rig


def world_bone_layout(rig):
    return {b.name: (rig.matrix_world @ b.head_local, rig.matrix_world @ b.tail_local) for b in rig.data.bones}


def world_bounds(objs):
    car_rig = sys.modules[ADDON_NAME].car_rig
    return [car_rig.object_bounds_xyz(o) for o in objs]


def max_bounds_delta(before, after):
    return max(abs(a - b) for xyz1, xyz2 in zip(before, after) for a, b in zip(xyz1, xyz2))


def test_rig_drives_model():
    reset_scene()
    body, _, wheels, brake = build_car()
    rig = rig_car(body, wheels, brake)
    layer = bpy.context.view_layer

    root = rig.pose.bones['Root']
    before = body.matrix_world.translation.copy()
    root.location = (0, 1, 0)
    layer.update()
    moved = (body.matrix_world.translation - before).length
    check(abs(moved - 1) < 1e-3, f'moving Root carries the body: {moved:.3f}')
    root.location = (0, 0, 0)

    wheel_before = wheels[0].matrix_world.to_quaternion()
    rig['Wheel.rotation.Ft.L'] = 1.0
    rig.update_tag()
    layer.update()
    spun = wheel_before.rotation_difference(wheels[0].matrix_world.to_quaternion()).angle
    check(abs(spun - 1) < 1e-3, f'wheel rotation property spins the wheel: {spun:.3f} rad')
    rig['Wheel.rotation.Ft.L'] = 0.0

    steering_before = wheels[0].matrix_world.to_quaternion()
    rig.pose.bones['Steering'].location.x = .3
    rig.update_tag()
    layer.update()
    steered = steering_before.rotation_difference(wheels[0].matrix_world.to_quaternion()).angle
    check(steered > .05, f'steering control turns the front wheel: {steered:.3f} rad')


def test_bake_along_follow_path_keeps_keyframes():
    reset_scene()
    body, _, wheels, brake = build_car()
    rig = rig_car(body, wheels, brake)
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.curve.primitive_bezier_circle_add(radius=8, location=(8, 0, 0))
    path = bpy.context.object
    path.select_set(False)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig

    cns = rig.pose.bones['Root'].constraints.new('FOLLOW_PATH')
    cns.target = path
    cns.use_curve_follow = True
    cns.use_fixed_location = True
    cns.forward_axis = 'TRACK_NEGATIVE_Y'
    data_path = 'pose.bones["Root"].constraints["%s"].offset_factor' % cns.name
    for frame, factor in ((1, 0.0), (48, 0.25)):
        cns.offset_factor = factor
        rig.keyframe_insert(data_path, frame=frame)
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 1, 48

    def offset_keys():
        bake_operators = sys.modules[ADDON_NAME].bake_operators
        animation_data = rig.animation_data
        fcurves = bake_operators.action_fcurves(animation_data.action, getattr(animation_data, 'action_slot', None))
        fcurve = fcurves.find(data_path) if fcurves is not None else None
        return len(fcurve.keyframe_points) if fcurve else 0

    result = bpy.ops.anim.car_wheels_rotation_bake('EXEC_DEFAULT', frame_start=1, frame_end=48)
    check(result == {'FINISHED'}, f'follow path: wheels baked: {result}')
    check(offset_keys() == 2, f'follow path: offset keyframes survive the wheel bake: {offset_keys()}')
    result = bpy.ops.anim.car_steering_bake('EXEC_DEFAULT', frame_start=1, frame_end=48)
    check(result == {'FINISHED'}, f'follow path: steering baked: {result}')
    check(offset_keys() == 2, f'follow path: offset keyframes survive the steering bake: {offset_keys()}')
    check('Follow Path' in rig.pose.bones['Root'].constraints, 'follow path: constraint kept')

    scene.frame_set(48)
    # A quarter of a circle of radius 8 is about 12.6 units, over wheels of radius .35.
    turned = abs(rig.get('Wheel.rotation.Ft.L', 0))
    check(turned > 30, f'follow path: wheels roll along the path: {turned:.1f} rad')
    steering = [abs(scene.frame_set(f) or rig.get('Steering.rotation', 0)) for f in range(2, 47)]
    check(min(steering) > .01, f'follow path: steering holds the turn: min {min(steering):.3f}')


def test_bake_explains_an_animated_armature_object():
    reset_scene()
    body, _, wheels, brake = build_car()
    rig = rig_car(body, wheels, brake)
    bpy.ops.object.mode_set(mode='OBJECT')
    rig.location = (0, 0, 0)
    rig.keyframe_insert('location', frame=1)
    rig.location = (0, -10, 0)
    rig.keyframe_insert('location', frame=24)
    for operator in (bpy.ops.anim.car_wheels_rotation_bake, bpy.ops.anim.car_steering_bake):
        try:
            result = operator('EXEC_DEFAULT', frame_start=1, frame_end=24)
            check(False, f'{operator.idname_py()} explains an animated armature object: {result}')
        except RuntimeError as error:
            check('Root bone' in str(error), f'{operator.idname_py()} explains: {str(error).splitlines()[0]}')
    animation_data = rig.animation_data
    fcurves = sys.modules[ADDON_NAME].bake_operators.action_fcurves(animation_data.action,
                                                                     getattr(animation_data, 'action_slot', None))
    check(fcurves is not None and fcurves.find('location', index=1) is not None, 'armature keyframes are kept')


def test_polls_without_a_rig():
    reset_scene()
    addon = sys.modules[ADDON_NAME]
    # Blender swallows an exception raised by poll, so the classes are polled directly.
    operators = (addon.bake_operators.ANIM_OT_carWheelsRotationBake, addon.bake_operators.ANIM_OT_carSteeringBake,
                 addon.bake_operators.ANIM_OT_carClearSteeringWheelsRotation,
                 addon.car_rig.POSE_OT_carAnimationRigGenerate, addon.car_rig.POSE_OT_carAnimationAddBrakeWheelBones)
    empty = bpy.data.objects.new('Empty', None)
    bpy.context.scene.collection.objects.link(empty)
    for active in (None, empty):
        bpy.context.view_layer.objects.active = active
        for operator in operators:
            try:
                check(not operator.poll(bpy.context), f'{operator.bl_idname} is unavailable with {active}')
            except Exception as error:
                check(False, f'{operator.bl_idname} poll raises with {active}: {error!r}')


def test_scaled_parented_model_rigs_like_plain():
    reset_scene()
    body, _, wheels, brake = build_car()
    reference_objects = world_bounds([body, *wheels, brake])
    reference = world_bone_layout(rig_car(body, wheels, brake))
    check(max_bounds_delta(reference_objects, world_bounds([body, *wheels, brake])) < SETTLE,
          'plain model stays in place when rigged')

    reset_scene()
    body, _, wheels, brake = build_scaled_parented_car()
    bpy.context.scene.cursor.location = (1, 2, 0)
    objects_before = world_bounds([body, *wheels, brake])
    layout = world_bone_layout(rig_car(body, wheels, brake))
    # The car has no WheelBrake.Ft.R object, so that brake takes its default place near the 3D cursor.
    deltas = {name: max((layout[name][0] - ref[0]).length, (layout[name][1] - ref[1]).length)
              for name, ref in reference.items() if name in layout and 'WheelBrake.Ft.R' not in name}
    worst = max(deltas, key=deltas.get)
    check(set(layout) == set(reference), f'scaled, parented model, cursor away, makes the same bones: {len(layout)}')
    check(deltas[worst] < 1e-3, f'scaled, parented model makes the same rig: worst {worst} off by {deltas[worst]:.3f}')
    check(max_bounds_delta(objects_before, world_bounds([body, *wheels, brake])) < SETTLE,
          'scaled, parented model stays in place when rigged')
    check(max_bounds_delta(reference_objects, objects_before) < 1e-4, 'both models share the same world geometry')


def main():
    print(f'[e2e] Blender {bpy.app.version_string}', flush=True)
    rigacar = import_addon()
    for test in (lambda: test_bounds(rigacar.car_rig), test_deformation_rig_without_invoke,
                 test_hidden_collection_still_rigs, test_edit_mode_failure_is_reported,
                 test_full_pipeline, test_rig_drives_model, test_bake_along_follow_path_keeps_keyframes,
                 test_bake_explains_an_animated_armature_object, test_polls_without_a_rig,
                 test_scaled_parented_model_rigs_like_plain):
        try:
            with viewport():
                test()
        except Exception:
            traceback.print_exc()
            failures.append(f'exception in {test}')
    print(f'[e2e] {len(failures)} failure(s)', flush=True)
    os._exit(1 if failures else 0)


if bpy.app.background:
    print('[e2e] FAIL needs a window: run under xvfb-run without --background', flush=True)
    os._exit(2)
bpy.app.timers.register(main, first_interval=.5)
