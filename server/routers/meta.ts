import { router, protectedProcedure, publicProcedure } from "../_core/trpc";
import { z } from "zod";
import { TRPCError } from "@trpc/server";
import * as metaApi from "../_core/meta";
import * as metaDb from "../meta.db";
import { getDb } from "../db";
import { contentPosts } from "../../drizzle/schema";
import { eq } from "drizzle-orm";

export const metaRouter = router({
  /**
   * Get Meta OAuth URL for user to authenticate
   */
  getOAuthUrl: protectedProcedure
    .query(({ ctx }) => {
      // Encode userId in state so callback can find user even if cookie is blocked
      const state = Buffer.from(JSON.stringify({ userId: ctx.user.id, r: Math.random().toString(36).slice(2) })).toString('base64url');
      const oauthUrl = metaApi.getMetaOAuthUrl(state);
      return { oauthUrl };
    }),

  /**
   * Handle OAuth callback and store credentials
   */
  handleOAuthCallback: protectedProcedure
    .input(z.object({
      code: z.string(),
    }))
    .mutation(async ({ ctx, input }) => {
      try {
        // Exchange code for access token
        const tokenResponse = await metaApi.exchangeMetaCode(input.code);

        // Get user info
        const user = await metaApi.getMetaUser(tokenResponse.access_token);

        // Get Instagram accounts
        const instagramAccounts = await metaApi.getInstagramAccounts(tokenResponse.access_token);

        // Get Facebook pages
        const facebookPages = await metaApi.getFacebookPages(tokenResponse.access_token);

        // Store Instagram accounts
        for (const account of instagramAccounts) {
          await metaDb.upsertMetaAccount(ctx.user.id, {
            accountType: "instagram_business",
            accountId: account.id,
            accountName: account.username || account.name,
            accessToken: tokenResponse.access_token,
            expiresAt: tokenResponse.expires_in
              ? new Date(Date.now() + tokenResponse.expires_in * 1000)
              : undefined,
          });
        }

        // Store Facebook pages
        for (const page of facebookPages) {
          await metaDb.upsertMetaAccount(ctx.user.id, {
            accountType: "facebook_page",
            accountId: page.id,
            accountName: page.name,
            accessToken: page.access_token,
          });
        }

        return {
          success: true,
          instagramAccounts: instagramAccounts.length,
          facebookPages: facebookPages.length,
        };
      } catch (error) {
        console.error("[Meta OAuth] Error:", error);
        throw new TRPCError({
          code: "INTERNAL_SERVER_ERROR",
          message: "Failed to authenticate with Meta",
        });
      }
    }),

  /**
   * Get user's connected Meta accounts
   */
  getAccounts: protectedProcedure
    .query(async ({ ctx }) => {
      const accounts = await metaDb.getUserMetaAccounts(ctx.user.id);
      return accounts;
    }),

  /**
   * Publish content to Instagram
   */
  publishToInstagram: protectedProcedure
    .input(z.object({
      accountId: z.string(),
      postId: z.number(),
      caption: z.string(),
      imageUrl: z.string().optional(),
    }))
    .mutation(async ({ ctx, input }) => {
      try {
        // Get Meta account
        const account = await metaDb.getMetaAccount(ctx.user.id, input.accountId);
        if (!account) {
          throw new TRPCError({
            code: "NOT_FOUND",
            message: "Instagram account not found",
          });
        }

        // Extract plain text from JSON carousel content if needed
        let caption = input.caption;
        try {
          const parsed = JSON.parse(input.caption);
          if (parsed.caption) {
            const hashtags = Array.isArray(parsed.hashtags) ? '\n\n' + parsed.hashtags.join(' ') : '';
            caption = parsed.caption + hashtags;
          }
        } catch {
          // Not JSON, use as-is
        }

        // Publish to Instagram
        const result = await metaApi.postToInstagram(
          input.accountId,
          account.accessToken,
          caption,
          input.imageUrl
        );

        // Update post status in database
        const db = await getDb();
        if (db) {
          await db
            .update(contentPosts)
            .set({
              status: "published",
              publishedAt: new Date(),
              metaPostId: result.id ? String(result.id) : null,
            } as any)
            .where(eq(contentPosts.id, input.postId));
        }

        return {
          success: true,
          postId: result.id,
        };
      } catch (error) {
        console.error("[Meta API] Instagram publish error:", error);
        throw new TRPCError({
          code: "INTERNAL_SERVER_ERROR",
          message: "Failed to publish to Instagram",
        });
      }
    }),

  /**
   * Publish content to Facebook page
   */
  publishToFacebook: protectedProcedure
    .input(z.object({
      pageId: z.string(),
      postId: z.number(),
      message: z.string(),
      imageUrl: z.string().optional(),
    }))
    .mutation(async ({ ctx, input }) => {
      try {
        // Get Meta account
        const account = await metaDb.getMetaAccount(ctx.user.id, input.pageId);
        if (!account) {
          throw new TRPCError({
            code: "NOT_FOUND",
            message: "Facebook page not found",
          });
        }

        // Extract plain text from JSON carousel content if needed
        let message = input.message;
        try {
          const parsed = JSON.parse(input.message);
          if (parsed.caption) {
            const hashtags = Array.isArray(parsed.hashtags) ? '\n\n' + parsed.hashtags.join(' ') : '';
            message = parsed.caption + hashtags;
          }
        } catch {
          // Not JSON, use as-is
        }

        // Publish to Facebook
        const result = await metaApi.postToFacebookPage(
          input.pageId,
          account.accessToken,
          message,
          input.imageUrl
        );

        // Update post status in database
        const db = await getDb();
        if (db) {
          await db
            .update(contentPosts)
            .set({
              status: "published",
              publishedAt: new Date(),
              metaPostId: result.id ? String(result.id) : null,
            } as any)
            .where(eq(contentPosts.id, input.postId));
        }

        return {
          success: true,
          postId: result.id,
        };
      } catch (error) {
        console.error("[Meta API] Facebook publish error:", error);
        throw new TRPCError({
          code: "INTERNAL_SERVER_ERROR",
          message: "Failed to publish to Facebook",
        });
      }
    }),

  /**
   * Disconnect Meta account
   */
  disconnectAccount: protectedProcedure
    .input(z.object({
      accountId: z.string(),
    }))
    .mutation(async ({ ctx, input }) => {
      try {
        const success = await metaDb.deactivateMetaAccount(ctx.user.id, input.accountId);
        if (!success) {
          throw new TRPCError({
            code: "NOT_FOUND",
            message: "Account not found",
          });
        }

        return { success: true };
      } catch (error) {
        console.error("[Meta API] Disconnect error:", error);
        throw new TRPCError({
          code: "INTERNAL_SERVER_ERROR",
          message: "Failed to disconnect account",
        });
      }
    }),

  /**
   * Fetch insights for a published post from Meta Graph API
   */
  getPostInsights: protectedProcedure
    .input(z.object({
      postId: z.number(),        // our DB post ID
      metaPostId: z.string(),    // Meta Graph post ID
      accountId: z.string(),     // Meta account ID (for token lookup)
    }))
    .query(async ({ ctx, input }) => {
      try {
        const account = await metaDb.getMetaAccount(ctx.user.id, input.accountId);
        if (!account) throw new TRPCError({ code: "NOT_FOUND", message: "Account not found" });

        const token = account.accessToken;
        const fields = "reach,impressions,like_count,comments_count,shares,saved";

        // Try IG insights first, then FB
        let insights: Record<string, number> = {};
        try {
          const igRes = await fetch(
            `https://graph.facebook.com/v19.0/${input.metaPostId}/insights?metric=reach,impressions,saved&access_token=${token}`
          );
          if (igRes.ok) {
            const igData = await igRes.json() as any;
            for (const item of igData?.data ?? []) {
              insights[item.name] = item.values?.[0]?.value ?? item.value ?? 0;
            }
          }
        } catch {}

        // Also fetch basic fields (likes, comments work on both FB/IG)
        try {
          const basicRes = await fetch(
            `https://graph.facebook.com/v19.0/${input.metaPostId}?fields=${fields}&access_token=${token}`
          );
          if (basicRes.ok) {
            const basicData = await basicRes.json() as any;
            if (basicData.like_count !== undefined) insights.likes = basicData.like_count;
            if (basicData.comments_count !== undefined) insights.comments = basicData.comments_count;
            if (basicData.shares?.count !== undefined) insights.shares = basicData.shares.count;
          }
        } catch {}

        // Cache in DB
        const db = await getDb();
        if (db && (insights.reach || insights.impressions)) {
          await db.update(contentPosts).set({
            metaReach: insights.reach ?? null,
            metaImpressions: insights.impressions ?? null,
            metaLikes: insights.likes ?? null,
          } as any).where(eq(contentPosts.id, input.postId));
        }

        return {
          reach: insights.reach ?? null,
          impressions: insights.impressions ?? null,
          likes: insights.likes ?? null,
          comments: insights.comments ?? null,
          shares: insights.shares ?? null,
          saved: insights.saved ?? null,
        };
      } catch (error) {
        console.error("[Meta API] Insights error:", error);
        throw new TRPCError({ code: "INTERNAL_SERVER_ERROR", message: "Failed to fetch insights" });
      }
    }),
});
