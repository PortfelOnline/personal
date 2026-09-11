/**
 * bridge-llm.ts — текстовая генерация через Code Assist мост с автоматическим выбором Flash/Pro.
 *
 * Drop-in замена invokeLLM для GMA-скриптов: принимает те же {model, maxTokens, messages}
 * и возвращает тот же shape {choices:[{message:{content}}]}. Никакого Groq/Manus.
 *
 * Мост: POST {GEMINI_BRIDGE_URL}/genai/v1beta/models/{AUTO}:generateContent
 *   - system-сообщения склеиваются в начало первого user-хода (мост нормализует роли)
 *   - thinkingBudget>0 обязателен для Pro (иначе 400 "only works in thinking")
 * Формат тела повторяет проверенный живой запрос (HTTP 200).
 */
// 🚨 НЕ читаем GEMINI_BRIDGE_URL из .env — там контейнерный адрес (http://viralcraft:3000/genai),
// а эти скрипты бегут на ХОСТЕ через npx tsx. Свой ключ + хостовый дефолт (docker-proxy :4400).
const BRIDGE = (process.env.GMA_BRIDGE_URL || 'http://127.0.0.1:4400').replace(/\/genai\/?$/, '');
const BRIDGE_MODEL = process.env.GMA_BRIDGE_MODEL || 'gemini-auto-agent';

// 11.09.2026: этот клиент бьёт в :4400 НАПРЯМУЮ, минуя /root/codeassist-openai-shim.py
// (:4405) с его circuit breaker'ом и недельным потолком — а это и есть настоящий
// ночной конвейер статей (gma-blog-nightly.ts), из-за которого 09-10.09.2026 гасла
// общая Google-квота и падал поиск в виджете 100zem.ru. Читаем/пишем ТЕ ЖЕ файлы
// состояния, что и шим, — так весь non-widget трафик (шим + этот клиент + aitrading
// grid-ai-analyst.sh) делит один пул и не выжигает больше 70% в неделю.
import * as fs from 'fs';

const BREAKER_FILE = '/root/.codeassist-breaker-state.json';
const WEEKLY_USAGE_FILE = '/root/.codeassist-weekly-usage.json';
const WEEKLY_BUDGET_POOLED = 386; // держать в синхроне с codeassist-openai-shim.py
const BREAKER_COOLDOWN_MS = 7 * 24 * 3600 * 1000;

function readJsonSafe(path: string): Record<string, number> {
  try {
    return JSON.parse(fs.readFileSync(path, 'utf-8'));
  } catch {
    return {};
  }
}

function writeJsonSafe(path: string, data: Record<string, number>): void {
  try {
    fs.writeFileSync(path, JSON.stringify(data));
  } catch {
    // недоступность файла состояния не должна ронять генерацию статьи
  }
}

function isoWeekKey(d: Date = new Date()): string {
  const date = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
  const dayNum = (date.getUTCDay() + 6) % 7; // Mon=0..Sun=6
  date.setUTCDate(date.getUTCDate() - dayNum + 3); // ближайший четверг
  const firstThursday = new Date(Date.UTC(date.getUTCFullYear(), 0, 4));
  const weekNum = 1 + Math.round(
    ((date.getTime() - firstThursday.getTime()) / 86400000 - 3 + ((firstThursday.getUTCDay() + 6) % 7)) / 7
  );
  return `${date.getUTCFullYear()}-W${String(weekNum).padStart(2, '0')}`;
}

function breakerWaitSeconds(): number | null {
  const state = readJsonSafe(BREAKER_FILE);
  const until = Math.max(...Object.values(state), 0);
  const now = Date.now() / 1000;
  return until && now < until ? Math.round(until - now) : null;
}

function recordBreakerOpen(model: string): void {
  const state = readJsonSafe(BREAKER_FILE);
  state[model] = Date.now() / 1000 + BREAKER_COOLDOWN_MS / 1000;
  writeJsonSafe(BREAKER_FILE, state);
}

function weeklyBudgetExceeded(): boolean {
  const data = readJsonSafe(WEEKLY_USAGE_FILE);
  return (data[isoWeekKey()] || 0) >= WEEKLY_BUDGET_POOLED;
}

function recordWeeklyAttempt(): void {
  const week = isoWeekKey();
  const data = readJsonSafe(WEEKLY_USAGE_FILE);
  writeJsonSafe(WEEKLY_USAGE_FILE, { [week]: (data[week] || 0) + 1 });
}

