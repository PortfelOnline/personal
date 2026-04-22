/**
 * Rewrite kadastrovyj-plan-kvartiry-po-adresu via standard pipeline
 * + custom post-processing to inject BTI conversion section
 */
import 'dotenv/config';
import { runBatchRewrite } from '../server/routers/articles';
import axios from 'axios';
import { invokeLLM } from '../server/_core/llm';

const SITE_URL = 'https://kadastrmap.info';
const WP_USER  = 'grudeves_vf97s8yc';
const WP_PASS  = process.env.WP_APP_PASSWORD_KAD ?? 'uX$8LCdpGKH9Rcd';
const AUTH     = 'Basic ' + Buffer.from(`${WP_USER}:${WP_PASS}`).toString('base64');
const API      = `${SITE_URL}/wp-json/wp/v2`;
const SLUG     = 'kadastrovyj-plan-kvartiry-po-adresu';
const URL      = `${SITE_URL}/kadastr/${SLUG}/`;

// Step 1: Standard full rewrite (3500+ words, multi-pass, FLUX images)
console.log('[step1] Starting standard rewrite pipeline...');
await runBatchRewrite(1, [URL]);
console.log('[step1] Done. Fetching article to inject BTI section...');

// Step 2: Get the freshly rewritten article
const res = await axios.get(`${API}/posts?slug=${SLUG}&_fields=id,content`, {
  headers: { Authorization: AUTH },
});
const post = res.data[0];
if (!post) throw new Error('Post not found after rewrite');

const currentHtml = post.content.rendered;

// Step 3: Generate a focused BTI conversion section using short prompt
const btiSection = await invokeLLM({
  model: 'llama-3.3-70b-versatile',
  messages: [
    { role: 'system', content: 'Ты SEO-копирайтер. Пишешь конкретный HTML-блок для вставки в статью.' },
    { role: 'user', content: `Напиши HTML-раздел (300-400 слов) для вставки в статью "Планировка квартиры по адресу".

Тема блока: ОФИЦИАЛЬНЫЙ поэтажный план БТИ vs бесплатная типовая схема.

Формат:
<h2>📋 Официальный поэтажный план БТИ: когда типовой схемы недостаточно</h2>
<p>[200+ слов: объяснить разницу. Типовые планировки на ЦИАН/ДомКлик — это схемы серии дома, НЕ конкретной квартиры. Для сделок, перепланировки, суда нужен официальный документ из БТИ с экспликацией, штампом и подписью. Конкретные случаи когда нужен именно официальный: банк/ипотека, наследство, суд, согласование перепланировки.]</p>
<h3>🛡️ Как получить официальный план через kadastrmap.info</h3>
<ol>
  <li>[шаг 1 — открыть kadastrmap.info/spravki/]</li>
  <li>[шаг 2 — ввести адрес или кадастровый номер]</li>
  <li>[шаг 3 — выбрать "Поэтажный план с экспликацией БТИ"]</li>
  <li>[шаг 4 — оплатить онлайн, получить в личном кабинете за 1-3 рабочих дня]</li>
</ol>
<p>[CTA 50 слов: почему быстрее и удобнее чем через МФЦ. Ссылка <a href="https://kadastrmap.info/spravki/">kadastrmap.info/spravki/</a>]</p>

Правила: конкретно, без воды, ссылки только на kadastrmap.info, никаких цен в рублях — только [BLOCK_PRICE] если нужно упомянуть цену.
Верни ТОЛЬКО HTML без обёрток.` },
  ],
  maxTokens: 1000,
});

const btiHtml = (btiSection.choices[0]?.message?.content ?? '').trim()
  .replace(/^```html?\s*/i, '').replace(/\s*```$/i, '').trim();

if (!btiHtml || btiHtml.length < 100) {
  console.log('[step3] BTI section too short, skipping injection');
  process.exit(0);
}

// Step 4: Inject BTI section before the first FAQ H2
const faqMarker = '<h2';
const faqIndex = currentHtml.indexOf('FAQ') > 0
  ? currentHtml.lastIndexOf('<h2', currentHtml.indexOf('FAQ'))
  : currentHtml.lastIndexOf('<h2');

let updatedHtml: string;
if (faqIndex > 0) {
  updatedHtml = currentHtml.slice(0, faqIndex) + '\n' + btiHtml + '\n' + currentHtml.slice(faqIndex);
} else {
  // Fallback: append before FAQ section marker or at end
  updatedHtml = currentHtml + '\n' + btiHtml;
}

await axios.post(`${API}/posts/${post.id}`, { content: updatedHtml }, {
  headers: { Authorization: AUTH, 'Content-Type': 'application/json' },
});

const finalWords = updatedHtml.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').split(' ').filter(Boolean).length;
console.log(`✅ Injected BTI section. Total: ~${finalWords} words`);
console.log(`   ${URL}`);
