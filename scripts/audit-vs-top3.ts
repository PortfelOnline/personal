/**
 * Audit: compare our recent v13 articles against their real top-3 competitors
 * on Google and Yandex. Output positions + metric comparison table.
 */
import 'dotenv/config';
import { fetchGoogleSerp, fetchYandexSerp } from '../server/_core/serpParser';
import { parseArticleFromUrl } from '../server/_core/articleParser';

const TARGETS = [
  { url: 'https://kadastrmap.info/kadastr/dlya-chego-nuzhna-vypiska-iz-egrn-na-zemelnyj-uchastok/', keyword: 'для чего нужна выписка ЕГРН на земельный участок' },
  { url: 'https://kadastrmap.info/kadastr/zachem-nuzhna-vypiska-iz-egrn-na-kvartiru/',              keyword: 'зачем нужна выписка ЕГРН на квартиру' },
  { url: 'https://kadastrmap.info/kadastr/kak-poluchit-vypisku-egrn-na-zemelnyj-uchastok/',         keyword: 'как получить выписку ЕГРН на земельный участок' },
];

interface Metrics {
  url: string; domain: string;
  words: number; h2: number; h3: number; faq: number; tables: number; images: number;
}

async function getMetrics(url: string): Promise<Metrics | null> {
  try {
    const parsed = await Promise.race([
      parseArticleFromUrl(url),
      new Promise<never>((_, rj) => setTimeout(() => rj(new Error('timeout')), 20000)),
    ]);
    const html = parsed.contentHtml || '';
    return {
      url,
      domain: (new URL(url).hostname).replace(/^www\./, ''),
      words: parsed.wordCount,
      h2: (html.match(/<h2\b/gi) || []).length,
      h3: (html.match(/<h3\b/gi) || []).length,
      faq: (html.match(/<details\b/gi) || []).length,
      tables: (html.match(/<table\b/gi) || []).length,
      images: (html.match(/<img\b/gi) || []).length,
    };
  } catch (e: any) {
    return null;
  }
}

async function main() {
  for (const t of TARGETS) {
    console.log(`\n${'='.repeat(80)}\n🎯 KEYWORD: ${t.keyword}\n   OUR URL: ${t.url}`);
    const [g, y] = await Promise.all([
      fetchGoogleSerp(t.keyword).catch(() => ({ results: [] as any[] })),
      fetchYandexSerp(t.keyword).catch(() => ({ results: [] as any[] })),
    ]);
    const gPos = g.results.findIndex((r: any) => r.domain?.includes('kadastrmap') || r.url?.includes('kadastrmap'));
    const yPos = y.results.findIndex((r: any) => r.domain?.includes('kadastrmap') || r.url?.includes('kadastrmap'));
    console.log(`\n📊 POSITIONS:  Google = ${gPos < 0 ? 'not in top-10' : `#${gPos + 1}`}  | Yandex = ${yPos < 0 ? 'not in top-10' : `#${yPos + 1}`}`);
    console.log(`\n📋 GOOGLE TOP-5:`);
    g.results.slice(0, 5).forEach((r: any, i: number) => console.log(`   ${i + 1}. ${r.domain}  ${(r.title || '').slice(0, 60)}`));
    console.log(`\n📋 YANDEX TOP-5:`);
    y.results.slice(0, 5).forEach((r: any, i: number) => console.log(`   ${i + 1}. ${r.domain}  ${(r.title || '').slice(0, 60)}`));

    // Parse our article + top-3 competitors
    const topCompetitors = [
      ...g.results.slice(0, 3),
      ...y.results.slice(0, 3),
    ].filter((r: any) => !r.domain?.includes('kadastrmap'));
    const uniqueTop = Array.from(new Map(topCompetitors.map((r: any) => [r.domain, r])).values()).slice(0, 5);

    console.log(`\n⚡ Parsing metrics...`);
    const [ours, ...tops] = await Promise.all([
      getMetrics(t.url),
      ...uniqueTop.map((c: any) => getMetrics(c.url)),
    ]);
    const validTops = tops.filter(Boolean) as Metrics[];

    if (!ours) { console.log('   ❌ our article parse failed'); continue; }
    if (validTops.length === 0) { console.log('   ⚠️  no competitor data parsable'); continue; }

    const avg = (k: keyof Omit<Metrics, 'url' | 'domain'>) =>
      Math.round(validTops.reduce((s, m) => s + (m[k] as number), 0) / validTops.length);
    const max = (k: keyof Omit<Metrics, 'url' | 'domain'>) =>
      Math.max(...validTops.map(m => m[k] as number));

    console.log(`\n📊 COMPARISON (our article vs top-${validTops.length} competitors):`);
    console.log(`   ${'Metric'.padEnd(10)} ${'Ours'.padStart(6)}  ${'Avg'.padStart(6)}  ${'Max'.padStart(6)}  Verdict`);
    for (const k of ['words', 'h2', 'h3', 'faq', 'tables', 'images'] as const) {
      const o = ours[k], a = avg(k), mx = max(k);
      const v = o >= mx ? '✅ >= max' : o >= a ? '🟡 >= avg' : '❌ below avg';
      console.log(`   ${k.padEnd(10)} ${String(o).padStart(6)}  ${String(a).padStart(6)}  ${String(mx).padStart(6)}  ${v}`);
    }
  }
}

main().catch(e => { console.error('[audit]', e?.message ?? e); process.exit(1); });
