# Rigacar

## Fork

_This fork keeps Rigacar working on current Blender and consolidates fixes from the community while the maintainer is absent._

### Compatibility

| Blender     | Status                 |
|-------------|------------------------|
| 5.1         | Supported, tested      |
| 4.5 LTS     | Supported, tested      |
| 4.0 - 4.4   | Supported, 4.0 tested  |
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

### Test

Run the end-to-end test from the repository root with any Blender. It needs a window, so use a virtual display when headless:

```bash
xvfb-run -a blender --factory-startup --python tests/e2e.py
```

It builds a car, rigs it, adds brakes, bakes wheels and steering, and clears them; it exits non-zero when a check fails.

Upstream readme description below.

## Upstream

Rigacar is a free addon for Blender. It is designed to fulfill the following goals:

* generate a complete rig as quickly as possible (actually few seconds) for standard car models
* provide tools to automate wheels animation
* allow efficient animation baking to be able to export animated models into real time renderers

Please read [full documentation](http://digicreatures.net/articles/rigacar.html) on my website.

You can also watch the series of video tutorials:

[![Rigacar Part 1](http://img.youtube.com/vi/D3XQxA_-TzY/0.jpg)](https://www.youtube.com/watch?v=D3XQxA_-TzY&list=PLH_mmrv8SfPFiEj93RJt3sBvHCnipI9qK "Rigacar video tutorials")
