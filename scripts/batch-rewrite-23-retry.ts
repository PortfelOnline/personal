/**
 * Batch-23 retry: статьи которые не опубликовались из-за SSL bad_record_mac
 * Запускать ПОСЛЕ завершения batch-23
 * Usage: npx tsx scripts/batch-rewrite-23-retry.ts
 */
import 'dotenv/config';
import { runBatchRewrite } from '../server/routers/articles';

const BASE = 'https://kadastrmap.info/kadastr/';
const SLUGS = [
  'kak-uznat-kadastrovuyu-stoimost-obekta',
  'kak-uznat-stoimost-uchastka-po-kadastru',
];

const URLS = SLUGS.map(s => `${BASE}${s}/`);
console.log(`[batch-23-retry] ${URLS.length} failed articles`);
const start = Date.now();
await runBatchRewrite(1, URLS);
const mins = ((Date.now() - start) / 60000).toFixed(1);
console.log(`[batch-23-retry] DONE in ${mins} min`);
