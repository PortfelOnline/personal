"""
Quora — профиль с ссылкой на сайт
DA: 93, Do-Follow: YES (ссылки в профиле — do-follow)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import time, tracker
from config import SITE_URL, EMAIL, USERNAME, DISPLAY_NAME, BIO_EN

PASSWORD = "Kadastr2025!"


def run():
    print("=== Quora ===")
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        try:
            print("Открываю Quora signup...")
            page.goto("https://www.quora.com/", timeout=20000)
            page.wait_for_load_state("networkidle")
            time.sleep(1)

            try:
                # Кнопка Sign Up
                page.click('a[href*="signup"], button:has-text("Sign Up")', timeout=5000)
                time.sleep(1)
                page.fill('input[name="email"], input[type="email"]', EMAIL)
                page.fill('input[name="password"], input[type="password"]', PASSWORD)
                btn = page.query_selector('button[type="submit"], input[type="submit"]')
                if btn: btn.click()
                time.sleep(2)
            except Exception as e:
                print(f"  Форма: {e}")

            print(f"URL: {page.url}")
            print("⚠️  Quora требует верификацию email и может показать CAPTCHA.")
            input("После регистрации/входа нажми Enter...")

            # Переход в профиль
            print("Открываю редактирование профиля...")
            page.goto("https://www.quora.com/profile/edit", timeout=15000)
            time.sleep(2)

            try:
                # Имя
                page.fill('input[name="full_name"], input[placeholder*="name"]', DISPLAY_NAME)
                # Bio / описание
                bio_sel = 'textarea[name="tagline"], textarea[placeholder*="bio"], textarea[placeholder*="about"]'
                page.fill(bio_sel, BIO_EN[:200])
                # Сайт
                for sel in ['input[name="website_url"]', 'input[placeholder*="website"]',
                            'input[placeholder*="URL"]', 'input[type="url"]']:
                    try:
                        page.fill(sel, SITE_URL)
                        break
                    except: pass

                page.click('button[type="submit"], button:has-text("Save")', timeout=5000)
                time.sleep(2)
                print("✅ Профиль обновлён")
            except Exception as e:
                print(f"  Не смог автоматически: {e}")
                print(f"  Заполни вручную: URL = {SITE_URL}")
                input("  Нажми Enter после сохранения...")

            # URL профиля — Quora использует имя пользователя
            profile_url = page.url
            try:
                page.goto("https://www.quora.com/profile", timeout=10000)
                profile_url = page.url
            except: pass

            tracker.save("Quora", 93, True, "profile", 1, "done", profile_url)

        except Exception as e:
            tracker.save("Quora", 93, True, "profile", 1, "failed", "", str(e))
            print(f"Ошибка: {e}")
        finally:
            input("Нажми Enter для закрытия браузера...")
            browser.close()


if __name__ == "__main__":
    run()
