import 'dotenv/config';
import axios from 'axios';

const KEY = process.env.YA_CLOUD_API_KEY;
const FOLDER = process.env.YA_CLOUD_FOLDER_ID;

// Test with groupsOnPage to get more results
const body = {
  folderId: FOLDER,
  query: { queryText: 'выписка ЕГРН онлайн', searchType: 'SEARCH_TYPE_RU' },
  region: '213',
  responseFormat: 'FORMAT_XML',
  groupSpec: { groupMode: 'GROUP_MODE_DEEP', groupsOnPage: 20, docsInGroup: 1 },
};

const resp = await axios.post('https://searchapi.api.cloud.yandex.net/v2/web/search', body, {
  headers: { Authorization: `Api-Key ${KEY}`, 'Content-Type': 'application/json' },
  timeout: 30000,
});

const xml = Buffer.from(resp.data.rawData, 'base64').toString('utf-8');

// Count results and find kadastrmap
const matches = [...xml.matchAll(/<url>(https?:\/\/[^<]+)<\/url>/g)];
console.log(`Total URLs: ${matches.length}`);
matches.forEach((m, i) => {
  const url = m[1];
  const domain = new URL(url).hostname.replace(/^www\./, '');
  const mark = domain.includes('kadastrmap') ? ' ← WE' : '';
  console.log(`  #${i+1} ${domain}${mark}`);
});
