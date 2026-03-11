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
