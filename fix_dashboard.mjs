import mysql from 'mysql2/promise';

const DB_URL = 'mysql://root@127.0.0.1:3306/strategy_dashboard';
const USER_ID = 1;

// SERP результаты из нашей проверки
const serpResults = {
  'https://kadastrmap.info/kadastr/vypiska-egrp-obremeneniem/': { g: 1, y: null },
  'https://kadastrmap.info/kadastr/chto-nuzhno-znat-o-kadastrovyh-vypiskah/': { g: 2, y: null },
  'https://kadastrmap.info/kadastr/kadastrovyj-plan-kvartiry-po-adresu/': { g: 3, y: null },
};

const conn = await mysql.createConnection('mysql://root:@127.0.0.1:3306/strategy_dashboard');

// 1. Исправить 4 неправильных URL (добавить /kadastr/)
const wrongUrls = [
  ['https://kadastrmap.info/kak-uznat-svedeniya-po-kadastrovomu-nomeru-egrn-i-karta/', 'https://kadastrmap.info/kadastr/kak-uznat-svedeniya-po-kadastrovomu-nomeru-egrn-i-karta/'],
  ['https://kadastrmap.info/karta-kadastrovoj-stoimosti-kak-uznat-tsenu-nedvizhimosti-onlajn/', 'https://kadastrmap.info/kadastr/karta-kadastrovoj-stoimosti-kak-uznat-tsenu-nedvizhimosti-onlajn/'],
  ['https://kadastrmap.info/chto-nuzhno-znat-o-kadastrovyh-vypiskah/', 'https://kadastrmap.info/kadastr/chto-nuzhno-znat-o-kadastrovyh-vypiskah/'],
  ['https://kadastrmap.info/zakazat-kadastrovuyu-vypisku-onlajn-tsena-sposoby-polucheniya/', 'https://kadastrmap.info/kadastr/zakazat-kadastrovuyu-vypisku-onlajn-tsena-sposoby-polucheniya/'],
];
for (const [old, fixed] of wrongUrls) {
  const [r] = await conn.execute('UPDATE articleAnalyses SET url=? WHERE url=?', [fixed, old]);
  console.log(`URL fix: ${old.split('/').slice(-2,-1)[0]} → ${r.affectedRows} rows`);
}

// 2. Обновить SERP позиции у статей где они NULL
const allArticles = [
  { url: 'https://kadastrmap.info/kadastr/zakazat-spravku-ob-obremenenii-nedvizhimosti-v-moskve-poshagovoe-rukovodstvo/', kw: 'справка об обременении недвижимости в Москве', g: null, y: null },
  { url: 'https://kadastrmap.info/kadastr/kak-snyat-obremenenie-s-ipotechnoj-kvartiry/', kw: 'как снять обременение с ипотечной квартиры', g: null, y: null },
  { url: 'https://kadastrmap.info/kadastr/kadastrovaya-stoimost-nedvizhimosti-v-rosreestre-kak-uznat/', kw: 'кадастровая стоимость недвижимости в Росреестре', g: null, y: null },
  { url: 'https://kadastrmap.info/kadastr/kak-uznat-vladeltsa-kvartiry-po-adresu-zakonnye-sposoby-i-vypiska/', kw: 'как узнать владельца квартиры по адресу', g: null, y: null },
  { url: 'https://kadastrmap.info/kadastr/kak-snyat-arest-s-kvartiry-chto-delat-sobstvenniku/', kw: 'как снять арест с квартиры', g: null, y: null },
  { url: 'https://kadastrmap.info/kadastr/kak-snyat-obremenenie-s-obekta-nedvizhimosti-poshagovaya-instruktsiya/', kw: 'как снять обременение с объекта недвижимости', g: null, y: null },
  { url: 'https://kadastrmap.info/kadastr/kak-proverit-sobstvennika-po-kadastrovomu-nomeru-onlajn/', kw: 'как проверить собственника по кадастровому номеру', g: null, y: null },
  { url: 'https://kadastrmap.info/kadastr/kak-snyat-obremenenie-posle-pogasheniya-ipoteki/', kw: 'как снять обременение после погашения ипотеки', g: null, y: null },
  { url: 'https://kadastrmap.info/kadastr/chto-nuzhno-znat-o-kadastrovyh-vypiskah/', kw: 'кадастровые выписки ЕГРН', g: 2, y: null },
  { url: 'https://kadastrmap.info/kadastr/karta-kadastrovoj-stoimosti-kak-uznat-tsenu-nedvizhimosti-onlajn/', kw: 'кадастровая стоимость онлайн', g: null, y: null },
  { url: 'https://kadastrmap.info/kadastr/zakazat-kadastrovuyu-vypisku-onlajn-tsena-sposoby-polucheniya/', kw: 'заказать кадастровую выписку онлайн', g: null, y: null },
  { url: 'https://kadastrmap.info/kadastr/kak-uznat-svedeniya-po-kadastrovomu-nomeru-egrn-i-karta/', kw: 'как узнать сведения по кадастровому номеру', g: null, y: null },
  { url: 'https://kadastrmap.info/kadastr/kadastrovyj-plan-kvartiry-po-adresu/', kw: 'кадастровый план квартиры по адресу', g: 3, y: null },
  { url: 'https://kadastrmap.info/kadastr/kadastrovyj-pasport-na-kvartiru/', kw: 'кадастровый паспорт на квартиру', g: null, y: null },
];

