import 'dotenv/config';
import { fetchYandexSerp } from '../server/_core/serpParser';

const ourDomain = 'kadastrmap.info';

const kw1 = 'кадастровый паспорт';
const d1 = await fetchYandexSerp(kw1);
const our1 = d1.results.find(r => r.domain.includes(ourDomain));
console.log(`\n[1] "${kw1}" → results: ${d1.results.length}`);
console.log(our1 ? `✅ kadastrmap.info: #${our1.position}` : `❌ kadastrmap.info: не в топ-${d1.results.length}`);
console.log('Top 3 конкуренты:');
d1.results.filter(r => !r.domain.includes(ourDomain)).slice(0, 3).forEach((r, i) =>
  console.log(`  ${i+1}. ${r.domain} — «${r.title.slice(0, 60)}»`)
);

const kw2 = 'кадастровый паспорт на земельный участок где получить';
const d2 = await fetchYandexSerp(kw2);
const our2 = d2.results.find(r => r.domain.includes(ourDomain));
console.log(`\n[2] "${kw2}" → results: ${d2.results.length}`);
console.log(our2 ? `✅ kadastrmap.info: #${our2.position}\n   ${our2.url}` : `❌ kadastrmap.info: не в топ-${d2.results.length}`);
console.log('Top 3 конкуренты:');
d2.results.filter(r => !r.domain.includes(ourDomain)).slice(0, 3).forEach((r, i) =>
  console.log(`  ${i+1}. ${r.domain} (#${r.position})`));
