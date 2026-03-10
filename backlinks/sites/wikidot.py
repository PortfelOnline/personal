"""
Wikidot — регистрация + создание wiki-сайта со статьёй
DA: 83, Do-Follow: Yes, Фаза 2
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import time
import tracker
from config import SITE_URL, EMAIL, USERNAME, DISPLAY_NAME

PASSWORD = "Kadastr2025!"
SITE_NAME = "kadastrmap"  # будет kadastrmap.wikidot.com


def run():
    print("=== Wikidot ===")
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        try:
            # Шаг 1: Регистрация
            print("Регистрация на Wikidot...")
            page.goto("https://www.wikidot.com/register")
            page.wait_for_load_state("networkidle")
            time.sleep(1)

            page.fill('input[name="login"]', USERNAME)
            page.fill('input[name="email"]', EMAIL)
            page.fill('input[name="password"]', PASSWORD)
            page.fill('input[name="password2"]', PASSWORD)

            # Чекбокс согласия
            try:
                page.check('input[name="agree"]')
            except:
                pass

            page.click('input[type="submit"], button[type="submit"]')
            page.wait_for_load_state("networkidle")
            time.sleep(2)
            print(f"URL после регистрации: {page.url}")

            input("Подтверди email, потом нажми Enter...")

            # Шаг 2: Создать новый сайт
            print("Создаю сайт...")
            page.goto("https://www.wikidot.com/create-site")
            page.wait_for_load_state("networkidle")
            time.sleep(1)

            page.fill('input[name="site"]', SITE_NAME)
            try:
                page.fill('input[name="name"]', "KadastrMap — Cadastral Map of Russia")
            except:
                pass

            page.click('input[type="submit"], button[type="submit"]')
            page.wait_for_load_state("networkidle")
            time.sleep(2)
            print(f"URL после создания сайта: {page.url}")

            # Шаг 3: Создать страницу с контентом
            print("Создаю страницу с контентом...")
            page.goto(f"https://{SITE_NAME}.wikidot.com/start")
            time.sleep(1)

            content_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "content")
            with open(os.path.join(content_dir, "article_en.txt"), "r", encoding="utf-8") as f:
                article = f.read()

            wikidot_content = f"""
= KadastrMap — Russia's Cadastral Map =

**Official service:** [{SITE_URL} kadastrmap.info] — Public Cadastral Map of Russia

----

{article}

----

**Visit:** [{SITE_URL} kadastrmap.info]
"""
            # Нажать Edit на странице
            try:
                page.click("a#edit-button, a.btn-primary[href*='edit']")
                time.sleep(1)
                page.fill('textarea#edit-area-original', wikidot_content)
                page.click('button[name="action"][value="savePage"], input[value="Save"]')
                page.wait_for_load_state("networkidle")
            except Exception as e:
                print(f"Не смог автоматически отредактировать страницу: {e}")
                print("Отредактируй вручную в открытом браузере")
                input("Нажми Enter когда готово...")

            profile_url = f"https://{SITE_NAME}.wikidot.com"
            tracker.save("Wikidot", 83, True, "Web 2.0", 2, "done", profile_url)

        except Exception as e:
            tracker.save("Wikidot", 83, True, "Web 2.0", 2, "failed", "", str(e))
            print(f"Ошибка: {e}")
        finally:
            input("Нажми Enter для закрытия браузера...")
            browser.close()


if __name__ == "__main__":
    run()
