#!/usr/bin/env python3
"""Live diagnosis of the RunPod Serverless endpoint (read-only unless a flag says otherwise).

Reads RUNPOD_API_KEY / RUNPOD_ENDPOINT_ID / MAX_PROCESSING_SECONDS from backend/.env
(or the environment). The API key is never printed.

  python gpu-worker/scripts/diagnose_endpoint.py                 # report only
  python gpu-worker/scripts/diagnose_endpoint.py --purge         # also cancel all queued jobs
  python gpu-worker/scripts/diagnose_endpoint.py --fix-timeout   # raise executionTimeoutMs if too low
  python gpu-worker/scripts/diagnose_endpoint.py --apply-fix     # set GPUs to RTX 4090/5090 + CUDA 13.0

APIs used (RunPod docs):
  GET  https://api.runpod.ai/v2/{id}/health               worker + job counts
  POST https://api.runpod.ai/v2/{id}/purge-queue          cancel queued (not running) jobs
  GET  https://rest.runpod.io/v1/endpoints/{id}           endpoint config (REST)
  PATCH https://rest.runpod.io/v1/endpoints/{id}          update config (only with --fix-timeout)
  POST https://api.runpod.io/graphql                      dataCenters.gpuAvailability / gpuTypes
Stdlib only, so it runs anywhere.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parents[2] / "backend" / ".env"
V2 = "https://api.runpod.ai/v2"
REST = "https://rest.runpod.io/v1"
GRAPHQL = "https://api.runpod.io/graphql"
DATA_CENTER = "EU-RO-1"
MIN_VRAM_GB = 24


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text("utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip("'\"")
    for k in ("RUNPOD_API_KEY", "RUNPOD_ENDPOINT_ID", "MAX_PROCESSING_SECONDS"):
        if os.environ.get(k):
            env[k] = os.environ[k]
    return env


def call(method: str, url: str, key: str, body: dict | None = None) -> tuple[int, object]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "User-Agent": "urdu-video-studio-diagnose/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode()
            return r.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, raw[:500]
    except urllib.error.URLError as e:
        return 0, str(e.reason)


def section(title: str) -> None:
    print(f"\n=== {title} ===")


def show_health(eid: str, key: str) -> dict:
    section("1. /health (worker + job counts)")
    status, h = call("GET", f"{V2}/{eid}/health", key)
    if status != 200 or not isinstance(h, dict):
        print(f"  FAILED HTTP {status}: {h}")
        return {}
    workers, jobs = h.get("workers", {}), h.get("jobs", {})
    for name in ("initializing", "ready", "idle", "running", "throttled", "unhealthy"):
        print(f"  workers.{name:<13} {workers.get(name, '(not reported)')}")
    for name, v in workers.items():  # anything else RunPod reports
        if name not in ("initializing", "ready", "idle", "running", "throttled", "unhealthy"):
            print(f"  workers.{name:<13} {v}")
    for name in ("inQueue", "inProgress", "completed", "failed", "retried"):
        print(f"  jobs.{name:<16} {jobs.get(name, '(not reported)')}")
    if workers.get("throttled"):
        print("  !! Throttled workers: the selected GPU types have no capacity right now.")
    if workers.get("unhealthy"):
        print("  !! Unhealthy workers: check the worker logs in the dashboard (image crash/OOM).")
    return h


def show_config(eid: str, key: str) -> dict:
    section("2. Endpoint config (REST)")
    status, cfg = call("GET", f"{REST}/endpoints/{eid}?includeTemplate=true", key)
    if status != 200 or not isinstance(cfg, dict):
        print(f"  FAILED HTTP {status}: {cfg}")
        return {}
    for f in (
        "name", "computeType", "gpuTypeIds", "gpuCount", "dataCenterIds", "networkVolumeId",
        "networkVolumeIds", "workersMin", "workersMax", "idleTimeout", "executionTimeoutMs",
        "scalerType", "scalerValue", "allowedCudaVersions", "flashboot", "version",
    ):
        if f in cfg:
            print(f"  {f:<20} {cfg[f]}")
    tpl = cfg.get("template") or {}
    if tpl:
        print(f"  template.imageName   {tpl.get('imageName')}")
        print(f"  template.containerDiskInGb {tpl.get('containerDiskInGb')}")
        print(f"  template.env keys    {sorted((tpl.get('env') or {}).keys())}")
    status, res = gql(key, "query { myself { endpoints { id gpuIds locations allowedCudaVersions } } }")
    if status == 200 and isinstance(res, dict) and res.get("data"):
        for ep in res["data"]["myself"]["endpoints"]:
            if ep["id"] == eid:
                cfg["_gpuIds"] = ep.get("gpuIds") or ""
                cfg["_locations"] = ep.get("locations") or ""
                print(f"  gpuIds (GraphQL)     {cfg['_gpuIds']!r}")
                print(f"  locations (GraphQL)  {cfg['_locations']!r}")
                print(f"  allowedCudaVersions  {ep.get('allowedCudaVersions')!r}  (min {cfg.get('minCudaVersion')})")
    env_keys = sorted((cfg.get("env") or {}).keys())
    if env_keys:
        print(f"  endpoint.env keys    {env_keys}")
    return cfg


def gql(key: str, query: str) -> tuple[int, object]:
    return call("POST", GRAPHQL, key, {"query": query})


def show_stock(key: str, cfg: dict) -> None:
    section(f"3. GPU stock in {DATA_CENTER}")
    q = """query { dataCenters { id name gpuAvailability { gpuTypeId displayName stockStatus } } }"""
    status, res = gql(key, q)
    errors = res.get("errors") if isinstance(res, dict) else None
    if status != 200 or errors or not isinstance(res, dict):
        print(f"  GraphQL failed HTTP {status}: {errors or res}")
        print("  -> Check stock manually: Dashboard > Serverless > endpoint > Edit > GPU selection.")
        return
    dcs = {d["id"]: d for d in res["data"]["dataCenters"]}
    dc = dcs.get(DATA_CENTER)
    if not dc:
        print(f"  {DATA_CENTER} not in data center list: {sorted(dcs)}")
        return
    avail = {g["gpuTypeId"]: g for g in dc["gpuAvailability"] or []}

    vram: dict[str, float] = {}
    s2, r2 = gql(key, "query { gpuTypes { id displayName memoryInGb } }")
    if s2 == 200 and isinstance(r2, dict) and not r2.get("errors"):
        vram = {g["id"]: g.get("memoryInGb") or 0 for g in r2["data"]["gpuTypes"]}

    tokens = [t.strip() for t in (cfg.get("_gpuIds") or "").split(",") if t.strip()]
    selected = list(cfg.get("gpuTypeIds") or []) or [t for t in tokens if not t.startswith("-")]
    excluded = [t[1:] for t in tokens if t.startswith("-")]
    if excluded:
        print(f"  Excluded GPUs: {excluded}")
    pools = [t for t in selected if t.isupper() and "_" in t]
    if pools:
        print(f"  Selected GPU pools: {pools} (a pool expands to several GPU types)")
        selected = [t for t in selected if t not in pools]
    if pools and excluded:
        print("  !! ROOT CAUSE CANDIDATE: a pool is selected AND its member GPUs are excluded.")
        print("     ADA_48_PRO = L40 / L40S / RTX 6000 Ada; excluding all three leaves zero GPUs,")
        print("     so no worker can ever be scheduled (stays Initializing / 0 workers).")
    print("  Selected GPU types:")
    any_stock = False
    for g in selected:
        st = (avail.get(g) or {}).get("stockStatus") or "not offered here"
        in_stock = st.lower() not in ("none", "unavailable", "not offered here", "")
        any_stock = any_stock or in_stock
        print(f"    {g:<40} {vram.get(g, '?')} GB   stock in {DATA_CENTER}: {st}")
    if pools and not selected:
        print("  (only pools selected - see above)")
    if selected and not any_stock:
        print(f"  !! ROOT CAUSE: none of the selected GPU types has stock in {DATA_CENTER}.")
        print("     Workers cannot start, so the endpoint sits at 'Initializing'/throttled.")

    print(f"  GPU types with >= {MIN_VRAM_GB} GB VRAM and stock in {DATA_CENTER}:")
    rows = []
    for gid, g in avail.items():
        st = g.get("stockStatus") or ""
        if st.lower() in ("none", "unavailable", ""):
            continue
        gb = vram.get(gid, 0)
        if gb >= MIN_VRAM_GB:
            rows.append((gb, gid, g.get("displayName") or gid, st))
    for gb, gid, name, st in sorted(rows):
        print(f"    {gid:<40} {name:<24} {gb:>4} GB  stock: {st}")
    if not rows:
        print("    (none) - nothing >= 24 GB is currently in stock in this data center.")
        print("    Wait, or create a new volume in another region and re-download the weights.")


RECOMMENDED_GPUS = ["NVIDIA GeForce RTX 4090", "NVIDIA GeForce RTX 5090"]  # >= 24 GB, stocked in EU-RO-1


def apply_fix(cfg: dict, eid: str, key: str) -> None:
    section("4b. Applying GPU / CUDA fix")
    body = {
        "gpuTypeIds": RECOMMENDED_GPUS,
        "allowedCudaVersions": ["13.0"],  # image is built on cuda13.0; host driver must be >= 13.0
    }
    print(f"  PATCH {body}")
    status, res = call("PATCH", f"{REST}/endpoints/{eid}", key, body)
    print(f"  HTTP {status}" + ("" if status == 200 else f" {res}"))
    print("  (RunPod does a rolling release; verify with a re-run of this script.)")


def check_settings(cfg: dict, env: dict, eid: str, key: str, fix: bool) -> None:
    section("4. Settings audit")
    problems = 0
    need_s = int(env.get("MAX_PROCESSING_SECONDS", "600"))
    have_ms = cfg.get("executionTimeoutMs")
    if have_ms is None:
        print("  executionTimeoutMs not reported.")
    elif have_ms < need_s * 1000:
        problems += 1
        print(f"  !! executionTimeoutMs={have_ms} ms < MAX_PROCESSING_SECONDS={need_s}s "
              f"({need_s * 1000} ms): RunPod would kill the job before the app gives up.")
        if fix:
            status, res = call("PATCH", f"{REST}/endpoints/{eid}", key,
                               {"executionTimeoutMs": need_s * 1000})
            print(f"  PATCH executionTimeoutMs -> {need_s * 1000}: HTTP {status}"
                  + ("" if status == 200 else f" {res}"))
        else:
            print("     Re-run with --fix-timeout, or Dashboard > Edit endpoint > Execution Timeout.")
    else:
        print(f"  executionTimeoutMs {have_ms} ms >= {need_s}s  OK")

    if not (cfg.get("networkVolumeId") or cfg.get("networkVolumeIds")):
        problems += 1
        print("  !! No network volume attached -> model dropdowns are empty (the earlier failure).")
    else:
        print(f"  network volume attached: {cfg.get('networkVolumeId') or cfg.get('networkVolumeIds')}  OK")

    dcs = cfg.get("dataCenterIds") or []
    if dcs and DATA_CENTER not in dcs:
        problems += 1
        print(f"  !! dataCenterIds {dcs} does not include {DATA_CENTER} (where the volume lives).")
    if cfg.get("workersMax") in (0, None):
        problems += 1
        print("  !! workersMax is 0: no worker can ever start.")
    if (cfg.get("workersMax") or 0) > 1:
        print(f"  note: workersMax={cfg.get('workersMax')}; each worker needs the volume's ~18 GB read.")
    cuda = cfg.get("minCudaVersion") or ""
    if not cfg.get("allowedCudaVersions") and cuda and float(cuda) < 13.0:
        problems += 1
        print(f"  !! Image needs host driver CUDA >= 13.0 but minCudaVersion={cuda} and no allowed list:")
        print("     a worker may land on a CUDA 12.x host and fail with 'driver too old'.")
        print("     Set Allowed CUDA versions = 13.0 (dashboard > Edit endpoint) or use --apply-fix.")
    if problems == 0:
        print("  no config problems found.")


def purge(eid: str, key: str) -> None:
    section("5. Purge queued jobs")
    status, res = call("POST", f"{V2}/{eid}/purge-queue", key)
    print(f"  HTTP {status}: {res}")
    print("  (only queued jobs are removed; a job already IN_PROGRESS keeps running)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--purge", action="store_true", help="cancel all stale queued jobs")
    ap.add_argument("--apply-fix", action="store_true",
                    help="PATCH gpuTypeIds=[RTX 4090, RTX 5090] and allowedCudaVersions=[13.0]")
    ap.add_argument("--fix-timeout", action="store_true",
                    help="raise executionTimeoutMs to MAX_PROCESSING_SECONDS if lower")
    args = ap.parse_args()

    env = load_env()
    key, eid = env.get("RUNPOD_API_KEY", ""), env.get("RUNPOD_ENDPOINT_ID", "")
    if not key or not eid:
        print(f"RUNPOD_API_KEY / RUNPOD_ENDPOINT_ID missing in {ENV_FILE}", file=sys.stderr)
        return 2
    print(f"endpoint: {eid}   api key: set ({len(key)} chars, not shown)")

    show_health(eid, key)
    cfg = show_config(eid, key)
    show_stock(key, cfg)
    if cfg:
        check_settings(cfg, env, eid, key, args.fix_timeout)
    if args.purge:
        purge(eid, key)  # purge BEFORE applying the fix so stale jobs don't start on new workers
    if args.apply_fix:
        apply_fix(cfg, eid, key)
    return 0


if __name__ == "__main__":
    sys.exit(main())
