import 'dotenv/config';
import axios from 'axios';

const KEY = process.env.YA_CLOUD_API_KEY;
const FOLDER = process.env.YA_CLOUD_FOLDER_ID;
const ourDomain = 'kadastrmap.info';

// Test long-tail specific keywords that match our articles
const keywords = [
  'заказать справку об обременении недвижимости в москве',
  'кадастровый паспорт земельного участка образец',
  'выписка ЕГРН что показывает',
  'кадастровый номер объекта недвижимости',
];

for (const queryText of keywords) {
  const body = {
    folderId: FOLDER,
    query: { queryText, searchType: 'SEARCH_TYPE_RU' },
    region: '213',
    responseFormat: 'FORMAT_XML',
    groupSpec: { groupMode: 'GROUP_MODE_DEEP', groupsOnPage: 20, docsInGroup: 1 },
  };
  const resp = await axios.post('https://searchapi.api.cloud.yandex.net/v2/web/search', body, {
    headers: { Authorization: `Api-Key ${KEY}`, 'Content-Type': 'application/json' },
    timeout: 30000,
  });
  const xml = Buffer.from(resp.data.rawData, 'base64').toString('utf-8');
  const matches = [...xml.matchAll(/<url>(https?:\/\/[^<]+)<\/url>/g)];
  const ourIdx = matches.findIndex(m => m[1].includes(ourDomain));
  if (ourIdx >= 0) {
    console.log(`✅ "${queryText}"`);
    console.log(`   → kadastrmap.info at #${ourIdx + 1}: ${matches[ourIdx][1]}`);
  } else {
    const top3 = matches.slice(0,3).map(m => new URL(m[1]).hostname.replace(/^www\./,'')).join(', ');
    console.log(`❌ "${queryText}" — top3: ${top3}`);
  }
}
