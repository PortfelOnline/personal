import { describe, it, expect } from 'vitest';
import { buildArticleToSocialPrompt } from './articleToSocial';

describe('buildArticleToSocialPrompt', () => {
  it('includes article title in prompt', () => {
    const prompt = buildArticleToSocialPrompt('AI Agent for Sales', 'AI agents help sales teams...');
    expect(prompt).toContain('AI Agent for Sales');
  });

  it('includes excerpt in prompt', () => {
    const prompt = buildArticleToSocialPrompt('Title', 'excerpt text here');
    expect(prompt).toContain('excerpt text here');
  });

  it('includes Facebook and Instagram instructions', () => {
    const prompt = buildArticleToSocialPrompt('Title', 'excerpt');
    expect(prompt.toLowerCase()).toContain('facebook');
    expect(prompt.toLowerCase()).toContain('instagram');
  });
});
