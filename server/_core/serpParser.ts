import axios from 'axios';
import * as cheerio from 'cheerio';
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
  const response = await axios.get(url, {
    headers: BROWSER_HEADERS,
    timeout: 20000,
    maxRedirects: 5,
    decompress: true,
    responseType: 'text',
    proxy: { protocol: 'http', host: p.host, port: p.port, auth: { username: p.username, password: p.password } },
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

/**
 * Parse Google search results
 */
export async function fetchGoogleSerp(keyword: string): Promise<SerpData> {
  const url = `https://www.google.ru/search?q=${encodeURIComponent(keyword)}&num=10&hl=ru&gl=ru`;

  const googleCaptcha = (h: string) =>
    h.includes('recaptcha') || h.includes('detected unusual traffic') || h.includes('captcha');

  let html: string;
  try {
    html = await fetchSerpHtml(url, googleCaptcha);
  } catch (error: any) {
    return { engine: 'google', keyword, results: [], error: `Ошибка загрузки: ${error?.message}` };
  }

  if (googleCaptcha(html)) {
    return { engine: 'google', keyword, results: [], error: 'Google заблокировал запрос (CAPTCHA). Все доступные прокси заблокированы.' };
  }

  const $ = cheerio.load(html);
  const results: SerpResult[] = [];

  // Strategy 1: data-async-context containers (modern Google)
  $('[data-async-context], [jscontroller][data-ved]').each((_, el) => {
    if (results.length >= 10) return;
    const $el = $(el as any);
    if ($el.find('[data-text-ad]').length > 0) return;
    const titleEl = $el.find('h3').first();
    const title = cleanText(titleEl.text());
    if (!title) return;
    const linkEl = $el.find('a[href^="http"], a[href^="/url"]').first();
    let href = linkEl.attr('href') || '';
    if (href.startsWith('/url?q=')) href = new URLSearchParams(href.slice(5)).get('q') || href;
    if (!href.startsWith('http') || href.includes('google')) return;
    const snippet = cleanText($el.find('.VwiC3b, .lEBKkf, [data-sncf] span').first().text());
    results.push({ position: results.length + 1, title, url: href, domain: extractDomain(href), snippet });
  });

  // Strategy 2: Standard .g containers
  if (results.length === 0) {
    $('div.g, div[data-sokoban-container]').each((_, el) => {
      if (results.length >= 10) return;
      const $el = $(el as any);
      if ($el.find('[data-text-ad]').length > 0) return;
      if ($el.closest('.ads-ad').length > 0) return;
      const title = cleanText($el.find('h3').first().text());
      if (!title) return;
      const linkEl = $el.find('a[href^="http"], a[href^="/url"]').first();
      let href = linkEl.attr('href') || '';
      if (href.startsWith('/url?q=')) href = new URLSearchParams(href.slice(5)).get('q') || href;
      if (!href.startsWith('http') || href.includes('google')) return;
      const snippet = cleanText($el.find('.VwiC3b, .s, [data-sncf] span, .st').first().text());
      results.push({ position: results.length + 1, title, url: href, domain: extractDomain(href), snippet });
    });
  }

  // Strategy 3: any a:has(h3) not inside ads
  if (results.length === 0) {
    $('a:has(h3)').each((_, el) => {
      if (results.length >= 10) return;
      const $el = $(el as any);
      if ($el.closest('[data-text-ad], .ads-ad').length > 0) return;
      const href = $el.attr('href') || '';
      if (!href.startsWith('http') || href.includes('google')) return;
      const title = cleanText($el.find('h3').text());
      if (!title) return;
      results.push({ position: results.length + 1, title, url: href, domain: extractDomain(href), snippet: '' });
    });
  }

  if (results.length === 0 && html.length < 5000) {
    return { engine: 'google', keyword, results: [], error: 'Google вернул пустой ответ (возможно заблокировал запрос)' };
  }

  return { engine: 'google', keyword, results };
}

/**
 * Parse Yandex search results
 */
export async function fetchYandexSerp(keyword: string): Promise<SerpData> {
  const url = `https://yandex.ru/search/?text=${encodeURIComponent(keyword)}&lr=213&numdoc=10`;

  const yandexCaptcha = (h: string) =>
    h.includes('showcaptcha') || h.includes('captcha') || h.includes('Проверка браузера');

  let html: string;
  try {
    html = await fetchSerpHtml(url, yandexCaptcha);
  } catch (error: any) {
    return { engine: 'yandex', keyword, results: [], error: `Ошибка загрузки: ${error?.message}` };
  }

  if (yandexCaptcha(html)) {
    return { engine: 'yandex', keyword, results: [], error: 'Яндекс заблокировал запрос (CAPTCHA). Все доступные прокси заблокированы.' };
  }

  const $ = cheerio.load(html);
  const results: SerpResult[] = [];

  // Yandex organic results — try multiple selectors
  const organicSelectors = [
    'li.serp-item article.organic',
    '.serp-item .organic',
    'article.organic',
    '.organic',
  ];

  let $items: cheerio.Cheerio<any> = $([]);
  for (const sel of organicSelectors) {
    const found = $(sel);
    if (found.length > 0) { $items = found; break; }
  }

  // Fallback: all serp-item
  if ($items.length === 0) {
    $items = $('li.serp-item');
  }

  $items.each((_, el) => {
    if (results.length >= 10) return;
    const $el = $(el as any);

    // Title — try multiple selectors
    const titleText = cleanText(
      $el.find('.OrganicTitle-LinkText, .organic__title-wrapper a, h2 a, .serp-item__title').first().text()
    );
    if (!titleText) return;

    // URL
    const linkEl = $el.find('.OrganicTitle-Link, .organic__title-wrapper a, h2 a').first();
    let href = linkEl.attr('href') || '';
    if (!href || (!href.startsWith('http') && !href.startsWith('//'))) return;
    if (href.startsWith('//')) href = 'https:' + href;
    if (href.includes('yandex.ru') && href.includes('/clck/')) {
      // Yandex click redirect — try to get real URL from data attribute
      href = linkEl.attr('data-url') || href;
    }

    // Snippet
    const snippet = cleanText(
      $el.find('.OrganicText, .organic__text, .serp-item__text, .organic__content-wrapper p').first().text()
    );

    results.push({
      position: results.length + 1,
      title: titleText,
      url: href,
      domain: extractDomain(href),
      snippet,
    });
  });

  return { engine: 'yandex', keyword, results };
}
