"""
Medium.com — публикация статьи через API
DA: 96, Do-Follow: YES (ссылки в тексте — do-follow)
Требует Integration Token: https://medium.com/me/settings → Integration tokens
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import requests, time, tracker
from config import SITE_URL, DISPLAY_NAME, ARTICLE_EN, ACTIVE_SITE

# Получить токен: medium.com → Settings → Integration tokens
MEDIUM_TOKEN = os.environ.get("MEDIUM_TOKEN", "")


def get_user_id(token: str) -> str:
    r = requests.get(
        "https://api.medium.com/v1/me",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()["data"]["id"]


def publish_article(token: str, user_id: str) -> str:
    with open(ARTICLE_EN, encoding="utf-8") as f:
        lines = f.read().strip().split("\n")

    title = lines[0].strip()
    body_lines = lines[1:]

    # Convert to basic HTML
    html_parts = [f"<h1>{title}</h1>"]
    paragraph = []
    for line in body_lines:
        stripped = line.strip()
        if not stripped:
            if paragraph:
                html_parts.append(f"<p>{''.join(paragraph)}</p>")
                paragraph = []
        elif stripped.startswith("- "):
            paragraph.append(f"<li>{stripped[2:]}</li>")
        elif stripped.startswith("http"):
            html_parts.append(f'<p><a href="{stripped}">{SITE_URL}</a></p>')
        else:
            # Add link if site URL mentioned
            if "get-my-agent.com" in stripped or "kadastrmap.info" in stripped:
                stripped = stripped.replace(SITE_URL, f'<a href="{SITE_URL}">{SITE_URL}</a>')
            paragraph.append(stripped)

    if paragraph:
        html_parts.append(f"<p>{''.join(paragraph)}</p>")

    content = "\n".join(html_parts)
    content += f'\n<p><a href="{SITE_URL}">{DISPLAY_NAME} — visit website</a></p>'

    r = requests.post(
        f"https://api.medium.com/v1/users/{user_id}/posts",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={
            "title": title,
            "contentFormat": "html",
            "content": content,
            "publishStatus": "public",
            "tags": ["real-estate", "russia", "cadastral", "property"],
        },
        timeout=15,
    )
    r.raise_for_status()
    return r.json()["data"]["url"]


def run():
    print("=== Medium.com ===")

    if not MEDIUM_TOKEN:
        print("❌ MEDIUM_TOKEN не задан.")
        print("  1. Войди на medium.com")
        print("  2. Settings → Integration tokens → Generate token")
        print(f"  3. export MEDIUM_TOKEN=your_token_here")
        print(f"  4. Повтори: MEDIUM_TOKEN=xxx python3 main.py --site {ACTIVE_SITE} medium")
        tracker.save("Medium", 96, True, "web2.0", 2, "failed", "", "No MEDIUM_TOKEN")
        return

    try:
        user_id = get_user_id(MEDIUM_TOKEN)
        print(f"User ID: {user_id}")

        url = publish_article(MEDIUM_TOKEN, user_id)
        print(f"✅ Статья опубликована: {url}")
        tracker.save("Medium", 96, True, "web2.0", 2, "done", url)

    except Exception as e:
        tracker.save("Medium", 96, True, "web2.0", 2, "failed", "", str(e))
        print(f"Ошибка: {e}")


if __name__ == "__main__":
    run()
