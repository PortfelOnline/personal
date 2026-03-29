import axios from 'axios';

const SERPAPI_KEY = 'f520ac79a974bb4f9b9c6a45d7cea91466014142507aeb6c947dc9657cc0b752';
const TARGET = 'kadastrmap.info';

async function checkGoogle(keyword) {
  try {
    const qs = new URLSearchParams({ engine:'google', q:keyword, hl:'ru', gl:'ru', num:'50', api_key:SERPAPI_KEY, output:'json' });
    const r = await axios.get(`https://serpapi.com/search?${qs}`, { timeout:30000 });
    const results = r.data.organic_results || [];
    const pos = results.findIndex(x => (x.link||'').includes(TARGET));
    return pos >= 0 ? pos + 1 : null;
  } catch(e) { return null; }
}

const candidates = [
  [8363, 'справка из ЕГРН заказать онлайн', 'vypiska-iz-egrn-zakazat-onlajn'],
  [8305, 'справка из ЕГРН на квартиру', 'vypiska-iz-egrn-na-kvartiru'],
  [8473, 'справка из ЕГРН стоимость', 'vypiska-iz-egrn-stoimost'],
  [8496, 'справка из ЕГРН быстро', 'vypiska-iz-egrn-bystro'],
  [8384, 'справка из ЕГРН на недвижимость', 'vypiska-iz-egrn-na-nedvizhimost'],
  [8843, 'справка из ЕГРН на земельный участок', 'vypiska-iz-egrn-na-zemelnyj-uchastok'],
  [8397, 'справка из ЕГРН на землю', 'vypiska-iz-egrn-na-zemlyu'],
  [5593, 'наложен ли арест на квартиру', 'nalozhen-li-arest-na-kvartiru'],
  [5550, 'как проверить не в залоге ли квартира', 'kak-proverit-ne-v-zaloge-li-kvartira'],
  [5587, 'квартира под залогом выписка', 'kvartira-pod-zalogom-spravka'],
];

console.log('ID     | G# | Запрос');
console.log('-------|----|---------------------------------');
for (const [id, kw, slug] of candidates) {
  const g = await checkGoogle(kw);
  const gStr = g ? `#${g}` : '—';
  console.log(`${id}  | ${gStr.padEnd(4)}| ${kw}`);
  await new Promise(r => setTimeout(r, 400));
}
