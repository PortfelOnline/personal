import { describe, expect, it, vi, beforeEach } from 'vitest';

const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

describe('discoverUrls — auto URL discovery for social agent', () => {
  beforeEach(() => {
    mockFetch.mockReset();
    process.env.SERPAPI_KEY = 'test_serp_key';
  });

  it('discoverUrls is exported from social-agent', async () => {
    vi.resetModules();
    const mod = await import('./social-agent');
    expect(typeof (mod as any).discoverUrls).toBe('function');
  });

  it('discoverUrls fetches SerpAPI with industry query and returns URLs', async () => {
    vi.resetModules();

    // Mock Google Trends RSS
    mockFetch.mockImplementationOnce(async () => ({
      ok: true,
      text: async () => `<rss><channel>
        <item><title><![CDATA[Real estate Mumbai]]></title></item>
        <item><title><![CDATA[Property registration India]]></title></item>
      </channel></rss>`,
    }));

    // Mock SerpAPI response
    mockFetch.mockImplementationOnce(async () => ({
      ok: true,
      json: async () => ({
        organic_results: [
          { link: 'https://magicbricks.com/article1', title: 'Mumbai property guide' },
          { link: 'https://99acres.com/article2', title: 'Property investment tips' },
          { link: 'https://get-my-agent.com/features', title: 'AI Agent for real estate' },
        ],
      }),
    }));

    const { discoverUrls } = (await import('./social-agent')) as any;
    const urls = await discoverUrls({ industry: 'real_estate', geo: 'IN', maxUrls: 5 });

    expect(Array.isArray(urls)).toBe(true);
    expect(urls.length).toBeGreaterThan(0);
    expect(urls[0]).toHaveProperty('url');
    expect(urls[0]).toHaveProperty('title');

    // Must call SerpAPI
    const serpCall = mockFetch.mock.calls.find(c => String(c[0]).includes('serpapi'));
    expect(serpCall).toBeDefined();
  });
});
