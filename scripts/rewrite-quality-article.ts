/**
 * Rewrite a low-quality article using a two-stage pipeline:
 *   Stage 1: SerpAPI Google Search → real facts, stats, snippets about AI agents
 *   Stage 2: Groq llama-3.3-70b → write 2000+ word SEO article using those facts
 *
 * Then update WordPress via REST API (JSON — no macOS SSL issue).
 * Image: Flux-generated locally, rsync + PHP upload instructions printed.
 *
 * Run: npx tsx scripts/rewrite-quality-article.ts
 */
import 'dotenv/config';
import { invokeLLM } from '../server/_core/llm';
import { generateDallEImage } from '../server/_core/imageGen';
import { writeFileSync, readFileSync } from 'fs';

const POST_ID = 1505;
const POST_TITLE = 'What Is an AI Agent for Your Website? (Complete Guide 2025)';

const AUTH = 'Basic ' + Buffer.from('wproot:Ear3N5QL9hKTfll4FmG9kW5h').toString('base64');
const BASE = 'https://get-my-agent.com/wp-json/wp/v2';
const SERPAPI_KEY = process.env.SERPAPI_KEY!;

// ─── Stage 1: Research via SerpAPI ───────────────────────────────────────────

async function researchTopic(): Promise<string> {
  console.log('  → Stage 1: Researching via SerpAPI...');

  const queries = [
    'AI agent for website benefits statistics 2025',
    'AI chatbot vs AI agent difference real estate website',
    'website AI agent lead generation conversion rate statistics',
  ];

  const snippets: string[] = [];

  for (const q of queries) {
    const url = `https://serpapi.com/search.json?q=${encodeURIComponent(q)}&api_key=${SERPAPI_KEY}&num=5&gl=us&hl=en`;
    const res = await fetch(url);
    if (!res.ok) { console.warn(`  SerpAPI ${res.status} for: ${q}`); continue; }
    const data = await res.json() as any;

    const organic: any[] = data.organic_results ?? [];
    for (const r of organic.slice(0, 4)) {
      const snippet = r.snippet ?? r.rich_snippet?.top?.extensions?.join(' ') ?? '';
      if (snippet) snippets.push(`[${r.title}] ${snippet}`);
    }

    // Also grab answer box if present
    const ab = data.answer_box;
    if (ab?.snippet) snippets.push(`[Answer Box] ${ab.snippet}`);
    if (ab?.answer) snippets.push(`[Answer Box] ${ab.answer}`);
  }

  const brief = snippets.slice(0, 20).join('\n\n');
  console.log(`  → Research: ${snippets.length} snippets, ${brief.length} chars`);
  return brief;
}

// ─── Stage 2: Write the full article with Groq ───────────────────────────────

async function writeArticle(researchBrief: string): Promise<{ html: string; excerpt: string }> {
  console.log('  → Stage 2: Writing 2000+ word article with Groq llama-3.3-70b...');

  const result = await invokeLLM({
    model: 'llama-3.3-70b-versatile',
    maxTokens: 4096,
    messages: [
      {
        role: 'system',
        content: `You are an expert SEO content writer for get-my-agent.com — an AI assistant platform for real estate agents. Write fluent, authoritative, engaging English. Use specific statistics and concrete examples. Never use filler phrases like "In today's digital landscape" or "In conclusion".`,
      },
      {
        role: 'user',
        content: `Write a comprehensive, high-quality blog article for real estate agents and business owners.

TITLE: ${POST_TITLE}

RESEARCH FACTS (incorporate naturally — use the specific stats and facts):
${researchBrief}

REQUIREMENTS:
- 2000–2500 words total
- Professional, authoritative tone — real estate niche
- Use specific statistics from the research facts above
- Mention get-my-agent.com naturally 3–4 times as THE solution for real estate agents
- Include a direct link to https://get-my-agent.com in the CTA

STRUCTURE (use exactly these H2 sections):
1. What Is an AI Agent for a Website? (explain clearly, differentiate from basic chatbots)
2. AI Agent vs. Traditional Chatbot: Key Differences (comparison table in HTML <table>)
3. How AI Agents Generate More Leads, 24/7 (specific conversion stats, examples)
4. Top Use Cases for Real Estate Agents (lead qualification, appointment booking, FAQ, follow-up)
5. How to Set Up an AI Agent on Your Website — Step by Step
6. FAQ (use <details><summary>Question?</summary>Answer</details> — minimum 8 questions)
7. Conclusion with strong CTA paragraph

HTML RULES:
- Use <h2> for main sections, <h3> for subsections
- Use <ul><li> for feature/benefit lists
- Use <strong> for key terms and stats
- Use <p> for all paragraphs
- The comparison table: <table><thead><tr><th>Feature</th><th>Traditional Chatbot</th><th>AI Agent</th></tr></thead><tbody>...</tbody></table>
- FAQ: <details><summary>Question text?</summary><p>Answer text.</p></details>

OUTPUT FORMAT:
EXCERPT: [150-character meta description — include "AI agent" and "real estate"]
---HTML---
[full article HTML]`,
      },
    ],
  });

  const raw = result.choices[0]?.message?.content;
  const text = typeof raw === 'string' ? raw : JSON.stringify(raw);

  const excerptMatch = text.match(/EXCERPT:\s*(.+)/);
  const excerpt = excerptMatch ? excerptMatch[1].trim().slice(0, 165) : POST_TITLE;

  const htmlMatch = text.match(/---HTML---\s*([\s\S]+)/);
  const html = htmlMatch ? htmlMatch[1].trim() : text;

  const wordCount = html.replace(/<[^>]+>/g, ' ').split(/\s+/).filter(Boolean).length;
  const h2count = (html.match(/<h2/gi) ?? []).length;
  console.log(`  → Article: ${wordCount} words, ${h2count} H2 sections, excerpt: "${excerpt.slice(0, 60)}..."`);

  return { html, excerpt };
}

