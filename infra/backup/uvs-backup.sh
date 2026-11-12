#!/usr/bin/env bash
# Installed on the VPS as /opt/uvs/uvs-backup.sh; run daily by /etc/cron.d/uvs-backup (T095c).
# Custom-format pg_dump of the uvs database into /opt/uvs/backups, keeping the newest 7.
#
# Restore (README "Restore a backup"):
#   podman exec -i uvs-postgres sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists' < FILE.dump
set -Eeuo pipefail

DIR=/opt/uvs/backups
KEEP=7
mkdir -p "$DIR"
chmod 700 "$DIR"

out="$DIR/uvs-$(date +%Y-%m-%d_%H%M).dump"
trap 'rm -f "$out.partial"' EXIT

# pg_dump runs inside the container at the lowest CPU priority; credentials come from the
# container's own environment, so no password is needed here.
podman exec uvs-postgres sh -c 'nice -n 19 pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$out.partial"
[[ -s "$out.partial" ]] || { echo "uvs-backup: pg_dump produced an empty file" >&2; exit 1; }
mv "$out.partial" "$out"
chmod 600 "$out"

# Retention: keep the newest $KEEP dumps (by name, which sorts by date).
ls -1 "$DIR"/uvs-*.dump | sort | head -n -"$KEEP" | xargs -r rm -f --

logger -t uvs-backup "wrote $out ($(du -h "$out" | cut -f1))"
