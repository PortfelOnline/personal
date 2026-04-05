/**
 * Batch-20: 25 HIGH-priority articles (2026-04-04)
 */
import 'dotenv/config';
import { runBatchRewrite } from '../server/routers/articles';

const BASE = 'https://kadastrmap.info/kadastr/';
const SLUGS = [
  'mfts-poluchit-vypisku-iz-egrp',
  'mozhno-li-poluchit-kadastrovyj-pasport-v-mfts',
  'mozhno-li-sejchas-zakazat-kadastrovyj-pasport',
  'mozhno-li-srochno-oformit-kadastrovyj-pasport-na-kvartiru',
  'nalogovaya-uznat-sobstvennika-zemelnogo-uchastka',
  'nuzhen-li-kadastrovyj-pasport-dlya-prodazhi-kvartiry',
  'nuzhna-li-vypiska-iz-egrn-dlya-prodazhi-kvartiry',
  'pochemu-vypiska-iz-egrn-platnaya',
  'poluchit-kadastrovyj-pasport-na-dom',
  'poluchit-kadastrovyj-pasport-na-obekt-nedvizhimosti',
  'poluchit-kadastrovyj-pasport-onlajn',
  'poluchit-kadastrovyj-pasport-onlajn-v-rosreestre',
  'poluchit-spravku-o-kadastrovoj-stoimosti-kvartiry',
  'poluchit-spravku-vypisku-egrn',
  'poluchit-vypisku-egrn-po-kadastrovomu-nomeru',
  'poluchit-vypisku-iz-egrn-cherez-internet',
  'poluchit-vypisku-iz-egrp',
  'poluchit-vypisku-iz-egrp-onlajn',
  'poluchit-vypisku-iz-egrp-onlajn-rosreestr',
  'pri-registratsii-prav-vypiska-iz-egrn-ne-trebuetsya',
  'rasshirennaya-kadastrovaya-vypiska-na-zemelnyj-uchastok',
  'rasshirennaya-vypiska-egrn-na-kvartiru',
  'rosreestr-kadastrovaya-vypiska',
  'rosreestr-kadastrovyj-plan',
  'rosreestr-poluchit-vypisku-iz-egrp',
];

const URLS = SLUGS.map(s => `${BASE}${s}/`);
console.log(`[batch-20] Starting: ${URLS.length} articles`);
const start = Date.now();
await runBatchRewrite(1, URLS);
const mins = ((Date.now() - start) / 60000).toFixed(1);
console.log(`[batch-20] DONE in ${mins} min`);
