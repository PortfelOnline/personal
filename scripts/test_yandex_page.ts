import 'dotenv/config';
import axios from 'axios';

const KEY = process.env.YA_CLOUD_API_KEY;
const FOLDER = process.env.YA_CLOUD_FOLDER_ID;

const body = {
  folderId: FOLDER,
  query: { queryText: 'кадастровый паспорт', searchType: 'SEARCH_TYPE_RU' },
  region: '213',
  responseFormat: 'FORMAT_XML',
  groupSpec: { groupMode: 'GROUP_MODE_DEEP', groupsOnPage: 50, docsInGroup: 1 },
};
const resp = await axios.post('https://searchapi.api.cloud.yandex.net/v2/web/search', body, {
  headers: { Authorization: `Api-Key ${KEY}`, 'Content-Type': 'application/json' },
  timeout: 30000,
});
const xml = Buffer.from(resp.data.rawData, 'base64').toString('utf-8');
// Check what groupings says
const groupingsMatch = xml.match(/groups-on-page="(\d+)"/);
const pageMatch = xml.match(/<page first="(\d+)" last="(\d+)">/);
const groups = [...xml.matchAll(/<group>/g)].length;
console.log('groups-on-page in XML:', groupingsMatch?.[1]);
console.log('page first/last:', pageMatch?.[1], pageMatch?.[2]);
console.log('actual <group> count:', groups);
