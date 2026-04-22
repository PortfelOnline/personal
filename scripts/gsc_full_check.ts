import { google } from 'googleapis';
const KEY_FILE = '/Users/evgenijgrudev/Downloads/curious-pointer-230707-16b0af3037fa.json';
const auth = new google.auth.GoogleAuth({ keyFile: KEY_FILE, scopes: ['https://www.googleapis.com/auth/webmasters.readonly'] });

async function main() {
  const sc = google.webmasters({ version: 'v3', auth });
  const site = 'sc-domain:kadastrmap.info';
  const end = '2026-04-05';
  const start = '2026-03-08';  // ~28 days

  // Топ-10 страниц
  const pages = await sc.searchanalytics.query({ siteUrl: site, requestBody: {
    startDate: start, endDate: end, dimensions: ['page'], rowLimit: 10,
    orderBy: [{ fieldName: 'clicks', sortOrder: 'DESCENDING' }],
  }});
  
  console.log('\n=== ТОП-10 страниц (клики) ===');
  const topPages = (pages.data.rows || []);
  for (const r of topPages) {
    const page = (r.keys?.[0]||'').replace('https://kadastrmap.info','');
    console.log(`clicks=${String(r.clicks).padStart(5)} impressions=${String(r.impressions).padStart(6)} pos=${String((r.position||0).toFixed(1)).padStart(5)} ctr=${((r.ctr||0)*100).toFixed(1)}%  ${page}`);
  }

  // Для топ-5 страниц — их ключевые запросы
  console.log('\n=== Запросы по топ-5 страницам ===');
  for (const r of topPages.slice(0, 5)) {
    const url = r.keys?.[0] || '';
    const page = url.replace('https://kadastrmap.info','');
    console.log(`\n--- ${page} ---`);
    const qr = await sc.searchanalytics.query({ siteUrl: site, requestBody: {
      startDate: start, endDate: end,
      dimensions: ['query'], dimensionFilterGroups: [{ filters: [{ dimension: 'page', operator: 'equals', expression: url }] }],
      rowLimit: 8, orderBy: [{ fieldName: 'impressions', sortOrder: 'DESCENDING' }],
    }});
    for (const q of (qr.data.rows || []).slice(0, 8)) {
      console.log(`  pos=${String((q.position||0).toFixed(1)).padStart(5)} clicks=${String(q.clicks).padStart(4)} imp=${String(q.impressions).padStart(5)}  ${q.keys?.[0]}`);
    }
  }

  // Запросы где позиция 4-20 (можно подтянуть)
  console.log('\n=== Запросы в позиции 4–20 (потенциал роста) ===');
  const all = await sc.searchanalytics.query({ siteUrl: site, requestBody: {
    startDate: start, endDate: end, dimensions: ['query', 'page'], rowLimit: 100,
    orderBy: [{ fieldName: 'impressions', sortOrder: 'DESCENDING' }],
  }});
  const opportunity = (all.data.rows||[]).filter(r => (r.position||0) >= 4 && (r.position||0) <= 20 && (r.impressions||0) > 50);
  for (const r of opportunity.slice(0, 20)) {
    const page = (r.keys?.[1]||'').replace('https://kadastrmap.info','');
    console.log(`  pos=${String((r.position||0).toFixed(1)).padStart(5)} imp=${String(r.impressions).padStart(5)} clicks=${String(r.clicks).padStart(4)}  ${r.keys?.[0]}  →  ${page}`);
  }
}
main().catch(console.error);
