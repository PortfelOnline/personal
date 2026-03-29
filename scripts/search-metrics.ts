/**
 * Search metrics loader: Keys.so positions + optional GSC / Yandex WM API.
 *
 * Usage (standalone analysis):
 *   npx tsx scripts/search-metrics.ts
 *
 * Exports:
 *   loadPositions() — loads positions.json
 *   getGoogleOpportunity(slug) — position-based opportunity score
 *   analyzePositions() — console report
 */
import { readFileSync } from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const POSITIONS_FILE = path.join(__dirname, 'positions.json');

export interface PositionEntry {
  query: string;
  freq: number | null;
  yandex: (number | null)[];
  google: (number | null)[];
  googleDelta?: (number | null)[];
}

export interface PositionsData {
  updated: string;
  dates: string[];
  summary: {
    visibility: number;
    avgPosition: number;
    effectiveness: number;
    top1: number; top5: number; top10: number; top50: number; top100: number;
  };
  queries: PositionEntry[];
}

export function loadPositions(): PositionsData {
  return JSON.parse(readFileSync(POSITIONS_FILE, 'utf8'));
}

/**
 * Get Google position opportunity bonus for a slug.
 * Matches slug keywords against monitored queries.
 *
 * Returns bonus score (0–40).
 */
export function getGoogleOpportunity(slug: string): number {
  const data = loadPositions();
  const words = slug.toLowerCase().replace(/-/g, ' ').split(' ').filter(w => w.length > 3);

  let bestScore = 0;

  for (const entry of data.queries) {
    const qWords = entry.query.toLowerCase().split(' ');
    // Count overlap between slug words and query words
    const overlap = words.filter(w => qWords.some(qw => qw.includes(w) || w.includes(qw))).length;
    if (overlap < 2 && words.length > 3) continue;
    if (overlap < 1) continue;

    const g = entry.google[0]; // latest position (28 Mar)
    const freq = entry.freq ?? 0;

    let score = 0;

    // Frequency bonus
    if (freq >= 500) score += 20;
    else if (freq >= 100) score += 10;
    else if (freq >= 20) score += 5;
    else if (freq >= 5) score += 2;

    // Position opportunity
    if (g === null) {
      // Not ranking — missed opportunity if high-freq
      if (freq >= 50) score += 8;
      else if (freq >= 10) score += 4;
    } else if (g <= 3) {
      score += 5; // Already top-3, maintain
    } else if (g <= 5) {
      score += 10; // Top-5, push to top-3
    } else if (g <= 10) {
      score += 15; // Top-10, high opportunity
    } else if (g <= 20) {
      score += 25; // Page 2 — easiest win
    } else if (g <= 50) {
      score += 10; // Page 3-5 — possible
    } else {
      score += 3; // Deep, hard
    }

    // Volatility bonus (big negative delta = falling, needs fixing)
    const delta = entry.googleDelta?.[0];
    if (delta !== null && delta !== undefined && delta <= -10) {
      score += 8; // Urgent: falling fast
    }

    bestScore = Math.max(bestScore, score);
  }

  return bestScore;
}

/**
 * Standalone: print position analysis report
 */
function analyzePositions(): void {
  const data = loadPositions();
  console.log(`\n=== АНАЛИЗ ПОЗИЦИЙ Keys.so (${data.updated}) ===`);
  console.log(`Visibility: ${data.summary.visibility}  AvgPos: ${data.summary.avgPosition}  Effectiveness: ${data.summary.effectiveness}`);
  console.log(`Top1: ${data.summary.top1}  Top5: ${data.summary.top5}  Top10: ${data.summary.top10}  Top50: ${data.summary.top50}  Top100: ${data.summary.top100}`);
  console.log(`\nYandex: ВСЕ позиции null (сайт не в ТОП-100 ни по одному запросу!)`);
  console.log(`Упоминаний в ИИ-ответах: 1, Результативность ИИ: 1.69 → КРИТИЧНО\n`);

  // Google opportunities
  const ranked = data.queries.filter(q => q.google[0] !== null).sort((a, b) => (a.google[0] ?? 999) - (b.google[0] ?? 999));
  const nearTop = ranked.filter(q => q.google[0] !== null && (q.google[0] as number) <= 20);
  const falling = data.queries.filter(q => {
    const d = q.googleDelta?.[0];
    return d !== null && d !== undefined && d <= -10;
  });
  const notRanking = data.queries.filter(q => q.google[0] === null && (q.freq ?? 0) >= 50);

  console.log(`--- Google: ТОП-20 (${nearTop.length} запросов) ---`);
  for (const q of nearTop) {
    const pos = q.google[0];
    const delta = q.googleDelta?.[0];
    const dStr = delta != null ? (delta > 0 ? `▲${delta}` : `▼${Math.abs(delta)}`) : '';
    console.log(`  pos=${String(pos).padStart(3)}${dStr.padStart(5)}  freq=${String(q.freq ?? '—').padStart(4)}  ${q.query}`);
  }

  if (falling.length) {
    console.log(`\n--- ⚠️  Падают в Google (delta ≤ -10) ---`);
    for (const q of falling) {
      const d = q.googleDelta![0];
      console.log(`  pos=${q.google[0]}  delta=${d}  ${q.query}`);
    }
  }

  if (notRanking.length) {
    console.log(`\n--- ❌ Не ранжируются в Google (freq ≥ 50) ---`);
    for (const q of notRanking) {
      console.log(`  freq=${q.freq}  ${q.query}`);
    }
  }

  console.log(`\n--- Стратегия улучшения ИИ-упоминаний ---`);
  console.log(`  1. FAQ-блоки (details/summary, schema FAQPage) в каждой статье`);
  console.log(`  2. Прямые ответы в первом абзаце (answer-first структура)`);
  console.log(`  3. Структурированные данные: Article, HowTo, FAQPage`);
  console.log(`  4. E-E-A-T: авторы, даты, источники (Росреестр)`);
  console.log(`  5. Приоритет: запросы pos 11-20 → page 2 → page 1 (лёгкий рост)`);
}

// Run if executed directly
const isMain = process.argv[1]?.endsWith('search-metrics.ts') || process.argv[1]?.endsWith('search-metrics.js');
if (isMain) {
  analyzePositions();
}
