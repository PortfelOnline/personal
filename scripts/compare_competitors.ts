import 'dotenv/config';
import axios from 'axios';
import * as cheerio from 'cheerio';
import { fetchYandexSerp } from '../server/_core/serpParser';

const targets = [
  {
    query: 'найти участок по кадастровому номеру со спутника',
    ourUrl: 'https://kadastrmap.info/kadastr/kadastrovaya-publichnaya-karta-so-sputnika/',
    googlePos: 4.6,
  },
  {
    query: 'найти участок по кадастровому номеру',
    ourUrl: 'https://kadastrmap.info/kadastr/raspolozhenie-po-kadastrovomu-nomeru/',
    googlePos: 6.6,
  },
  {
    query: 'как узнать планировку квартиры по адресу',
    ourUrl: 'https://kadastrmap.info/kadastr/kadastrovyj-plan-kvartiry-po-adresu/',
    googlePos: 3.9,
  },
];

async function fetchText(url: string): Promise<{words: number, h2: number, h3: number, hasFaq: boolean, hasTable: boolean}> {
  try {
    const r = await axios.get(url, { headers: { 'User-Agent': 'Mozilla/5.0' }, timeout: 15000 });
    const $ = cheerio.load(r.data);
    $('script,style,nav,header,footer').remove();
    const text = $('body').text().replace(/\s+/g, ' ');
    const words = text.split(' ').filter(Boolean).length;
    const h2 = $('h2').length;
    const h3 = $('h3').length;
    const hasFaq = $('details, .faq, [class*="faq"], [itemtype*="FAQPage"]').length > 0;
    const hasTable = $('table').length > 0;
    return { words, h2, h3, hasFaq, hasTable };
  } catch {
    return { words: 0, h2: 0, h3: 0, hasFaq: false, hasTable: false };
  }
}

for (const t of targets) {
  console.log(`\n${'='.repeat(65)}`);
  console.log(`QUERY: "${t.query}"`);
  console.log(`Google pos: ${t.googlePos} | Яндекс: ?`);

  const yd = await fetchYandexSerp(t.query);
  const ydOur = yd.results.find(r => r.domain.includes('kadastrmap.info'));
  console.log(`Яндекс позиция: ${ydOur ? '#' + ydOur.position : 'не в топ-100'}`);

  // Our article
  const our = await fetchText(t.ourUrl);
  console.log(`\nНАША СТАТЬЯ: ${t.ourUrl}`);
  console.log(`  слов: ${our.words} | H2: ${our.h2} | H3: ${our.h3} | FAQ: ${our.hasFaq} | таблица: ${our.hasTable}`);

  // Top 3 Yandex competitors
  const competitors = yd.results.filter(r => !r.domain.includes('kadastrmap.info')).slice(0, 3);
  console.log(`\nКОНКУРЕНТЫ (Яндекс топ-3):`);
  for (const c of competitors) {
    const stats = await fetchText(c.url);
    console.log(`  #${c.position} ${c.domain}`);
    console.log(`    слов: ${stats.words} | H2: ${stats.h2} | H3: ${stats.h3} | FAQ: ${stats.hasFaq} | таблица: ${stats.hasTable}`);
    console.log(`    "${c.title.slice(0, 60)}"`);
    console.log(`    ${c.url}`);
  }
}
