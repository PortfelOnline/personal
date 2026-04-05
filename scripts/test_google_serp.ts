import { fetchPageHtml } from '../server/_core/browser';

const html = await fetchPageHtml('https://www.google.com/search?q=кадастровый+паспорт+квартиры&hl=ru&gl=ru&num=10', 3000);
console.log('len:', html.length);
console.log('title:', html.match(/<title[^>]*>([^<]*)</)?.[1]?.slice(0,60));
// Check for results
const divG = (html.match(/<div class="g"/g) || []).length;
const h3   = (html.match(/<h3/g) || []).length;
const sorry = html.includes('/sorry/') || html.includes('unusual traffic');
console.log('div.g count:', divG, '| h3 count:', h3, '| captcha:', sorry);
if (h3 > 0) {
  // Parse titles
  const titles = [...html.matchAll(/<h3[^>]*>([^<]+)<\/h3>/g)].slice(0,5);
  titles.forEach(m => console.log(' -', m[1].slice(0,70)));
}
process.exit(0);
