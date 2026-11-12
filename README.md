# Urdu Video Studio

Students turn an idea into a short Urdu-narrated video. Spec, plan and tasks live in
`specs/001-video-generation/` (start with `quickstart.md` for local development).

**Licensing — non-commercial only.** The narration model (OmniVoice Urdu fine-tune) is
licensed CC-BY-NC, so this whole deployment may only be used for non-commercial,
educational purposes (Constitution Principle VIII).

## Architecture

| Piece | What it is | Production address |
|---|---|---|
| `frontend` | Next.js (standalone server) | `127.0.0.1:3100` |
| `backend` | FastAPI API | `127.0.0.1:8100` |
| `worker` | RQ worker: calls RunPod, assembles the video with ffmpeg | — |
| `scheduler` | marks stuck jobs failed and refunds the daily quota | — |
| `postgres` / `redis` | data / sessions + job queue | not published |
| `gpu-worker/` | RunPod Serverless container (Wan 2.2 + OmniVoice) | RunPod |

The browser only ever talks to one origin. Apache (cPanel) sends `/api/*` to the backend
(stripping `/api`) and everything else to the frontend. The frontend can also forward
`/api/*` itself, which is how the app works through an SSH tunnel before a domain exists.
Variables: `backend/.env.example` (development), `infra/.env.production.example` (production).

## Running the backend tests

The tests **truncate tables**, so they never use `DATABASE_URL`. They require a separate
database whose name ends in `_test`, supplied via `TEST_DATABASE_URL` (process env or
`backend/.env`; see `backend/.env.example`). If it is missing or the name doesn't end in
`_test`, pytest aborts immediately with a clear message. The test session also forces
`VIDEO_PROVIDER=mock` and `STORAGE_PROVIDER=local` (temp dir), so tests can't spend GPU time or
touch R2.

```bash
docker exec urdu-video-studio-dev-postgres-1 psql -U urdu_video_studio -d postgres \
  -c "CREATE DATABASE urdu_video_studio_test"            # one time
cd backend && source .venv/bin/activate
export TEST_DATABASE_URL=postgresql+psycopg://urdu_video_studio:urdu_video_studio@localhost:5432/urdu_video_studio_test
DATABASE_URL=$TEST_DATABASE_URL alembic upgrade head     # one time / after migrations
pytest
```

## Deploy

The server is a **shared cPanel/WHM VPS with 12 live sites**. Everything below is built
so that this app can't disturb them:

- Images are built **on your WSL machine**, never on the VPS.
- Containers run in **podman**. Don't install docker-ce: on AlmaLinux 8 it would remove
  podman and break the other projects' containers.
- Our containers, volumes and network are all named `uvs-*`. Ports bind to `127.0.0.1`
  only, and memory is capped at about 1.2 GB in total.
- On the VPS you **only** use `/opt/uvs/uvs` to run compose commands. It can only see
  this project.

In the commands below, replace `VPS_IP` with the server's IP address. Commands marked
**(WSL)** run on your machine, from the repo folder. Commands marked **(VPS)** run on the
server after `ssh -p 22 root@VPS_IP`.

### Step 1 — SSH key (WSL)

Create a key, unless `ls ~/.ssh/id_ed25519.pub` already shows one:

```bash
ssh-keygen -t ed25519 -C "uvs-deploy"
```

Copy it to the server (asks for the root password one last time):

```bash
ssh-copy-id -p 22 root@VPS_IP
```

Check that login now works without a password. Answer `yes` if it asks about the host key:

```bash
ssh -p 22 root@VPS_IP 'echo ok'
```

### Step 2 — Tell deploy.sh where the server is (WSL)

```bash
cp infra/deploy.env.example infra/deploy.env
```

```bash
nano infra/deploy.env
```

Set `VPS_HOST=VPS_IP`, and leave `VPS_PORT=22`. This file is gitignored.

### Step 3 — One-time server setup (VPS)

Check which network backend podman uses:

```bash
podman info --format '{{.Host.NetworkBackend}}'
```

If it prints `cni`, install the plugin that lets containers find each other by name:

```bash
dnf install -y podman-plugins
```

If it prints `netavark`, check `rpm -q aardvark-dns` instead, which does the same job.

Install the Docker Compose binary (v5.7.1, the version this setup was tested with), with
its checksum verified:

