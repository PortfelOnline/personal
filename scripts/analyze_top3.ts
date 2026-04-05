import 'dotenv/config';
import { fetchYandexSerp } from '../server/_core/serpParser';
import { fetchGoogleSerp } from '../server/_core/serpParser';

const ourDomain = 'kadastrmap.info';

const queries = [
  'планировка квартиры по адресу',
  'план квартиры по адресу',
  'найти участок по кадастровому номеру со спутника',
];

for (const kw of queries) {
  console.log(`\n${'='.repeat(60)}`);
  console.log(`QUERY: "${kw}"`);

  // Yandex
  const yd = await fetchYandexSerp(kw);
  const ydOur = yd.results.find(r => r.domain.includes(ourDomain));
  console.log(`\nЯндекс (${yd.results.length} results):`);
  if (ydOur) {
    console.log(`  ✅ kadastrmap.info: #${ydOur.position}`);
  } else {
    console.log(`  ❌ kadastrmap.info: не в топ-${yd.results.length}`);
  }
  console.log('  Топ-3 конкуренты:');
  yd.results.filter(r => !r.domain.includes(ourDomain)).slice(0, 3).forEach((r, i) => {
    console.log(`    ${i+1}. #${r.position} ${r.domain}`);
    console.log(`       ${r.title.slice(0, 70)}`);
    console.log(`       ${r.url}`);
  });

  // Google
  const gd = await fetchGoogleSerp(kw);
  const gdOur = gd.results.find(r => r.domain.includes(ourDomain));
  console.log(`\nGoogle (${gd.results.length} results):`);
  if (gdOur) {
    console.log(`  ✅ kadastrmap.info: #${gdOur.position}`);
    console.log(`     ${gdOur.url}`);
  } else {
    console.log(`  ❌ kadastrmap.info: не найден`);
  }
  console.log('  Топ-3 конкуренты:');
  gd.results.filter(r => !r.domain.includes(ourDomain)).slice(0, 3).forEach((r, i) => {
    console.log(`    ${i+1}. #${r.position} ${r.domain} — ${r.url}`);
  });
}
