import 'dotenv/config';
import axios from 'axios';

const KEY = process.env.YA_CLOUD_API_KEY;
const FOLDER = process.env.YA_CLOUD_FOLDER_ID;
const ourDomain = 'kadastrmap.info';

// Use exact title from the etalon article
const keywords = [
  'справка об обременении недвижимости москва пошаговое руководство',
  'kadastrmap выписка ЕГРН',
  'kadastrmap.info',
  'кадастровая карта кадастровый номер kadastrmap',
];

for (const queryText of keywords) {
  const body = {
    folderId: FOLDER,
    query: { queryText, searchType: 'SEARCH_TYPE_RU' },
    region: '213',
    responseFormat: 'FORMAT_XML',
    groupSpec: { groupMode: 'GROUP_MODE_DEEP', groupsOnPage: 10, docsInGroup: 1 },
  };
  try {
    const resp = await axios.post('https://searchapi.api.cloud.yandex.net/v2/web/search', body, {
      headers: { Authorization: `Api-Key ${KEY}`, 'Content-Type': 'application/json' },
      timeout: 30000,
    });
    const xml = Buffer.from(resp.data.rawData, 'base64').toString('utf-8');
    const matches = [...xml.matchAll(/<url>(https?:\/\/[^<]+)<\/url>/g)];
    const ourIdx = matches.findIndex(m => m[1].includes(ourDomain));
    if (ourIdx >= 0) {
      console.log(`✅ "${queryText}" → #${ourIdx + 1}`);
      console.log(`   ${matches[ourIdx][1]}`);
    } else {
      console.log(`❌ "${queryText}" → top: ${matches.slice(0,3).map(m => {
        try { return new URL(m[1]).hostname.replace(/^www\./, ''); } catch { return m[1]; }
      }).join(', ')}`);
    }
  } catch (e: any) {
    console.log(`ERROR "${queryText}": ${e.message}`);
  }
}
