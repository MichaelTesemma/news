import { serve } from "https://deno.land/std@0.177.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.48.1";
import { corsHeaders, handleCors, jsonResponse, textResponse } from "./_shared/cors.ts";

const supabaseUrl = Deno.env.get("SUPABASE_URL") ?? "";
const supabaseKey = Deno.env.get("SUPABASE_SERVICE_KEY") ?? "";
const supabase = createClient(supabaseUrl, supabaseKey);

const SITE_URL = Deno.env.get("SITE_URL") ?? "https://ethiopiadigest.com";

type Article = Record<string, unknown>;
interface PaginatedResult {
  items: Article[];
  total: number;
  page: number;
  pages: number;
}

async function listArticles(page: number, perPage: number, sourceId: number | null): Promise<PaginatedResult> {
  perPage = Math.min(perPage, 100);
  let query = supabase
    .from("articles")
    .select("*, source:source_id(name)", { count: "exact" })
    .order("published_at", { ascending: false, nullsFirst: false });
  if (sourceId) query = query.eq("source_id", sourceId);
  const from = (page - 1) * perPage;
  const to = from + perPage - 1;
  const { data, error, count } = await query.range(from, to);
  if (error) throw error;
  return {
    items: (data ?? []) as Article[],
    total: count ?? 0,
    page,
    pages: Math.ceil((count ?? 0) / perPage) || 1,
  };
}

function serializeArticle(a: Article): Record<string, unknown> {
  const src = a.source as { name?: string } | undefined;
  return {
    id: a.id,
    title: a.title,
    url: a.url,
    summary: a.summary ?? null,
    body: a.body ?? null,
    image_url: a.image_url ?? null,
    author: a.author ?? null,
    category: a.category ?? null,
    language: a.language ?? null,
    view_count: a.view_count ?? 0,
    source: src?.name ?? "",
    source_id: a.source_id ?? null,
    published_at: a.published_at ?? null,
    updated_at: a.updated_at ?? null,
  };
}

function serializeRelated(a: Article): Record<string, unknown> {
  const src = a.source as { name?: string } | undefined;
  return {
    id: a.id,
    title: a.title,
    url: a.url,
    summary: a.summary ?? null,
    image_url: a.image_url ?? null,
    source: src?.name ?? "",
    published_at: a.published_at ?? null,
  };
}

serve(async (req: Request) => {
  const corsCheck = handleCors(req);
  if (corsCheck) return corsCheck;

  const url = new URL(req.url);
  let path = url.pathname.replace(/^\/api/, "") || "/";
  if (path === "") path = "/";
  const params = url.searchParams;
  const method = req.method;

  try {
    // Sitemap
    if (path === "/sitemap.xml") return handleSitemap();

    // RSS
    if (path === "/rss.xml") return handleRSS(req);

    // Robots
    if (path === "/robots.txt") return handleRobots(req);

    // Articles
    const relatedMatch = path.match(/^\/articles\/(\d+)\/related$/);
    if (relatedMatch) return handleRelated(parseInt(relatedMatch[1]));

    const articleMatch = path.match(/^\/articles\/(\d+)$/);
    if (articleMatch) return handleArticle(parseInt(articleMatch[1]));

    if (path === "/articles/search") return handleSearch(params);
    if (path === "/articles/trending") return handleTrending();
    if (path === "/articles") return handleListArticles(params);

    // Other endpoints
    if (path === "/sources") return handleSources();
    if (path === "/categories") return handleCategories();
    if (path === "/dashboard") return handleDashboard();
    if (path === "/digest") return handleDigest();
    if (path === "/" || path === "") return handleIndex();

    return jsonResponse({ error: "Not found" }, 404);
  } catch (err) {
    console.error(err);
    const message = err instanceof Error ? err.message : "Internal error";
    return jsonResponse({ error: message }, 500);
  }
});

async function handleIndex(): Promise<Response> {
  return jsonResponse({
    name: "The Ethiopia Digest API",
    endpoints: {
      "GET /api/articles": "Paginated article list (?source=&page=&per_page=)",
      "GET /api/articles/:id": "Single article detail",
      "GET /api/articles/:id/related": "Related articles",
      "GET /api/articles/search": "Full-text search (?q=&page=&per_page=)",
      "GET /api/articles/trending": "Most viewed articles",
      "GET /api/categories": "All article categories",
      "GET /api/sources": "List all sources",
      "GET /api/dashboard": "Dashboard stats",
      "GET /api/digest": "Site info and metadata",
      "GET /sitemap.xml": "XML sitemap",
      "GET /robots.txt": "Robots exclusion",
      "GET /rss.xml": "RSS feed",
    },
  });
}

