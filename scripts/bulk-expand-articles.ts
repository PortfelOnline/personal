/**
 * Bulk-expand all EN blog articles on get-my-agent.com to 1600+ words.
 * Each article gets: 6+ H2 sections, H3 subsections, FAQ with <details>, stats, CTA.
 * Two Groq calls per article (sections 1-3 + sections 4-6) to avoid token truncation.
 *
 * Run: npx tsx scripts/bulk-expand-articles.ts
 */
import 'dotenv/config';

const GROQ_KEY = process.env.BUILT_IN_FORGE_API_KEY!;
const AUTH = 'Basic ' + Buffer.from('wproot:Ear3N5QL9hKTfll4FmG9kW5h').toString('base64');
const BASE = 'https://get-my-agent.com/wp-json/wp/v2';

const ARTICLES = [
  {
    id: 1504,
    title: 'AI Agent vs Chatbot: What\'s the Difference and Which Do You Need?',
    focus: 'Compare AI agents vs traditional chatbots for real estate websites. Cover: intelligence, personalization, learning, CRM integration. Recommend get-my-agent.com as the AI agent solution.',
  },
  {
    id: 1639,
    title: 'AI Follow-Up Strategies That Turn Cold Leads into Hot Buyers',
    focus: 'Automated follow-up sequences for real estate: personalized AI messages, timing optimization, re-engagement campaigns. Stats on follow-up timing and conversion. get-my-agent.com automates all of this.',
  },
  {
    id: 1622,
    title: 'How to Automate Your Real Estate Social Media with AI',
    focus: 'AI content generation for Instagram, Facebook, LinkedIn: posts, captions, scheduling. Save 10+ hours/week. Engagement stats. Tools and step-by-step guide. get-my-agent.com content features.',
  },
  {
    id: 1593,
    title: 'Top 5 Ways Real Estate Agents Can Use AI to Close More Deals',
    focus: 'Practical AI tactics: AI chatbots for instant response, automated outreach, smart CRM, social media automation, personalized listings. Stats on each tactic. Numbered list format with deep dives.',
  },
  {
    id: 1619,
    title: 'AI vs Traditional Real Estate Marketing: What Really Works in 2025',
    focus: 'ROI comparison: AI marketing vs traditional (print ads, cold calling, open houses). Cost-per-lead, time investment, conversion rates. Data-driven argument for AI. get-my-agent.com ROI.',
  },
  {
    id: 1640,
    title: 'How to Build a 24/7 Real Estate Lead Machine with AI',
    focus: 'Full system design: AI chatbot + automated email/WhatsApp + CRM integration + human handoff workflow. Step-by-step implementation guide. get-my-agent.com as the central platform.',
  },
  {
    id: 1616,
    title: 'How to Generate Real Estate Leads with AI: A Step-by-Step Guide',
    focus: 'Lead generation funnel using AI: social media ads targeting, landing pages, chatbot qualification, CRM integration. Stats: AI generates 50%+ more qualified leads. Actionable steps.',
  },
  {
    id: 1590,
    title: 'How AI is Transforming Real Estate Agent Workflows in 2025',
    focus: 'AI automation tools saving time: lead capture, follow-ups, content creation, admin tasks. Before/after comparison. Time savings stats. get-my-agent.com workflow automation features.',
  },
  {
    id: 1631,
    title: 'Using AI to Write Better Property Listings That Sell Faster',
    focus: 'AI copywriting for property descriptions: emotional triggers, SEO optimization, A/B testing results. Examples of before/after listings. sell 20% faster with optimized descriptions.',
  },
  {
    id: 1634,
    title: 'How Real Estate Agents Can Use WhatsApp AI Chatbots to Grow Their Business',
    focus: 'WhatsApp Business API + AI for real estate: automated responses, appointment booking, lead nurturing. WhatsApp open rates (98%!) vs email. Setup guide. get-my-agent.com WhatsApp integration.',
  },
  {
    id: 1628,
    title: 'How AI Helps Real Estate Agents Respond to Leads Faster',
    focus: 'Speed-to-lead statistics (5-minute rule = 100x conversion). AI instant response systems, 24/7 availability, impact on lead conversion. Implementation guide. get-my-agent.com response speed.',
  },
  {
    id: 1596,
    title: 'The Complete Guide to AI Chatbots for Real Estate Agents',
    focus: 'How AI chatbots qualify leads 24/7, answer buyer questions, schedule viewings, hand off to agents. Detailed setup guide. Comparison of features. get-my-agent.com chatbot capabilities.',
  },
  {
    id: 1625,
    title: 'The Best AI Tools for Real Estate Agents in 2025',
    focus: 'Roundup: CRM AI, chatbots, image generation, virtual tours, automated follow-ups. Each tool with pros/cons/pricing. Why get-my-agent.com is the all-in-one solution. Comparison table.',
  },
  {
    id: 1599,
    title: 'Why Every Real Estate Agent Needs an AI Assistant in 2025',
    focus: 'Benefits: 24/7 availability, instant responses, lead qualification, time savings. Competitive advantage stats. Common objections addressed. How get-my-agent.com changes the game.',
  },
];

