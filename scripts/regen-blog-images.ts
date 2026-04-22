/**
 * Regenerate unique cover images for all 13 blog articles.
 * Each prompt has a distinct visual concept, scene type, and color palette.
 * Run: npx tsx scripts/regen-blog-images.ts
 */
import 'dotenv/config';
import { generateDallEImage } from '../server/_core/imageGen';
import { writeFileSync, readFileSync } from 'fs';

const ARTICLES = [
  {
    id: 1590,
    slug: 'ai-transforming-real-estate-agent-workflows-2025',
    prompt: 'Glowing holographic workflow diagram floating above a real estate agent desk, automated pipeline steps in blue and gold light, dark moody office background, cinematic depth of field, photorealistic 8k, no text',
  },
  {
    id: 1593,
    slug: 'top-5-ways-real-estate-agents-use-ai-close-more-deals',
    prompt: 'Five glowing golden trophy icons arranged around a handshake between agent and client, deep blue gradient background, abstract light rays, wide angle, photorealistic, no text',
  },
  {
    id: 1596,
    slug: 'complete-guide-ai-chatbots-real-estate-agents',
    prompt: 'Close-up of smartphone screen showing AI chat conversation with property listing images and quick reply bubbles, hand holding phone, blurred luxury apartment building in background, warm afternoon light, photorealistic, no text',
  },
  {
    id: 1599,
    slug: 'why-every-real-estate-agent-needs-ai-assistant-2025',
    prompt: 'Friendly glowing blue AI hologram assistant beside a confident female real estate agent in front of a luxury home exterior, golden hour lighting, wide cinematic shot, photorealistic, no text',
  },
  {
    id: 1616,
    slug: 'how-to-generate-real-estate-leads-with-ai-guide',
    prompt: 'Abstract glowing funnel made of light with small silhouetted people flowing into it and emerging as golden coins, teal and orange color palette, dark background, digital art, cinematic, no text',
  },
  {
    id: 1619,
    slug: 'ai-vs-traditional-real-estate-marketing-what-works',
    prompt: 'Bold split composition: left half shows vintage newspaper property ads and printed flyers in sepia grayscale; right half shows vibrant neon digital dashboard with AI graphs and colorful metrics; sharp dividing line down center, photorealistic, no text',
  },
  {
    id: 1622,
    slug: 'automate-real-estate-social-media-with-ai',
    prompt: 'Young real estate agent sitting relaxed on a modern sofa with coffee mug, phone screen showing a social media content grid with posts automatically publishing, morning sunlight, Instagram aesthetic, photorealistic, no text',
  },
  {
    id: 1625,
    slug: 'best-ai-tools-real-estate-agents-2025',
    prompt: 'Overhead flat lay of minimalist white desk with MacBook, iPad, iPhone and smart speaker each showing different colorful AI tool interfaces, soft diffused natural light, clean product photography style, no text',
  },
  {
    id: 1628,
    slug: 'how-ai-helps-real-estate-agents-respond-leads-faster',
    prompt: 'Electric lightning bolt striking a smartphone notification bell at center frame, speed blur trails, electric blue and white energy on pitch black background, dramatic contrast, photorealistic, no text',
  },
  {
    id: 1631,
    slug: 'using-ai-write-better-property-listings-sell-faster',
    prompt: 'Large elegant monitor displaying a luxury property listing with AI-highlighted golden text keywords, beautiful interior home visible in the listing photo, warm inviting living room light, editorial photography, no text',
  },
  {
    id: 1634,
    slug: 'real-estate-agents-whatsapp-ai-chatbots-grow-business',
    prompt: 'Two smartphones floating side by side showing active WhatsApp property chat with AI quick replies and apartment photos in green chat bubbles, blurred night city skyline background, neon reflections, photorealistic, no text',
  },
  {
    id: 1639,
    slug: 'ai-follow-up-strategies-cold-leads-hot-buyers',
    prompt: 'Abstract visualization: icy blue frozen figures on left side melting and transforming through glowing AI energy stream into warm red glowing active buyers on right side, dark background, particle effects, digital art, no text',
  },
  {
    id: 1640,
    slug: 'build-24-7-real-estate-lead-machine-with-ai',
    prompt: 'Nighttime city skyline visible through large office window, laptop screen in foreground showing automated lead dashboard with green active indicators, clock on wall shows 3am, empty office chair, long exposure light trails outside, cinematic, no text',
  },
];

console.log(`[regen-images] Generating ${ARTICLES.length} unique images...\n`);

const generated: { id: number; slug: string; localPath: string }[] = [];

for (let i = 0; i < ARTICLES.length; i++) {
  const { id, slug, prompt } = ARTICLES[i];
  console.log(`[${i + 1}/${ARTICLES.length}] ${slug}`);
  try {
    const imgUrl = await generateDallEImage(prompt, 150_000);
    const srcPath = imgUrl.replace('file://', '');
    const namedPath = `/tmp/regen-${slug}.jpg`;
    writeFileSync(namedPath, readFileSync(srcPath));
    generated.push({ id, slug, localPath: namedPath });
    console.log(`  ✓ ${namedPath}\n`);
  } catch (err) {
    console.error(`  ✗ ${err instanceof Error ? err.message : err}\n`);
  }
}

// Write manifest so upload step knows what to do
const manifest = generated.map(g => `${g.id}|${g.slug}`).join('\n');
writeFileSync('/tmp/regen-manifest.txt', manifest);
console.log(`\n[regen-images] Generated ${generated.length}/${ARTICLES.length} images.`);
console.log('Manifest: /tmp/regen-manifest.txt');
console.log('\nNext steps:');
console.log('  rsync /tmp/regen-*.jpg n:/tmp/');
console.log('  ssh n "php8.1 /tmp/wp_regen_upload.php"');