async function handleListArticles(params: URLSearchParams): Promise<Response> {
  const page = parseInt(params.get("page") || "1");
  const perPage = parseInt(params.get("per_page") || "20");
  const sourceId = params.has("source") ? parseInt(params.get("source")!) : null;
  const result = await listArticles(page, perPage, sourceId);
  return jsonResponse({
    articles: result.items.map(serializeArticle),
    page: result.page,
    pages: result.pages,
    total: result.total,
  });
}

async function handleArticle(id: number): Promise<Response> {
  const { data, error } = await supabase
    .from("articles")
    .select("*, source:source_id(name)")
    .eq("id", id)
    .single();
  if (error || !data) return jsonResponse({ error: "not found" }, 404);

  const words = ((data.body as string) ?? "").split(/\s+/).length;
  const readingTime = Math.max(1, Math.round(words / 200));

  await supabase.rpc("increment_view_count", { article_id: id }).catch(() => {
    supabase.from("articles").update({ view_count: (data.view_count ?? 0) + 1 }).eq("id", id).then();
  });

  const result = serializeArticle(data as Article);
  result.reading_time = readingTime;
  return jsonResponse(result);
}

async function handleRelated(id: number): Promise<Response> {
  const { data: article, error } = await supabase
    .from("articles")
    .select("source_id, category")
    .eq("id", id)
    .single();
  if (error || !article) return jsonResponse({ error: "not found" }, 404);

  let query = supabase
    .from("articles")
    .select("*, source:source_id(name)")
    .neq("id", id)
    .limit(6);

  if (article.category) {
    query = query.eq("category", article.category);
  } else {
    query = query.eq("source_id", article.source_id);
  }

  const { data: related } = await query;
  const articles = (related ?? [])
    .filter((a: Article) => a.body)
    .map(serializeRelated);
  return jsonResponse({ articles });
}

async function handleSearch(params: URLSearchParams): Promise<Response> {
  const q = params.get("q")?.trim() ?? "";
  const page = parseInt(params.get("page") || "1");
  const perPage = Math.min(parseInt(params.get("per_page") || "30"), 100);

  if (!q) return jsonResponse({ articles: [], total: 0, page: 1, pages: 0 });

  const from = (page - 1) * perPage;
  const to = from + perPage - 1;

  const { data, error, count } = await supabase
    .from("articles")
    .select("*, source:source_id(name)", { count: "exact" })
    .or(`title.ilike.%${q}%,summary.ilike.%${q}%,author.ilike.%${q}%`)
    .order("published_at", { ascending: false, nullsFirst: false })
    .range(from, to);

  if (error) throw error;

  const articles = (data ?? []).map((a: Article) => {
    const src = a.source as { name?: string } | undefined;
    return {
      id: a.id,
      title: a.title,
      url: a.url,
      summary: a.summary ?? null,
      image_url: a.image_url ?? null,
      source: src?.name ?? "",
      source_id: a.source_id ?? null,
      author: a.author ?? null,
      category: a.category ?? null,
      language: a.language ?? null,
      published_at: a.published_at ?? null,
    };
  });

  return jsonResponse({
    articles,
    page,
    pages: Math.ceil((count ?? 0) / perPage) || 1,
    total: count ?? 0,
  });
}

async function handleTrending(): Promise<Response> {
  const { data, error } = await supabase
    .from("articles")
    .select("*, source:source_id(name)")
    .gt("view_count", 0)
    .order("view_count", { ascending: false })
    .limit(10);
  if (error) throw error;

  return jsonResponse({
    articles: (data ?? []).map((a: Article) => {
      const src = a.source as { name?: string } | undefined;
      return {
        id: a.id,
        title: a.title,
        url: a.url,
        summary: a.summary ?? null,
        image_url: a.image_url ?? null,
        source: src?.name ?? "",
        view_count: a.view_count ?? 0,
        published_at: a.published_at ?? null,
      };
    }),
  });
}

async function handleSources(): Promise<Response> {
  const { data: sources } = await supabase.from("sources").select("*").order("name");

  const { count: enCount } = await supabase
    .from("articles")
    .select("*", { count: "exact", head: true })
    .eq("language", "en");

  const { count: amCount } = await supabase
    .from("articles")
    .select("*", { count: "exact", head: true })
    .eq("language", "am");

  return jsonResponse({
    sources: sources ?? [],
    lang_en: enCount ?? 0,
    lang_am: amCount ?? 0,
  });
}

async function handleCategories(): Promise<Response> {
  const { data, error } = await supabase
    .from("articles")
    .select("category");
  if (error) throw error;

  const counts = new Map<string, number>();
  for (const row of data ?? []) {
    const cat = (row.category as string)?.trim();
    if (cat) counts.set(cat, (counts.get(cat) ?? 0) + 1);
  }

  return jsonResponse({
    categories: Array.from(counts.entries())
      .sort((a, b) => b[1] - a[1])
      .map(([name, count]) => ({ name, count })),
  });
}

