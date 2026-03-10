"""
Backlink Bot — конфигурация
Сайт: kadastrmap.info
"""

SITE_URL = "https://kadastrmap.info"
EMAIL = "info@kadastrmap.info"
USERNAME = "kadastrmap"
DISPLAY_NAME = "KadastrMap"

BIO_RU = (
    "Публичная кадастровая карта России. "
    "Поиск объектов недвижимости по кадастровому номеру и адресу. "
    "База 50+ млн объектов, актуализированная на 2025 год. "
    "kadastrmap.info"
)

BIO_EN = (
    "Russia's public cadastral map. "
    "Search real estate objects by cadastral number or address. "
    "50M+ objects updated in 2025. "
    "kadastrmap.info"
)

# Анкоры для ротации
ANCHORS = [
    "kadastrmap.info",
    "KadastrMap",
    "публичная кадастровая карта",
    "кадастровая карта России",
    "кадастровый номер онлайн",
    "выписка из ЕГРН",
    "кадастровая стоимость участка",
    "проверить объект недвижимости",
    "узнать больше",
    "перейти на сайт",
]

# Файл учёта результатов
RESULTS_FILE = "results/progress.csv"