async function groq(systemMsg: string, userMsg: string): Promise<string> {
  const res = await fetch('https://api.groq.com/openai/v1/chat/completions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${GROQ_KEY}` },
    body: JSON.stringify({
      model: 'llama-3.3-70b-versatile',
      max_tokens: 4000,
      messages: [
        { role: 'system', content: systemMsg },
        { role: 'user', content: userMsg },
      ],
    }),
  });
  const data = await res.json() as any;
  if (!res.ok) throw new Error(`Groq ${res.status}: ${JSON.stringify(data).slice(0, 200)}`);
  return data.choices?.[0]?.message?.content ?? '';
}

const SYS = `Expert SEO content writer for get-my-agent.com — AI assistant platform for real estate agents.
Write thorough HTML. Every H2 section: 250-350 words. Use <h2><h3><p><ul><li><strong>.
Specific stats and real examples required. No Markdown. HTML only. Start output with <h2>.`;

async function expandArticle(id: number, title: string, focus: string): Promise<void> {
  console.log(`\n[ID=${id}] ${title}`);

  // Part 1: intro + 3 core sections
  console.log('  → Part 1 (sections 1–3)...');
  const part1 = await groq(SYS, `Write the FIRST 3 H2 sections of a comprehensive blog article.

Article title: "${title}"
Focus: ${focus}

SECTION 1 — Opening/Introduction H2 (create a compelling headline):
3 paragraphs. Open with a striking statistic. Define the topic clearly. Explain why it matters to real estate agents in 2025. <ul> with 5 key benefits. Mention get-my-agent.com.

SECTION 2 — Core concepts / How it works H2 (create relevant headline):
Explain the mechanism in detail. Use <h3> subsections (2-3). Include realistic statistics. Give concrete real estate examples. 250-300 words.

SECTION 3 — Benefits & Results H2 (create relevant headline):
ROI stats, time savings, conversion improvements. <h3> subsections. Before/after comparison where relevant. Specific numbers and percentages. 250-300 words.

HTML only. Start with <h2>.`);

  // Part 2: practical sections + FAQ + CTA
  console.log('  → Part 2 (sections 4–6 + FAQ + CTA)...');
  const part2 = await groq(SYS, `Write the LAST sections of a comprehensive blog article.

Article title: "${title}"
Focus: ${focus}

SECTION 4 — Practical How-To H2 (create relevant headline):
Step-by-step guide with <h3>Step N: Title</h3> (4-5 steps). Each step 60-80 words. Practical, actionable. Mention get-my-agent.com in relevant step.

SECTION 5 — Common Mistakes / Tips H2 (create relevant headline):
<ul> of 5-6 specific mistakes or pro tips. Each point 2-3 sentences. Actionable advice.

SECTION 6 — FAQ <h2>Frequently Asked Questions</h2>
8 FAQ items as <details><summary>Question text?</summary><p>Answer 50-70 words</p></details>.
Questions specific to "${title}" topic. Include "How does get-my-agent.com help with X?" as one question.

SECTION 7 — <h2>Get Started with AI for Your Real Estate Business</h2>
2 strong paragraphs: urgency + CTA. Link to https://get-my-agent.com. <ul> of 4 immediate benefits from signing up. Inspiring closing sentence.

HTML only. Start with <h2>.`);

  const fullHtml = part1.trim() + '\n\n' + part2.trim();
  const words = fullHtml.replace(/<[^>]+>/g, ' ').split(/\s+/).filter(Boolean).length;
  const h2s = (fullHtml.match(/<h2/gi) ?? []).length;
  const faq = (fullHtml.match(/<details/gi) ?? []).length;

  // Update WordPress
  const upd = await fetch(`${BASE}/posts/${id}`, {
    method: 'POST',
    headers: { Authorization: AUTH, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      title,
      content: fullHtml,
      status: 'publish',
    }),
  });
  const j = await upd.json() as any;
  if (!upd.ok) {
    console.error(`  ✗ WP error: ${JSON.stringify(j).slice(0, 200)}`);
    return;
  }
  const finalW = (j.content?.rendered ?? '').replace(/<[^>]+>/g, ' ').split(/\s+/).filter(Boolean).length;
  console.log(`  ✓ Updated: ${finalW} words, ${h2s} H2s, ${faq} FAQ items`);
}

console.log(`[bulk-expand] Expanding ${ARTICLES.length} articles...\n`);
const start = Date.now();

for (const { id, title, focus } of ARTICLES) {
  try {
    await expandArticle(id, title, focus);
  } catch (err) {
    console.error(`  ✗ Error on ID=${id}: ${err instanceof Error ? err.message : err}`);
  }
}

const mins = ((Date.now() - start) / 60000).toFixed(1);
console.log(`\n[bulk-expand] Done in ${mins} min`);
