"""
Backlink Bot — мульти-сайтовая конфигурация
Поддерживает несколько доменов. Выбор через env: BACKLINK_SITE=kadastrmap
"""
import os

# ── Профили сайтов ────────────────────────────────────────────────────────────
SITES = {
    "kadastrmap": {
        "url":          "https://kadastrmap.info",
        "email":        "info@kadastrmap.info",
        "username":     "kadastrmap",
        "display_name": "KadastrMap",
        "bio_ru": (
            "Публичная кадастровая карта России. "
            "Поиск объектов недвижимости по кадастровому номеру и адресу. "
            "База 50+ млн объектов, актуализированная на 2025 год. "
            "kadastrmap.info"
        ),
        "bio_en": (
            "Russia's public cadastral map. "
            "Search real estate objects by cadastral number or address. "
            "50M+ objects updated in 2025. "
            "kadastrmap.info"
        ),
        "anchors_ru": [
            "kadastrmap.info",
            "KadastrMap",
            "публичная кадастровая карта",
            "кадастровая карта России",
            "кадастровый номер онлайн",
            "выписка из ЕГРН",
            "кадастровая стоимость участка",
            "проверить объект недвижимости",
        ],
        "anchors_en": [
            "kadastrmap.info",
            "KadastrMap",
            "Russia cadastral map",
            "cadastral number lookup",
            "EGRN extract online",
            "learn more",
            "visit website",
        ],
        "article_ru": "content/article_kadastrmap_ru.txt",
        "article_en": "content/article_kadastrmap_en.txt",
    },
    "get-my-agent": {
        "url":          "https://get-my-agent.com",
        "email":        "info@get-my-agent.com",
        "username":     "getmyagent",
        "display_name": "GetMyAgent",
        "bio_ru": (
            "AI-агенты для автоматизации бизнеса. "
            "Создайте своего персонального агента за минуты — без кода. "
            "get-my-agent.com"
        ),
        "bio_en": (
            "AI agents for business automation. "
            "Create your personal AI agent in minutes — no code required. "
            "get-my-agent.com"
        ),
        "anchors_ru": [
            "get-my-agent.com",
            "GetMyAgent",
            "AI агент онлайн",
            "создать AI агента",
            "автоматизация с ИИ",
            "узнать больше",
        ],
        "anchors_en": [
            "get-my-agent.com",
            "GetMyAgent",
            "AI agent builder",
            "create AI agent",
            "business automation AI",
            "learn more",
            "visit website",
        ],
        "article_ru": "content/article_agent_ru.txt",
        "article_en": "content/article_agent_en.txt",
    },
}

# ── Активный профиль (задаётся через env BACKLINK_SITE или аргумент --site) ───
_active = os.environ.get("BACKLINK_SITE", "kadastrmap")
if _active not in SITES:
    raise ValueError(f"Unknown site '{_active}'. Available: {list(SITES.keys())}")

_cfg = SITES[_active]

SITE_URL     = _cfg["url"]
EMAIL        = _cfg["email"]
USERNAME     = _cfg["username"]
DISPLAY_NAME = _cfg["display_name"]
BIO_RU       = _cfg["bio_ru"]
BIO_EN       = _cfg["bio_en"]
ANCHORS      = _cfg["anchors_en"]
ANCHORS_RU   = _cfg["anchors_ru"]
ARTICLE_RU   = _cfg["article_ru"]
ARTICLE_EN   = _cfg["article_en"]
ACTIVE_SITE  = _active

PASSWORD = "Kadastr2025!"   # менять под каждый сайт

# ── Трекер ────────────────────────────────────────────────────────────────────
RESULTS_FILE = f"results/progress_{ACTIVE_SITE}.csv"
