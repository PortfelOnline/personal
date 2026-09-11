#!/bin/bash
# AI-разбор состояния grid-mainnet через Code Assist мост (Gemini, localhost:4400/genai).
# READ-ONLY: только читает логи/конфиг/дашборд, НЕ трогает бота и ордера. Шлёт разбор в Telegram.
# v2 (2026-07-05): + снапшот биржи (позиции/ордера), мёртвые зоны сетки, ошибки лога,
#   авто-капитал/депозиты, kill-breach; убран протухший хардкод «депозит $100».
SVC=grid-mainnet
DIR=/root/$SVC
LOG=$DIR/$SVC.log
UNIT=/etc/systemd/system/$SVC.service
ALOG=$DIR/ai-analyst.log
BRIDGE="localhost:4400/genai/v1beta/models/gemini-3.5-pro:generateContent"
NOW=$(date '+%Y-%m-%d %H:%M:%S')
[ -f /root/grid-alert.env ] && . /root/grid-alert.env
tg(){ [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_CHAT_ID" ] && \
  curl -s -m 10 "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
    --data-urlencode chat_id="$TELEGRAM_CHAT_ID" --data-urlencode text="$1" >/dev/null 2>&1; }

# --- сбор статистики (read-only) ---
EQ_SERIES=$(grep -oE 'equity=[0-9.]+' "$LOG" 2>/dev/null | tail -20 | sed 's/equity=//' | tr '\n' ' ')
ROT_TOTAL=$(grep -acE 'фьюч-ротация:.*закрываем' "$LOG" 2>/dev/null); [ -z "$ROT_TOTAL" ] && ROT_TOTAL=0
# суточная ДЕЛЬТА ротаций = total - baseline. СВОЙ baseline-файл (.rotation_ai_daily), НЕ общий с
# daily-report — иначе daily-report перезапишет baseline до нас и ROT_24H всегда станет 0.
AIBASE_F="$DIR/.rotation_ai_daily"
RBASE=$(cat "$AIBASE_F" 2>/dev/null); [ -z "$RBASE" ] && RBASE=$ROT_TOTAL
[ "$ROT_TOTAL" -lt "$RBASE" ] && RBASE=0
ROT_24H=$(( ROT_TOTAL - RBASE ))
echo "$ROT_TOTAL" > "$AIBASE_F"   # сдвигаем baseline на текущий total (для следующих суток)
CFG=$(grep -oE 'GRID_(AUTO_CAPITAL|SPOT_FRAC|FUT_FRAC|FUT_ENABLED|FUT_LONG_ONLY|TREND_CONFIRM|TREND_THRESHOLD|MAX_CAPITAL_USD|FUT_CAPITAL_USD|MAX_BOTS|FUT_MAX_BOTS|KILL_SWITCH_FRAC)=[^ ]+' "$UNIT" 2>/dev/null | tr '\n' ' ')
TRENDS=$(tail -50 "$LOG" 2>/dev/null | grep -E 'тренд |режим |подтверждаем' | tail -8)
STATS=$(tail -12 "$DIR/stats.log" 2>/dev/null)
STATS_DATE=$(stat -c %y "$DIR/stats.log" 2>/dev/null | cut -d. -f1)

# авто-капитал: последний цикл + задетекченные депозиты (сдвиг базлайна роста)
AC=$(grep -a 'авто-капитал' "$LOG" 2>/dev/null | tail -1); [ -z "$AC" ] && AC='n/a'
DEPOSITS=$(grep -a 'детект депозита' "$LOG" 2>/dev/null | tail -3); [ -z "$DEPOSITS" ] && DEPOSITS='нет'

# ошибки ТЕКУЩЕГО процесса (лог без таймстемпов → сегмент после последнего 'цикл запущен');
# рестарты за ~3000 строк — отдельным счётчиком (крэши ловит watchdog, тут только контекст)
SEG=$(tail -3000 "$LOG" 2>/dev/null | awk '/цикл запущен/{n=NR} {l[NR]=$0} END{for(i=n+1;i<=NR;i++) print l[i]}')
RESTARTS=$(tail -3000 "$LOG" 2>/dev/null | grep -ac 'цикл запущен')
ERRS_RAW=$(printf '%s\n' "$SEG" | "$DIR/ops/grid-log-error-filter.sh")
ERRC=$(printf '%s' "$ERRS_RAW" | grep -c . )
ERRS=$(printf '%s' "$ERRS_RAW" | sort | uniq -c | sort -rn | head -5)
[ -z "$ERRS" ] && ERRS='нет'

# kill-switch breach + базлайн роста из БД бота (read-only).
# PAPER_MODE=true в .env → db.ts пишет всё в trading-paper.db (см. src/db.ts) — пробуем оба пути.
KB=$(python3 - "$DIR/trading-paper.db" "$DIR/trading.db" <<'PY' 2>/dev/null
import sqlite3, sys
for path in sys.argv[1:]:
    try:
        c = sqlite3.connect('file:' + path + '?mode=ro', uri=True)
        rows = dict(c.execute("select key, value from config where key in ('grid_kill_breach','grid_growth_baseline')").fetchall())
        print(f"breach={rows.get('grid_kill_breach','0')} growth_baseline={rows.get('grid_growth_baseline','n/a')}")
        break
    except Exception:
        continue
else:
    print('n/a')
PY
)

# снапшот биржи с дашборда: позиции, ордера, мёртвые зоны сетки (расстояние цены до уровней)
DASH_AUTH=$(grep -E '^DASHBOARD_(USER|PASS)=' "$DIR/.env" 2>/dev/null | cut -d= -f2 | paste -sd: -)
SNAP_F=$(mktemp /tmp/grid-snap.XXXXXX.json)
curl -s --noproxy '*' -m 15 -u "$DASH_AUTH" http://localhost:4200/api/realmoney-main -o "$SNAP_F"
# ВАЖНО: python-скрипт через heredoc занимает stdin — JSON передаём файлом, НЕ pipe'ом
SNAP=$(python3 - "$SNAP_F" <<'PY' 2>/dev/null
import json, sys
try:
    d = json.load(open(sys.argv[1]))
except Exception:
    print('n/a (снапшот недоступен)'); raise SystemExit
print(f"equity ${d.get('equity',0):.2f} (старт ${d.get('start',0):.2f}, рост {d.get('pnlPct',0):+.2f}%), "
      f"свободно ${d.get('cashUsdt',0):.2f}, в лимитках ${d.get('ordersReserveUsd',0):.2f}, "
      f"Δ24ч {d.get('chg24h',0):+.2f}, realized {d.get('realizedPnl',0):+.2f}, комиссии всего {d.get('feesTotal',0):.2f}")
price = {}
for p in d.get('positions') or []:
    print(f"ПОЗ {p.get('kind','')} {p.get('coin','')} {p.get('dir','')} qty {p.get('qty')} @ {p.get('price')} "
          f"avg {p.get('avg')} uPnL {p.get('pnl'):+.2f} ({p.get('share',0):.0f}% депо)")
    if p.get('price'): price[str(p.get('coin','')) + 'USDT'] = p['price']
grids = {}
for o in d.get('orders') or []:
    grids.setdefault(o['symbol'], {'Buy': [], 'Sell': []})[o['side']].append(o['price'])
for sym, g in grids.items():
    buys, sells = sorted(g['Buy'], reverse=True), sorted(g['Sell'])
    cur = price.get(sym) or ((buys[0] + sells[0]) / 2 if buys and sells else 0)
    bd = f"-{(cur - buys[0]) / cur * 100:.1f}%" if buys and cur else 'нет'
    sd = f"+{(sells[0] - cur) / cur * 100:.1f}%" if sells and cur else 'нет'
    print(f"СЕТКА {sym}: цена {cur}, {len(buys)} buy (ближайший {bd}), {len(sells)} sell (ближайший {sd})")
PY
)
rm -f "$SNAP_F"
[ -z "$SNAP" ] && SNAP='n/a'

# maker-watch.ts не грузит dotenv → --env-file=.env для ключей + GRID_TESTNET=false поверх
# (.env обманчиво testnet=true; иначе mainnet-ключи на testnet-URL = 401 empty body)
START_MS=$(date -d '24 hours ago' +%s%3N 2>/dev/null)
MK=$(cd "$DIR" && GRID_TESTNET=false timeout 25 node_modules/.bin/tsx --env-file=.env maker-watch.ts "$START_MS" 2>/dev/null | tail -1)
[ -z "$MK" ] && MK='n/a'
# P&L attribution за сутки (комиссии/realized/funding/net) — биржевой источник правды
PNL=$(cd "$DIR" && GRID_TESTNET=false timeout 35 node_modules/.bin/tsx --env-file=.env pnl-attribution.ts "$START_MS" 2>/dev/null | tail -1)
[ -z "$PNL" ] && PNL='n/a'
ACT24=$("$DIR/ops/grid-order-activity.sh" "$LOG" 2>/dev/null)
[ -z "$ACT24" ] && ACT24='n/a'

IMPROVEMENTS=$(tail -25 /root/grid-improvements.log 2>/dev/null); [ -z "$IMPROVEMENTS" ] && IMPROVEMENTS="(журнал пуст)"
PROMPT="Ты риск-аналитик крипто grid-бота на Bybit (mainnet, РЕАЛЬНЫЕ деньги; trend-aware grid: spot + futures с плечом ≤2x; авто-капитал: кэпы = доли реального equity, депозиты подхватываются автоматически и сдвигают базлайн роста). Кратко, на русском, БЕЗ markdown-разметки, для Telegram. Ответь СТРОГО в формате:
1) Вердикт: ОК / ВНИМАНИЕ / ТРЕВОГА + причина одной строкой
2) Торговля за сутки: были ли сделки и ПОЧЕМУ (смотри СЕТКА-строки: если цена в мёртвой зоне между ближайшим buy и sell — скажи это с цифрами)
3) Риски: только реальные по свежим данным (плечо/liq позиций, funding-дренаж, ошибки лога, kill-breach, перекос долей)
4) Действия: конкретные ТОЛЬКО если ROT_24H>2, net<0 при наличии сделок, есть ошибки в логе или kill-breach>0; иначе пиши 'параметры не трогать'\n5) Следующий шаг к совершенству: ОДИН конкретный микро-шаг оптимизации (параметр→значение, ожидаемый эффект на net/комиссии/эффективность, риск) с учётом раздела УЖЕ ПРИМЕНЕНО — цель постепенно довести стратегию до оптимума. Если рано (ждём эффекта прошлого изменения) — пиши 'наблюдаем метрики предыдущего шага'. НЕ предлагай уже применённое или отклонённое.

