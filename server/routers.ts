import { COOKIE_NAME } from "@shared/const";
import { getSessionCookieOptions } from "./_core/cookies";
import { systemRouter } from "./_core/systemRouter";
import { publicProcedure, router, protectedProcedure } from "./_core/trpc";
import { z } from "zod";
import { invokeLLM } from "./_core/llm";
import { createContentPost, getUserContentPosts, getContentTemplates, createContentTemplate, updateContentPost, deleteContentPost } from "./db";
import { metaRouter } from "./routers/meta";
import { botsRouter } from "./routers/bots";
import { wordpressRouter } from "./routers/wordpress";
import { articlesRouter } from "./routers/articles";

export const appRouter = router({
  system: systemRouter,
  meta: metaRouter,
  bots: botsRouter,
  wordpress: wordpressRouter,
  articles: articlesRouter,
  auth: router({
    me: publicProcedure.query(opts => opts.ctx.user),
    logout: publicProcedure.mutation(({ ctx }) => {
      const cookieOptions = getSessionCookieOptions(ctx.req);
      ctx.res.clearCookie(COOKIE_NAME, { ...cookieOptions, maxAge: -1 });
      return {
        success: true,
      } as const;
    }),
  }),

  content: router({
    generatePost: protectedProcedure
      .input(z.object({
        pillarType: z.enum(["desi_business_owner", "five_minute_transformation", "roi_calculator"]),
        platform: z.enum(["facebook", "instagram", "whatsapp", "youtube"]),
        language: z.enum(["hinglish", "hindi", "english", "tamil", "telugu", "bengali"]).default("hinglish"),
        customPrompt: z.string().optional(),
      }))
      .mutation(async ({ ctx, input }) => {
        const isYouTube = input.platform === "youtube";

        const prompts: Record<string, Record<string, string>> = {
          facebook: {
            desi_business_owner: "Write a Facebook post for Indian business owners using Hinglish humor. Show the struggle of missing customer messages at night vs having an AI agent. Add a relatable story hook (e.g. 'Raat 2 baje ek message aaya...'). Include call-to-action. Under 200 words.",
            five_minute_transformation: `Write a Facebook post showing how to set up an AI consultant in 5 minutes. Step-by-step, use language: ${input.language}. Add excitement and a free trial CTA. Under 200 words.`,
            roi_calculator: "Write a Facebook post comparing hiring staff (₹15,000-30,000/month) vs AI agent (₹999/month). Use 'Paisa Vasool' angle. Include ROI math. Under 200 words.",
          },
          instagram: {
            desi_business_owner: "Write an Instagram Reel script for Indian SMBs. Hinglish, funny, hook in first 3 seconds. Show customer service struggle vs AI. Include text overlays idea and hashtags. Under 150 words.",
            five_minute_transformation: `Write an Instagram Reel script: 5-minute AI setup demo. Fast cuts, timer visible, language: ${input.language}. End with free trial link. Under 150 words.`,
            roi_calculator: "Write an Instagram carousel caption about cost savings: staff vs AI agent ₹999/month. Use bold stats, emojis, Hinglish. Under 150 words.",
          },
          whatsapp: {
            desi_business_owner: "Write a WhatsApp Business broadcast message for Indian shop owners. Casual, short, in Hinglish. Show how AI handles customer queries 24/7. Include a WhatsApp demo link. Under 100 words.",
            five_minute_transformation: `Write a WhatsApp Business message: 'Set up your AI agent in 5 minutes'. Language: ${input.language}. Conversational tone, include free trial link. Under 100 words.`,
            roi_calculator: "Write a WhatsApp broadcast about ROI: compare cost of missed leads vs ₹999/month AI. Add urgency. Under 100 words.",
          },
          youtube: {
            desi_business_owner: `Write a YouTube Shorts script (max 60 sec) for Indian business owners. Hook in first 2 seconds. Use Hinglish humor about missing customer messages. Show before/after with Get My Agent. End with subscribe CTA. Format: [HOOK] [PROBLEM] [SOLUTION] [CTA]. Language: ${input.language}.`,
            five_minute_transformation: `Write a full YouTube video script (5-7 min) showing complete AI agent setup demo. Structured: intro hook, step-by-step setup (paste code → agent live), results, CTA to free trial. Language: ${input.language}. Include suggested title, description, and tags.`,
            roi_calculator: `Write a YouTube Shorts script (max 60 sec) about ROI: hiring staff ₹15,000-30,000/month vs AI ₹999/month. Use a calculator visual idea. Language: ${input.language}. Format: [HOOK] [MATH] [PUNCHLINE] [CTA]. Include suggested title and 10 tags.`,
          },
        };

        const platformPrompts = prompts[input.platform] || prompts.instagram;
        const basePrompt = platformPrompts[input.pillarType];

        const systemPrompt = isYouTube
          ? "You are a YouTube content strategist for the Indian market. Create engaging video scripts, optimized titles, descriptions, and tags that help Indian business owners understand the value of AI. Use cultural references and relatable examples."
          : "You are a social media content expert for the Indian market. Create engaging, viral-worthy content that resonates with Indian business owners. Use cultural references, humor, and local language preferences. Always include relevant hashtags and emojis.";

        const userPrompt = input.customPrompt || basePrompt;

        const response = await invokeLLM({
          messages: [
            { role: "system", content: systemPrompt },
            { role: "user", content: userPrompt },
          ],
        });

        const contentText = typeof response.choices[0]?.message.content === 'string' 
          ? response.choices[0].message.content 
          : "";
        
        const hashtagMatch = contentText.match(/#\w+/g);
        const hashtags = hashtagMatch ? hashtagMatch.join(" ") : "#GetMyAgent #AI #IndianBusiness";

        return {
          content: contentText,
          hashtags,
          platform: input.platform,
          language: input.language,
          pillarType: input.pillarType,
        };
      }),

    savePost: protectedProcedure
      .input(z.object({
        title: z.string(),
        content: z.string(),
        platform: z.enum(["facebook", "instagram", "whatsapp", "youtube"]),
        language: z.string(),
        hashtags: z.string().optional(),
        status: z.enum(["draft", "scheduled", "published"]).default("draft"),
        scheduledAt: z.date().optional(),
      }))
      .mutation(async ({ ctx, input }) => {
        const result = await createContentPost(ctx.user.id, {
          title: input.title,
          content: input.content,
          platform: input.platform,
          language: input.language,
          hashtags: input.hashtags,
          status: input.status,
          scheduledAt: input.scheduledAt,
        });
        return result;
      }),

    listPosts: protectedProcedure
      .input(z.object({
        status: z.enum(["draft", "scheduled", "published", "archived"]).optional(),
      }))
      .query(async ({ ctx, input }) => {
        const posts = await getUserContentPosts(ctx.user.id, input.status);
        return posts;
      }),

    listTemplates: protectedProcedure
      .query(async ({ ctx }) => {
        const templates = await getContentTemplates(ctx.user.id);
        return templates;
      }),

    saveTemplate: protectedProcedure
      .input(z.object({
        title: z.string(),
        pillarType: z.enum(["desi_business_owner", "five_minute_transformation", "roi_calculator"]),
        platform: z.enum(["facebook", "instagram", "whatsapp", "youtube", "all"]),
        language: z.enum(["hinglish", "hindi", "english", "tamil", "telugu", "bengali"]),
        prompt: z.string(),
        description: z.string().optional(),
      }))
      .mutation(async ({ ctx, input }) => {
        const result = await createContentTemplate(ctx.user.id, {
          title: input.title,
          pillarType: input.pillarType,
          platform: input.platform,
          language: input.language,
          prompt: input.prompt,
          description: input.description,
        });
        return result;
      }),

    updatePost: protectedProcedure
      .input(z.object({
        id: z.number(),
        title: z.string().optional(),
        content: z.string().optional(),
        hashtags: z.string().optional(),
        status: z.enum(["draft", "scheduled", "published", "archived"]).optional(),
        scheduledAt: z.date().optional().nullable(),
      }))
      .mutation(async ({ ctx, input }) => {
        const { id, ...updates } = input;
        await updateContentPost(ctx.user.id, id, updates);
        return { success: true };
      }),

    deletePost: protectedProcedure
      .input(z.object({ id: z.number() }))
      .mutation(async ({ ctx, input }) => {
        await deleteContentPost(ctx.user.id, input.id);
        return { success: true };
      }),

    schedulePost: protectedProcedure
      .input(z.object({
        id: z.number(),
        scheduledAt: z.date(),
      }))
      .mutation(async ({ ctx, input }) => {
        await updateContentPost(ctx.user.id, input.id, {
          scheduledAt: input.scheduledAt,
          status: 'scheduled',
        });
        return { success: true };
      }),

    generateVariation: protectedProcedure
      .input(z.object({
        content: z.string(),
        platform: z.enum(["facebook", "instagram", "whatsapp", "youtube"]),
        language: z.enum(["hinglish", "hindi", "english", "tamil", "telugu", "bengali"]).default("hinglish"),
      }))
      .mutation(async ({ input }) => {
        const response = await invokeLLM({
          messages: [
            { role: "system", content: "You are a social media content expert for the Indian market. Create a variation of the given post that feels fresh but conveys the same message. Keep it engaging with emojis and hashtags." },
            { role: "user", content: `Create a variation of this ${input.platform} post in ${input.language}:\n\n${input.content}` },
          ],
        });
        const variation = typeof response.choices[0]?.message.content === 'string'
          ? response.choices[0].message.content : "";
        return { variation };
      }),

    suggestHashtags: protectedProcedure
      .input(z.object({
        content: z.string(),
        platform: z.enum(["facebook", "instagram", "whatsapp", "youtube"]),
      }))
      .mutation(async ({ input }) => {
        const response = await invokeLLM({
          messages: [
            { role: "system", content: "You are a social media hashtag expert for the Indian market. Suggest relevant, trending hashtags." },
            { role: "user", content: `Suggest 10 relevant hashtags for this ${input.platform} post. Return ONLY the hashtags separated by spaces, no explanations:\n\n${input.content}` },
          ],
        });
        const hashtags = typeof response.choices[0]?.message.content === 'string'
          ? response.choices[0].message.content.trim() : "";
        return { hashtags };
      }),
  }),
});

export type AppRouter = typeof appRouter;
