import { ENV } from './env';

/**
 * Generate an image via DALL-E 3 and return the temporary URL.
 */
export async function generateDallEImage(prompt: string, timeoutMs = 50_000): Promise<string> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  let response: Response;
  try {
    response = await fetch(`${ENV.forgeApiUrl.replace(/\/$/, '')}/v1/images/generations`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${ENV.forgeApiKey}`,
      },
      body: JSON.stringify({
        model: 'dall-e-3',
        prompt,
        n: 1,
        size: '1792x1024',
        quality: 'standard',
      }),
      signal: controller.signal,
    });
  } finally {
    clearTimeout(timer);
  }

  if (!response.ok) {
    const err = await response.text();
    throw new Error(`DALL-E error: ${response.status} – ${err}`);
  }

  const data = (await response.json()) as { data: { url: string }[] };
  const url = data?.data?.[0]?.url;
  if (!url) throw new Error('DALL-E returned no image URL');
  return url;
}
