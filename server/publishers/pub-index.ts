import { getFirstPending, updateBacklinkPost, insertBacklinkPost, getAllBacklinkPosts } from "../backlinks.db";
import { generateDzenArticle, generateSparkArticle, generateKwAnswer, PRIORITY_PAGES, pickNextPage } from "./content-generator";
import { publishToDzen } from "./dzen";
import { publishToSpark } from "./spark";
import { publishToKw } from "./kw";
import type { BacklinkPost } from "../../drizzle/schema";

export type Platform = "dzen" | "spark" | "kw";

export async function generateAndQueue(platform: Platform, targetUrl?: string): Promise<number> {
  const all           = await getAllBacklinkPosts();
  const platformCount = all.filter(p => p.platform === platform).length;

  let page = pickNextPage(platformCount);
  if (targetUrl) {
    const found = PRIORITY_PAGES.find(p => p.url === targetUrl);
    if (found) page = found;
  }

  let title:   string;
  let article: string;

  if (platform === "dzen") {
    const r = await generateDzenArticle(page.url, page.anchor);
    title = r.title; article = r.article;
  } else if (platform === "spark") {
    const r = await generateSparkArticle(page.url, page.anchor);
    title = r.title; article = r.article;
  } else {
    const r = await generateKwAnswer(page.url, page.anchor);
    title = r.question; article = r.article;
  }

  return insertBacklinkPost({ platform, targetUrl: page.url, anchorText: page.anchor, title, article, status: "pending" });
}

export async function publishPost(post: BacklinkPost): Promise<void> {
  await updateBacklinkPost(post.id, { status: "publishing" });
  try {
    let publishedUrl: string;
    if (post.platform === "dzen")        publishedUrl = await publishToDzen(post);
    else if (post.platform === "spark")  publishedUrl = await publishToSpark(post);
    else                                 publishedUrl = await publishToKw(post);

    await updateBacklinkPost(post.id, { status: "published", publishedUrl, publishedAt: new Date() });
    console.log(`[Backlinks] Published ${post.platform} id=${post.id} -> ${publishedUrl}`);
  } catch (err: any) {
    await updateBacklinkPost(post.id, { status: "failed", errorMsg: err.message ?? String(err) });
    console.error(`[Backlinks] FAILED ${post.platform} id=${post.id}:`, err.message);
    throw err;
  }
}

export async function publishNext(platform: Platform): Promise<void> {
  const post = await getFirstPending(platform);
  if (!post) { console.log(`[Backlinks] No pending posts for ${platform}`); return; }
  await publishPost(post);
}
