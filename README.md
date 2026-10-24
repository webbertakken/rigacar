# Rigacar

## Fork

_This fork keeps Rigacar working on current Blender and consolidates fixes from the community while the maintainer is absent._

### Compatibility

| Blender     | Status                 |
|-------------|------------------------|
| 5.0 - 5.1   | Supported, tested      |
| 4.5 LTS     | Supported, tested      |
| 4.0 - 4.4   | Supported, tested      |
| 3.x and older | Use upstream Rigacar |

### Install

1. Download `rigacar-<version>.zip` from the [releases](https://github.com/webbertakken/rigacar/releases).
2. In Blender, open _Edit > Preferences > Add-ons_ and choose _Install from Disk_ (_Install..._ before 4.2).
3. Enable _Rigacar (Generates Car Rig)_.

### What the fork changes

- Bone collections and bone colour palettes replace armature layers and bone groups (Blender 4.0).
- Baking passes its options as `BakeOptions` (Blender 4.1).
- Baking reads and writes F-curves through the action's slot, and selects bones through pose bones (Blender 4.4 and 5.0).
- Rig generation creates missing driver modifiers, runs without the invoke step, and reports edit mode failures.
- The body bone is sized from the body's true bounds, including collection instances and parented children.
- Rigging keeps the car where it is: parented or scaled parts, a 3D cursor away from the origin, and _Move origin_ no longer shift it.
- Operators stay quietly unavailable, instead of raising errors, when no car rig is active.

### Troubleshooting

- **Installing does nothing, or reports "No module named rigacar-...".** Install the release zip, not GitHub's _Code > Download ZIP_. Blender imports the add-on by its folder name, which must be exactly `rigacar`.
- **The Rigacar tab is missing from the sidebar.** It only appears while a car rig is the active object. Add one with _Add > Armature > Car (deformation rig)_, select it, then press _N_.
- **Only one big bone appears, or the car doesn't move with the rig.** Select every part of the car (body, wheels and brakes) before adding the deformation rig; Rigacar only rigs selected objects. Their names must end with `Body`, `Wheel.Ft.L`, `Wheel.Ft.R`, `Wheel.Bk.L`, `Wheel.Bk.R`, and optionally `WheelBrake.Ft.L` and so on. Dots, dashes, underscores or spaces work as separators, and extra wheels add a number, as in `Wheel.Bk.L.001`.
- **Wheels are the wrong size or float.** Model the car facing -Y, with the wheels resting on the grid floor; Rigacar measures each wheel's radius from the floor.
- **Without target objects, the rig doesn't fit the car.** Adjust the bones in the _Add car deformation rig_ panel straight after adding it, or in Edit mode.
- **Baking does nothing.** Animate the `Root` bone in Pose mode, not the armature object. A _Follow Path_ constraint goes on the `Root` bone too.
- **The car distorts in bends along a path.** Apply the curve's scale (_Object > Apply > Scale_) before following it.

### Test

Run the end-to-end test from the repository root with any Blender. It needs a window, so use a virtual display when headless:

```bash
xvfb-run -a blender --factory-startup --python tests/e2e.py

# or on several versions at once
tests/matrix.sh ~/Applications/blender-*/blender
```

It builds a car, rigs it, checks the controls drive it, adds brakes, bakes wheels and steering (also along a Follow Path), and clears them. It also rigs a scaled, parented car away from the 3D cursor. It exits non-zero when a check fails.

Upstream readme description below.

## Upstream

Rigacar is a free addon for Blender. It is designed to fulfill the following goals:

* generate a complete rig as quickly as possible (actually few seconds) for standard car models
* provide tools to automate wheels animation
* allow efficient animation baking to be able to export animated models into real time renderers

Please read [full documentation](http://digicreatures.net/articles/rigacar.html) on my website.

You can also watch the series of video tutorials:

[![Rigacar Part 1](http://img.youtube.com/vi/D3XQxA_-TzY/0.jpg)](https://www.youtube.com/watch?v=D3XQxA_-TzY&list=PLH_mmrv8SfPFiEj93RJt3sBvHCnipI9qK "Rigacar video tutorials")