// ─── Main ─────────────────────────────────────────────────────────────────────

console.log(`\n[rewrite-quality] Rewriting post ID=${POST_ID}: ${POST_TITLE}\n`);

// Stage 1: Research
const researchBrief = await researchTopic();

// Stage 2: Write
const { html, excerpt } = await writeArticle(researchBrief);

// Stage 3: Update WordPress content
console.log('\n  → Updating WordPress post...');
const updateRes = await fetch(`${BASE}/posts/${POST_ID}`, {
  method: 'POST',
  headers: { Authorization: AUTH, 'Content-Type': 'application/json' },
  body: JSON.stringify({
    title: POST_TITLE,
    content: html,
    excerpt,
    status: 'publish',
  }),
});

if (!updateRes.ok) {
  const err = await updateRes.text();
  throw new Error(`WP update failed: ${updateRes.status} – ${err.slice(0, 300)}`);
}
const updated = await updateRes.json() as any;
const h2count = (updated.content?.rendered ?? '').split('<h2').length - 1;
const finalWords = (updated.content?.rendered ?? '').replace(/<[^>]+>/g, ' ').split(/\s+/).filter(Boolean).length;
console.log(`  ✓ WordPress updated: ${finalWords} words, ${h2count} H2s`);

// Stage 4: Generate cover image
console.log('\n  → Generating Flux cover image...');
const imgPrompt = 'Futuristic AI assistant hologram emerging from a laptop screen in a sleek modern real estate office, glowing blue neural network connections, professional male agent looking impressed, warm ambient office lighting, photorealistic 8k editorial photography, no text overlay';

let localImagePath = '';
try {
  const imgUrl = await generateDallEImage(imgPrompt, 150_000);
  const srcPath = imgUrl.replace('file://', '');
  localImagePath = `/tmp/ai-agent-website-cover.jpg`;
  writeFileSync(localImagePath, readFileSync(srcPath));
  console.log(`  ✓ Image saved: ${localImagePath}`);
} catch (err) {
  console.error(`  ✗ Image failed: ${err instanceof Error ? err.message : err}`);
}

// Stage 5: Write PHP upload script and print instructions
const phpScript = `<?php
$auth = 'Basic ' . base64_encode('wproot:Ear3N5QL9hKTfll4FmG9kW5h');
$localFile = '/tmp/ai-agent-website-cover.jpg';
$postId = ${POST_ID};

$ch = curl_init('https://get-my-agent.com/wp-json/wp/v2/media');
curl_setopt_array($ch, [
  CURLOPT_POST => true,
  CURLOPT_RETURNTRANSFER => true,
  CURLOPT_HTTPHEADER => [
    'Authorization: ' . $auth,
    'Content-Disposition: attachment; filename=ai-agent-website-cover.jpg',
    'Content-Type: image/jpeg',
  ],
  CURLOPT_POSTFIELDS => file_get_contents($localFile),
]);
$r = json_decode(curl_exec($ch), true);
curl_close($ch);
$mediaId = $r['id'] ?? 0;
echo "Media ID: $mediaId\\n";

if ($mediaId) {
  $ch2 = curl_init('https://get-my-agent.com/wp-json/wp/v2/posts/' . $postId);
  curl_setopt_array($ch2, [
    CURLOPT_CUSTOMREQUEST => 'POST',
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_HTTPHEADER => ['Authorization: ' . $auth, 'Content-Type: application/json'],
    CURLOPT_POSTFIELDS => json_encode(['featured_media' => $mediaId]),
  ]);
  $r2 = json_decode(curl_exec($ch2), true);
  curl_close($ch2);
  echo "Featured media set to: " . ($r2['featured_media'] ?? 'error') . "\\n";
  echo "Done!\\n";
}
`;

writeFileSync('/tmp/wp_upload_ai_agent.php', phpScript);

console.log('\n[rewrite-quality] ✓ DONE');
console.log('\n─── Upload cover image (run in terminal) ───');
if (localImagePath) {
  console.log(`rsync ${localImagePath} n:/tmp/ && rsync /tmp/wp_upload_ai_agent.php n:/tmp/ && ssh n "php8.1 /tmp/wp_upload_ai_agent.php"`);
}
console.log(`\nArticle: https://get-my-agent.com/en/what-is-ai-agent-for-website/`);
