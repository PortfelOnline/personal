import 'dotenv/config';
import { fetchYandexSerp } from '../server/_core/serpParser';

const ourDomain = 'kadastrmap.info';

// Try keywords where kadastrmap.info likely ranks
const keywords = [
  'кадастровая выписка онлайн kadastrmap',
  'выписка из ЕГРН заказать kadastrmap',
  'обременение недвижимости kadastrmap',
  'кадастровый паспорт онлайн заказать',
];

for (const kw of keywords) {
  const data = await fetchYandexSerp(kw);
  const our = data.results.find(r => r.domain.includes(ourDomain));
  if (our) {
    console.log(`✅ "${kw}" → #${our.position}`);
  } else {
    console.log(`❌ "${kw}" → not in top ${data.results.length}`);
    console.log(`   top3: ${data.results.slice(0,3).map(r => r.domain).join(', ')}`);
  }
}
