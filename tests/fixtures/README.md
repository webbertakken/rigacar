# Test fixtures

- `sedan-sports.glb` and `Textures/colormap.png` come from Kenney's [Car Kit](https://kenney.nl/assets/car-kit) (version 3.1), licensed [CC0](http://creativecommons.org/publicdomain/zero/1.0/). Thanks, [Kenney](https://www.kenney.nl).

The sedan faces -Y with its wheels on the floor. Its spoiler is a child of the body, and each wheel's origin sits on the axle, about 0.13 units inboard of the wheel's centre, as in many real models. `tests/e2e.py` imports it and renames its parts to Rigacar's names.
