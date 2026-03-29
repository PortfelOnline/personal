import { getDueScheduledPosts, updateContentPost } from './db';
import * as metaDb from './meta.db';
import * as metaApi from './_core/meta';

// Optimal posting hours per platform (IST)
const OPTIMAL_HOURS: Record<string, number[]> = {
  instagram: [8, 12, 18, 20],  // 8am, 12pm, 6pm, 8pm
  facebook:  [9, 13, 17, 20],  // 9am, 1pm, 5pm, 8pm
};

/**
 * Extract the ready-to-post text from a content post.
 * JSON-structured posts (carousel/reel/story) have a `caption` field.
 * Feed posts have hook + paragraphs + cta.
 * Falls back to raw content if parsing fails.
 */
function extractPublishText(content: string, hashtags: string | null): string {
  const sanitize = (s: string) =>
    s.replace(/"((?:[^"\\]|\\.)*)"/gs, (m) =>
      m.replace(/\n/g, '\\n').replace(/\r/g, '\\r').replace(/\t/g, '\\t')
    );

  try {
    const parsed = JSON.parse(sanitize(content));

    // Carousel / Reel / Story — use pre-built caption
    if (parsed.caption) {
      const base = parsed.caption;
      return hashtags ? `${base}\n\n${hashtags}` : base;
    }

    // Feed post — build from fields
    if (parsed.hook) {
      const parts: string[] = [parsed.hook];
      if (parsed.paragraphs?.length) parts.push(...parsed.paragraphs);
      if (parsed.cta) parts.push(parsed.cta);
      if (hashtags) parts.push(hashtags);
      return parts.join('\n\n');
    }
  } catch {
    // not JSON — fall through
  }

  // Plain text fallback
  return hashtags ? `${content}\n\n${hashtags}` : content;
}

async function publishPost(
  post: Awaited<ReturnType<typeof getDueScheduledPosts>>[number]
): Promise<void> {
  const accounts = await metaDb.getUserMetaAccounts(post.userId);
  const platformAccountType =
    post.platform === 'instagram' ? 'instagram_business' : 'facebook_page';
  const account = accounts.find(
    (a) => a.accountType === platformAccountType && a.isActive
  );

  if (!account || (post.platform !== 'instagram' && post.platform !== 'facebook')) {
    // WhatsApp/YouTube or no Meta account connected — just flip to published
    await updateContentPost(post.userId, post.id, {
      status: 'published',
      publishedAt: new Date(),
    });
    console.log(`[ContentScheduler] Marked post ${post.id} as published (no Meta account)`);
    return;
  }

  const caption = extractPublishText(post.content, post.hashtags ?? null);

  if (post.platform === 'instagram') {
    await metaApi.postToInstagram(
      account.accountId,
      account.accessToken,
      caption,
      post.mediaUrl ?? undefined
    );
  } else {
    await metaApi.postToFacebookPage(
      account.accountId,
      account.accessToken,
      caption,
      post.mediaUrl ?? undefined
    );
  }

  await updateContentPost(post.userId, post.id, {
    status: 'published',
    publishedAt: new Date(),
  });
  console.log(`[ContentScheduler] Published post ${post.id} → ${post.platform}`);
}

async function runScheduler() {
  try {
    const posts = await getDueScheduledPosts();
    if (posts.length === 0) return;

    console.log(`[ContentScheduler] Processing ${posts.length} due post(s)`);

    for (const post of posts) {
      try {
        await publishPost(post);
      } catch (err) {
        console.error(`[ContentScheduler] Failed to publish post ${post.id}:`, err);
        // Put back to draft so user can retry or reschedule
        await updateContentPost(post.userId, post.id, { status: 'draft' });
      }
    }
  } catch (err) {
    console.error('[ContentScheduler] Unexpected error:', err);
  }
}

export function initContentScheduler() {
  // Run once immediately on startup to catch any posts missed during downtime
  runScheduler();
  setInterval(() => runScheduler(), 60_000);
  console.log('[ContentScheduler] Started — checking every 60s');
}

/**
 * Returns the next optimal posting time for a given platform (IST).
 * Used by auto-generation to pre-schedule posts.
 */
export function nextOptimalTime(platform: string, afterDate = new Date()): Date {
  const hours = OPTIMAL_HOURS[platform] ?? [9, 18];
  const d = new Date(afterDate);
  // Convert to IST offset
  const istOffset = 5.5 * 60 * 60 * 1000;
  const istNow = new Date(d.getTime() + istOffset);
  const currentHour = istNow.getUTCHours();

  const next = hours.find(h => h > currentHour);
  if (next !== undefined) {
    // Same day, next slot
    istNow.setUTCHours(next, 0, 0, 0);
  } else {
    // Next day, first slot
    istNow.setUTCDate(istNow.getUTCDate() + 1);
    istNow.setUTCHours(hours[0], 0, 0, 0);
  }
  // Convert back to UTC
  return new Date(istNow.getTime() - istOffset);
}
