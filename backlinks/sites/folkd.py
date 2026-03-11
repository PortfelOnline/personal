"""
Folkd.com — социальная закладка (bookmark)
DA: 60, Do-Follow: YES
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
    print("=== Folkd.com ===")
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        try:
            print("Регистрация на Folkd...")
            page.goto("https://www.folkd.com/register", timeout=20000)
            page.wait_for_load_state("networkidle")
            time.sleep(1)

            try:
                page.fill('input[name="username"], input[name="user"]', USERNAME)
                page.fill('input[name="email"]', EMAIL)
                page.fill('input[name="password"]', PASSWORD)
                page.fill('input[name="password2"], input[name="password_confirm"]', PASSWORD)
                page.click('input[type="submit"], button[type="submit"]')
                time.sleep(2)
            except Exception as e:
                print(f"  Форма: {e}")

            input("Зарегистрировался? Нажми Enter...")

            # Добавляем закладки
            for url, title in BOOKMARK_PAGES:
                try:
                    page.goto(f"https://www.folkd.com/submit/go.php?u={url}&t={title.replace(' ', '+')}")
                    time.sleep(1)
                    # Заполнить теги/описание если есть форма
                    try:
                        page.fill('input[name="tags"]', "кадастр недвижимость Россия")
                        page.click('input[type="submit"], button[type="submit"]')
                        time.sleep(1)
                    except: pass
                    print(f"  ✅ Добавлено: {url}")
                except Exception as e:
                    print(f"  Ошибка для {url}: {e}")

            profile_url = f"https://www.folkd.com/user/{USERNAME}"
            tracker.save("Folkd", 60, True, "bookmark", 1, "done", profile_url)

        except Exception as e:
            tracker.save("Folkd", 60, True, "bookmark", 1, "failed", "", str(e))
            print(f"Ошибка: {e}")
        finally:
            input("Нажми Enter для закрытия...")
            browser.close()


if __name__ == "__main__":
    run()
