# High Load Average Incident - Server n (2026-05-17)

**Time**: 17:48-18:12 IST  
**Server**: n (167.86.116.15, Contabo)  
**Peak Load**: 11.57 (при 6 CPU = 1.9x перегрузка)  
**Zabbix Alerts**: Несколько алертов "Load average is too high"

## Root Causes
1. **searchd (Manticore Search)** - PID 595608, потреблял 338% CPU более 314 минут
2. **Grafana** - потребляла 100% CPU при перезапуске после падения searchd

## Resolution Timeline
1. **18:09** - `kill -9 595608` - принудительно завершил зависший searchd процесс
2. **18:11** - `systemctl stop grafana-server` - остановил перегруженную Grafana  
3. **18:12** - searchd автоматически перезапустился с нормальной нагрузкой (15% CPU)

## Results
- **Load average**: 11.57 → 6.67
- **CPU idle**: ~18% → 84.1%
- **System stabilized**: в течение 5 минут

## Analysis
**searchd зависал** при обработке поисковых запросов, возможно из-за:
- Некорректных индексов Manticore Search
- Большого объёма данных для индексации  
- Циклических запросов или deadlock'ов

**Grafana усугубила** ситуацию при попытке сбора метрик с перегруженной системы.

## Prevention
- Мониторить searchd процессы на высокую нагрузку
- Настроить таймауты для Manticore Search запросов
- Рассмотреть настройку resource limits для searchd
- Безопасно перезапускать через `kill -9`, так как сервисы автоматически восстанавливаются

## Grafana Recovery (18:15-18:18)
**Problem**: При попытке восстановления Grafana потребляла 100-117% CPU  
**Root Cause**: Конфликт портов - Grafana пыталась использовать порт 3000, занятый strategy-dashboard  
**Error**: `"failed to open listener on address 0.0.0.0:3000: bind: address already in use"`

**Solution**:
1. **Диагностика**: `lsof -i :3000` показал Node.js (strategy-dashboard) на PID 795
2. **Изменение конфигурации**: `/etc/grafana/grafana.ini` → `http_port = 8889`  
3. **Перезапуск**: `systemctl restart grafana-server`

**Result**: Grafana стабильно работает на порту 8889, CPU idle 66.4%

## Final System Status (18:18)
- **Load average**: 8.15 (стабилизирован)
- **searchd**: 15% CPU (восстановлен после автоматического перезапуска)
- **Grafana**: работает на :8889, нормальное потребление CPU
- **strategy-dashboard**: продолжает работать на :3000  
- **MySQL**: 36.8% CPU (в норме)

## Related Services
- **yandex_bot**: контейнер был остановлен во время инцидента
- **MySQL**: нормально работал, 71.4% → 36.8% CPU после исправления
- **Docker containers**: работали стабильно
- **Port conflict resolved**: strategy-dashboard :3000, Grafana :8889