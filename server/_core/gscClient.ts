/**
 * Google Search Console client for enriching article rewrites.
 * Uses service account key (same as analytics-mcp).
 */
import { google } from 'googleapis';
import { subDays, format } from 'date-fns';

const KEY_FILE =
  process.env.GSC_KEY_FILE ||
  '/Users/evgenijgrudev/Downloads/curious-pointer-230707-16b0af3037fa.json';

const DEFAULT_SITE = process.env.GSC_SITE_URL || 'sc-domain:kadastrmap.info';
const DEFAULT_SITE_BASE = 'https://kadastrmap.info';

function getService() {
  const creds = (google.auth as any).fromJSON
    ? null
    : null;
  const auth = new (google.auth.GoogleAuth)({
    keyFile: KEY_FILE,
    scopes: ['https://www.googleapis.com/auth/webmasters.readonly'],
  });
  return google.webmasters({ version: 'v3', auth });
}

export interface GscQuery {
  query: string;
  clicks: number;
  impressions: number;
  ctr: number;
  position: number;
}

/**
 * Get top GSC queries for a specific page URL.
 * Returns empty array on error (graceful fallback).
 */
export async function fetchGscPageQueries(
  pageUrl: string,
  days = 28,
  limit = 20,
): Promise<GscQuery[]> {
  try {
    const endDate = format(subDays(new Date(), 1), 'yyyy-MM-dd');
    const startDate = format(subDays(new Date(), days), 'yyyy-MM-dd');
    const fullUrl = pageUrl.startsWith('http') ? pageUrl : `${DEFAULT_SITE_BASE}${pageUrl}`;

    const sc = getService();
    const res = await sc.searchanalytics.query({
      siteUrl: DEFAULT_SITE,
      requestBody: {
        startDate,
        endDate,
        dimensions: ['query'],
        rowLimit: limit,
        orderBy: [{ fieldName: 'impressions', sortOrder: 'DESCENDING' }],
        dimensionFilterGroups: [{
          filters: [{
            dimension: 'page',
            operator: 'equals',
            expression: fullUrl,
          }],
        }],
      } as any,
    } as any);

    const rows = (res as any).data?.rows || [];
    return rows.map((r: any) => ({
      query: r.keys[0] as string,
      clicks: r.clicks as number,
      impressions: r.impressions as number,
      ctr: Math.round((r.ctr as number) * 1000) / 10,
      position: Math.round((r.position as number) * 10) / 10,
    }));
  } catch (err: any) {
    console.warn('[GSC] fetchGscPageQueries error:', err?.message);
    return [];
  }
}

/**
 * Format GSC queries as a prompt block for LLM.
 */
export function formatGscBlock(queries: GscQuery[]): string {
  if (!queries.length) return '';
  const lines = queries.slice(0, 15).map(
    q => `  - "${q.query}" (${q.impressions} показов, поз. ${q.position})`,
  );
  return `\nРЕАЛЬНЫЕ ПОИСКОВЫЕ ЗАПРОСЫ ЭТОЙ СТРАНИЦЫ (из Google Search Console):\n${lines.join('\n')}\nОптимизируй статью под эти запросы — используй их формулировки в заголовках и тексте.\n`;
}
