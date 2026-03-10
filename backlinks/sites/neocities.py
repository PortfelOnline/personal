"""
NeoCities — регистрация + загрузка статьи через API
DA: 83, Do-Follow: Yes, Фаза 2
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import requests
import time
import tracker
from config import SITE_URL, EMAIL, USERNAME, DISPLAY_NAME, BIO_EN

NEOCITIES_API = "https://neocities.org/api"
PASSWORD = "Kadastr2025!"  # пароль для нового аккаунта


def register(page):
    """Зарегистрировать аккаунт через браузер."""
    print("Открываю страницу регистрации...")
    page.goto("https://neocities.org/signup")
    page.wait_for_load_state("networkidle")

    page.fill('input[name="sitename"]', USERNAME)
    page.fill('input[name="email"]', EMAIL)
    page.fill('input[name="password"]', PASSWORD)

    page.click('input[type="submit"], button[type="submit"]')
    page.wait_for_load_state("networkidle")
    time.sleep(2)

    url = page.url
    print(f"После регистрации URL: {url}")
    return "neocities.org" in url


def upload_page():
    """Загрузить HTML страницу через API."""
    content_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "content")
    with open(os.path.join(content_dir, "article_en.txt"), "r", encoding="utf-8") as f:
        text = f.read()

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Cadastral Mapping in Russia | KadastrMap</title>
<style>
  body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; line-height: 1.7; color: #333; }}
  h1 {{ color: #2c5f8a; }}
  a {{ color: #2c5f8a; }}
  .site-link {{ background: #f0f7ff; border-left: 4px solid #2c5f8a; padding: 12px 16px; margin: 20px 0; border-radius: 4px; }}
</style>
</head>
<body>
<h1>Cadastral Mapping in Russia: Digital Tools for Real Estate</h1>
<div class="site-link">
  Official service: <a href="{SITE_URL}" rel="dofollow"><strong>kadastrmap.info</strong></a> — Russia's public cadastral map
</div>
{"".join(f"<p>{p}</p>" for p in text.split(chr(10)+chr(10)) if p.strip())}
<hr>
<p><a href="{SITE_URL}">{SITE_URL}</a></p>
</body>
</html>"""

    resp = requests.post(
        f"{NEOCITIES_API}/upload",
        auth=(USERNAME, PASSWORD),
        files={"index.html": ("index.html", html, "text/html")},
        timeout=30,
    )
    data = resp.json()
    if data.get("result") == "success":
        return f"https://{USERNAME}.neocities.org"
    else:
        raise Exception(f"Upload failed: {data}")


def run():
    print("=== NeoCities ===")
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # headless=False чтобы видеть что происходит
        page = browser.new_page()

        try:
            ok = register(page)
            if not ok:
                print("Регистрация не прошла, проверь браузер")
                input("Нажми Enter после ручной регистрации...")

            print("Загружаю страницу через API...")
            url = upload_page()
            tracker.save("NeoCities", 83, True, "Web 2.0", 2, "done", url)

        except Exception as e:
            tracker.save("NeoCities", 83, True, "Web 2.0", 2, "failed", "", str(e))
            print(f"Ошибка: {e}")
        finally:
            input("Нажми Enter для закрытия браузера...")
            browser.close()


if __name__ == "__main__":
    run()
