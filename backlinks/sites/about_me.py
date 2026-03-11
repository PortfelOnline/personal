"""
About.me — профиль с ссылкой на сайт
DA: 71, Do-Follow: YES
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import time, tracker
from config import SITE_URL, EMAIL, USERNAME, DISPLAY_NAME, BIO_EN

PASSWORD = "Kadastr2025!"


def run():
    print("=== About.me ===")
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        try:
            print("Регистрация на About.me...")
            page.goto("https://about.me/signup", timeout=20000)
            page.wait_for_load_state("networkidle")
            time.sleep(1)

            try:
                page.fill('input[name="email"], input[type="email"]', EMAIL)
                page.fill('input[name="password"], input[type="password"]', PASSWORD)
                btn = page.query_selector('button[type="submit"], input[type="submit"]')
                if btn: btn.click()
                time.sleep(2)
            except Exception as e:
                print(f"  Форма: {e}")

            print(f"URL: {page.url}")
            input("Завершил регистрацию/вошёл? Нажми Enter...")

            # Редактирование профиля
            page.goto("https://about.me/account/profile", timeout=15000)
            time.sleep(1)

            try:
                page.fill('input[name="headline"], input[placeholder*="headline"]',
                          f"{DISPLAY_NAME} — {SITE_URL}")
                page.fill('textarea[name="bio"], textarea[placeholder*="bio"]', BIO_EN[:200])

                # Поле для сайта
                for sel in ['input[name="website"]', 'input[name="url"]', 'input[placeholder*="website"]']:
                    try:
                        page.fill(sel, SITE_URL)
                        break
                    except: pass

                page.click('button[type="submit"], button:has-text("Save")', timeout=5000)
                time.sleep(2)
            except Exception as e:
                print(f"  Не смог автоматически: {e}")
                print(f"  Заполни вручную: URL = {SITE_URL}")
                input("  Нажми Enter после сохранения...")

            profile_url = f"https://about.me/{USERNAME}"
            tracker.save("About.me", 71, True, "profile", 1, "done", profile_url)

        except Exception as e:
            tracker.save("About.me", 71, True, "profile", 1, "failed", "", str(e))
            print(f"Ошибка: {e}")
        finally:
            input("Нажми Enter для закрытия...")
            browser.close()


if __name__ == "__main__":
    run()