// Обновить serpKeyword и позиции для уже существующих записей
for (const a of allArticles) {
  const [r] = await conn.execute(
    'UPDATE articleAnalyses SET serpKeyword=?, googlePos=?, yandexPos=? WHERE url=? AND userId=?',
    [a.kw, a.g, a.y, a.url, USER_ID]
  );
  if (r.affectedRows > 0) console.log(`Updated: ${a.kw} | G:${a.g ?? '-'} Y:${a.y ?? '-'}`);
}

// 3. Вставить пропущенные статьи
const missing = [
  { url: 'https://kadastrmap.info/kadastr/kak-uznat-est-li-obremenenie-na-kvartiru/', kw: 'как узнать есть ли обременение на квартиру', title: 'Как узнать, есть ли обременение на квартиру', g: null, y: null },
  { url: 'https://kadastrmap.info/kadastr/gde-proverit-kvartiru-na-obremenenie/', kw: 'где проверить квартиру на обременение', title: 'Где проверить квартиру на обременение', g: null, y: null },
  { url: 'https://kadastrmap.info/kadastr/vypiska-egrp-obremeneniem/', kw: 'выписка ЕГРП обременением', title: 'Выписка ЕГРП обременением', g: 1, y: null },
  { url: 'https://kadastrmap.info/kadastr/proverit-kvartiru-arest-sudebnyh-pristavov/', kw: 'проверить квартиру арест судебных приставов', title: 'Проверить квартиру арест судебных приставов', g: null, y: null },
  { url: 'https://kadastrmap.info/kadastr/kak-uznat-kvartira-v-zaloge-ili-net/', kw: 'как узнать квартира в залоге', title: 'Как узнать, квартира в залоге или нет', g: null, y: null },
  { url: 'https://kadastrmap.info/kadastr/kak-uznat-kvartira-v-areste-ili-net/', kw: 'как узнать квартира в аресте', title: 'Как узнать, квартира в аресте или нет', g: null, y: null },
  { url: 'https://kadastrmap.info/kadastr/kak-uznat-nalozhen-li-arest-na-kvartiru/', kw: 'как узнать наложен ли арест на квартиру', title: 'Как узнать, наложен ли арест на квартиру', g: null, y: null },
  { url: 'https://kadastrmap.info/kadastr/rosreestr-2026-proverka-obremenij-stala-obyazatelnoj-pri-ipotechnykh-sdelkakh/', kw: 'Росреестр 2026 проверка обременений', title: 'Росреестр 2026: проверка обременений при ипотеке', g: null, y: null },
  { url: 'https://kadastrmap.info/kadastr/kak-proverit-kvartiru-na-obremenenie-pri-pokupke/', kw: 'как проверить квартиру на обременение при покупке', title: 'Как проверить квартиру на обременение при покупке', g: null, y: null },
];

for (const a of missing) {
  const [exists] = await conn.execute('SELECT id FROM articleAnalyses WHERE url=? AND userId=? LIMIT 1', [a.url, USER_ID]);
  if (exists.length > 0) { console.log(`Already exists: ${a.kw}`); continue; }
  
  await conn.execute(`INSERT INTO articleAnalyses 
    (userId, url, originalTitle, originalContent, wordCount, improvedTitle, improvedContent, 
     metaTitle, metaDescription, keywords, seoScore, serpKeyword, googlePos, yandexPos)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    [USER_ID, a.url, a.title, '', 2000, a.title, '', a.title, '', '[]', 75, a.kw, a.g, a.y]
  );
  console.log(`Inserted: ${a.kw} | G:${a.g ?? '-'}`);
}

await conn.end();
console.log('\nДашборд обновлён!');