function isCodeAssistQuotaError(error: unknown): boolean {
  let text = '';
  try { text = JSON.stringify(error); } catch { text = String(error); }
  return /RESOURCE_EXHAUSTED|codeassist\s+429|HTTP\s+429/i.test(text);
}

function resolveCodeAssistRequestedModel(requestedModel: string | undefined): string {
  if (!requestedModel) return BRIDGE_MODEL;
  return /gemini[^/]*(?:auto|pro|flash)|(?:auto|pro|flash)[^/]*gemini/i.test(requestedModel)
    ? requestedModel
    : BRIDGE_MODEL;
}

type Msg = { role: string; content: string };
type BridgeParams = { model?: string; maxTokens?: number; max_tokens?: number; messages: Msg[] };
type BridgeResult = { choices: Array<{ message: { role: string; content: string } }> };

const sleep = (ms: number) => new Promise(r => setTimeout(r, ms));

export async function bridgeLLM(params: BridgeParams): Promise<BridgeResult> {
  const waitSec = breakerWaitSeconds();
  if (waitSec !== null) {
    throw Object.assign(
      new Error(`bridgeLLM: breaker open (общая Google-квота исчерпана), retry через ${waitSec}s`),
      { code: 429, status: 'RESOURCE_EXHAUSTED' },
    );
  }
  if (weeklyBudgetExceeded()) {
    throw Object.assign(
      new Error(`bridgeLLM: недельный потолок ${WEEKLY_BUDGET_POOLED} запросов исчерпан — резерв квоты для виджета 100zem.ru`),
      { code: 429, status: 'RESOURCE_EXHAUSTED' },
    );
  }
  recordWeeklyAttempt();

  const sys = params.messages.filter(m => m.role === 'system').map(m => m.content).join('\n\n');
  const rest = params.messages.filter(m => m.role !== 'system');
  const contents = rest.map((m, i) => ({
    role: m.role === 'assistant' || m.role === 'model' ? 'model' : 'user',
    parts: [{ text: i === 0 && sys ? `${sys}\n\n${m.content}` : m.content }],
  }));
  if (contents.length === 0) contents.push({ role: 'user', parts: [{ text: sys }] });

  const body = {
    contents,
    generationConfig: {
      maxOutputTokens: params.maxTokens ?? params.max_tokens ?? 4000,
      thinkingConfig: { thinkingBudget: 256 },
    },
  };
  const requestedModel = resolveCodeAssistRequestedModel(params.model);
  const url = `${BRIDGE}/genai/v1beta/models/${requestedModel}:generateContent`;

  let lastErr = '';
  let lastAttempt = 0;
  let quotaExhausted = false;
  for (let attempt = 1; attempt <= 3; attempt++) {
    lastAttempt = attempt;
    try {
      const r = await fetch(url, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify(body),
        signal: AbortSignal.timeout(150000),
      });
      const txt = await r.text();
      if (!r.ok) {
        lastErr = `HTTP ${r.status}: ${txt.slice(0, 300)}`;
        // Исчерпанная квота не восстановится за секунды: не повторяем тот же запрос
        // трижды и не понижаем явно сложную Pro-задачу до Flash.
        if (isCodeAssistQuotaError({ code: r.status, message: txt })) {
          quotaExhausted = true;
          recordBreakerOpen(requestedModel);
          break;
        }
        if (r.status >= 500 || r.status === 429) { await sleep(2500 * attempt); continue; }
        throw new Error(`bridgeLLM ${lastErr}`);
      }
      const data = JSON.parse(txt);
      const parts = data?.candidates?.[0]?.content?.parts ?? [];
      const text = parts.map((p: { text?: string }) => p.text ?? '').join('').trim();
      if (!text) { lastErr = `empty response: ${txt.slice(0, 300)}`; await sleep(2500 * attempt); continue; }
      return { choices: [{ message: { role: 'assistant', content: text } }] };
    } catch (e) {
      lastErr = e instanceof Error ? e.message : String(e);
      if (attempt < 3) { await sleep(2500 * attempt); continue; }
    }
  }
  throw Object.assign(
    new Error(`bridgeLLM failed after ${lastAttempt} attempt${lastAttempt === 1 ? '' : 's'}: ${lastErr}`),
    quotaExhausted ? { code: 429, status: 'RESOURCE_EXHAUSTED' } : {},
  );
}

// alias — чтобы скрипты меняли только строку импорта
export { bridgeLLM as invokeLLM };
