import 'dotenv/config';
import { invokeLLM } from '../server/_core/llm';

const AUTH = 'Basic ' + Buffer.from('wproot:Ear3N5QL9hKTfll4FmG9kW5h').toString('base64');
const BASE = 'https://get-my-agent.com/wp-json/wp/v2';

const POSTS = [
  {
    id: 1599,
    title: 'Why Every Real Estate Agent Needs an AI Assistant in 2025',
    focus: 'Add 2-3 new H2 sections covering: how AI handles objections, how AI integrates with existing CRM tools, and a comparison of top AI platforms for agents',
  },
  {
    id: 1634,
    title: 'How Real Estate Agents Can Use WhatsApp AI Chatbots to Grow Their Business',
    focus: 'Add 2-3 new H2 sections covering: setting up WhatsApp Business API, best practices for automated conversations, and measuring ROI of WhatsApp AI chatbots',
  },
];

for (const { id, title, focus } of POSTS) {
  const res = await fetch(`${BASE}/posts/${id}?_fields=content`, { headers: { Authorization: AUTH } });
  const post = await res.json() as any;
  const existing = post.content?.rendered ?? '';

  console.log(`\n[ID=${id}] Adding H2 sections to: ${title}`);

  const result = await invokeLLM({
    model: 'llama-3.3-70b-versatile',
    maxTokens: 1200,
    messages: [
      {
        role: 'system',
        content: 'Expert real estate content writer for get-my-agent.com. Write clean HTML only: <h2>, <h3>, <p>, <ul><li>. Mention get-my-agent.com naturally 1-2 times.',
      },
      {
        role: 'user',
        content: `Article: "${title}"

Task: ${focus}

Write 2-3 new <h2> sections (250-350 words total) as HTML to APPEND to the article. Start directly with <h2>. No intro text.`,
      },
    ],
  });

  const raw = result.choices[0]?.message?.content;
  const addition = typeof raw === 'string' ? raw.trim() : '';
  if (!addition) { console.log('  LLM empty, skip'); continue; }

  const updateRes = await fetch(`${BASE}/posts/${id}`, {
    method: 'POST',
    headers: { Authorization: AUTH, 'Content-Type': 'application/json' },
    body: JSON.stringify({ content: existing + '\n' + addition }),
  });
  const updated = await updateRes.json() as any;
  const h2count = (updated.content?.rendered ?? '').split('<h2').length - 1;
  console.log(`  ✓ Updated. H2 count now: ${h2count}`);
}
console.log('\nDone.');
