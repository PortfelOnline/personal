export type ArticleStatus = 'todo' | 'in_progress' | 'done';

export interface PosSnapshot {
  date: string; // YYYY-MM-DD
  googlePos: number | null;
  yandexPos: number | null;
}

// ─── News ────────────────────────────────────────────────────────────────────
export interface KadmapNews {
  postId: number;
  slug: string;
  title: string;
  keyword?: string; // for SERP position check
  publishedAt: string; // YYYY-MM-DD
  images?: number;
}

export interface NewsProgress {
  googlePos?: number | null;
  yandexPos?: number | null;
  prevGooglePos?: number | null;
  prevYandexPos?: number | null;
  posCheckedAt?: string;
  posHistory?: PosSnapshot[];
  top3Google?: { pos: number; domain: string; title: string }[];
}

export const KADMAP_NEWS: KadmapNews[] = [
  {
    postId: 333241,
    slug: 'rosreestr-2026-proverka-obremenij-stala-obyazatelnoj-pri-ipotechnykh-sdelkakh',
    title: 'Росреестр 2026: проверка обременений стала обязательной при ипотечных сделках',
    keyword: 'росреестр 2026 проверка обременений',
    publishedAt: '2026-03-25',
    images: 5,
  },
];

export const NEWS_STORAGE_KEY = 'kadmap_news_progress';

