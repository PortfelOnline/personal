export function buildArticleToSocialPrompt(title: string, excerpt: string): string {
  return `You are a social media copywriter for get-my-agent.com — an AI agent SaaS for businesses.

Based on this blog article, create TWO social media posts:

Article title: "${title}"
Article excerpt: ${excerpt}

Return ONLY valid JSON (no markdown fences):
{
  "facebook": {
    "text": "Full Facebook post (150-300 words). Hook + value + soft CTA to read the article. Use line breaks for readability.",
    "hashtags": ["#GetMyAgent", "#AIAgent", "#BusinessAutomation"]
  },
  "instagram": {
    "caption": "Instagram caption (80-150 words). Punchy hook, 3-5 bullet points with emojis, CTA.",
    "hashtags": ["#GetMyAgent", "#AIAgent", "#SmallBusiness", "#Automation"]
  }
}`;
}

export function parseArticleToSocialResponse(raw: string): { facebook: string; ig: string; fbHashtags: string; igHashtags: string } {
  try {
    const json = JSON.parse(raw.replace(/^```json\s*|\s*```$/g, '').trim());
    return {
      facebook: json.facebook?.text ?? raw,
      ig: json.instagram?.caption ?? raw,
      fbHashtags: Array.isArray(json.facebook?.hashtags) ? json.facebook.hashtags.join(' ') : '#GetMyAgent #AIAgent',
      igHashtags: Array.isArray(json.instagram?.hashtags) ? json.instagram.hashtags.join(' ') : '#GetMyAgent #AIAgent',
    };
  } catch {
    return { facebook: raw, ig: raw, fbHashtags: '#GetMyAgent', igHashtags: '#GetMyAgent' };
  }
}
