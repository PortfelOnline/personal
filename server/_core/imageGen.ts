const IMAGE_API_URL = process.env.IMAGE_API_URL ?? 'https://api.together.xyz';
const IMAGE_API_KEY = process.env.IMAGE_API_KEY ?? '';
const IMAGE_MODEL   = process.env.IMAGE_MODEL   ?? 'black-forest-labs/FLUX.1.1-pro';

/**
 * Generate an image via Together AI FLUX and return the temporary URL.
 */
export async function generateDallEImage(prompt: string, timeoutMs = 60_000): Promise<string> {
  if (!IMAGE_API_KEY) {
    throw new Error('IMAGE_API_KEY not configured (set Together AI key in .env)');
  }

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  let response: Response;
  try {
    response = await fetch(`${IMAGE_API_URL.replace(/\/$/, '')}/v1/images/generations`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${IMAGE_API_KEY}`,
      },
      body: JSON.stringify({
        model: IMAGE_MODEL,
        prompt,
        n: 1,
        width: 1792,
        height: 1024,
      }),
      signal: controller.signal,
    });
  } finally {
    clearTimeout(timer);
  }

  if (!response.ok) {
    const err = await response.text();
    throw new Error(`Image generation error: ${response.status} – ${err}`);
  }

  const data = (await response.json()) as { data: { url: string; b64_json?: string }[] };
  const url = data?.data?.[0]?.url;
  if (!url) throw new Error('Together AI returned no image URL');
  return url;
}
