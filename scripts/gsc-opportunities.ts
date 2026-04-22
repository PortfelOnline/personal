/**
 * Find top-10 most promising articles:
 * High impressions (demand exists) + position 5-20 (can reach top-3)
 * + fetch top-3 competitor domains per page
 */
import 'dotenv/config';
import { google } from 'googleapis';
import { fetchGoogleSerp } from '../server/_core/serpParser';

const GSC_SITE = process.env.GSC_SITE_URL ?? 'sc-domain:kadastrmap.info';
const KEY_FILE = process.env.GSC_KEY_FILE ?? '/Users/evgenijgrudev/Downloads/curious-pointer-230707-16b0af3037fa.json';

async function getGscClient() {
  const auth = new google.auth.GoogleAuth({ keyFile: KEY_FILE, scopes: ['https://www.googleapis.com/auth/webmasters.readonly'] });
  return google.searchconsole({ version: 'v1', auth });
}

async function main() {
  const gsc = await getGscClient();

  // Get pages by impressions (last 28 days)
  const pagesResp = await gsc.searchanalytics.query({
    siteUrl: GSC_SITE,
    requestBody: {
      startDate: '2026-03-09', endDate: '2026-04-06',
      dimensions: ['page'],
      rowLimit: 200,
      dimensionFilterGroups: [{
        filters: [{ dimension: 'page', operator: 'contains', expression: '/kadastr/' }]
      }],
    },
  });

  const pages = (pagesResp.data.rows ?? [])
    .filter(r => {
      const pos = r.position ?? 0;
      return pos >= 4 && pos <= 25 && (r.impressions ?? 0) >= 100;
    })
    .sort((a, b) => {
      // Score: impressions * potential_gain (higher pos = more room to grow)
      const scoreA = (a.impressions ?? 0) * Math.log(a.position ?? 1);
      const scoreB = (b.impressions ?? 0) * Math.log(b.position ?? 1);
      return scoreB - scoreA;
    })
    .slice(0, 15);

  console.log('\n=== ТОП-15 перспективных страниц (impressions × gap) ===\n');
  for (const p of pages) {
    const slug = (p.keys?.[0] ?? '').replace('https://kadastrmap.info', '');
    console.log(
      `pos=${String((p.position ?? 0).toFixed(1)).padStart(5)}  ` +
      `impr=${String(p.impressions ?? 0).padStart(6)}  ` +
      `clicks=${String(p.clicks ?? 0).padStart(5)}  ` +
      `ctr=${((p.ctr ?? 0) * 100).toFixed(1).padStart(4)}%  ${slug}`
    );
  }

  // For top-10, get their main query and check competitors
  const top10 = pages.slice(0, 10);
  console.log('\n=== Конкуренты по топ-10 ===\n');

  for (const p of top10) {
    const pageUrl = p.keys?.[0] ?? '';
    const slug = pageUrl.replace('https://kadastrmap.info', '');

    // Get best query for this page
    const qResp = await gsc.searchanalytics.query({
      siteUrl: GSC_SITE,
      requestBody: {
        startDate: '2026-03-09', endDate: '2026-04-06',
        dimensions: ['query'],
        rowLimit: 1,
        dimensionFilterGroups: [{ filters: [{ dimension: 'page', operator: 'equals', expression: pageUrl }] }],
      },
    });
    const topQuery = qResp.data.rows?.[0]?.keys?.[0] ?? '';

    console.log(`\n📄 ${slug}`);
    console.log(`   pos=${p.position?.toFixed(1)} | impr=${p.impressions} | query="${topQuery}"`);

    if (!topQuery) continue;

    try {
      const serp = await fetchGoogleSerp(topQuery);
      const competitors = serp.results
        .filter(r => !r.domain?.includes('kadastrmap'))
        .slice(0, 3)
        .map((r, i) => `  ${i + 1}. ${r.domain} (pos ${r.position})`);
      if (competitors.length) console.log('   Конкуренты:\n' + competitors.join('\n'));

      const ourPos = serp.results.find(r => r.domain?.includes('kadastrmap'));
      if (ourPos) console.log(`   Наша позиция в Google SERP: #${ourPos.position}`);
    } catch (e: any) {
      console.log(`   SERP error: ${e.message?.slice(0, 50)}`);
    }

    await new Promise(r => setTimeout(r, 1500));
  }
}

main().catch(e => { console.error(e); process.exit(1); });
