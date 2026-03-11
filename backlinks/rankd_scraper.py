#!/usr/bin/env python3
"""
Rankd SEO — скрапер базы платформ.

Запуск:
  python3 rankd_scraper.py          # открывает браузер, ты логинишься вручную
  python3 rankd_scraper.py --headless  # если уже сохранена сессия в rankd_session.json

Результат: rankd_platforms.json — список всех платформ с DA, DoFollow, типом, инструкцией.
"""
import sys
import json
import time
import re
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

RANKD_URL   = "https://rankdseo.com"
SESSION_FILE = Path(__file__).parent / "rankd_session.json"
OUTPUT_FILE  = Path(__file__).parent / "rankd_platforms.json"

HEADLESS = "--headless" in sys.argv


def scrape_platform_page(page, url: str) -> dict | None:
    """Scrape a single platform page and return structured data."""
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
        time.sleep(0.5)

        html = page.content()

        # Title / platform name
        title = page.title().replace(" - Rankd SEO", "").replace("| Rankd SEO", "").strip()

        # Extract DA, PA, DoFollow from page text
        text = page.inner_text("body")
        da = pa = 0
        do_follow = False

        m = re.search(r'DA[:\s]+(\d+)', text)
        if m: da = int(m.group(1))

        m = re.search(r'PA[:\s]+(\d+)', text)
        if m: pa = int(m.group(1))

        m = re.search(r'Do-Follow[:\s]+(YES|NO)', text, re.IGNORECASE)
        if m: do_follow = m.group(1).upper() == "YES"

        # Website URL
        website = ""
        m = re.search(r'Website[:\s]+(https?://\S+)', text)
        if m: website = m.group(1).rstrip('.')

        # Link type (from category tags or title keywords)
        link_type = "profile"
        text_lower = text.lower()
        if "bookmark" in text_lower or "bookmarking" in text_lower:
            link_type = "bookmark"
        elif "web 2.0" in text_lower or "blog" in text_lower:
            link_type = "web2.0"
        elif "article" in text_lower or "guest post" in text_lower:
            link_type = "article"

        # Instructions — grab the main content block
        instructions = ""
        try:
            instructions = page.inner_text(".entry-content, .post-content, article") or ""
            # Clean up
            instructions = re.sub(r'\n{3,}', '\n\n', instructions).strip()
        except:
            pass

        return {
            "name": title,
            "url": url,
            "website": website,
            "da": da,
            "pa": pa,
            "do_follow": do_follow,
            "type": link_type,
            "instructions": instructions[:2000],
        }
    except Exception as e:
        print(f"  Error scraping {url}: {e}")
        return None


def get_all_platform_urls(page) -> list[str]:
    """Get all platform page URLs from the Rankd database."""
    urls = set()

    # Try the main backlinks listing with pagination
    for page_num in range(1, 50):  # Up to 50 pages
        if page_num == 1:
            url = f"{RANKD_URL}/backlinks/"
        else:
            url = f"{RANKD_URL}/backlinks/page/{page_num}/"

        page.goto(url, wait_until="domcontentloaded", timeout=20000)
        time.sleep(0.3)

        # Check if 404 / no content
        if page.url.endswith("/backlinks/") and page_num > 1:
            break
        if "404" in page.title() or "Page not found" in page.title():
            break

        # Collect post links
        links = page.eval_on_selector_all(
            "a[href]",
            "els => els.map(el => el.href)"
        )

        page_urls = [
            l for l in links
            if "rankdseo.com" in l
            and l.count("/") >= 5  # actual post URL depth
            and "/category/" not in l
            and "/author/" not in l
            and "/membership" not in l
            and "/wpauto" not in l
            and "/page/" not in l
            and "/tag/" not in l
            and l != f"{RANKD_URL}/"
        ]

        new_count = len([u for u in page_urls if u not in urls])
        urls.update(page_urls)
        print(f"  Page {page_num}: found {len(page_urls)} links ({new_count} new), total: {len(urls)}")

        if new_count == 0:
            break

    # Also try category pages
    for cat in ["backlinks", "backlink", "profiles", "bookmarks", "web-2-0"]:
        try:
            page.goto(f"{RANKD_URL}/category/{cat}/", wait_until="domcontentloaded", timeout=15000)
            links = page.eval_on_selector_all("a[href]", "els => els.map(el => el.href)")
            page_urls = [l for l in links if "rankdseo.com" in l and l.count("/") >= 5]
            urls.update(page_urls)
        except:
            pass

    return list(urls)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)

        # Try to restore session
        if SESSION_FILE.exists():
            print(f"Restoring session from {SESSION_FILE}...")
            ctx = browser.new_context(storage_state=str(SESSION_FILE))
        else:
            ctx = browser.new_context()

        page = ctx.new_page()

        # Check if logged in
        page.goto(RANKD_URL, wait_until="domcontentloaded", timeout=20000)
        logged_in = "logout" in page.content().lower() or "my-profile" in page.content().lower()

        if not logged_in:
            print("\n⚠️  Не авторизован. Открываю страницу входа...")
            page.goto(f"{RANKD_URL}/wp-login.php")
            print("👉 Войди в аккаунт Rankd в браузере, потом нажми Enter здесь...")
            input()
            # Save session
            ctx.storage_state(path=str(SESSION_FILE))
            print(f"Сессия сохранена → {SESSION_FILE}")
        else:
            print("✅ Авторизован")

        # Collect all platform URLs
        print("\n📋 Собираю список платформ...")
        urls = get_all_platform_urls(page)
        print(f"Найдено URL: {len(urls)}")

        # Scrape each platform
        platforms = []
        existing = {}
        if OUTPUT_FILE.exists():
            with open(OUTPUT_FILE) as f:
                for item in json.load(f):
                    existing[item["url"]] = item

        print(f"\n🔍 Скрапинг платформ (уже есть: {len(existing)})...")
        for i, url in enumerate(urls, 1):
            if url in existing:
                platforms.append(existing[url])
                continue

            print(f"  [{i}/{len(urls)}] {url}")
            data = scrape_platform_page(page, url)
            if data:
                platforms.append(data)
                # Save incrementally
                with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                    json.dump(platforms + list(existing.values()), f, ensure_ascii=False, indent=2)

            time.sleep(0.5)

        browser.close()

    # Final save & stats
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(platforms, f, ensure_ascii=False, indent=2)

    do_follow = [p for p in platforms if p["do_follow"]]
    print(f"\n✅ Готово! Всего платформ: {len(platforms)}")
    print(f"   Do-Follow: {len(do_follow)}")
    print(f"   No-Follow: {len(platforms) - len(do_follow)}")
    print(f"   Файл: {OUTPUT_FILE}")

    # Print top Do-Follow by DA
    top = sorted(do_follow, key=lambda x: x["da"], reverse=True)[:20]
    print("\nТоп Do-Follow платформы по DA:")
    for p in top:
        print(f"  DA{p['da']:>3}  {p['name']:<30}  {p['website']}")


if __name__ == "__main__":
    main()
