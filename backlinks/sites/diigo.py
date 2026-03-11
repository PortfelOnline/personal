"""
Diigo — социальная закладка + профиль
DA: 70, Do-Follow: YES (закладки индексируются)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import time, tracker
from config import SITE_URL, EMAIL, USERNAME, DISPLAY_NAME, BIO_EN, ANCHORS

PASSWORD = "Kadastr2025!"

# Страницы для добавления в закладки
BOOKMARK_PAGES = [
    (SITE_URL, f"{DISPLAY_NAME} — главная"),
    (SITE_URL + "/kadastr/", "Статьи о кадастре"),
    (SITE_URL + "/reestr/", "Кадастровый реестр"),
]


def run():
    print("=== Diigo ===")
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        try:
            print("Регистрация на Diigo...")
            page.goto("https://www.diigo.com/sign-up", timeout=20000)
            page.wait_for_load_state("networkidle")
            time.sleep(1)

            try:
                page.fill('input[name="username"]', USERNAME)
                page.fill('input[name="email"]', EMAIL)
                page.fill('input[name="password"]', PASSWORD)
                page.fill('input[name="password2"], input[name="confirm_password"]', PASSWORD)
                page.click('input[type="submit"], button[type="submit"]')
                time.sleep(2)
            except Exception as e:
                print(f"  Форма: {e}")

            print(f"URL: {page.url}")
            input("Зарегистрировался? Нажми Enter...")

            # Добавляем закладки
            for url, title in BOOKMARK_PAGES:
                try:
                    page.goto(f"https://www.diigo.com/post?url={url}&title={title.replace(' ', '+')}")
                    time.sleep(2)
                    try:
                        # Заполнить описание/теги если есть форма
                        page.fill('textarea[name="description"]', BIO_EN[:200])
                        page.fill('input[name="tags"]', "кадастр недвижимость Россия")
                        page.click('input[type="submit"], button[type="submit"]')
                        time.sleep(1)
                    except: pass
                    print(f"  ✅ Добавлено: {url}")
                except Exception as e:
                    print(f"  Ошибка для {url}: {e}")

            # Обновить профиль
            try:
                page.goto(f"https://www.diigo.com/user/{USERNAME}/profile", timeout=10000)
                time.sleep(1)
                page.click('a:has-text("Edit Profile"), button:has-text("Edit")', timeout=5000)
                time.sleep(1)
                page.fill('input[name="url"], input[placeholder*="website"]', SITE_URL)
                page.fill('textarea[name="bio"], textarea[name="description"]', BIO_EN[:200])
                page.click('input[type="submit"], button[type="submit"]')
                time.sleep(1)
            except Exception as e:
                print(f"  Профиль: {e}")

            profile_url = f"https://www.diigo.com/user/{USERNAME}"
            tracker.save("Diigo", 70, True, "bookmark", 1, "done", profile_url)

        except Exception as e:
            tracker.save("Diigo", 70, True, "bookmark", 1, "failed", "", str(e))
            print(f"Ошибка: {e}")
        finally:
            input("Нажми Enter для закрытия...")
            browser.close()


if __name__ == "__main__":
    run()