export function loadNewsProgress(): Record<number, NewsProgress> {
  try {
    const raw = localStorage.getItem(NEWS_STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch { return {}; }
}

export function saveNewsProgress(p: Record<number, NewsProgress>): void {
  localStorage.setItem(NEWS_STORAGE_KEY, JSON.stringify(p));
}

export interface KadmapArticle {
  postId: number;
  slug: string;
  title: string;
  keyword?: string; // main target keyword for SERP check
  priority: 'high' | 'medium' | 'low';
  wordsBefore?: number;
  seoScoreBefore?: number;
  reason: string; // why this article matters
  needsMap?: boolean; // whether wp outmap=1 should be set (map widget shown)
}

/** Auto-detect if an article should show the map widget (outmap=1 in WordPress) */
export function getMapFlag(slug: string): boolean {
  const mapSlugs = ['karta', 'raspolozhenie', 'plan', 'mezhevanie', 'sputnik', 'uchastok', 'kadastr-'];
  const noMapSlugs = ['obremenenie', 'arest', 'zalog', 'dolg', 'proverit', 'snyat', 'uznat'];
  const s = slug.toLowerCase();
  if (noMapSlugs.some(k => s.includes(k))) return false;
  if (mapSlugs.some(k => s.includes(k))) return true;
  return false;
}

export interface ArticleProgress {
  status: ArticleStatus;
  wordsAfter?: number;
  seoScoreAfter?: number;
  doneAt?: string; // ISO date
  notes?: string;
  googlePos?: number | null;
  yandexPos?: number | null;
  prevGooglePos?: number | null;
  prevYandexPos?: number | null;
  posCheckedAt?: string;
  posHistory?: PosSnapshot[];
  top3Google?: { pos: number; domain: string; title: string }[];
  top3Yandex?: { pos: number; domain: string; title: string }[];
}

// Sorted by conversion potential (buyer intent)
export const KADMAP_ARTICLES: KadmapArticle[] = [
  // ✅ ETALON
  {
    postId: 332861,
    slug: 'zakazat-spravku-ob-obremenenii-nedvizhimosti-v-moskve-poshagovoe-rukovodstvo',
    title: 'Заказать справку об обременении недвижимости в Москве — пошаговое руководство',
    priority: 'high',
    wordsBefore: 800,
    seoScoreBefore: 90,
    reason: 'Эталонная статья — стандарт для всех остальных',
  },
  // ✅ DONE
  {
    postId: 5535,
    slug: 'kak-proverit-kvartiru-na-obremenenie-pri-pokupke',
    title: 'Как проверить квартиру на обременение при покупке',
    keyword: 'как проверить квартиру на обременение при покупке',
    priority: 'high',
    wordsBefore: 436,
    seoScoreBefore: 75,
    reason: 'Горячий buyer intent — человек готов купить документ',
  },
  {
    postId: 4299,
    slug: 'proverit-kvartiru-na-obremenenie-onlajn',
    title: 'Проверить квартиру на обременение онлайн',
    keyword: 'проверить квартиру на обременение онлайн',
    priority: 'high',
    reason: 'Транзакционный запрос, высокий intent',
  },
  {
    postId: 4305,
    slug: 'kak-proverit-kvartiru-na-obremenenie',
    title: 'Как проверить квартиру на обременение',
    keyword: 'как проверить квартиру на обременение',
    priority: 'high',
    reason: 'Основной информационный запрос кластера',
  },
  {
    postId: 5607,
    slug: 'proverit-kvartiru-arest-sudebnyh-pristavov',
    title: 'Проверить квартиру арест судебных приставов',
    keyword: 'проверить квартиру арест судебных приставов',
    priority: 'high',
    reason: 'Buyer с острой проблемой — высокая конверсия',
  },
  {
    postId: 7129,
    slug: 'gde-proverit-kvartiru-na-obremenenie',
    title: 'Где проверить квартиру на обременение?',
    keyword: 'где проверить квартиру на обременение',
    priority: 'high',
    reason: 'BOFU-запрос с явным intent купить',
  },
  // ✅ DONE — второй батч 2026-03-25
  {
    postId: 4302,
    slug: 'kak-uznat-est-li-obremenenie-na-kvartiru',
    title: 'Как узнать обременение на квартиру через интернет',
    keyword: 'как узнать обременение на квартиру',
    priority: 'high',
    reason: 'Информационный + транзакционный интент',
  },
  {
    postId: 4308,
    slug: 'kak-uznat-nalozhen-li-arest-na-kvartiru',
    title: 'Как узнать наложен ли арест на квартиру?',
    keyword: 'как узнать наложен ли арест на квартиру',
    priority: 'high',
    reason: 'Острая проблема — человек ищет выход',
  },
  {
    postId: 5522,
    slug: 'kak-uznat-kvartira-v-areste-ili-net',
    title: 'Как узнать квартира в аресте или нет',
    keyword: 'как узнать квартира в аресте или нет',
    priority: 'high',
    reason: 'Бинарный вопрос с высоким intent',
  },
  {
    postId: 5558,
    slug: 'kak-uznat-kvartira-v-zaloge-ili-net',
    title: 'Как узнать квартира в залоге или нет',
    keyword: 'как узнать квартира в залоге или нет',
    priority: 'high',
    reason: 'Залог/ипотека — горячий intent перед сделкой',
  },
  // ✅ DONE — кадастровая карта / расположение батч 2026-03-25
  {
    postId: 732,
    slug: 'raspolozhenie-po-kadastrovomu-nomeru',
    title: 'Расположение земельного участка по кадастровому номеру',
    keyword: 'расположение по кадастровому номеру',
    priority: 'high',
    wordsBefore: 200,
    seoScoreBefore: 55,
    reason: 'G#3 — уже в топ-3, реврайт поднимет до #1',
    needsMap: true,
  },
  {
    postId: 1111,
    slug: 'kadastrovaya-publichnaya-karta-so-sputnika',
    title: 'Кадастровая публичная карта со спутника',
    keyword: 'кадастровая публичная карта со спутника',
    priority: 'high',
    wordsBefore: 1777,
    seoScoreBefore: 55,
    reason: 'G#4 — реврайт до эталона переведёт в топ-1/2',
    needsMap: true,
  },
  {
    postId: 8751,
    slug: 'kadastrovyj-plan-kvartiry-po-adresu',
    title: 'Кадастровый план квартиры по адресу',
    keyword: 'кадастровый план квартиры по адресу',
    priority: 'high',
    wordsBefore: 2586,
    seoScoreBefore: 50,
    reason: 'G#4 — низкий SEO score, нужен полный реврайт',
    needsMap: true,
  },
  // Средний приоритет — TODO
  {
    postId: 331661,
    slug: 'kak-snyat-obremenenie-posle-pogasheniya-ipoteki',
    title: 'Как снять обременение после погашения ипотеки',
    priority: 'medium',
    reason: 'Ипотечный кластер — переход к заказу выписки',
  },
  {
    postId: 4312,
    slug: 'proverit-kvartiru-na-dolgi-pered-pokupkoy',
    title: 'Проверить квартиру на долги перед покупкой',
    priority: 'medium',
    reason: 'Покупатели вторичного жилья — ID=4312 это attachment, не post! Требует создания нового поста',
  },
  {
    postId: 5707,
    slug: 'vypiska-egrp-obremeneniem',
    title: 'Как узнать есть ли обременение на квартиру',
    priority: 'medium',
    reason: 'Высокочастотный информационный запрос',
  },
];

export const STORAGE_KEY = 'kadmap_article_progress';

export function loadProgress(): Record<number, ArticleProgress> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

export function saveProgress(progress: Record<number, ArticleProgress>): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(progress));
}

