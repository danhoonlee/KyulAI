#!/usr/bin/env bash
set -u

if [ "$#" -lt 1 ] || [ "$#" -gt 3 ]; then
  echo "Usage: $0 <remote-batch-root> [max-jobs] [threads-per-job]" >&2
  exit 2
fi

BATCH_ROOT="$1"
MAX_JOBS="${2:-5}"
THREADS="${3:-4}"
OPENRADIOSS_ROOT=/home/user/.local/opt/openradioss/latest-20260728/OpenRadioss
MPI_ROOT=/home/user/.local/opt/openmpi-conda
MUMPS_ENGINE=/home/user/projects/OpenRadioss-mumps-src/exec/engine_linux64_gf_ompi

export OPENRADIOSS_PATH="$OPENRADIOSS_ROOT"
export RAD_CFG_PATH="$OPENRADIOSS_ROOT/hm_cfg_files"
export RAD_H3D_PATH="$OPENRADIOSS_ROOT/extlib/h3d/lib/linux64"
export PATH="$MPI_ROOT/bin:$PATH"
export LD_LIBRARY_PATH="$OPENRADIOSS_ROOT/extlib/hm_reader/linux64:$OPENRADIOSS_ROOT/extlib/h3d/lib/linux64:$MPI_ROOT/lib:${LD_LIBRARY_PATH:-}"
export OMP_STACKSIZE=400m

run_one() {
  local case_dir="$1"
  local test_id
  test_id="$(basename "$case_dir")"
  if [ -f "$case_dir/complete" ]; then
    return 0
  fi
  (
    cd "$case_dir" || exit 1
    date -Iseconds > started_at.txt
    if ! "$OPENRADIOSS_ROOT/exec/starter_linux64_gf" \
      -i "${test_id}_0000.rad" -nspmd 1 -nt "$THREADS" > starter.console.log 2>&1; then
      printf 'starter failed\n' > failed
      return 1
    fi
    if ! "$MPI_ROOT/bin/mpirun" -np 1 "$MUMPS_ENGINE" \
      -i "${test_id}_0001.rad" -nt "$THREADS" > engine.console.log 2>&1; then
      printf 'engine failed\n' > failed
      return 1
    fi
    if ! grep -q "NORMAL TERMINATION" "${test_id}_0001.out"; then
      printf 'engine did not terminate normally\n' > failed
      return 1
    fi
    if ! "$OPENRADIOSS_ROOT/exec/th_to_csv_linux64_gf" \
      "${test_id}T01" > th_extract.log 2>&1; then
      printf 'time-history conversion failed\n' > failed
      return 1
    fi
    if ! python3 "$BATCH_ROOT/extract_radioss_reaction_history.py" \
      "${test_id}T01.csv" reaction_force.csv; then
      printf 'reaction extraction failed\n' > failed
      return 1
    fi
    find "$case_dir" -maxdepth 1 -type f -name '*.rst' -delete
    date -Iseconds > completed_at.txt
    : > complete
  )
}

pids=()
case_dirs=("$BATCH_ROOT"/Test_[0-9][0-9][0-9])
for case_dir in "${case_dirs[@]}"; do
  while [ "$(jobs -rp | wc -l)" -ge "$MAX_JOBS" ]; do
    wait -n || true
  done
  run_one "$case_dir" &
  pids+=("$!")
done
for pid in "${pids[@]}"; do
  wait "$pid" || true
done

complete_count="$(find "$BATCH_ROOT" -mindepth 2 -maxdepth 2 -type f -name complete | wc -l)"
failed_count="$(find "$BATCH_ROOT" -mindepth 2 -maxdepth 2 -type f -name failed | wc -l)"
printf 'complete=%s failed=%s total=%s\n' "$complete_count" "$failed_count" "${#case_dirs[@]}" \
  | tee "$BATCH_ROOT/batch_finished.txt"
if [ "$complete_count" -ne "${#case_dirs[@]}" ]; then
  exit 1
fi
