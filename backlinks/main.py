"""
Backlink Bot — точка входа
Запуск: python3 main.py [site]

Примеры:
  python3 main.py telegra_ph     # запустить конкретный сайт
  python3 main.py all            # все сайты
  python3 main.py status         # показать прогресс
"""
import sys
import tracker

SITES = {
    "telegra_ph": ("sites.telegra_ph", "run"),
    # следующие добавляем по мере написания
}


def main():
    tracker.init()

    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1]

    if cmd == "status":
        tracker.show()
        return

    if cmd == "all":
        for name, (module, func) in SITES.items():
            run_site(name, module, func)
        tracker.show()
        return

    if cmd in SITES:
        module, func = SITES[cmd]
        run_site(cmd, module, func)
    else:
        print(f"Неизвестная команда: {cmd}")
        print(f"Доступные сайты: {', '.join(SITES.keys())}")


def run_site(name, module_path, func_name):
    print(f"\n{'='*40}")
    print(f"Запуск: {name}")
    print(f"{'='*40}")
    try:
        import importlib
        mod = importlib.import_module(module_path)
        getattr(mod, func_name)()
    except Exception as e:
        print(f"Критическая ошибка в {name}: {e}")


if __name__ == "__main__":
    main()
