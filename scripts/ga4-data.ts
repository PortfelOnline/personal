import { google } from 'googleapis';

const KEY_FILE = '/Users/evgenijgrudev/Downloads/curious-pointer-230707-16b0af3037fa.json';
const PROPERTY_ID = '378244966'; // KadastrMap.info

const auth = new google.auth.GoogleAuth({
  keyFile: KEY_FILE,
  scopes: ['https://www.googleapis.com/auth/analytics.readonly'],
});

async function main() {
  const data = google.analyticsdata({ version: 'v1beta', auth });

  // Трафик за 28 дней по каналам
  console.log('=== GA4: Сессии по каналам (28 дней) ===');
  const channels = await data.properties.runReport({
    property: `properties/${PROPERTY_ID}`,
    requestBody: {
      dateRanges: [{ startDate: '28daysAgo', endDate: 'yesterday' }],
      dimensions: [{ name: 'sessionDefaultChannelGroup' }],
      metrics: [{ name: 'sessions' }, { name: 'engagementRate' }, { name: 'conversions' }],
      orderBys: [{ metric: { metricName: 'sessions' }, desc: true }],
    },
  });
  for (const r of channels.data.rows || []) {
    const ch = (r.dimensionValues?.[0].value || '').padEnd(30);
    const s = r.metricValues?.[0].value;
    const e = parseFloat(r.metricValues?.[1].value || '0').toFixed(2);
    console.log(`${ch} sessions=${s}  engRate=${e}`);
  }

  // Топ страниц Organic Search
  console.log('\n=== GA4: Топ-20 страниц (Organic Search, 28 дней) ===');
  const pages = await data.properties.runReport({
    property: `properties/${PROPERTY_ID}`,
    requestBody: {
      dateRanges: [{ startDate: '28daysAgo', endDate: 'yesterday' }],
      dimensions: [{ name: 'pagePath' }],
      metrics: [{ name: 'sessions' }, { name: 'screenPageViews' }, { name: 'bounceRate' }],
      dimensionFilter: {
        filter: {
          fieldName: 'sessionDefaultChannelGroup',
          stringFilter: { value: 'Organic Search', matchType: 'EXACT' },
        },
      },
      orderBys: [{ metric: { metricName: 'sessions' }, desc: true }],
      limit: 20,
    },
  });
  for (const r of pages.data.rows || []) {
    const path = (r.dimensionValues?.[0].value || '');
    console.log(`sessions=${String(r.metricValues?.[0].value).padStart(5)}  views=${String(r.metricValues?.[1].value).padStart(5)}  bounce=${parseFloat(r.metricValues?.[2].value||'0').toFixed(2)}  ${path}`);
  }

  // Динамика по неделям (90 дней) — все сессии
  console.log('\n=== GA4: Динамика (по неделям, 90 дней) ===');
  const weekly = await data.properties.runReport({
    property: `properties/${PROPERTY_ID}`,
    requestBody: {
      dateRanges: [{ startDate: '90daysAgo', endDate: 'yesterday' }],
      dimensions: [{ name: 'yearWeek' }],
      metrics: [{ name: 'sessions' }],
      orderBys: [{ dimension: { dimensionName: 'yearWeek' }, desc: false }],
    },
  });
  for (const r of weekly.data.rows || []) {
    const yw = r.dimensionValues?.[0].value || '';
    const wkStr = `${yw.slice(0,4)}-w${yw.slice(4)}`;
    console.log(`${wkStr}  sessions=${r.metricValues?.[0].value}`);
  }
}
main().catch(console.error);