```bash
cd /tmp && curl -fLO https://github.com/docker/compose/releases/download/v5.7.1/docker-compose-linux-x86_64 && curl -fLO https://github.com/docker/compose/releases/download/v5.7.1/docker-compose-linux-x86_64.sha256 && sha256sum -c docker-compose-linux-x86_64.sha256 && install -m 0755 docker-compose-linux-x86_64 /usr/local/bin/docker-compose && cd
```

```bash
docker-compose version
```

Turn on podman's Docker-compatible API socket, which docker-compose talks to. It is a
root-only unix socket, not a network port:

```bash
systemctl enable --now podman.socket
```

Confirm the boot-time restarter is on. It should print `enabled`:

```bash
systemctl is-enabled podman-restart.service
```

### Step 4 — Production settings (VPS, then WSL, then VPS)

**(VPS)** Create the app folder:

```bash
mkdir -p /opt/uvs && chmod 700 /opt/uvs
```

**(WSL)** Upload the template:

```bash
scp -P 22 infra/.env.production.example root@VPS_IP:/opt/uvs/.env
```

**(VPS)** Lock the file down, then generate the two secrets. Run this twice: once for
`POSTGRES_PASSWORD`, once for `SESSION_COOKIE_SECRET`.

```bash
chmod 600 /opt/uvs/.env
```

```bash
openssl rand -hex 32
```

**(VPS)** Fill in every empty value: the RunPod, R2 and OpenAI keys plus the two secrets.
If nano is missing, install it first with `dnf install -y nano`.

```bash
nano /opt/uvs/.env
```

### Step 5 — First deploy (WSL)

`deploy.sh` refuses to run if you have uncommitted changes, because the image tag is the
git commit. Commit first, then:

```bash
./infra/deploy.sh
```

It builds both images, uploads them, migrates the database, starts the stack and ends
with a health check like this:

```
API      127.0.0.1:8100/health     -> {"status":"ok"}
API      127.0.0.1:3100/api/health -> {"status":"ok"}  (Next.js rewrite / SSH-tunnel path)
Frontend 127.0.0.1:3100/           -> HTTP 200
```

The first upload is about 400 MB, so give it a few minutes. Later deploys upload only
the image that changed.

### Step 6 — Open the app through an SSH tunnel (WSL + Chrome)

Leave this running. It prints nothing; stop it with Ctrl+C when you're done:

```bash
ssh -N -L 3100:127.0.0.1:3100 -p 22 root@VPS_IP
```

Open **http://localhost:3100** in Chrome, register, log in and create a video. The
tunnel only exposes the app to you. Nothing is public yet.

### Step 7 — Daily database backup (VPS)

Schedule it for 03:15 every night:

```bash
echo '15 3 * * * root /opt/uvs/uvs-backup.sh' > /etc/cron.d/uvs-backup
```

Run it once now and check that a `.dump` file appeared. Seven days of dumps are kept:

```bash
/opt/uvs/uvs-backup.sh && ls -lh /opt/uvs/backups
```

### Everyday commands (VPS)

| What | Command |
|---|---|
| Status of the 6 containers | `/opt/uvs/uvs ps` |
| Follow a service's logs | `/opt/uvs/uvs logs -f --tail 100 worker` |
| Restart one service | `/opt/uvs/uvs restart backend` |
| Apply a changed `/opt/uvs/.env` | `/opt/uvs/uvs up -d --force-recreate backend worker scheduler` |
| Health check (from WSL) | `./infra/deploy.sh check` |
| Memory use | `podman stats --no-stream --filter name=uvs-` |

**Never** run `podman system prune`, `podman volume prune`, `podman stop -a` or
`podman rm -a`. They act on every project on the server, and a volume prune would delete
the database while it is stopped. `/opt/uvs/uvs down -v` is blocked on purpose.

### Deploy an update (WSL)

Commit your changes, then:

```bash
./infra/deploy.sh
```

A video that is rendering during a deploy is interrupted. The scheduler marks it failed
and refunds the student's daily quota. If you can, deploy when nobody is rendering.

### Roll back to the previous release (WSL)

```bash
./infra/deploy.sh rollback
```

This switches the containers back to the previous image tag; the VPS keeps the live tag
and the one before it. Database migrations are **not** undone. If the bad release
changed the schema, restore a backup (below) as well.

