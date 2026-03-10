"""
Трекер прогресса — сохраняет результаты в CSV
"""
import csv
import os
from datetime import datetime

RESULTS_FILE = os.path.join(os.path.dirname(__file__), "results/progress.csv")

HEADERS = ["date", "site", "da", "do_follow", "type", "phase", "status", "profile_url", "notes"]


def init():
    """Создать файл с заголовками если не существует."""
    os.makedirs(os.path.dirname(RESULTS_FILE), exist_ok=True)
    if not os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(HEADERS)


def save(site: str, da: int, do_follow: bool, link_type: str,
         phase: int, status: str, profile_url: str = "", notes: str = ""):
    """Записать результат."""
    init()
    with open(RESULTS_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            site,
            da,
            "Yes" if do_follow else "No",
            link_type,
            phase,
            status,   # done / failed / pending
            profile_url,
            notes,
        ])
    print(f"[{status.upper()}] {site} → {profile_url or '—'}")


def show():
    """Вывести текущий прогресс."""
    init()
    done = failed = pending = 0
    with open(RESULTS_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["status"] == "done":
                done += 1
            elif row["status"] == "failed":
                failed += 1
            else:
                pending += 1
    print(f"\nПрогресс: ✅ {done} | ❌ {failed} | ⏳ {pending}")
