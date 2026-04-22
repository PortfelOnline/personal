import { readFileSync } from "fs";
import { resolve } from "path";

async function main() {
  const raw = [".env.local", ".env"].flatMap(f => {
    try { return readFileSync(resolve(process.cwd(), f), "utf-8").split("\n"); } catch { return []; }
  });
  const env: Record<string, string> = {};
  for (const line of raw) {
    const m = line.match(/^([A-Z_][A-Z0-9_]*)=(.*)$/);
    if (m) env[m[1]] = m[2].replace(/^['"]|['"]$/g, "");
  }
  process.env.DATABASE_URL = process.env.DATABASE_URL ?? env["DATABASE_URL"];

  const { getFirstPending, getBacklinkPost } = await import("../server/backlinks.db");
  const { publishPost } = await import("../server/publishers/pub-index");

  const post = await getFirstPending("dzen");
  if (!post) { console.log("No pending dzen posts"); return; }

  console.log(`Publishing post #${post.id}: "${post.title?.substring(0, 70)}"`);
  console.log(`Target: https://kadastrmap.info${post.targetUrl}`);
  console.log(`Article: ${post.article?.length ?? 0} chars`);

  try {
    await publishPost(post);
    const updated = await getBacklinkPost(post.id);
    console.log(`\n✅ Published! Status: ${updated?.status}`);
    console.log(`   URL: ${updated?.publishedUrl}`);
  } catch (err: any) {
    console.error(`\n❌ FAILED: ${err.message}`);
    console.log(`   Screenshot: /tmp/backlinks-error-dzen-*.png`);
  }
}

main().catch(console.error);