Метрика перекрута: ротаций фьюча >2/сутки = fee-bleed вернулся (фикс TREND_THRESHOLD=0.04/CONFIRM=5 от 2026-06-28, оценивай только период после).
ШТАТНОЕ (не риск, не предлагай фиксов): строки 'фьюч отсев ... < minOrderQty' — это pre-filter, дорогая монета отсеивается ДО движка и слот уходит другому боту; 'дублей нет' при placed=0.
Если исполнений n=0, но placedOrders велик и placedCycles повторяются, это order-churn: ордера переставляются без сделок, теряется maker-очередь. При наличии исполнений часть placedOrders может быть штатной заменой после fill — не называй всё churn автоматически.

ДАННЫЕ:
Конфиг: $CFG
Авто-капитал (последний цикл): $AC
Депозиты за период: $DEPOSITS
Ротаций фьюча за сутки: $ROT_24H
Kill-switch: $KB
Equity-ряд (хронологически): $EQ_SERIES
Фьюч-исполнения 24ч (maker дешевле taker): $MK
ПОСТАНОВКИ ОРДЕРОВ 24ч (только live): $ACT24
P&L 24ч (биржевой: realized=closed-pnl, fees, funding, net): $PNL
СНАПШОТ БИРЖИ (позиции, сетки, мёртвые зоны):
$SNAP
Ошибки с последнего рестарта: count=$ERRC (рестартов за ~3000 строк лога: $RESTARTS)
$ERRS
Тренды сейчас:
$TRENDS
ИСТОРИЧЕСКОЕ (фон, snapshot $STATS_DATE, может быть старым):
$STATS
УЖЕ ПРИМЕНЕНО/ОТКЛОНЕНО (не повторяй, предлагай следующее):
$IMPROVEMENTS
Без воды и дисклеймеров."

