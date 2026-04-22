import 'dotenv/config';
import { fetchYandexSerp } from '../server/_core/serpParser';

const queries = [
  'кадастровый паспорт',
  'кадастровый номер по адресу',
  'выписка из ЕГРН',
  'планировка квартиры по адресу',
  'найти участок по кадастровому номеру',
  'площадь квартиры по кадастровому номеру',
  'кадастровая карта со спутника',
  'узнать собственника квартиры',
];

const domain = 'kadastrmap.info';
for (const q of queries) {
  try {
    const d = await fetchYandexSerp(q);
    const our = d.results.find(r => r.domain?.includes(domain));
    const pos = our ? `#${our.position}` : `нет в топ-${d.results.length}`;
    const top3 = d.results.filter(r => !r.domain?.includes(domain)).slice(0, 3)
      .map(r => r.domain).join(', ');
    console.log(`${pos.padEnd(12)} "${q}"`);
    if (!our) console.log(`            конкуренты: ${top3}`);
  } catch(e: any) {
    console.log(`ERR          "${q}": ${e.message?.slice(0,50)}`);
  }
}
