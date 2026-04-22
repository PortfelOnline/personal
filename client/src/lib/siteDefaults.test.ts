import { describe, it, expect } from 'vitest';
import { getDefaultCatalogUrl, getDefaultCtaUrl } from './siteDefaults';

describe('getDefaultCatalogUrl', () => {
  it('appends /kadastr/ for kadastrmap domains', () => {
    expect(getDefaultCatalogUrl('https://kadastrmap.info')).toBe('https://kadastrmap.info/kadastr/');
  });

  it('returns siteUrl with trailing slash for unknown domains', () => {
    expect(getDefaultCatalogUrl('https://example.com')).toBe('https://example.com/');
  });
});

describe('getDefaultCtaUrl', () => {
  it('appends /spravki/ for kadastrmap domains', () => {
    expect(getDefaultCtaUrl('https://kadastrmap.info')).toBe('https://kadastrmap.info/spravki/');
  });
});

describe('getDefaultCatalogUrl for get-my-agent', () => {
  it('appends /en/blog/ for get-my-agent domains', () => {
    expect(getDefaultCatalogUrl('https://get-my-agent.com')).toBe('https://get-my-agent.com/en/blog/');
  });
});
