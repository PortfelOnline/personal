import 'dotenv/config';
import { writeFileSync } from 'fs';

const GROQ_KEY = process.env.BUILT_IN_FORGE_API_KEY!;
const AUTH = 'Basic ' + Buffer.from('wproot:Ear3N5QL9hKTfll4FmG9kW5h').toString('base64');

async function groq(prompt: string): Promise<string> {
  const res = await fetch('https://api.groq.com/openai/v1/chat/completions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${GROQ_KEY}` },
    body: JSON.stringify({
      model: 'llama-3.3-70b-versatile',
      max_tokens: 4000,
      messages: [
        {
          role: 'system',
          content: 'Expert SEO content writer for get-my-agent.com — AI assistant for real estate agents. Write thorough, detailed HTML. Each H2 section: 250-350 words minimum. Use <h2><h3><p><ul><li><strong><table><details><summary>. No Markdown. HTML only.',
        },
        { role: 'user', content: prompt },
      ],
    }),
  });
  const data = await res.json() as any;
  return data.choices?.[0]?.message?.content ?? '';
}

console.log('Part 1: sections 1–4...');
const part1 = await groq(`Write 4 detailed H2 sections for an article titled "What Is an AI Agent for Your Website? (Complete Guide 2025)" targeting real estate agents. Each section: 250-350 words.

SECTION 1 — <h2>What Is an AI Agent for a Website?</h2>
Define clearly (not a chatbot, but an intelligent AI system). Cover: natural language understanding, 24/7 availability, learning from conversations, task automation. Stat: 90% of home buyers start their search online. 3 paragraphs. <ul> listing 5 core capabilities. End: introduce get-my-agent.com as the purpose-built AI agent for real estate.

SECTION 2 — <h2>AI Agent vs. Traditional Chatbot: Key Differences</h2>
Open with 1 paragraph: why the distinction matters. Then a full HTML <table> with headers Feature | Traditional Chatbot | AI Agent, and 6 rows: Intelligence Level, Personalization, Learning Ability, Task Completion, CRM Integration, Cost. Then 2 paragraphs explaining what this means for real estate agents. Why AI agents are the clear choice.

SECTION 3 — <h2>How AI Agents Generate More Leads, 24/7</h2>
3 paragraphs with specific stats: 67% of consumers prefer AI for simple inquiries (Salesforce 2024); leads contacted within 5 minutes are 100x more likely to convert; AI handles 80% of routine queries automatically.
<h3>Instant Response Wins the Lead</h3> — 1 detailed paragraph with example.
<h3>Qualifying Leads While You Sleep</h3> — 1 paragraph + scenario example (3am inquiry, AI qualifies and books appointment).

SECTION 4 — <h2>Top Use Cases for Real Estate Agents</h2>
<h3>Lead Qualification</h3> — 70 words: how AI asks qualifying questions, filters serious buyers.
<h3>Appointment Booking</h3> — 70 words: calendar integration, reduces back-and-forth.
<h3>Property Search Assistance</h3> — 70 words: AI helps match buyers to listings.
<h3>24/7 FAQ Support</h3> — 70 words: handles common questions, never misses a lead.
Closing paragraph mentioning get-my-agent.com covers all 4 use cases.

OUTPUT: Raw HTML only. Start with <h2>.`);

console.log('Part 2: sections 5–8...');
const part2 = await groq(`Write 4 detailed H2 sections for an article titled "What Is an AI Agent for Your Website? (Complete Guide 2025)" targeting real estate agents. Each section: 250-350 words.

SECTION 5 — <h2>The ROI of an AI Agent: Real Numbers</h2>
Open: agents using AI see 30-40% reduction in support costs and 25% increase in lead conversions (cite industry data).
<h3>Cost Savings</h3>: compare hiring a human VA ($800-1,500/month, 8 hours/day, vacations, sick days) vs AI agent ($99-299/month, 24/7, zero days off). <table> with 3 rows: VA vs AI on Cost, Availability, Capacity.
<h3>Revenue Impact</h3>: agent handles 50 inquiries/month manually → AI handles 200+. Example: converting 5% of 150 extra leads at $3,000 commission = $22,500 extra revenue per year.
Closing paragraph: mention get-my-agent.com pricing and free trial.

SECTION 6 — <h2>How to Set Up an AI Agent on Your Website — Step by Step</h2>
5 detailed steps, each as <h3>Step N: Title</h3> followed by 60-80 word paragraph:
Step 1: Choose the Right Platform (recommend get-my-agent.com, purpose-built for real estate, no coding needed)
Step 2: Create Your AI Agent Profile (name, personality, knowledge base about your listings and services)
Step 3: Customize Lead Qualification Questions (budget, timeline, property type, location)
Step 4: Embed the Widget on Your Website (copy-paste one line of code, works on any website)
Step 5: Monitor, Analyze, and Optimize (review conversation logs weekly, refine responses)

SECTION 7 — <h2>Common Questions About AI Agents for Real Estate</h2>
9 FAQ items, each as <details><summary>Question?</summary><p>Answer (50-70 words)</p></details>:
Q1: Will an AI agent replace me as a real estate agent?
Q2: How long does it take to set up an AI agent?
Q3: Can the AI agent integrate with my existing CRM?
Q4: What languages does the AI agent support?
Q5: Is the AI agent mobile-friendly?
Q6: How does the AI agent qualify leads?
Q7: What happens if the AI gives a wrong answer?
Q8: Is my clients data safe and secure?
Q9: How much does get-my-agent.com cost?

SECTION 8 — <h2>Start Growing Your Real Estate Business with AI Today</h2>
2 paragraphs: first on the competitive urgency (agents who adopt AI now capture market share); second as direct CTA for https://get-my-agent.com.
<ul> with 4 bullet points: what you get immediately when you sign up.
Closing sentence: inspiring call to action.

OUTPUT: Raw HTML only. Start with <h2>.`);

const fullHtml = part1.trim() + '\n\n' + part2.trim();
const words = fullHtml.replace(/<[^>]+>/g, ' ').split(/\s+/).filter(Boolean).length;
const h2s = (fullHtml.match(/<h2/gi) ?? []).length;
console.log(`\nCombined: ${words} words, ${h2s} H2s`);

writeFileSync('/tmp/article_1505_full.html', fullHtml);
console.log('Saved to /tmp/article_1505_full.html');

const excerpt = 'Discover what AI agents for websites are, how they generate real estate leads 24/7, and how to set one up. Complete guide with ROI stats for 2025.';

const upd = await fetch('https://get-my-agent.com/wp-json/wp/v2/posts/1505', {
  method: 'POST',
  headers: { Authorization: AUTH, 'Content-Type': 'application/json' },
  body: JSON.stringify({
    title: 'What Is an AI Agent for Your Website? (Complete Guide 2025)',
    content: fullHtml,
    excerpt,
    status: 'publish',
  }),
});
const j = await upd.json() as any;
if (!upd.ok) { console.error('WP error:', JSON.stringify(j).slice(0, 200)); process.exit(1); }
const finalW = (j.content?.rendered ?? '').replace(/<[^>]+>/g, ' ').split(/\s+/).filter(Boolean).length;
const finalH = (j.content?.rendered ?? '').split('<h2').length - 1;
console.log(`WP updated: ${finalW} words, ${finalH} H2s`);
console.log('Article: https://get-my-agent.com/en/what-is-ai-agent-for-website/');
