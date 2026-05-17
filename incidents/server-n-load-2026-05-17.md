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

## Related Services
- **yandex_bot**: контейнер был остановлен во время инцидента
- **MySQL**: нормально работал, 36.8% → 11.1% CPU после исправления
- **Docker containers**: работали стабильно