#!/usr/bin/env python3
"""
Backlink Bot — точка входа

Запуск:
  python3 main.py --site kadastrmap telegra_ph    # конкретная платформа
  python3 main.py --site get-my-agent telegra_ph  # для другого домена
  python3 main.py --site kadastrmap all           # все платформы
  python3 main.py --site kadastrmap status        # прогресс
  python3 main.py --site kadastrmap top20         # топ-20 do-follow из Rankd
  python3 rankd_scraper.py                        # обновить базу Rankd

Без --site используется дефолтный домен (kadastrmap).
"""
import sys
import os

# ── Разбор --site аргумента ───────────────────────────────────────────────────
args = sys.argv[1:]
if "--site" in args:
    idx = args.index("--site")
    os.environ["BACKLINK_SITE"] = args[idx + 1]
    args = args[:idx] + args[idx+2:]

import config   # noqa (после установки env)
import tracker

# ── Зарегистрированные платформы ──────────────────────────────────────────────
SITES = {
    # Полностью автоматические (API)
    "telegra_ph": ("sites.telegra_ph", "run"),  # DA 81
    # Браузерные (Playwright)
    "neocities":  ("sites.neocities",  "run"),  # DA 77
    "wikidot":    ("sites.wikidot",    "run"),  # DA 83
    "disqus":     ("sites.disqus",     "run"),  # DA 93
    "about_me":   ("sites.about_me",   "run"),  # DA 71
    "medium":     ("sites.medium",     "run"),  # DA 96
    "quora":      ("sites.quora",      "run"),  # DA 93
    "folkd":      ("sites.folkd",      "run"),  # DA 60, bookmark
    "diigo":      ("sites.diigo",      "run"),  # DA 70, bookmark
}


def run_site(name, module_path, func_name):
    print(f"\n{'='*50}")
    print(f"Платформа: {name}  |  Сайт: {config.ACTIVE_SITE} ({config.SITE_URL})")
    print(f"{'='*50}")
    try:
        import importlib
        mod = importlib.import_module(module_path)
        getattr(mod, func_name)()
    except Exception as e:
        print(f"Критическая ошибка в {name}: {e}")
        import traceback; traceback.print_exc()


def run_top_rankd(n=20):
    """Запустить топ-N do-follow платформ из Rankd через браузер (полу-авто)."""
    import json
    from pathlib import Path
    rankd_file = Path(__file__).parent / "rankd_platforms.json"
    if not rankd_file.exists():
        print("❌ rankd_platforms.json не найден. Запусти: python3 rankd_scraper.py")
        return

    with open(rankd_file) as f:
        platforms = json.load(f)

    done_sites = _get_done_sites()
    pending = [p for p in platforms if p["do_follow"] and p["name"] not in done_sites]
    top = sorted(pending, key=lambda x: x["da"], reverse=True)[:n]

    print(f"\nТоп-{n} Do-Follow (ещё не сделано):")
    for p in top:
        print(f"  DA{p['da']:>3}  {p['name']:<30}  {p['website']}")
    input("\nНажми Enter для старта (откроется браузер)...")

    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)
        for p in top:
            print(f"\n=== {p['name']} (DA {p['da']}) ===")
            print(f"Сайт: {p['website']}")
            print("Инструкция:")
            print(p["instructions"][:600])
            print(f"\nТекущий профиль: {config.DISPLAY_NAME} | {config.SITE_URL}")

            page = browser.new_page()
            try:
                page.goto(p["website"], timeout=15000)
            except Exception:
                pass

            result = input("Результат (done/skip/fail): ").strip().lower()
            profile_url = notes = ""
            if result == "done":
                profile_url = input("URL профиля (Enter пропустить): ").strip()
            else:
                notes = input("Заметки: ").strip()

            status = {"done": "done", "fail": "failed"}.get(result, "skipped")
            tracker.save(p["name"], p["da"], p["do_follow"], p["type"],
                         1, status, profile_url, notes)
            page.close()
        browser.close()


def _get_done_sites() -> set:
    """Вернуть набор уже обработанных платформ из CSV."""
    import csv
    from pathlib import Path
    done = set()
    csv_file = Path(__file__).parent / config.RESULTS_FILE
    if not csv_file.exists():
        return done
    with open(csv_file, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("status") == "done":
                done.add(row["site"])
    return done


def main():
    tracker.init()

    if not args:
        print(__doc__)
        return

    cmd = args[0]

    if cmd == "status":
        tracker.show()
    elif cmd == "top20":
        run_top_rankd(20)
        tracker.show()
    elif cmd == "all":
        for name, (module, func) in SITES.items():
            run_site(name, module, func)
        tracker.show()
    elif cmd in SITES:
        run_site(cmd, *SITES[cmd])
    else:
        print(f"Неизвестная команда: {cmd}")
        print(f"Платформы: {', '.join(SITES.keys())}")
        print("Или: all | status | top20")


if __name__ == "__main__":
    main()