# 11.09.2026: этот скрипт бьёт НАПРЯМУЮ в :4400/genai, минуя шим на :4405
# (codeassist-openai-shim.py) с его circuit breaker'ом — то есть даже когда шим уже
# держит breaker открытым для конвейера статей kadastrmap (после RESOURCE_EXHAUSTED),
# этот cron всё равно долбит тот же Google-аккаунт напрямую. Читаем и пишем ТОТ ЖЕ
# файл состояния, что и шим, чтобы не расходовать попытки впустую и не мешать
# восстановлению квоты. Проверяем оба бакета модели (3.1 и 3.5) — квота, судя по
# эмпирике, общая на аккаунт, не строго по имени модели.
BREAKER_FILE=/root/.codeassist-breaker-state.json
BREAKER_WAIT=$(python3 -c "
import json, time
try:
    with open('$BREAKER_FILE') as f:
        state = json.load(f)
except Exception:
    state = {}
now = time.time()
until = state.get('gemini-3.5-pro') or state.get('gemini-3.1-pro')
if until and now < until:
    print(int(until - now))
")
if [ -n "$BREAKER_WAIT" ]; then
  echo "[$NOW] breaker open (общая квота Google), пропускаем запрос, осталось ${BREAKER_WAIT}s" >> "$ALOG"
  tg "🤖 AI-разбор grid-mainnet ($NOW)
Квота Google Code Assist исчерпана (breaker открыт мостом), анализ отложен, retry через ${BREAKER_WAIT}s."
  exit 0
fi

# --- запрос к мосту (JSON через python — надёжное экранирование) ---
BODY=$(python3 -c "import json,sys; print(json.dumps({'contents':[{'parts':[{'text':sys.argv[1]}]}]}))" "$PROMPT")
RESP=$(curl -s -m 60 "$BRIDGE" -H 'Content-Type: application/json' -d "$BODY")

# RESOURCE_EXHAUSTED от Google — открываем тот же breaker, что и шим (7 дней), чтобы
# следующий запуск (свой и шима) не бил вхолостую по ещё не восстановленной квоте.
if printf '%s' "$RESP" | grep -q 'RESOURCE_EXHAUSTED'; then
  python3 -c "
import json, time
path = '$BREAKER_FILE'
try:
    with open(path) as f:
        state = json.load(f)
except Exception:
    state = {}
state['gemini-3.5-pro'] = time.time() + 7*24*3600
with open(path, 'w') as f:
    json.dump(state, f)
"
  echo "[$NOW] RESOURCE_EXHAUSTED — breaker OPEN для gemini-3.5-pro (7 дней)" >> "$ALOG"
fi
TEXT=$(printf '%s' "$RESP" | python3 -c "
import sys,json
try:
    d=json.load(sys.stdin)
    t=(d.get('candidates') or [{}])[0].get('content',{}).get('parts',[{}])[0].get('text')
    print(t or d.get('error',{}).get('message') or 'пустой ответ моста')
except Exception as e:
    print('parse error: '+str(e))
")

echo "[$NOW] eq_last=${EQ_SERIES##* } rot_total=$ROT_TOTAL errc=$ERRC mk=$MK" >> "$ALOG"
echo "[$NOW] AI: $TEXT" >> "$ALOG"
[ -f "$ALOG" ] && tail -300 "$ALOG" > "$ALOG.tmp" && mv "$ALOG.tmp" "$ALOG"

tg "🤖 AI-разбор grid-mainnet ($NOW)
$TEXT"
echo "--- AI ОТВЕТ ---"; echo "$TEXT"
