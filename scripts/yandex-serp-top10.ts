import 'dotenv/config';
import { fetchYandexSerp } from '../server/_core/serpParser';

const queries = [
  { slug: 'raspolozhenie-po-kadastrovomu-nomeru', q: 'найти участок по кадастровому номеру', gscPos: 8.2, impr: 6229 },
  { slug: 'kadastrovyj-plan-kvartiry-po-adresu', q: 'планировка квартиры по адресу', gscPos: 5.3, impr: 5132 },
  { slug: 'kadastrovaya-publichnaya-karta-so-sputnika', q: 'найти участок по кадастровому номеру со спутника', gscPos: 8.1, impr: 3157 },
  { slug: 'kadastrovyj-nomer-po-adresu-obekta-nedvizhimosti', q: 'кадастровый номер по адресу', gscPos: 15.1, impr: 1944 },
  { slug: 'ploshchad-po-kadastrovomu-nomeru', q: 'узнать площадь квартиры по кадастровому номеру', gscPos: 10.9, impr: 2016 },
  { slug: 'rosreestr-spravochnaya-informatsiya-po-obektam-nedvizhimosti-onlajn', q: 'справочная информация по объектам недвижимости росреестр', gscPos: 18.6, impr: 1010 },
  { slug: 'proverit-obremenenie-na-nedvizhimost', q: 'проверить обременение на недвижимость онлайн', gscPos: 17.5, impr: 870 },
  { slug: 'kadastrovye-koordinaty', q: 'кадастровая карта с координатами', gscPos: 12.7, impr: 974 },
  { slug: 'uznat-sobstvennika-zemelnogo-uchastka-po-kadastrovomu-nomeru', q: 'узнать собственника по кадастровому номеру', gscPos: 12.7, impr: 933 },
  { slug: 'kadastrovyj-plan-zemelnogo-uchastka', q: 'план земельного участка по кадастровому номеру', gscPos: 13.7, impr: 840 },
];

const domain = 'kadastrmap.info';

async function run() {
  for (const { slug, q, gscPos, impr } of queries) {
    try {
      const d = await fetchYandexSerp(q);
      const our = d.results.find(r => r.domain?.includes(domain));
      const yPos = our ? `#${our.position}` : `нет в топ-${d.results.length}`;
      const top3 = d.results.filter(r => !r.domain?.includes(domain)).slice(0, 3).map(r => `${r.domain}(#${r.position})`).join(', ');
      console.log(`\n📄 ${slug}`);
      console.log(`   Google: #${gscPos} | Яндекс: ${yPos} | impr=${impr}`);
      console.log(`   Запрос: "${q}"`);
      console.log(`   Конкуренты: ${top3}`);
    } catch(e: any) {
      console.log(`\n📄 ${slug}`);
      console.log(`   Google: #${gscPos} | impr=${impr}`);
      console.log(`   Запрос: "${q}"`);
      console.log(`   Яндекс: ERR ${e.message?.slice(0,50)}`);
    }
    await new Promise(r => setTimeout(r, 2500));
  }
}

run().catch(e => { console.error(e); process.exit(1); });
