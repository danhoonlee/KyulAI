# OpenRadioss solver build (WSL serving host)

The laminate converter emits OpenRadioss decks, so this host keeps a local
solver build. The upstream source is **not** vendored here — only the patches
and the build recipe needed to reproduce it.

## Local checkout

`~/projects/OpenRadioss-mumps-src` — clone of https://github.com/OpenRadioss/OpenRadioss
Built against upstream `1b28119` (2026-08-18).

| Binary | Built | Notes |
|---|---|---|
| `exec/starter_linux64_gf` | 2026-08-27 | SMP, `-no-python` |
| `exec/engine_linux64_gf_ompi` | 2026-08-18 | OpenMPI, `-no-python` |

## Toolchain

Not the system compilers — a conda environment at
`~/.local/opt/openmpi-conda` (gfortran/gcc 15.3.0, cmake 3.29.6, Open MPI 5.0.10).
The system `g++` (15.2.0) is used for C++; its ABI matches the conda `libstdc++`
the binaries link against.

## Build

```bash
C=~/.local/opt/openmpi-conda
export PATH="$C/bin:$PATH"
export LD_LIBRARY_PATH="$C/lib:/usr/lib/x86_64-linux-gnu"
export CC="$C/bin/gcc" FC="$C/bin/gfortran" CXX=/usr/bin/g++

cd ~/projects/OpenRadioss-mumps-src
git apply ~/projects/KyulAI/infrastructure/openradioss/patches/*.patch

cd starter && ./build_script.sh -arch=linux64_gf -no-python -release -nt=20
cp cbuild_starter_linux64_gf/starter_linux64_gf ../exec/
```

`/usr/lib/x86_64-linux-gnu` **must** be on `LD_LIBRARY_PATH` at link time. The
bundled `extlib/hm_reader/linux64/libapr-1.so` needs `libuuid.so.1` and
`libcrypt.so.1`, and the conda linker does not search the system directory on
its own; without it the link dies on `undefined reference to
uuid_generate@UUID_1.0`. Setting `LDFLAGS` does not help — the arch file
overwrites `CMAKE_EXE_LINKER_FLAGS`.

## Run

```bash
C=~/.local/opt/openmpi-conda
OR=~/projects/OpenRadioss-mumps-src
export LD_LIBRARY_PATH="$C/lib:/usr/lib/x86_64-linux-gnu:$OR/extlib/hm_reader/linux64"
export RAD_CFG_PATH="$OR/hm_cfg_files"

$OR/exec/starter_linux64_gf -i <run>_0000.rad -nt 4
OMP_NUM_THREADS=8 $OR/exec/engine_linux64_gf_ompi -i <run>_0001.rad
```

The hm_reader directory on `LD_LIBRARY_PATH` is required at run time too, or the
starter aborts with `libhm_reader_linux64.so: cannot open shared object file`.

## Patches

Both are upstream defects in the `PYTHON_DISABLED` build, not local
customisation. Each applies independently; together they produce exactly the
tree these binaries were built from.

### 0001-define-my_real-when-python-disabled.patch

`common_source/modules/cpp_python_funct.cpp` defines the `my_real` typedef
inside the `#ifndef PYTHON_DISABLED` block, so a `-no-python` build fails to
compile — declarations that stay active still use the type. The patch hoists
the typedef above that block.

### 0002-stub-missing-python-disabled-entry-points.patch

The `#else` branch of that same file stubs out the Python entry points for
`-no-python` builds, but seven symbols that `python_mod.F90` binds to are
missing from it:

```
cpp_python_create_context      cpp_python_free_context
cpp_python_sync                cpp_python_update_active_node
cpp_python_update_active_node_ids
cpp_python_add_ints_to_dict    cpp_python_add_doubles_to_dict
```

The starter link fails on them. The patch adds no-op stubs matching the
signatures of the enabled definitions.

## Verified 2026-08-27

`Test_001 (1).inp` converted, then:

- starter: `NORMAL TERMINATION`, 0 errors, 0 warnings, 14.2 s, wrote
  `Test_001_0000_0001.rst`
- engine: run from that restart

## Related

Deck generation and result extraction live in the laminate converter — see
`docs/OPENRADIOSS_LAMINATE_CONVERSION.md`.
