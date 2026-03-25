import { eq, and, desc, gte, sql } from "drizzle-orm";
import { drizzle } from "drizzle-orm/mysql2";
import { articleAnalyses, ArticleAnalysis, InsertArticleAnalysis } from "../drizzle/schema";

let _db: ReturnType<typeof drizzle> | null = null;

async function getDb() {
  if (!_db && process.env.DATABASE_URL) {
    try {
      _db = drizzle(process.env.DATABASE_URL);
    } catch (error) {
      console.warn("[Database] Failed to connect:", error);
      _db = null;
    }
  }
  return _db;
}

export async function saveArticleAnalysis(
  userId: number,
  data: Omit<InsertArticleAnalysis, 'userId'>
): Promise<number | null> {
  const db = await getDb();
  if (!db) throw new Error("Database not available");

  const result = await db.insert(articleAnalyses).values({ ...data, userId });
  return (result as any)?.[0]?.insertId ?? (result as any)?.insertId ?? null;
}

export async function getUserAnalysisHistory(
  userId: number,
  limit = 5000
): Promise<ArticleAnalysis[]> {
  const db = await getDb();
  if (!db) return [];

  return db
    .select()
    .from(articleAnalyses)
    .where(eq(articleAnalyses.userId, userId))
    .orderBy(desc(articleAnalyses.createdAt))
    .limit(limit);
}

export async function getAnalysisById(
  userId: number,
  id: number
): Promise<ArticleAnalysis | null> {
  const db = await getDb();
  if (!db) return null;

  const result = await db
    .select()
    .from(articleAnalyses)
    .where(and(eq(articleAnalyses.userId, userId), eq(articleAnalyses.id, id)))
    .limit(1);

  return result[0] || null;
}

export async function deleteAnalysis(userId: number, id: number): Promise<boolean> {
  const db = await getDb();
  if (!db) return false;

  await db
    .delete(articleAnalyses)
    .where(and(eq(articleAnalyses.userId, userId), eq(articleAnalyses.id, id)));

  return true;
}

export interface ProgressStats {
  totalImproved: number;
  improvedThisWeek: number;
  improvedThisMonth: number;
  avgSeoScore: number;
  avgWordsBefore: number;
  topSeoScore: number;
}

export async function getProgressStats(userId: number): Promise<ProgressStats> {
  const db = await getDb();
  if (!db) return { totalImproved: 0, improvedThisWeek: 0, improvedThisMonth: 0, avgSeoScore: 0, avgWordsBefore: 0, topSeoScore: 0 };

  const weekAgo  = new Date(Date.now() - 7  * 24 * 60 * 60 * 1000);
  const monthAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);

  const [all, thisWeek, thisMonth] = await Promise.all([
    db.select({
      count:        sql<number>`COUNT(DISTINCT url)`,
      avgSeoScore:  sql<number>`ROUND(AVG(seoScore), 0)`,
      avgWordsBefore: sql<number>`ROUND(AVG(wordCount), 0)`,
      topSeoScore:  sql<number>`MAX(seoScore)`,
    })
    .from(articleAnalyses)
    .where(eq(articleAnalyses.userId, userId)),

    db.select({ count: sql<number>`COUNT(DISTINCT url)` })
    .from(articleAnalyses)
    .where(and(eq(articleAnalyses.userId, userId), gte(articleAnalyses.createdAt, weekAgo))),

    db.select({ count: sql<number>`COUNT(DISTINCT url)` })
    .from(articleAnalyses)
    .where(and(eq(articleAnalyses.userId, userId), gte(articleAnalyses.createdAt, monthAgo))),
  ]);

  const row = all[0];
  return {
    totalImproved:    Number(row?.count ?? 0),
    improvedThisWeek:  Number(thisWeek[0]?.count ?? 0),
    improvedThisMonth: Number(thisMonth[0]?.count ?? 0),
    avgSeoScore:       Number(row?.avgSeoScore ?? 0),
    avgWordsBefore:    Number(row?.avgWordsBefore ?? 0),
    topSeoScore:       Number(row?.topSeoScore ?? 0),
  };
}

export interface LibraryEntry {
  url: string;
  originalTitle: string;
  improvedTitle: string;
  bestSeoScore: number;
  latestWordCount: number;
  versionsCount: number;
  latestCreatedAt: Date;
  latestId: number;
  googlePos: number | null;
  yandexPos: number | null;
}

/**
 * Library: one entry per URL, latest version data + version count
 */
export async function getLibrary(userId: number): Promise<LibraryEntry[]> {
  const db = await getDb();
  if (!db) return [];

  // Drizzle doesn't support GROUP BY + subquery cleanly — use raw SQL
  const rows = await db.execute(sql`
    SELECT
      a.url,
      a.originalTitle,
      a.improvedTitle,
      MAX(a.seoScore)   AS bestSeoScore,
      (SELECT aa.wordCount  FROM articleAnalyses aa WHERE aa.userId = ${userId} AND aa.url = a.url ORDER BY aa.createdAt DESC LIMIT 1) AS latestWordCount,
      COUNT(*)           AS versionsCount,
      MAX(a.createdAt)   AS latestCreatedAt,
      (SELECT aa.id FROM articleAnalyses aa WHERE aa.userId = ${userId} AND aa.url = a.url ORDER BY aa.createdAt DESC LIMIT 1) AS latestId,
      (SELECT aa.googlePos FROM articleAnalyses aa WHERE aa.userId = ${userId} AND aa.url = a.url ORDER BY aa.createdAt DESC LIMIT 1) AS googlePos,
      (SELECT aa.yandexPos FROM articleAnalyses aa WHERE aa.userId = ${userId} AND aa.url = a.url ORDER BY aa.createdAt DESC LIMIT 1) AS yandexPos
    FROM articleAnalyses a
    WHERE a.userId = ${userId}
    GROUP BY a.url, a.originalTitle, a.improvedTitle
    ORDER BY MAX(a.createdAt) DESC
  `) as any;

  const data = Array.isArray(rows) ? (Array.isArray(rows[0]) ? rows[0] : rows) : [];
  return data.map((r: any) => ({
    url: r.url,
    originalTitle: r.originalTitle,
    improvedTitle: r.improvedTitle,
    bestSeoScore: Number(r.bestSeoScore ?? 0),
    latestWordCount: Number(r.latestWordCount ?? 0),
    versionsCount: Number(r.versionsCount ?? 1),
    latestCreatedAt: new Date(r.latestCreatedAt),
    latestId: Number(r.latestId ?? 0),
    googlePos: r.googlePos != null ? Number(r.googlePos) : null,
    yandexPos: r.yandexPos != null ? Number(r.yandexPos) : null,
  }));
}

/**
 * All versions (runs) for a specific URL, newest first
 */
export async function getArticleVersions(
  userId: number,
  url: string
): Promise<Array<{ id: number; seoScore: number; wordCount: number; createdAt: Date; improvedTitle: string }>> {
  const db = await getDb();
  if (!db) return [];

  const rows = await db
    .select({
      id: articleAnalyses.id,
      seoScore: articleAnalyses.seoScore,
      wordCount: articleAnalyses.wordCount,
      createdAt: articleAnalyses.createdAt,
      improvedTitle: articleAnalyses.improvedTitle,
    })
    .from(articleAnalyses)
    .where(and(eq(articleAnalyses.userId, userId), eq(articleAnalyses.url, url)))
    .orderBy(desc(articleAnalyses.createdAt));

  return rows;
}
