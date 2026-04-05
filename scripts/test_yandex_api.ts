import 'dotenv/config';
import { fetchYandexSerp } from '../server/_core/serpParser';

const keyword = 'кадастровый паспорт квартиры';
const ourDomain = 'kadastrmap.info';

console.log(`Testing Yandex SERP for: "${keyword}"\n`);
const data = await fetchYandexSerp(keyword);

console.log(`Engine: ${data.engine}`);
console.log(`Total results: ${data.results.length}`);
if (data.error) console.log(`Error: ${data.error}`);

const ourResult = data.results.find(r => r.domain.includes(ourDomain));
if (ourResult) {
  console.log(`\n✅ kadastrmap.info position: #${ourResult.position}`);
  console.log(`   URL: ${ourResult.url}`);
  console.log(`   Title: ${ourResult.title.slice(0, 80)}`);
} else {
  console.log(`\n❌ kadastrmap.info NOT in top ${data.results.length}`);
}

console.log('\nTop 10 results:');
data.results.slice(0, 10).forEach(r => {
  const mark = r.domain.includes(ourDomain) ? ' ← WE ARE HERE' : '';
  console.log(`  #${r.position} ${r.domain}${mark}`);
});

const competitors = data.results.filter(r => !r.domain.includes(ourDomain)).slice(0, 3);
console.log('\nTop 3 competitors:');
competitors.forEach((r, i) => {
  console.log(`  ${i+1}. ${r.domain} (#${r.position})`);
  console.log(`     ${r.title.slice(0, 70)}`);
});

// Test 2: keyword where we should rank
const keyword2 = 'кадастровая выписка заказать';
console.log(`\n\n--- Test 2: "${keyword2}" ---`);
const data2 = await fetchYandexSerp(keyword2);
console.log(`Results: ${data2.results.length}`);
const our2 = data2.results.find(r => r.domain.includes(ourDomain));
if (our2) {
  console.log(`✅ kadastrmap.info position: #${our2.position} — ${our2.url}`);
} else {
  console.log(`❌ kadastrmap.info not in top ${data2.results.length}`);
}
console.log('Top 5:');
data2.results.slice(0, 5).forEach(r => {
  const mark = r.domain.includes(ourDomain) ? ' ← WE' : '';
  console.log(`  #${r.position} ${r.domain}${mark}`);
});
