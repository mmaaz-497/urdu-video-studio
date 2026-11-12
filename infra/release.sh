#!/usr/bin/env bash
# Installed on the VPS as /opt/uvs/release.sh and run by infra/deploy.sh (T095a).
#
#   release.sh deploy <tag>   migrate the DB with <tag>'s image, switch the stack to <tag>
#   release.sh rollback       switch back to the release before the current one
#   release.sh check          health check only
#
# Files in /opt/uvs: RELEASE (tag that is live), PREVIOUS_RELEASE (rollback target).
set -Eeuo pipefail
trap 'echo "release.sh: FAILED at line $LINENO: $BASH_COMMAND" >&2' ERR

UVS_DIR=/opt/uvs
UVS="$UVS_DIR/uvs"
cd "$UVS_DIR"

die() { echo "release.sh: $*" >&2; exit 1; }

# Must match the ipv4_address/extra_hosts values in docker-compose.prod.yml.
UVS_NET=uvs-net
UVS_SUBNET=10.89.77.0/24
UVS_GATEWAY=10.89.77.1

ensure_network() {
  # uvs-net is created here, with container DNS disabled: on this cPanel host the system
  # nameserver answers on the bridge gateway's port 53 and REFUSEs podman's dnsname/aardvark
  # queries. Names come from extra_hosts; outside lookups use the host's resolvers.
  if podman network exists "$UVS_NET"; then
    local dns subnet
    dns=$(podman network inspect "$UVS_NET" --format '{{.DNSEnabled}}')
    subnet=$(podman network inspect "$UVS_NET" --format '{{range .Subnets}}{{.Subnet}}{{end}}')
    if [[ "$dns" == false && "$subnet" == "$UVS_SUBNET" ]]; then
      return 0
    fi
    echo "==> Replacing $UVS_NET (dns=$dns subnet=$subnet) with dns=false subnet=$UVS_SUBNET"
    # Removes only OUR containers (volumes, i.e. the database, are kept).
    "$UVS" down --remove-orphans
    podman network rm "$UVS_NET" \
      || die "could not remove $UVS_NET; containers still attached: $(podman ps -a --filter network=$UVS_NET --format '{{.Names}}' | tr '\n' ' ')"
  fi
  echo "==> Creating network $UVS_NET ($UVS_SUBNET, container DNS disabled)"
  podman network create --disable-dns --subnet "$UVS_SUBNET" --gateway "$UVS_GATEWAY" \
    --label io.uvs.managed=true "$UVS_NET" >/dev/null
}

check_name_resolution() {
  # Internal names come from /etc/hosts (extra_hosts); external ones from the host's resolvers.
  podman exec uvs-backend python -c '
import socket, sys
bad = []
for host in ("postgres", "redis", "backend", "api.openai.com", "api.runpod.ai"):
    try:
        socket.getaddrinfo(host, 443)
    except OSError as exc:
        bad.append(f"{host} ({exc})")
if bad:
    sys.exit("cannot resolve: " + ", ".join(bad))
' || die "name resolution inside uvs-backend failed (see above)"
  podman exec uvs-frontend node -e "require('dns').lookup('backend', e => process.exit(e ? 1 : 0))" \
    || die "uvs-frontend cannot resolve 'backend'"
  echo "DNS      postgres, redis, backend, api.openai.com, api.runpod.ai resolve inside the containers"
}

health_status() { podman inspect --format '{{.State.Health.Status}}' "$1" 2>/dev/null || echo missing; }

wait_healthy() { # wait_healthy <seconds> <container>...
  local deadline=$((SECONDS + $1)); shift
  for c in "$@"; do
    until [[ "$(health_status "$c")" == healthy ]]; do
      if (( SECONDS >= deadline )); then
        echo "--- last log lines of $c ---" >&2
        podman logs --tail 40 "$c" >&2 || true
        die "$c did not become healthy (status: $(health_status "$c"))"
      fi
      sleep 3
    done
  done
}

EXPECTED_CONTAINERS=(uvs-postgres uvs-redis uvs-backend uvs-worker uvs-scheduler uvs-frontend)

