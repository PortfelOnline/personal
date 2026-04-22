export function getDefaultCatalogUrl(siteUrl: string): string {
  const base = siteUrl.replace(/\/$/, '');
  if (base.includes('kadastrmap')) return base + '/kadastr/';
  if (base.includes('get-my-agent')) return base + '/en/blog/';
  return base + '/';
}

export function getDefaultCtaUrl(siteUrl: string): string {
  const base = siteUrl.replace(/\/$/, '');
  if (base.includes('kadastrmap')) return base + '/spravki/';
  return base + '/';
}
