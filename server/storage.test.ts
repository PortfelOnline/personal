import { describe, expect, it, vi, beforeEach } from 'vitest';

const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

let mockForgeUrl = 'https://forge.example.com';
let mockForgeKey = 'test-key';

vi.mock('./_core/env', () => ({
  ENV: {
    get forgeApiUrl() { return mockForgeUrl; },
    get forgeApiKey() { return mockForgeKey; },
  },
}));

describe('storagePut', () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  it('uploads to correct URL with auth header', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ url: 'https://cdn.example.com/file.pdf' }),
    } as any);

    const { storagePut } = await import('./storage');
    const result = await storagePut('doc.pdf', Buffer.from('data'), 'application/pdf');

    expect(result).toEqual({ key: 'doc.pdf', url: 'https://cdn.example.com/file.pdf' });

    const [url, opts] = mockFetch.mock.calls[0] as [URL, RequestInit];
    expect(String(url)).toContain('/v1/storage/upload');
    expect(String(url)).toContain('path=doc.pdf');
    expect((opts.headers as Record<string, string>).Authorization).toBe('Bearer test-key');
  });

  it('normalizes leading slash in key', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ url: 'https://cdn.example.com/f' }),
    } as any);

    const { storagePut } = await import('./storage');
    await storagePut('/leading/file.pdf', 'data');
    const [url] = mockFetch.mock.calls[0] as [URL];
    expect(url.searchParams.get('path')).toBe('leading/file.pdf');
  });

  it('includes filename from key in FormData', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ url: 'https://cdn.example.com/img.png' }),
    } as any);

    const { storagePut } = await import('./storage');
    await storagePut('images/photo.png', 'data');

    const [, opts] = mockFetch.mock.calls[0] as [URL, RequestInit];
    expect(opts.body).toBeInstanceOf(FormData);
    const form = opts.body as FormData;
    expect(form.has('file')).toBe(true);
    const file = form.get('file') as File;
    expect(file.name).toBe('photo.png');
    expect(file.type).toBe('application/octet-stream');
  });

  it('throws on HTTP error', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 403,
      statusText: 'Forbidden',
      text: async () => 'Forbidden',
    } as any);

    const { storagePut } = await import('./storage');
    await expect(storagePut('x.pdf', 'data')).rejects.toThrow(/Storage upload failed.*403/);
  });

  it('throws when credentials are missing', async () => {
    mockForgeUrl = '';
    mockForgeKey = '';

    const { storagePut } = await import('./storage');
    await expect(storagePut('x.pdf', 'data')).rejects.toThrow('Storage proxy credentials missing');

    mockForgeUrl = 'https://forge.example.com';
    mockForgeKey = 'test-key';
  });
});

describe('storageGet', () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  it('returns download URL from API', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ url: 'https://cdn.example.com/dl/doc.pdf?token=abc' }),
    } as any);

    const { storageGet } = await import('./storage');
    const result = await storageGet('doc.pdf');

    expect(result).toEqual({ key: 'doc.pdf', url: 'https://cdn.example.com/dl/doc.pdf?token=abc' });

    const [url, opts] = mockFetch.mock.calls[0] as [URL, RequestInit];
    expect(String(url)).toContain('/v1/storage/downloadUrl');
    expect(String(url)).toContain('path=doc.pdf');
    expect((opts.headers as Record<string, string>).Authorization).toBe('Bearer test-key');
  });

  it('normalizes leading slash', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ url: 'https://cdn.example.com/dl' }),
    } as any);

    const { storageGet } = await import('./storage');
    await storageGet('/nested/file.txt');
    const [url] = mockFetch.mock.calls[0] as [URL];
    expect(url.searchParams.get('path')).toBe('nested/file.txt');
  });
});
