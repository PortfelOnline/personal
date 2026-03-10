"""
Telegra.ph — публикация статьи без регистрации
DA: 81, Do-Follow: Yes, Фаза 2
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import requests
import tracker
from config import SITE_URL, DISPLAY_NAME

TELEGRAPH_API = "https://api.telegra.ph"


def create_account():
    """Создать анонимный аккаунт Telegraph."""
    resp = requests.post(f"{TELEGRAPH_API}/createAccount", data={
        "short_name": "KadastrMap",
        "author_name": DISPLAY_NAME,
        "author_url": SITE_URL,
    })
    data = resp.json()
    if not data.get("ok"):
        raise Exception(f"Ошибка создания аккаунта: {data}")
    return data["result"]["access_token"]


def publish_article(access_token: str, title: str, content_file: str) -> str:
    """Опубликовать статью из файла, вернуть URL."""
    with open(content_file, "r", encoding="utf-8") as f:
        text = f.read()

    # Разбиваем на параграфы
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    # Форматируем в Telegraph Node format
    content = []
    for i, para in enumerate(paragraphs):
        if i == 0:
            # Первый параграф — заголовок уже передаётся отдельно
            continue
        if para.startswith("- "):
            # Список
            items = [line[2:] for line in para.split("\n") if line.startswith("- ")]
            content.append({
                "tag": "ul",
                "children": [{"tag": "li", "children": [item]} for item in items]
            })
        elif para.startswith("https://"):
            content.append({
                "tag": "p",
                "children": [{"tag": "a", "attrs": {"href": para}, "children": [para]}]
            })
        else:
            # Обычный параграф — добавляем ссылку если упоминается kadastrmap.info
            if "kadastrmap.info" in para:
                parts = para.split("kadastrmap.info")
                children = []
                for j, part in enumerate(parts):
                    if part:
                        children.append(part)
                    if j < len(parts) - 1:
                        children.append({
                            "tag": "a",
                            "attrs": {"href": SITE_URL},
                            "children": ["kadastrmap.info"]
                        })
                content.append({"tag": "p", "children": children})
            else:
                content.append({"tag": "p", "children": [para]})

    import json
    resp = requests.post(f"{TELEGRAPH_API}/createPage", data={
        "access_token": access_token,
        "title": title,
        "author_name": DISPLAY_NAME,
        "author_url": SITE_URL,
        "content": json.dumps(content),
        "return_content": False,
    })
    data = resp.json()
    if not data.get("ok"):
        raise Exception(f"Ошибка публикации: {data}")
    return "https://telegra.ph/" + data["result"]["path"]


def run():
    print("=== Telegra.ph ===")
    try:
        token = create_account()
        print(f"Аккаунт создан, token: {token[:20]}...")

        content_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "content")

        # Публикуем EN статью
        url_en = publish_article(
            token,
            "How to Check Real Estate Objects Using Russia's Cadastral Map",
            os.path.join(content_dir, "article_en.txt"),
        )
        tracker.save("Telegra.ph (EN)", 81, True, "Web 2.0", 2, "done", url_en)

        # Публикуем RU статью
        url_ru = publish_article(
            token,
            "Как проверить объект недвижимости по кадастровому номеру",
            os.path.join(content_dir, "article_ru.txt"),
        )
        tracker.save("Telegra.ph (RU)", 81, True, "Web 2.0", 2, "done", url_ru)

    except Exception as e:
        tracker.save("Telegra.ph", 81, True, "Web 2.0", 2, "failed", "", str(e))
        print(f"Ошибка: {e}")


if __name__ == "__main__":
    run()
