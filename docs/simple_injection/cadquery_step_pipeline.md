# Simple Injection STEP to GLB Pipeline

The web app currently renders a DOE-driven parametric 3D preview from `L`, `W`, `t`, `D`, and gate dimensions. For exact CAD geometry, STEP files can be converted to browser-ready GLB assets with CadQuery.

## Install

CadQuery is optional and only needed when regenerating GLB assets.

```bash
/Users/danlee/KyulAI_codex/.venv/bin/python -m pip install 'cadquery>=2.5,<3'
```

If pip upgrades `numpy` to a 2.x release, restore the existing ML runtime version after installation:

```bash
/Users/danlee/KyulAI_codex/.venv/bin/python -m pip install 'numpy==1.26.4'
```

## Convert

```bash
/Users/danlee/KyulAI_codex/.venv/bin/python scripts/simple_injection/convert_step_to_glb.py --force
```

Default input:

```text
data/datasets/Simple_Injection/step
```

Default output:

```text
src/frontend/simple-injection/assets/step-glb
```

The script searches nested folders, so files such as `step/G01-G30 STEP FILE/G01.stp` are detected automatically. It writes one `Gxx.glb` file per geometry and a `manifest.json` for later UI integration.

## Why CadQuery

CadQuery can import STEP files and export assemblies to glTF/GLB, which makes it a good Python-native bridge between CAD geometry and a Three.js web viewer. The parametric preview should stay as a fallback because it is instant, dependency-free, and works even before exact CAD assets are generated.
