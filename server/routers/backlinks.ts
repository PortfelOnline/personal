import { router, protectedProcedure } from "../_core/trpc";
import { z } from "zod";
import { TRPCError } from "@trpc/server";
import {
  getAllBacklinkPosts, getBacklinkPost, updateBacklinkPost,
  deleteBacklinkPost, getStatsByPlatform,
} from "../backlinks.db";
import { publishPost, publishNext, generateAndQueue } from "../publishers/pub-index";
import { PRIORITY_PAGES } from "../publishers/content-generator";

const PLATFORM = z.enum(["dzen", "spark", "kw"]);

export const backlinksRouter = router({
  getQueue: protectedProcedure
    .query(() => getAllBacklinkPosts()),

  getStats: protectedProcedure
    .query(() => getStatsByPlatform()),

  generate: protectedProcedure
    .input(z.object({ platform: PLATFORM, targetUrl: z.string().optional() }))
    .mutation(async ({ input }) => {
      if (input.targetUrl && !PRIORITY_PAGES.find(p => p.url === input.targetUrl)) {
        throw new TRPCError({ code: "BAD_REQUEST", message: "Unknown target URL" });
      }
      const id = await generateAndQueue(input.platform, input.targetUrl);
      return { id };
    }),

  publish: protectedProcedure
    .input(z.object({ id: z.number() }))
    .mutation(async ({ input }) => {
      const post = await getBacklinkPost(input.id);
      if (!post) throw new TRPCError({ code: "NOT_FOUND" });
      if (post.status === "publishing" || post.status === "published") {
        throw new TRPCError({ code: "BAD_REQUEST", message: `Post already ${post.status}` });
      }
      await updateBacklinkPost(post.id, { status: "pending" });
      await publishPost({ ...post, status: "pending" });
      return { ok: true };
    }),

  publishNext: protectedProcedure
    .input(z.object({ platform: PLATFORM }))
    .mutation(async ({ input }) => {
      await publishNext(input.platform);
      return { ok: true };
    }),

  retry: protectedProcedure
    .input(z.object({ id: z.number() }))
    .mutation(async ({ input }) => {
      const post = await getBacklinkPost(input.id);
      if (!post) throw new TRPCError({ code: "NOT_FOUND" });
      await updateBacklinkPost(post.id, { status: "pending", errorMsg: null as any });
      return { ok: true };
    }),

  delete: protectedProcedure
    .input(z.object({ id: z.number() }))
    .mutation(async ({ input }) => {
      await deleteBacklinkPost(input.id);
      return { ok: true };
    }),
});
