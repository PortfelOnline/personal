import axios from 'axios';
import * as cheerio from 'cheerio';
import { HttpsProxyAgent } from 'https-proxy-agent';
import { fetchPageHtml } from './browser';
import { getRandomWorkingProxy, banProxy } from '../bots';

export interface SerpResult {
  position: number;
  title: string;
  url: string;
  domain: string;
  snippet: string;
}

export interface SerpData {
  engine: 'google' | 'yandex';
  keyword: string;
  results: SerpResult[];
  error?: string;
}

const BROWSER_HEADERS = {
  'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
  'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
  'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
  'Accept-Encoding': 'gzip, deflate, br',
  'Cache-Control': 'no-cache',
  'Connection': 'keep-alive',
  'Upgrade-Insecure-Requests': '1',
};

function extractDomain(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, '');
  } catch {
    return url;
  }
}

function cleanText(text: string): string {
  return text.replace(/\s+/g, ' ').trim();
}

async function fetchHtmlAxios(url: string, extraHeaders: Record<string, string> = {}): Promise<string> {
  const response = await axios.get(url, {
    headers: { ...BROWSER_HEADERS, ...extraHeaders },
    timeout: 15000,
    maxRedirects: 5,
    decompress: true,
    responseType: 'text',
  });
  return response.data as string;
}

async function fetchHtml(url: string): Promise<string> {
  try {
    return await fetchPageHtml(url, 1500);
  } catch (err: any) {
    console.warn('[SERP] Puppeteer failed, falling back to axios:', err?.message);
    return fetchHtmlAxios(url);
  }
}

function parseProxy(proxy: string): { host: string; port: number; username: string; password: string } | null {
  const m = proxy.match(/^([^:]+):([^@]+)@([^:]+):(\d+)$/);
  if (!m) return null;
  return { username: m[1], password: m[2], host: m[3], port: parseInt(m[4], 10) };
}

async function fetchHtmlViaProxy(url: string, proxy: string): Promise<string> {
  const p = parseProxy(proxy);
  if (!p) throw new Error('Invalid proxy format');
  const proxyUrl = `http://${p.username}:${p.password}@${p.host}:${p.port}`;
  const agent = new HttpsProxyAgent(proxyUrl);
  const response = await axios.get(url, {
    headers: BROWSER_HEADERS,
    timeout: 20000,
    maxRedirects: 5,
    decompress: true,
    responseType: 'text',
    proxy: false,
    httpsAgent: agent,
  });
  return response.data as string;
}

async function fetchSerpHtml(url: string, isCaptcha: (html: string) => boolean): Promise<string> {
  for (let i = 0; i < 3; i++) {
    const proxy = getRandomWorkingProxy();
    if (!proxy) break;
    try {
      const html = await fetchHtmlViaProxy(url, proxy);
      if (isCaptcha(html)) {
        banProxy(proxy);
        console.warn(`[SERP] CAPTCHA via proxy ${proxy.split('@')[1]} — banned, retrying`);
        continue;
      }
      return html;
    } catch (err: any) {
      console.warn(`[SERP] Proxy ${proxy.split('@')[1]} failed: ${err?.message}`);
    }
  }
  // No working proxies — fall back to direct request
  return fetchHtml(url);
}

const SERPAPI_KEY = process.env.SERPAPI_KEY;

async function fetchViaSerpApi(params: Record<string, string>): Promise<any> {
  if (!SERPAPI_KEY) throw new Error('SERPAPI_KEY not configured');
  const qs = new URLSearchParams({ ...params, api_key: SERPAPI_KEY, output: 'json' });
  const response = await axios.get(`https://serpapi.com/search?${qs}`, { timeout: 30000 });
  return response.data;
}

/**
 * Fetch Google search results via SerpAPI
 */
export async function fetchGoogleSerp(keyword: string): Promise<SerpData> {
  if (!SERPAPI_KEY) {
    return { engine: 'google', keyword, results: [], error: 'SERPAPI_KEY не настроен' };
  }
  try {
    const data = await fetchViaSerpApi({ engine: 'google', q: keyword, hl: 'ru', gl: 'ru', num: '50' });
    const organicResults: SerpResult[] = (data.organic_results || []).slice(0, 50).map((r: any, i: number) => ({
      position: r.position ?? i + 1,
      title: r.title ?? '',
      url: r.link ?? '',
      domain: extractDomain(r.link ?? ''),
      snippet: r.snippet ?? '',
    }));
    return { engine: 'google', keyword, results: organicResults };
  } catch (err: any) {
    console.warn('[SERP] SerpAPI Google error:', err?.message);
    return { engine: 'google', keyword, results: [], error: err?.message };
  }
}

/**
 * Fetch Yandex search results via SerpAPI
 */
export async function fetchYandexSerp(keyword: string): Promise<SerpData> {
  if (!SERPAPI_KEY) {
    return { engine: 'yandex', keyword, results: [], error: 'SERPAPI_KEY не настроен' };
  }
  try {
    const data = await fetchViaSerpApi({ engine: 'yandex', text: keyword, lr: '213', lang: 'ru', numdoc: '50' });
    const organicResults: SerpResult[] = (data.organic_results || []).slice(0, 50).map((r: any, i: number) => ({
      position: r.position ?? i + 1,
      title: r.title ?? '',
      url: r.link ?? '',
      domain: extractDomain(r.link ?? ''),
      snippet: r.snippet ?? '',
    }));
    return { engine: 'yandex', keyword, results: organicResults };
  } catch (err: any) {
    console.warn('[SERP] SerpAPI Yandex error:', err?.message);
    return { engine: 'yandex', keyword, results: [], error: err?.message };
  }
}
