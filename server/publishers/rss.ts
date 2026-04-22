import type { BacklinkPost } from "../../drizzle/schema";

function escXml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

export function buildRssFeed(posts: BacklinkPost[]): string {
  const items = posts
    .filter(p => p.publishedUrl && p.publishedAt)
    .map(p => `    <item>
      <title>${escXml(p.title ?? "")}</title>
      <link>${escXml(p.publishedUrl!)}</link>
      <description>${escXml((p.article ?? "").substring(0, 500))}</description>
      <pubDate>${p.publishedAt!.toUTCString()}</pubDate>
      <guid>${escXml(p.publishedUrl!)}</guid>
    </item>`)
    .join("\n");

  return `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>kadastrmap.info — Кадастр и недвижимость</title>
    <link>https://kadastrmap.info</link>
    <description>Полезные статьи о кадастре и недвижимости</description>
    <language>ru</language>
${items}
  </channel>
</rss>`;
}