async function handleDashboard(): Promise<Response> {
  const { data: sources } = await supabase.from("sources").select("*").order("name");

  const { count: totalArticles } = await supabase
    .from("articles")
    .select("*", { count: "exact", head: true });

  const { count: enCount } = await supabase
    .from("articles")
    .select("*", { count: "exact", head: true })
    .eq("language", "en");

  const { count: amCount } = await supabase
    .from("articles")
    .select("*", { count: "exact", head: true })
    .eq("language", "am");

  return jsonResponse({
    total_articles: totalArticles ?? 0,
    total_sources: (sources ?? []).length,
    lang_en: enCount ?? 0,
    lang_am: amCount ?? 0,
    sources: sources ?? [],
  });
}

async function handleDigest(): Promise<Response> {
  const { count: total } = await supabase
    .from("articles")
    .select("*", { count: "exact", head: true });

  const { count: en } = await supabase
    .from("articles")
    .select("*", { count: "exact", head: true })
    .eq("language", "en");

  const { count: am } = await supabase
    .from("articles")
    .select("*", { count: "exact", head: true })
    .eq("language", "am");

  const { count: sourceCount } = await supabase
    .from("sources")
    .select("*", { count: "exact", head: true });

  const { data: newest } = await supabase
    .from("articles")
    .select("*, source:source_id(name)")
    .order("published_at", { ascending: false, nullsFirst: false })
    .limit(1)
    .single();

  return jsonResponse({
    name: "The Ethiopia Digest",
    description: "Curated news from across Ethiopia's media landscape. English and Amharic articles from independent sources.",
    total_articles: total ?? 0,
    total_sources: sourceCount ?? 0,
    lang_en: en ?? 0,
    lang_am: am ?? 0,
    newest_article: newest ? serializeArticle(newest as Article) : null,
  });
}

function handleRobots(req: Request): Response {
  const siteUrl = new URL(req.url).origin;
  return textResponse(
    `User-agent: *\nAllow: /\nSitemap: ${siteUrl}/sitemap.xml\n`,
  );
}

async function handleSitemap(): Promise<Response> {
  const siteUrl = SITE_URL;

  const { data: articles } = await supabase
    .from("articles")
    .select("id, published_at")
    .order("published_at", { ascending: false, nullsFirst: false })
    .limit(500);

  const urls = [
    { loc: siteUrl, priority: "1.0" },
    { loc: `${siteUrl}/search`, priority: "0.8" },
    { loc: `${siteUrl}/bookmarks`, priority: "0.3" },
  ];

  for (const a of articles ?? []) {
    urls.push({
      loc: `${siteUrl}/article/${a.id}`,
      lastmod: a.published_at ?? new Date().toISOString(),
      priority: "0.9",
    });
  }

  const xml = [
    `<?xml version="1.0" encoding="UTF-8"?>`,
    `<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">`,
    ...urls.map((u) => {
      let entry = `  <url><loc>${u.loc}</loc><priority>${u.priority}</priority>`;
      if ("lastmod" in u) entry += `<lastmod>${u.lastmod}</lastmod>`;
      entry += `</url>`;
      return entry;
    }),
    `</urlset>`,
  ].join("\n");

  return textResponse(xml, 200, "application/xml");
}

async function handleRSS(req: Request): Promise<Response> {
  const siteUrl = SITE_URL;

  const { data: articles } = await supabase
    .from("articles")
    .select("*, source:source_id(name)")
    .order("published_at", { ascending: false, nullsFirst: false })
    .limit(50);

  const nowStr = new Date().toUTCString();

  const items = (articles ?? []).map((a: Article) => {
    const src = a.source as { name?: string } | undefined;
    const pub = a.published_at ? new Date(a.published_at as string).toUTCString() : nowStr;
    const desc = ((a.summary ?? a.body ?? "") as string).slice(0, 500)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    const title = (a.title as string ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    return `    <item>
      <title>${title}</title>
      <link>${siteUrl}/article/${a.id}</link>
      <guid>${siteUrl}/article/${a.id}</guid>
      <pubDate>${pub}</pubDate>
      <description>${desc}</description>
      <source>${src?.name ?? ""}</source>
    </item>`;
  }).join("\n");

  const rss = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>The Ethiopia Digest</title>
    <link>${siteUrl}</link>
    <description>Curated news from across Ethiopia's media landscape</description>
    <language>en</language>
    <lastBuildDate>${nowStr}</lastBuildDate>
    <atom:link href="${siteUrl}/rss.xml" rel="self" type="application/rss+xml"/>
${items}
  </channel>
</rss>`;

  return textResponse(rss, 200, "application/rss+xml");
}
