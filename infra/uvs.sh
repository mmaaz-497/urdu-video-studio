#!/usr/bin/env bash
# Installed on the VPS as /opt/uvs/uvs by infra/deploy.sh (T093a).
#
# The ONLY way to run compose for this stack. It pins the project name (uvs), the compose
# file, the image tag and the podman socket, so a command can never act on another
# project's containers (tokoshopee-postgres, fiv-cobalt, ...) and never on a wrong tag.
#
#   /opt/uvs/uvs ps                 status of our 6 containers
#   /opt/uvs/uvs logs -f worker     follow one service's logs
#   /opt/uvs/uvs restart backend    restart one service
#   /opt/uvs/uvs up -d              (re)create anything whose config changed
set -euo pipefail

UVS_DIR=/opt/uvs
COMPOSE_BIN=/usr/local/bin/docker-compose
cd "$UVS_DIR"

if [[ -z "${UVS_TAG:-}" ]]; then
  [[ -s RELEASE ]] || { echo "uvs: $UVS_DIR/RELEASE is missing - run infra/deploy.sh first" >&2; exit 1; }
  UVS_TAG=$(<RELEASE)
fi
export UVS_TAG
export DOCKER_HOST=unix:///run/podman/podman.sock
unset COMPOSE_FILE COMPOSE_PROFILES

[[ -S /run/podman/podman.sock ]] || { echo "uvs: podman.socket is not running: systemctl enable --now podman.socket" >&2; exit 1; }
[[ -x $COMPOSE_BIN ]] || { echo "uvs: $COMPOSE_BIN not found (see README, Deploy step 3)" >&2; exit 1; }

# Refuse the commands that delete data or shared images.
if [[ "${1:-}" == "down" ]]; then
  for arg in "$@"; do
    case "$arg" in
      -v|--volumes|--volumes=*|--rmi|--rmi=*)
        echo "uvs: refusing '$arg' - it would delete the database volume or images." >&2
        exit 1 ;;
    esac
  done
fi

exec "$COMPOSE_BIN" --project-name uvs --project-directory "$UVS_DIR" \
  -f "$UVS_DIR/docker-compose.prod.yml" "$@"
