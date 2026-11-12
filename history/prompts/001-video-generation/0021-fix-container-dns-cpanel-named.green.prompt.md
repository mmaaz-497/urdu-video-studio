---
id: 0021
title: Fix container DNS refused by cPanel named
stage: green
date: 2026-11-12
surface: agent
model: claude-opus-5-5
feature: 001-video-generation
branch: main
user: Maaz
command: (free-form) first deploy failed at alembic: failed to resolve host 'postgres'
labels: ["deployment","podman","dns","cni","cpanel","bugfix","phase-8"]
links:
  spec: specs/001-video-generation/spec.md
  ticket: null
  adr: null
  pr: null
files:
 - infra/docker-compose.prod.yml
 - infra/release.sh
 - specs/001-video-generation/plan.md
 - specs/001-video-generation/tasks.md
tests:
 - Reproduction on AlmaLinux 8.10 + podman 4.9.4 (CNI) + named (listen-on any, recursion no): dnsmasq answers until `systemctl restart named`, then postgres/old-postgres/api.openai.com all REFUSED (identical to the VPS output)
 - deploy.sh of committed 366fae4 to that VM, then named restart -> backend cannot resolve postgres/redis
 - deploy.sh of the fix over the running old stack: uvs-net replaced in place, re-tag without upload, all checks green
 - named restarted again after the fix: all names resolve; 15 s mock job ready through SSH tunnel
 - simulated boot (podman start --all --filter restart-policy=always): healthy in ~21 s with fixed IPs
 - exact real-server state (no RELEASE, old DNS-enabled uvs-net, only postgres+redis up) -> release.sh deploy succeeds, DB volume kept
 - shellcheck -S warning (pass)
---

## Prompt

First deploy failed at `alembic upgrade head`: psycopg.OperationalError: failed to resolve host 'postgres'. Images shipped fine, and uvs-postgres and uvs-redis started. The real VPS uses the CNI network backend (podman-plugins installed), not netavark like your test VM, so service-name aliases may not resolve. Diagnostics from the VPS are below. Find the root cause and fix it so service discovery works on CNI (for example, connect via container names, or fix the network/alias config) — verify the fix against these facts, don't guess. Keep it working on netavark too. Don't touch tokoshopee-postgres or fiv-cobalt. Tell me the exact commands to retry the deploy.

[root@108-181-242-170 ~]# podman ps -a --filter name=uvs- --format '{{.Names}} {{.Status}}'; echo "--- network"; podman network inspect uvs-net --format '{{.Driver}} dns={{.DNSEnabled}}'; grep -E '"type"|domainName' /etc/cni/net.d/uvs-net.conflist 2>&1; rpm -q dnsmasq; echo "--- postgres aliases"; podman inspect uvs-postgres --format '{{range $k,$v := .NetworkSettings.Networks}}{{$k}} aliases={{$v.Aliases}}{{end}}'; echo "--- DNS test"; podman run --rm --network uvs-net docker.io/library/redis:7-alpine sh -c 'nslookup postgres; nslookup uvs-postgres' 2>&1 | tail -12
uvs-postgres Up 4 minutes (healthy)uvs-redis Up 4 minutes (healthy)--- networkbridge dns=true         "type": "bridge",
            "type": "host-local",         "type": "portmap",         "type": "firewall",         "type": "tuning"         "type": "dnsname",         "domainName": "dns.podman",
dnsmasq-2.79-37.el8_10.x86_64
--- postgres aliases
uvs-net aliases=[uvs-postgres postgres aeb06590b547]
--- DNS test** server can't find postgres.dns.podman: REFUSED
** server can't find postgres.dns.podman: REFUSED

Server:         10.89.0.1
Address:        10.89.0.1:53

** server can't find uvs-postgres.dns.podman: REFUSED

** server can't find uvs-postgres.dns.podman: REFUSED

## Response snapshot

Root cause: not CNI aliases (registered correctly) but cPanel's nameserver. named (listen-on any, recursion off) binds every interface address incl. the podman bridge gateway 10.89.0.1:53 whenever it restarts/reloads; from then on it receives the containers' queries instead of dnsname's dnsmasq and answers REFUSED for service names, container names and outside hosts. Reproduced exactly on AlmaLinux 8.10 + podman 4.9.4 + named. Fix: release.sh creates uvs-net with --disable-dns and subnet 10.89.77.0/24 (replacing an old DNS-enabled uvs-net in place; only our containers removed, volumes kept); fixed IPs per service + extra_hosts for postgres/redis/backend; one-off `migrate` service for alembic; post-deploy name-resolution check. Works identically on netavark (no DNS used). Verified on a VM recreating the real server's exact state.

## Outcome

- ✅ Impact: deploy no longer depends on container DNS; immune to named restarts; outbound DNS (OpenAI/RunPod/R2) also fixed.
- 🧪 Tests: reproduction + 6 verification scenarios listed above, all pass.
- 📁 Files: compose, release.sh, plan.md, tasks.md (T093e).
- 🔁 Next prompts: commit, `./infra/deploy.sh`, then Step 6 (SSH tunnel).
- 🧠 Reflection: the user's hypothesis (CNI aliases) was reasonable but the REFUSED rcode pointed elsewhere; dnsmasq never REFUSEs its own local domain.

## Evaluation notes (flywheel)

- Failure modes observed: earlier nested tests missed this because no system nameserver ran on the test VM.
- Graders run and results (PASS/FAIL): shellcheck PASS; all VM scenarios PASS.
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): add a cPanel-like named to any future pre-deploy test VM by default.
