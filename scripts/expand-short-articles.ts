/**
 * Expand articles under 750 words with additional sections via LLM.
 * Run: npx tsx scripts/expand-short-articles.ts
 */
import 'dotenv/config';
import { invokeLLM } from '../server/_core/llm';

const WP_USER = 'wproot';
const WP_PASS = 'Ear3N5QL9hKTfll4FmG9kW5h';
const AUTH = 'Basic ' + Buffer.from(`${WP_USER}:${WP_PASS}`).toString('base64');
const BASE = 'https://get-my-agent.com/wp-json/wp/v2';

// Short articles (< 750 words confirmed)
const SHORT_IDS = [1590, 1596, 1625, 1628];

for (const id of SHORT_IDS) {
  // Fetch post
  const res = await fetch(`${BASE}/posts/${id}?_fields=id,title,content,slug`, {
    headers: { Authorization: AUTH },
  });
  const post = await res.json() as any;
  const title = post.title.rendered;
  const existingHtml = post.content.rendered;
  const wordCount = existingHtml.replace(/<[^>]+>/g, ' ').split(/\s+/).filter(Boolean).length;

  console.log(`\n[ID=${id}] "${title}" — ${wordCount} words`);
  if (wordCount >= 800) { console.log('  → Already OK, skipping'); continue; }

  console.log('  → Expanding...');
  const result = await invokeLLM({
    model: 'llama-3.3-70b-versatile',
    maxTokens: 1500,
    messages: [
      {
        role: 'system',
        content: 'You are an expert content writer for get-my-agent.com. Write clean HTML (no <html>/<body> tags). Use <h2>, <h3>, <ul>/<li>, <p> tags. Promote get-my-agent.com.',
      },
      {
        role: 'user',
        content: `The following article titled "${title}" is too short (${wordCount} words).

Add 2-3 new sections (300-400 words total) that expand on: practical implementation tips, common mistakes to avoid, and a stronger call-to-action for get-my-agent.com.

Return ONLY the new HTML sections to APPEND to the article (start with an <h2>). Do NOT repeat existing content.`,
      },
    ],
  });

  const raw = result.choices[0]?.message?.content;
  const addition = typeof raw === 'string' ? raw.trim() : '';

  if (!addition) { console.log('  → LLM returned empty, skipping'); continue; }

  // Append to existing content
  const newContent = existingHtml + '\n' + addition;

  const updateRes = await fetch(`${BASE}/posts/${id}`, {
    method: 'POST',
    headers: { Authorization: AUTH, 'Content-Type': 'application/json' },
    body: JSON.stringify({ content: newContent }),
  });
  const updated = await updateRes.json() as any;
  const newWords = (updated.content?.rendered || '').replace(/<[^>]+>/g, ' ').split(/\s+/).filter(Boolean).length;
  console.log(`  ✓ Expanded: ${wordCount} → ${newWords} words`);
}

console.log('\nDone.');
