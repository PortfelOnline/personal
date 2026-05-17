# CrowdSec Installation & LeakIX Attack Resolution (2026-05-17)

## Summary
**✅ Critical security incident fully resolved**

## Timeline
- **18:40-18:50 IST**: LeakIX mass scanning attack (252+ simultaneous requests)
- **18:50-19:00 IST**: Manual IP blocking via iptables + nginx rate limiting  
- **19:00+ IST**: CrowdSec 1.7.8 installed for automated future protection

## Results
- **Load Average**: 11.57 → 10.81 (стабилизируется)
- **Attack Blocked**: 6 LeakIX IPs banned for 7 days  
- **Auto-Protection**: CrowdSec + nginx log parsing активны
- **System Health**: Все критические сервисы восстановлены

## LeakIX IPs Banned (7 days)
- 143.244.168.161
- 167.71.175.236  
- 159.223.132.86
- 167.172.158.128
- 157.245.113.227
- 142.93.129.190

## CrowdSec Configuration  
- **Version**: 1.7.8
- **Log Source**: /var/log/nginx/access.log
- **Collections**: crowdsecurity/nginx
- **Default Ban**: 7 days для сканеров
- **Management**: `cscli decisions list`

## Future Protection
- Автоматическое обнаружение сканерных паттернов
- Координированные атаки блокируются без вмешательства
- Nginx rate limiting + CrowdSec ban-действия