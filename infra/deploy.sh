#!/usr/bin/env bash
# Build on THIS machine (WSL), ship to the VPS, migrate, restart, health-check (T095a).
# Nothing is ever built on the VPS: a Next.js build would starve its live sites of RAM.
#
#   ./infra/deploy.sh             deploy the committed HEAD
#   ./infra/deploy.sh rollback    switch the VPS back to the previous release
#   ./infra/deploy.sh check       health check only
#
# Needs VPS_HOST (and optionally VPS_PORT, default 22) from the environment or from
# infra/deploy.env (gitignored; copy infra/deploy.env.example). Environment wins.
set -Eeuo pipefail
trap 'echo; echo "DEPLOY FAILED (line $LINENO): $BASH_COMMAND" >&2; echo "The live release is unchanged unless the output above says otherwise; status: ./infra/deploy.sh check" >&2' ERR

ROOT=$(git rev-parse --show-toplevel)
cd "$ROOT"

env_host=${VPS_HOST:-}; env_port=${VPS_PORT:-}
if [[ -f infra/deploy.env ]]; then
  # shellcheck disable=SC1091
  source infra/deploy.env
fi
VPS_HOST=${env_host:-${VPS_HOST:-}}
VPS_PORT=${env_port:-${VPS_PORT:-22}}
[[ -n "$VPS_HOST" ]] || { echo "VPS_HOST is not set (export it, or put it in infra/deploy.env)" >&2; exit 1; }

# One multiplexed SSH connection for every step below.
SSH_CTL="$HOME/.ssh/uvs-deploy-%C"
SSH=(ssh -p "$VPS_PORT" -o BatchMode=yes -o ConnectTimeout=15
     -o ControlMaster=auto -o ControlPath="$SSH_CTL" -o ControlPersist=120 "root@$VPS_HOST")
remote() { "${SSH[@]}" "$@"; }

step() { printf '\n==> %s\n' "$*"; }

preflight_remote() {
  step "Checking the VPS ($VPS_HOST:$VPS_PORT)"
  remote 'set -e
    command -v podman >/dev/null || { echo "podman is missing"; exit 1; }
    test -x /usr/local/bin/docker-compose || { echo "docker-compose missing: README Deploy step 3"; exit 1; }
    test -S /run/podman/podman.sock || { echo "podman.socket not running: systemctl enable --now podman.socket"; exit 1; }
    test -s /opt/uvs/.env || { echo "/opt/uvs/.env missing: README Deploy step 4"; exit 1; }
    echo "podman $(podman --version | cut -d" " -f3), $(/usr/local/bin/docker-compose version --short | sed "s/^/compose /"), free RAM: $(free -m | awk "/Mem:/{print \$7}") MB"'
}

install_infra_files() {
  step "Uploading compose file and VPS scripts to /opt/uvs"
  local f dest mode
  for f in docker-compose.prod.yml:docker-compose.prod.yml:0644 \
           uvs.sh:uvs:0755 release.sh:release.sh:0755 \
           backup/uvs-backup.sh:uvs-backup.sh:0755; do
    IFS=: read -r src dest mode <<<"$f"
    remote "cat > /opt/uvs/.$dest.tmp && chmod $mode /opt/uvs/.$dest.tmp && mv -f /opt/uvs/.$dest.tmp /opt/uvs/$dest" \
      < "infra/$src"
  done
}

ship_image() { # ship_image <name>: make localhost/<name>:$TAG exist on the VPS
  local ref="localhost/$1:$TAG" id
  id=$(docker image inspect --format '{{.Id}}' "$ref"); id=${id#sha256:}
  if remote "podman image exists $ref"; then
    echo "$ref: already on the VPS"
  elif remote "podman image exists $id"; then
    remote "podman tag $id $ref"
    echo "$ref: unchanged image, re-tagged on the VPS (no upload)"
  else
    echo "$ref: uploading (docker save | gzip | ssh | podman load) ..."
    docker save "$ref" | gzip -6 | remote "gunzip | podman load"
    remote "podman image exists $ref" || { echo "$ref did not arrive on the VPS" >&2; return 1; }
  fi
}

cmd_deploy() {
  step "Checking the git working tree"
  if [[ -n "$(git status --porcelain)" ]]; then
    git status --short >&2
    echo "Refusing to deploy: commit or stash the changes above first." >&2
    exit 1
  fi
  TAG=$(git rev-parse --short HEAD)
  echo "Deploying commit $TAG: $(git log -1 --format=%s)"

  preflight_remote
  remote 'mkdir -p /opt/uvs && chmod 700 /opt/uvs'

  # Build from an export of exactly HEAD, so the tag always matches what is in the image.
  BUILD_CTX=$(mktemp -d)
  trap 'rm -rf "$BUILD_CTX"' EXIT
  git archive HEAD backend frontend | tar -x -C "$BUILD_CTX"

  step "Building localhost/uvs-backend:$TAG"
  docker build -t "localhost/uvs-backend:$TAG" "$BUILD_CTX/backend"
  step "Building localhost/uvs-frontend:$TAG"
  docker build -t "localhost/uvs-frontend:$TAG" \
    --build-arg NEXT_PUBLIC_API_BASE_URL=/api \
    --build-arg BACKEND_ORIGIN=http://backend:8000 \
    "$BUILD_CTX/frontend"

  step "Shipping images"
  ship_image uvs-backend
  ship_image uvs-frontend

  install_infra_files

  step "Migrating and restarting on the VPS"
  remote "/opt/uvs/release.sh deploy $TAG"
  printf '\nDeployed %s. Test it: ssh -N -L 3100:127.0.0.1:3100 -p %s root@%s  then open http://localhost:3100\n' \
    "$TAG" "$VPS_PORT" "$VPS_HOST"
}

case "${1:-deploy}" in
  deploy)   cmd_deploy ;;
  rollback) preflight_remote; remote "/opt/uvs/release.sh rollback" ;;
  check)    remote "/opt/uvs/release.sh check" ;;
  *) echo "usage: $0 [deploy|rollback|check]" >&2; exit 1 ;;
esac
