import { google } from 'googleapis';

const KEY_FILE = '/Users/evgenijgrudev/Downloads/curious-pointer-230707-16b0af3037fa.json';
const auth = new google.auth.GoogleAuth({
  keyFile: KEY_FILE,
  scopes: [
    'https://www.googleapis.com/auth/webmasters.readonly',
    'https://www.googleapis.com/auth/analytics.readonly',
  ],
});

async function main() {
  // ---- Список GA4 свойств ----
  const admin = google.analyticsadmin({ version: 'v1beta', auth });
  console.log('=== GA4 Properties ===');
  try {
    const props = await admin.properties.list({ filter: 'parent:accounts/83931097' });
    console.log(JSON.stringify(props.data, null, 2));
  } catch(e: any) { console.log('GA props error:', e.message); }

  // ---- GSC: топ запросов за последние 28 дней ----
  const sc = google.webmasters({ version: 'v3', auth });
  console.log('\n=== GSC: Топ-30 запросов (28 дней) ===');
  try {
    const res = await sc.searchanalytics.query({
      siteUrl: 'sc-domain:kadastrmap.info',
      requestBody: {
        startDate: '2026-03-07',
        endDate: '2026-04-03',
        dimensions: ['query'],
        rowLimit: 30,
        orderBy: [{ fieldName: 'clicks', sortOrder: 'DESCENDING' }],
      },
    });
    const rows = res.data.rows || [];
    for (const r of rows) {
      console.log(`clicks=${String(r.clicks).padStart(5)}  pos=${String((r.position||0).toFixed(1)).padStart(5)}  ${r.keys?.[0]}`);
    }
    console.log(`\nТотал показов/кликов: ${rows.reduce((s,r)=>s+(r.impressions||0),0)} / ${rows.reduce((s,r)=>s+(r.clicks||0),0)}`);
  } catch(e: any) { console.log('GSC error:', e.message); }

  // ---- GSC: статистика по страницам ----
  console.log('\n=== GSC: Топ-20 страниц по кликам (28 дней) ===');
  try {
    const res = await sc.searchanalytics.query({
      siteUrl: 'sc-domain:kadastrmap.info',
      requestBody: {
        startDate: '2026-03-07',
        endDate: '2026-04-03',
        dimensions: ['page'],
        rowLimit: 20,
        orderBy: [{ fieldName: 'clicks', sortOrder: 'DESCENDING' }],
      },
    });
    const rows = res.data.rows || [];
    for (const r of rows) {
      const page = (r.keys?.[0] || '').replace('https://kadastrmap.info', '');
      console.log(`clicks=${String(r.clicks).padStart(5)}  pos=${String((r.position||0).toFixed(1)).padStart(5)}  ${page}`);
    }
  } catch(e: any) { console.log('GSC pages error:', e.message); }
}
main();