### Restore a backup (VPS)

Pick a file with `ls /opt/uvs/backups`. Stop the app so nothing writes during the restore:

```bash
/opt/uvs/uvs stop backend worker scheduler
```

Restore it, replacing `FILE` with the backup's name:

```bash
podman exec -i uvs-postgres sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists' < /opt/uvs/backups/FILE.dump
```

Start the app again:

```bash
/opt/uvs/uvs start backend worker scheduler
```

## When the domain is ready

Until now the app is reachable only through the SSH tunnel. These steps put it on
`https://DOMAIN` with a free AutoSSL certificate. Replace `DOMAIN` with the domain and
`CPUSER` with its cPanel username.

**1. WHM: create the cPanel account.** In WHM go to Account Functions → Create a New
Account, with domain `DOMAIN`. Note the username (`CPUSER`).

**2. DNS.** At your DNS provider, create an `A` record for `DOMAIN` (and `www`, if you want
it) pointing to `VPS_IP`. Wait until this prints `VPS_IP`:

```bash
dig +short DOMAIN
```

**3. Certificate (VPS).** Run AutoSSL for the account:

```bash
/usr/local/cpanel/bin/autossl_check --user=CPUSER
```

In WHM → SSL/TLS → Manage AutoSSL → Manage Users, `DOMAIN` should show a valid
certificate. This can take a few minutes.

**4. Check the Apache modules (VPS).** You should see `proxy_module`,
`proxy_http_module`, `headers_module` and `rewrite_module`:

```bash
httpd -M 2>/dev/null | grep -E 'proxy_module|proxy_http_module|headers_module|rewrite_module'
```

**5. Install the proxy includes.** These only affect `DOMAIN`'s own virtual hosts. HTTPS
proxies `/api/` to `127.0.0.1:8100` and everything else to `127.0.0.1:3100`. HTTP
redirects to HTTPS. `/.well-known/` is never proxied, so AutoSSL renewals keep working.

**(VPS)** Create the include folders:

```bash
mkdir -p /etc/apache2/conf.d/userdata/ssl/2_4/CPUSER/DOMAIN /etc/apache2/conf.d/userdata/std/2_4/CPUSER/DOMAIN
```

**(WSL)** Upload the HTTPS include:

```bash
scp -P 22 infra/apache/ssl/urdu-video-studio.conf root@VPS_IP:/etc/apache2/conf.d/userdata/ssl/2_4/CPUSER/DOMAIN/
```

**(WSL)** Upload the HTTP include:

```bash
scp -P 22 infra/apache/std/urdu-video-studio.conf root@VPS_IP:/etc/apache2/conf.d/userdata/std/2_4/CPUSER/DOMAIN/
```

**(VPS)** Rebuild the Apache config:

```bash
/scripts/rebuildhttpdconf
```

**(VPS)** Test the config. It must print `Syntax OK`; if it doesn't, see "Undo" below and
don't restart:

```bash
apachectl -t
```

**(VPS)** Restart Apache:

```bash
/scripts/restartsrv_httpd
```

**6. Point the app at its domain (VPS).** In `/opt/uvs/.env`, set
`FRONTEND_BASE_URL=https://DOMAIN`. That is the base URL used in password-reset emails.
Also set `EMAIL_FROM` to an address on a domain verified in Resend.

```bash
nano /opt/uvs/.env
```

Apply the change:

```bash
/opt/uvs/uvs up -d --force-recreate backend worker scheduler
```

**7. Test.** This should print `{"status":"ok"}`:

```bash
curl -fsS https://DOMAIN/api/health
```

This should show `301` and a `Location: https://DOMAIN/` line:

```bash
curl -sI http://DOMAIN/ | head -3
```

This must show Apache's own `404`, not the app, which proves AutoSSL's path is not proxied:

```bash
curl -sI http://DOMAIN/.well-known/x | head -1
```

Then open `https://DOMAIN`, register and log in.

**Undo** (VPS) — remove the two include files and rebuild:

```bash
rm /etc/apache2/conf.d/userdata/{ssl,std}/2_4/CPUSER/DOMAIN/urdu-video-studio.conf && /scripts/rebuildhttpdconf && /scripts/restartsrv_httpd
```
