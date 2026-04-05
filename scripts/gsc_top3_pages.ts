import 'dotenv/config';
import { google } from 'googleapis';

const KEY_FILE = '/Users/evgenijgrudev/Downloads/curious-pointer-230707-16b0af3037fa.json';
const auth = new google.auth.GoogleAuth({ keyFile: KEY_FILE, scopes: ['https://www.googleapis.com/auth/webmasters.readonly'] });
const sc = google.webmasters({ version: 'v3', auth });

const queries = [
  'планировка квартиры по адресу',
  'план квартиры по адресу',
  'найти участок по кадастровому номеру со спутника',
];

for (const query of queries) {
  console.log(`\n=== "${query}" ===`);
  try {
    const res = await sc.searchanalytics.query({
      siteUrl: 'sc-domain:kadastrmap.info',
      requestBody: {
        startDate: '2026-03-07',
        endDate: '2026-04-03',
        dimensions: ['query', 'page'],
        dimensionFilterGroups: [{
          filters: [{ dimension: 'query', operator: 'equals', expression: query }]
        }],
        rowLimit: 5,
        orderBy: [{ fieldName: 'clicks', sortOrder: 'DESCENDING' }],
      },
    });
    for (const r of (res.data.rows || [])) {
      console.log(`  pos=${r.position?.toFixed(1).padStart(5)}  clicks=${String(r.clicks).padStart(4)}  ${r.keys?.[1]}`);
    }
  } catch(e: any) { console.log('Error:', e.message); }
}

// Also get top 10 queries near position 3-10 (best improvement potential)
console.log('\n\n=== Запросы позиция 3-10 (потенциал роста в топ-3) ===');
const res2 = await sc.searchanalytics.query({
  siteUrl: 'sc-domain:kadastrmap.info',
  requestBody: {
    startDate: '2026-03-07',
    endDate: '2026-04-03',
    dimensions: ['query', 'page'],
    rowLimit: 200,
    orderBy: [{ fieldName: 'impressions', sortOrder: 'DESCENDING' }],
  },
});
const rows = (res2.data.rows || [])
  .filter(r => (r.position || 0) >= 3.5 && (r.position || 0) <= 10)
  .sort((a, b) => (b.impressions || 0) - (a.impressions || 0))
  .slice(0, 10);
for (const r of rows) {
  console.log(`  pos=${r.position?.toFixed(1).padStart(5)}  imp=${String(r.impressions).padStart(5)}  clicks=${String(r.clicks).padStart(4)}  ${r.keys?.[0]}`);
  console.log(`    └─ ${r.keys?.[1]}`);
}
