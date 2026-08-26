# OpenRadioss solver build (WSL serving host)

The laminate converter emits OpenRadioss decks, so this host keeps a local
solver build. The upstream source is **not** vendored here — only the patches
needed to build it are.

## Local checkout

`~/projects/OpenRadioss-mumps-src` — clone of https://github.com/OpenRadioss/OpenRadioss
Built against upstream `1b28119` (2026-08-18).

Built engine: `exec/engine_linux64_gf_ompi` (gfortran + OpenMPI, x86-64).

## Patches

Apply from the OpenRadioss checkout root, in order:

```bash
cd ~/projects/OpenRadioss-mumps-src
git apply /home/user/projects/KyulAI/infrastructure/openradioss/patches/*.patch
```

### 0001-define-my_real-when-python-disabled.patch

`common_source/modules/cpp_python_funct.cpp` defines the `my_real` typedef
inside the `#ifndef PYTHON_DISABLED` block, so a build with Python disabled
fails to compile — `my_real` is used by declarations that are still active.
The patch hoists the typedef above that block, leaving it defined either way.

Verify it is already applied with:

```bash
git apply --check --reverse infrastructure/openradioss/patches/0001-*.patch
```

## Related

Deck generation and result extraction live in the laminate converter — see
`docs/OPENRADIOSS_LAMINATE_CONVERSION.md`.
