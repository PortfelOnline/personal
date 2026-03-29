import axios from 'axios';

const SERPAPI_KEY = 'f520ac79a974bb4f9b9c6a45d7cea91466014142507aeb6c947dc9657cc0b752';
const TARGET_DOMAIN = 'kadastrmap.info';

async function checkSerp(keyword, engine) {
  const params = engine === 'google'
    ? { engine: 'google', q: keyword, hl: 'ru', gl: 'ru', num: '50', api_key: SERPAPI_KEY }
    : { engine: 'yandex', text: keyword, lr: '213', lang: 'ru', numdoc: '50', api_key: SERPAPI_KEY };

  try {
    const qs = new URLSearchParams({ ...params, output: 'json' });
    const res = await axios.get(`https://serpapi.com/search?${qs}`, { timeout: 30000 });
    const results = res.data.organic_results || [];
    const pos = results.findIndex(r => (r.link || '').includes(TARGET_DOMAIN));
    return pos >= 0 ? pos + 1 : null;
  } catch (e) {
    return `ERR:${e.message.slice(0,30)}`;
  }
}

// Список статей: [keyword, url]
const articles = [
  ['справка об обременении недвижимости в Москве', 'https://kadastrmap.info/kadastr/zakazat-spravku-ob-obremenenii-nedvizhimosti-v-moskve-poshagovoe-rukovodstvo/'],
  ['Как снять обременение с ипотечной квартиры', 'https://kadastrmap.info/kadastr/kak-snyat-obremenenie-s-ipotechnoj-kvartiry/'],
  ['Кадастровая стоимость недвижимости в Росреестре', 'https://kadastrmap.info/kadastr/kadastrovaya-stoimost-nedvizhimosti-v-rosreestre-kak-uznat/'],
  ['Как узнать владельца квартиры по адресу', 'https://kadastrmap.info/kadastr/kak-uznat-vladeltsa-kvartiry-po-adresu-zakonnye-sposoby-i-vypiska/'],
  ['Как снять арест с квартиры', 'https://kadastrmap.info/kadastr/kak-snyat-arest-s-kvartiry-chto-delat-sobstvenniku/'],
  ['Как снять обременение с объекта недвижимости', 'https://kadastrmap.info/kadastr/kak-snyat-obremenenie-s-obekta-nedvizhimosti-poshagovaya-instruktsiya/'],
  ['Как проверить собственника по кадастровому номеру', 'https://kadastrmap.info/kadastr/kak-proverit-sobstvennika-po-kadastrovomu-nomeru-onlajn/'],
  ['Как снять обременение после погашения ипотеки', 'https://kadastrmap.info/kadastr/kak-snyat-obremenenie-posle-pogasheniya-ipoteki/'],
  ['Кадастровые выписки ЕГРН', 'https://kadastrmap.info/kadastr/chto-nuzhno-znat-o-kadastrovyh-vypiskah/'],
  ['Кадастровая стоимость онлайн', 'https://kadastrmap.info/kadastr/karta-kadastrovoj-stoimosti-kak-uznat-tsenu-nedvizhimosti-onlajn/'],
  ['заказать кадастровую выписку онлайн', 'https://kadastrmap.info/kadastr/zakazat-kadastrovuyu-vypisku-onlajn-tsena-sposoby-polucheniya/'],
  ['как узнать сведения по кадастровому номеру', 'https://kadastrmap.info/kadastr/kak-uznat-svedeniya-po-kadastrovomu-nomeru-egrn-i-karta/'],
  ['как узнать есть ли обременение на квартиру', 'https://kadastrmap.info/kadastr/kak-uznat-est-li-obremenenie-na-kvartiru/'],
  ['где проверить квартиру на обременение', 'https://kadastrmap.info/kadastr/gde-proverit-kvartiru-na-obremenenie/'],
  ['выписка ЕГРП обременением', 'https://kadastrmap.info/kadastr/vypiska-egrp-obremeneniem/'],
  ['проверить квартиру арест судебных приставов', 'https://kadastrmap.info/kadastr/proverit-kvartiru-arest-sudebnyh-pristavov/'],
  ['как узнать квартира в залоге', 'https://kadastrmap.info/kadastr/kak-uznat-kvartira-v-zaloge-ili-net/'],
  ['как узнать квартира в аресте', 'https://kadastrmap.info/kadastr/kak-uznat-kvartira-v-areste-ili-net/'],
  ['как узнать наложен ли арест на квартиру', 'https://kadastrmap.info/kadastr/kak-uznat-nalozhen-li-arest-na-kvartiru/'],
  ['как проверить квартиру на обременение при покупке', 'https://kadastrmap.info/kadastr/kak-proverit-kvartiru-na-obremenenie-pri-pokupke/'],
  ['Кадастровый план квартиры по адресу', 'https://kadastrmap.info/kadastr/kadastrovyj-plan-kvartiry-po-adresu/'],
  ['кадастровый паспорт на квартиру', 'https://kadastrmap.info/kadastr/kadastrovyj-pasport-na-kvartiru/'],
];

console.log('Ключевое слово | Google | Yandex | URL');
console.log('---');

const results = [];
for (const [keyword, url] of articles) {
  const [g, y] = await Promise.all([checkSerp(keyword, 'google'), checkSerp(keyword, 'yandex')]);
  const gStr = g === null ? 'не в топ-50' : (typeof g === 'string' ? g : `#${g}`);
  const yStr = y === null ? 'не в топ-50' : (typeof y === 'string' ? y : `#${y}`);
  console.log(`${keyword.padEnd(50)} | G:${gStr.padEnd(10)} | Y:${yStr.padEnd(10)} | ${url}`);
  results.push({ keyword, url, googlePos: typeof g === 'number' ? g : null, yandexPos: typeof y === 'number' ? y : null });
  await new Promise(r => setTimeout(r, 500)); // небольшая задержка между запросами
}

// Записать результаты в файл для следующего шага
import { writeFileSync } from 'fs';
writeFileSync('/tmp/serp_results.json', JSON.stringify(results, null, 2));
console.log('\nРезультаты сохранены в /tmp/serp_results.json');