// Seed initial known statuses
export const INITIAL_PROGRESS: Record<number, ArticleProgress> = {
  332861: {
    status: 'done',
    wordsAfter: 3440,
    seoScoreAfter: 100,
    doneAt: '2026-03-01',
    notes: 'Эталонная статья — все PageSpeed/SEO оптимизации применены. Метадеск исправлен 2026-03-25 (убран хардкод цены)',
  },
  5535: {
    status: 'done',
    wordsAfter: 2877,
    doneAt: '2026-03-25',
    notes: '17 H2, 10 FAQ, 9 тематических картинок, метадеск обновлён',
  },
  4299: {
    status: 'done',
    wordsAfter: 3200,
    doneAt: '2026-03-25',
    notes: '15 H2, 11 FAQ, 9 картинок, транзакционный интент. BLOCK_PRICE, [PRICE_3_DISC], отзывы',
  },
  4305: {
    status: 'done',
    wordsAfter: 3100,
    doneAt: '2026-03-25',
    notes: '15 H2, 3 H3, 11 FAQ, 9 картинок, how-to информационный интент. CTA=10 (доработано 2026-03-25)',
  },
  5607: {
    status: 'done',
    wordsAfter: 3300,
    doneAt: '2026-03-25',
    notes: '15 H2, 11 FAQ, 9 картинок, проблемный/срочный интент (арест ФССП). CTA=10 (доработано 2026-03-25)',
  },
  7129: {
    status: 'done',
    wordsAfter: 3000,
    doneAt: '2026-03-25',
    notes: '15 H2, 11 FAQ, 9 картинок, BOFU-сравнение сервисов. Таблица сравнения способов',
  },
  4302: {
    status: 'done',
    wordsAfter: 3100,
    doneAt: '2026-03-25',
    notes: '15 H2, 11 FAQ, 9 картинок, информационный+транзакционный интент. image016 из 2017/04/',
  },
  4308: {
    status: 'done',
    wordsAfter: 3200,
    doneAt: '2026-03-25',
    notes: '15 H2, 3 H3, 10 FAQ, 9 картинок, острая проблема — арест на квартиру',
  },
  5522: {
    status: 'done',
    wordsAfter: 3000,
    doneAt: '2026-03-25',
    notes: '15 H2, 10 FAQ, 9 картинок, бинарный вопрос. Таблица Арест vs Запрет',
  },
  5558: {
    status: 'done',
    wordsAfter: 3100,
    doneAt: '2026-03-25',
    notes: '15 H2, 10 FAQ, 9 картинок, залог/ипотека интент. Особенности по банкам (Сбер/ВТБ/Альфа)',
  },
  331661: {
    status: 'todo',
    notes: 'ID исправлен (был 5464 = revision). Требует реврайта до эталонного стандарта',
  },
  4312: {
    status: 'todo',
    notes: 'ID=4312 — attachment (изображение), не статья. Требует создания нового поста с правильным postId',
  },
  5707: {
    status: 'done',
    wordsAfter: 3100,
    doneAt: '2026-03-25',
    notes: '15 H2, 10 FAQ, 9 картинок, информационный запрос. 3 способа проверки. CTA=14, BLOCK_PRICE, отзывы',
  },
  732: {
    status: 'done',
    wordsAfter: 2450,
    doneAt: '2026-03-25',
    notes: '24 H2, 11 FAQ, 9 картинок, BLOCK_PRICE, CTA=9. Охранные зоны, межевание, реестровая ошибка, таблица способов. G#3 → цель #1',
  },
  1111: {
    status: 'done',
    wordsAfter: 1800,
    doneAt: '2026-03-25',
    notes: '17 H2, 11 FAQ, 9 картинок, BLOCK_PRICE, CTA=9. Спутниковый режим, охранные зоны, сравнение с Google Maps, таблица. G#4 → цель #1/2',
  },
  8751: {
    status: 'done',
    wordsAfter: 3500,
    doneAt: '2026-03-25',
    notes: '20 H2, 5 H3, 10 FAQ, 9 картинок, BLOCK_PRICE, CTA=9. Перепланировка, наследование, суд/раздел имущества. G#4 → цель #1/2',
  },
};
