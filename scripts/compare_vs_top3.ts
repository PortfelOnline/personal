/**
 * Сравниваем топ-GSC статьи с конкурентами: слова, H2, FAQ, картинки
 */
import 'dotenv/config';
import { fetchGoogleSerp } from '../server/_core/serpParser';
import { parseArticleFromUrl } from '../server/_core/articleParser';

const TARGETS = [
  { url: 'https://kadastrmap.info/kadastr/kadastrovyj-plan-kvartiry-po-adresu/', keyword: 'кадастровый план квартиры по адресу', gscPos: 18.4, gscImpr: 2943 },
  { url: 'https://kadastrmap.info/kadastr/raspolozhenie-po-kadastrovomu-nomeru/',  keyword: 'расположение по кадастровому номеру',  gscPos: 7.1,  gscImpr: 996 },
  { url: 'https://kadastrmap.info/kadastr/gos-kadastr-nedvizhimosti/',             keyword: 'государственный кадастр недвижимости', gscPos: 19.1, gscImpr: 528 },
  { url: 'https://kadastrmap.info/kadastr/gkn-onlajn-rosreestr/',                  keyword: 'гкн онлайн росреестр',                 gscPos: 6.0,  gscImpr: 181 },
];

interface Metrics {
  url: string; domain: string;
  words: number; h2: number; h3: number; faq: number; tables: number; images: number;
}

async function getMetrics(url: string): Promise<Metrics | null> {
  try {
    const parsed = await Promise.race([
      parseArticleFromUrl(url),
      new Promise<never>((_, rj) => setTimeout(() => rj(new Error('timeout')), 25000)),
    ]);
    const html = parsed.contentHtml || '';
    return {
      url, domain: new URL(url).hostname.replace(/^www\./, ''),
      words: parsed.wordCount,
      h2:     (html.match(/<h2\b/gi) || []).length,
      h3:     (html.match(/<h3\b/gi) || []).length,
      faq:    (html.match(/<details\b/gi) || []).length,
      tables: (html.match(/<table\b/gi) || []).length,
      images: (html.match(/<img\b/gi) || []).length,
    };
  } catch { return null; }
}

function grade(ours: number, best: number): string {
  const ratio = ours / Math.max(best, 1);
  if (ratio >= 0.9) return '✅';
  if (ratio >= 0.6) return '⚠️ ';
  return '❌';
}

async function main() {
  for (const target of TARGETS) {
    console.log(`\n${'═'.repeat(72)}`);
    console.log(`📄 ${target.keyword}`);
    console.log(`   GSC: pos ${target.gscPos} | показов ${target.gscImpr}`);
    console.log('─'.repeat(72));

    let serpUrls: string[] = [];
    try {
      const serpRes = await fetchGoogleSerp(target.keyword, { maxResults: 10 });
      serpUrls = (serpRes.results || [])
        .map((r: any) => r.url || r.link)
        .filter((u: string) => u && !u.includes('kadastrmap.info'))
        .slice(0, 3);
      console.log(`  SERP топ-3: ${serpUrls.map((u: string) => new URL(u).hostname).join(', ')}`);
    } catch (e: any) {
      console.log(`  ⚠️  SERP недоступен: ${e.message}`);
    }

    const ourMetrics = await getMetrics(target.url);

    const compMetrics: Metrics[] = [];
    for (const compUrl of serpUrls) {
      const m = await getMetrics(compUrl);
      if (m) compMetrics.push(m);
      await new Promise(r => setTimeout(r, 1500));
    }

    const all = [ourMetrics, ...compMetrics].filter(Boolean) as Metrics[];
    if (!all.length) { console.log('  Нет данных для сравнения'); continue; }

    const maxW = Math.max(...all.map(m => m.words));
    const maxH2 = Math.max(...all.map(m => m.h2));
    const maxFaq = Math.max(...all.map(m => m.faq));
    const maxImg = Math.max(...all.map(m => m.images));

    console.log(`\n  ${'Домен'.padEnd(32)} ${'Слова'.padStart(6)} ${'H2'.padStart(3)} ${'H3'.padStart(3)} ${'FAQ'.padStart(4)} ${'Фото'.padStart(5)}`);
    console.log(`  ${'─'.repeat(54)}`);

    for (const m of all) {
      const isOurs = m.url.includes('kadastrmap.info');
      const prefix = isOurs ? '🏠' : '🔴';
      const domain = (isOurs ? 'НАШ САЙТ' : m.domain).slice(0, 30).padEnd(32);
      const wGr  = grade(m.words, maxW);
      const fGr  = grade(m.faq,   maxFaq);
      const iGr  = grade(m.images, maxImg);
      console.log(`  ${prefix} ${domain} ${m.words.toString().padStart(5)} ${wGr} ${m.h2.toString().padStart(2)} ${m.h3.toString().padStart(2)} ${m.faq.toString().padStart(3)} ${fGr} ${m.images.toString().padStart(4)} ${iGr}`);
    }

    if (ourMetrics) {
      const gaps: string[] = [];
      if (ourMetrics.words  < maxW   * 0.8) gaps.push(`📝 +${maxW   - ourMetrics.words} слов (лидер: ${maxW})`);
      if (ourMetrics.faq   < maxFaq  * 0.7) gaps.push(`❓ +${maxFaq  - ourMetrics.faq} FAQ (лидер: ${maxFaq})`);
      if (ourMetrics.images < maxImg * 0.7) gaps.push(`🖼️  +${maxImg - ourMetrics.images} картинок (лидер: ${maxImg})`);
      console.log(gaps.length
        ? `\n  📌 Нужно: ${gaps.join(' | ')}`
        : '\n  ✅ Метрики не хуже конкурентов');
    }

    await new Promise(r => setTimeout(r, 2000));
  }
  console.log(`\n${'═'.repeat(72)}\n`);
}

main().catch(console.error);
