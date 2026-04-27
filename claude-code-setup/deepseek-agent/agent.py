#!/usr/bin/env python3
"""
DeepSeek Agent — 24/7 scheduled AI tasks in Docker.
Replaces Claude Code Cloud Code triggers.

Scheduler: APScheduler (in-process cron)
HTTP API:  stdlib http.server (:8766)

Endpoints:
  GET  /health        — status + uptime
  GET  /tasks         — list scheduled tasks with next run time
  POST /run/<name>    — trigger task manually

Timezone: UTC. IST = UTC+5:30.
  nightly-cleanup:   22:27 UTC daily   (3:57 IST)
  weekly-refs-update: 3:30 UTC Monday  (9:00 IST)
"""

import sys
import os
import json
import signal
import time
import subprocess
import shlex
import shutil
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread

# Ensure deepseek_api is importable from the same directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from deepseek_api import chat, FAST_MODEL

START_TIME = datetime.now(timezone.utc)


# ── Tasks ────────────────────────────────────────────────────────

def nightly_cleanup():
    """Daily maintenance: clean logs, check disk, AI summary."""
    log("nightly-cleanup: starting")

    # Clean Docker builder cache (>48h unused)
    r = run("docker builder prune --filter until=48h --force 2>&1 | tail -1")
    log(f"  docker prune: {r.strip()}")

    # Check disk
    disk = shutil.disk_usage("/")
    pct = disk.used / disk.total * 100
    log(f"  disk: {pct:.1f}% ({disk.free // 1024**3}G free)")

    # DeepSeek daily summary
    try:
        summary = chat(
            "Кратко (1-2 предложения): сегодняшняя дата — "
            + datetime.now(timezone.utc).strftime("%Y-%m-%d")
            + ". Напомни проверить бэкапы и логи сервера n. Ответь на русском.",
            model=FAST_MODEL,
            temperature=0.3,
        )
        log(f"  AI summary: {summary.strip()}")
    except Exception as e:
        log(f"  AI summary failed: {e}")

    if pct > 85:
        _alert(f"Disk usage {pct:.1f}% on server n")

    log("nightly-cleanup: done")


def weekly_refs_update():
    """Weekly: update reference repos + graphify graphs."""
    log("weekly-refs-update: starting")

    # Update managed refs pool
    refs_dir = os.path.expanduser("~/.claude/refs")
    if os.path.isdir(refs_dir):
        for name in os.listdir(refs_dir):
            path = os.path.join(refs_dir, name)
            if os.path.isdir(os.path.join(path, ".git")):
                r = run(f"cd {shlex.quote(path)} && git fetch --prune --quiet origin 2>&1 && git reset --hard origin/HEAD --quiet 2>&1")
                log(f"  refs/{name}: {r.strip() or 'ok'}")

    # AI summary
    try:
        summary = chat(
            "Ты — DevOps-ассистент. Сегодня понедельник, время еженедельного обновления. "
            "Напомни проверить: 1) бэкапы сервера n, 2) обновления пакетов, "
            "3) свободное место на диске. Ответь коротко, на русском.",
            model=FAST_MODEL,
            temperature=0.3,
        )
        log(f"  AI: {summary.strip()}")
    except Exception as e:
        log(f"  AI failed: {e}")

    log("weekly-refs-update: done")


TASKS = {
    "nightly-cleanup": {
        "func": nightly_cleanup,
        "cron": {"hour": 22, "minute": 27},  # 3:57 IST
        "description": "Daily maintenance + AI summary",
    },
    "weekly-refs-update": {
        "func": weekly_refs_update,
        "cron": {"day_of_week": "mon", "hour": 3, "minute": 30},  # 9:00 IST Monday
        "description": "Weekly refs update + graphify rebuild",
    },
}


# ── Helpers ──────────────────────────────────────────────────────

def log(msg: str):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[{ts}] {msg}", flush=True)


def run(cmd: str) -> str:
    try:
        return subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, timeout=120).decode()
    except subprocess.CalledProcessError as e:
        return e.output.decode() if e.output else str(e)


def _alert(msg: str):
    log(f"ALERT: {msg}")
    try:
        chat(
            f"Отправь alert: {msg}. Ответь OK.",
            model=FAST_MODEL,
            temperature=0.1,
        )
    except Exception:
        pass


# ── HTTP API ─────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # suppress access logs

    def _json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False, indent=2).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            uptime = str(datetime.now(timezone.utc) - START_TIME).split(".")[0]
            jobs = []
            for job in scheduler.get_jobs():
                jobs.append({
                    "name": job.name,
                    "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                })
            self._json({"status": "ok", "uptime": uptime, "tasks": jobs})

        elif self.path == "/tasks":
            jobs = []
            for job in scheduler.get_jobs():
                jobs.append({
                    "name": job.name,
                    "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                    "trigger": str(job.trigger),
                })
            self._json(jobs)

        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):
        path = self.path.rstrip("/")
        if path.startswith("/run/") and len(path) > 5:
            name = path[5:]
            if name in TASKS:
                log(f"Manual trigger: {name}")
                Thread(target=TASKS[name]["func"], daemon=True).start()
                self._json({"triggered": name})
            else:
                self._json({"error": f"unknown task: {name}"}, 404)
        else:
            self._json({"error": "use POST /run/<task_name>"}, 400)


# ── Main ─────────────────────────────────────────────────────────

scheduler = BackgroundScheduler(timezone="UTC")
scheduler.start()

for name, cfg in TASKS.items():
    scheduler.add_job(
        cfg["func"],
        CronTrigger(**cfg["cron"], timezone="UTC"),
        name=name,
        replace_existing=True,
    )
    log(f"Scheduled: {name} ({cfg['description']})")

log("DeepSeek Agent started")

# Graceful shutdown on SIGTERM (Docker stop)
signal.signal(signal.SIGTERM, lambda *_: (log("Shutting down..."), scheduler.shutdown(wait=False), sys.exit(0)))

# HTTP server
server = HTTPServer(("0.0.0.0", 8766), Handler)
log("HTTP API on :8766")
server.serve_forever()
