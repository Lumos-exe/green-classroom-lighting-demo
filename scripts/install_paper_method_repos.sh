#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
THIRD_PARTY_DIR="${ROOT_DIR}/third_party"

VGGT_REPO_URL="https://github.com/facebookresearch/vggt.git"
GS_REPO_URL="https://github.com/graphdeco-inria/gaussian-splatting.git"

mkdir -p "${THIRD_PARTY_DIR}"

clone_or_update() {
  local url="$1"
  local target="$2"
  local recursive="${3:-false}"

  if [ -d "${target}/.git" ]; then
    echo "[paper_method] found ${target}; fetching latest refs"
    git -C "${target}" fetch --all --tags
  else
    echo "[paper_method] cloning ${url} -> ${target}"
    if [ "${recursive}" = "true" ]; then
      git clone --recursive "${url}" "${target}"
    else
      git clone "${url}" "${target}"
    fi
  fi
}

clone_or_update "${VGGT_REPO_URL}" "${THIRD_PARTY_DIR}/vggt" false
clone_or_update "${GS_REPO_URL}" "${THIRD_PARTY_DIR}/gaussian-splatting" true

cat <<'MSG'

[paper_method] External repositories are ready under third_party/.
They are intentionally ignored by git. Install their Python/CUDA dependencies
according to the upstream README files before using --backend real.
MSG
