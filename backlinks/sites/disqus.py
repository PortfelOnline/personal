"""
Disqus — профиль с ссылкой на сайт
DA: 93, Do-Follow: NO (но высокий авторитет домена, хороший для brand signals)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import time, tracker
from config import SITE_URL, EMAIL, USERNAME, DISPLAY_NAME, BIO_EN, ACTIVE_SITE

PASSWORD = "Kadastr2025!"


def run():
    print("=== Disqus ===")
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        try:
            # Регистрация
            print("Регистрация на Disqus...")
            page.goto("https://disqus.com/profile/signup/", timeout=20000)
            page.wait_for_load_state("networkidle")
            time.sleep(1)

            # Поля регистрации
            try:
                page.fill('input[name="email"]', EMAIL)
                page.fill('input[name="username"]', USERNAME)
                page.fill('input[name="name"]', DISPLAY_NAME)
                page.fill('input[name="password"]', PASSWORD)
                page.click('button[type="submit"], input[type="submit"]')
                time.sleep(2)
            except Exception as e:
                print(f"  Ошибка заполнения формы: {e}")

            print(f"URL: {page.url}")
            print("⚠️  Может потребоваться email-подтверждение и CAPTCHA.")
            input("После регистрации/входа нажми Enter...")

            # Редактирование профиля
            print("Открываю профиль для редактирования...")
            page.goto("https://disqus.com/by/me/profile/", timeout=15000)
            time.sleep(1)

            try:
                # Кнопка Edit Profile
                page.click("a[href*='edit'], button:has-text('Edit')", timeout=5000)
                time.sleep(1)
            except:
                page.goto("https://disqus.com/profile/details/", timeout=15000)
                time.sleep(1)

            # Добавляем URL сайта
            try:
                page.fill('input[name="url"], input[placeholder*="website"], input[type="url"]', SITE_URL)
                page.fill('textarea[name="about"], textarea[placeholder*="bio"]',
                          BIO_EN[:150])
                page.click('button[type="submit"], input[type="submit"]')
                time.sleep(2)
            except Exception as e:
                print(f"  Не смог автоматически заполнить профиль: {e}")
                print(f"  Заполни вручную: URL = {SITE_URL}")
                input("  Нажми Enter после сохранения...")

            profile_url = f"https://disqus.com/by/{USERNAME}/"
            tracker.save("Disqus", 93, False, "profile", 1, "done", profile_url)

        except Exception as e:
            tracker.save("Disqus", 93, False, "profile", 1, "failed", "", str(e))
            print(f"Ошибка: {e}")
        finally:
            input("Нажми Enter для закрытия браузера...")
            browser.close()


if __name__ == "__main__":
    run()
