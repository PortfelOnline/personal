import { fetchPageHtml } from '../server/_core/browser';

const html = await fetchPageHtml('https://yandex.ru/search/?text=кадастровый+паспорт&lr=213', 5000);
console.log('len:', html.length);
console.log('title:', html.match(/<title[^>]*>([^<]*)</)?.[1]?.slice(0,80));
const organic = (html.match(/class="[^"]*organic[^"]*"/g) || []);
console.log('organic classes found:', organic.length, organic.slice(0,3));
const serp = (html.match(/serp-item|data-cid|OrganicTitle/g) || []);
console.log('serp patterns:', serp.length);
console.log('first 600:', html.slice(0,600));
process.exit(0);