check_restart_policies() {
  # podman-restart.service only restarts containers whose policy is "always" at boot. We do
  # not reboot a server with 12 live sites to test that, so check the policy itself.
  local bad=0 c policy names
  names=$(podman ps -a --filter 'name=^uvs-' --format '{{.Names}}')
  for c in "${EXPECTED_CONTAINERS[@]}"; do
    grep -qx "$c" <<<"$names" || { echo "MISSING container $c" >&2; bad=1; }
  done
  for c in $names; do
    policy=$(podman inspect --format '{{.HostConfig.RestartPolicy.Name}}' "$c")
    if [[ "$policy" != always ]]; then
      echo "RESTART POLICY: $c has '${policy:-none}', expected 'always' (would not come back after a reboot)" >&2
      bad=1
    fi
  done
  (( bad == 0 )) || die "restart-policy check failed"
  echo "Reboot   all $(wc -w <<<"$names") uvs-* containers have restart policy 'always'; podman-restart.service is $(systemctl is-enabled podman-restart.service 2>/dev/null || echo unknown)"
  [[ "$(systemctl is-enabled podman-restart.service 2>/dev/null)" == enabled ]] \
    || die "podman-restart.service is not enabled: systemctl enable podman-restart.service"
}

check() {
  wait_healthy 180 uvs-postgres uvs-redis uvs-backend uvs-frontend
  for c in uvs-worker uvs-scheduler; do
    [[ "$(podman inspect --format '{{.State.Status}}' "$c" 2>/dev/null)" == running ]] \
      || die "$c is not running: podman logs --tail 50 $c"
  done
  echo "API      127.0.0.1:8100/health     -> $(curl -fsS --max-time 5 http://127.0.0.1:8100/health)"
  echo "API      127.0.0.1:3100/api/health -> $(curl -fsS --max-time 5 http://127.0.0.1:3100/api/health)  (Next.js rewrite / SSH-tunnel path)"
  echo "Frontend 127.0.0.1:3100/           -> HTTP $(curl -fsS --max-time 10 -o /dev/null -w '%{http_code}' http://127.0.0.1:3100/)"
  check_name_resolution
  check_restart_policies
  "$UVS" ps --format 'table {{.Name}}\t{{.Image}}\t{{.Status}}'
  echo "Live release: $(<RELEASE)"
}

switch_to() { # switch_to <tag>: start the stack on <tag>
  UVS_TAG="$1" "$UVS" up -d --remove-orphans
}

prune_images() { # keep only the live and the rollback tag of OUR images
  local keep
  keep=" $(<RELEASE) $(cat PREVIOUS_RELEASE 2>/dev/null || true) "
  podman images --format '{{.Repository}}:{{.Tag}}' \
    | grep -E '^localhost/uvs-(backend|frontend):' \
    | while read -r ref; do
        [[ "$keep" == *" ${ref##*:} "* ]] || podman rmi "$ref" >/dev/null 2>&1 || true
      done
}

cmd_deploy() {
  local tag="${1:?usage: release.sh deploy <tag>}"
  [[ -s .env ]] || die "$UVS_DIR/.env is missing - create it from infra/.env.production.example (README step 4)"
  chmod 600 .env
  for img in backend frontend; do
    podman image exists "localhost/uvs-$img:$tag" || die "image localhost/uvs-$img:$tag is not loaded"
  done
  local prev; prev=$(cat RELEASE 2>/dev/null || true)

  UVS_TAG="$tag" ensure_network

  echo "==> Starting postgres + redis"
  UVS_TAG="$tag" "$UVS" up -d postgres redis
  wait_healthy 120 uvs-postgres uvs-redis

  echo "==> alembic upgrade head (image $tag)"
  UVS_TAG="$tag" "$UVS" run --rm --no-deps migrate

  echo "==> Switching the stack to $tag"
  switch_to "$tag"
  echo "$tag" > RELEASE
  if [[ -n "$prev" && "$prev" != "$tag" ]]; then echo "$prev" > PREVIOUS_RELEASE; fi

  echo "==> Health check"
  check
  prune_images
}

cmd_rollback() {
  [[ -s PREVIOUS_RELEASE ]] || die "no PREVIOUS_RELEASE recorded - nothing to roll back to"
  local cur prev; cur=$(<RELEASE); prev=$(<PREVIOUS_RELEASE)
  for img in backend frontend; do
    podman image exists "localhost/uvs-$img:$prev" || die "image localhost/uvs-$img:$prev is gone"
  done
  echo "==> Rolling back $cur -> $prev (database migrations are NOT reverted)"
  switch_to "$prev"
  echo "$prev" > RELEASE
  echo "$cur" > PREVIOUS_RELEASE
  check
}

case "${1:-}" in
  deploy)   shift; cmd_deploy "$@" ;;
  rollback) cmd_rollback ;;
  check)    check ;;
  *) die "usage: release.sh deploy <tag> | rollback | check" ;;
esac
