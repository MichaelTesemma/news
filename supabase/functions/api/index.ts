import { withSupabase } from "npm:@supabase/server";

const SITE_URL = Deno.env.get("SITE_URL") ?? "https://ethiopiadigest.com";

interface Article {
  id: number;
  title: string;
  url: string;
  summary?: string;
  body?: string;
  image_url?: string;
  author?: string;
  category?: string;
  language?: string;
  view_count?: number;
  source_id?: number;
  published_at?: string;
  updated_at?: string;
  source?: { name: string } | null;
}

function serializeArticle(a: Article) {
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
    source: a.source?.name ?? "",
    source_id: a.source_id ?? null,
    published_at: a.published_at ?? null,
    updated_at: a.updated_at ?? null,
  };
}

function serializeRelated(a: Article) {
  return {
    id: a.id,
    title: a.title,
    url: a.url,
    summary: a.summary ?? null,
    image_url: a.image_url ?? null,
    source: a.source?.name ?? "",
    published_at: a.published_at ?? null,
  };
}

export default {
  fetch: withSupabase({ auth: "publishable" }, async (req, ctx) => {
    const url = new URL(req.url);
    const path = url.pathname.replace(/^\/api/, "") || "/";
    const params = url.searchParams;

    const { supabase: db, supabaseAdmin: admin } = ctx;

    try {
      // Sitemap
      if (path === "/sitemap.xml") {
        const { data: articles } = await db
          .from("articles")
          .select("id, published_at")
          .order("published_at", { ascending: false, nullsFirst: false })
          .limit(500);

        const urls = [
          { loc: SITE_URL, priority: "1.0" },
          { loc: `${SITE_URL}/search`, priority: "0.8" },
          { loc: `${SITE_URL}/bookmarks`, priority: "0.3" },
        ];

        for (const a of articles ?? []) {
          urls.push({
            loc: `${SITE_URL}/article/${a.id}`,
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

        return new Response(xml, {
          headers: { "Content-Type": "application/xml" },
        });
      }

      // RSS
      if (path === "/rss.xml") {
        const { data: articles } = await db
          .from("articles")
          .select("*, source:source_id(name)")
          .order("published_at", { ascending: false, nullsFirst: false })
          .limit(50);

        const nowStr = new Date().toUTCString();
        const items = (articles ?? []).map((a: Article) => {
          const pub = a.published_at
            ? new Date(a.published_at).toUTCString()
            : nowStr;
          const desc = (a.summary ?? a.body ?? "").toString().slice(0, 500)
            .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
          const title = (a.title ?? "").toString()
            .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
          return `    <item>
      <title>${title}</title>
      <link>${SITE_URL}/article/${a.id}</link>
      <guid>${SITE_URL}/article/${a.id}</guid>
      <pubDate>${pub}</pubDate>
      <description>${desc}</description>
      <source>${a.source?.name ?? ""}</source>
    </item>`;
        }).join("\n");

        const rss = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>The Ethiopia Digest</title>
    <link>${SITE_URL}</link>
    <description>Curated news from across Ethiopia's media landscape</description>
    <language>en</language>
    <lastBuildDate>${nowStr}</lastBuildDate>
    <atom:link href="${SITE_URL}/rss.xml" rel="self" type="application/rss+xml"/>
${items}
  </channel>
</rss>`;

        return new Response(rss, {
          headers: { "Content-Type": "application/rss+xml" },
        });
      }

      // Robots
      if (path === "/robots.txt") {
        return new Response(
          `User-agent: *\nAllow: /\nSitemap: ${SITE_URL}/sitemap.xml\n`,
          { headers: { "Content-Type": "text/plain" } },
        );
      }

      // Articles: related
      const relatedMatch = path.match(/^\/articles\/(\d+)\/related$/);
      if (relatedMatch) {
        const id = parseInt(relatedMatch[1]);
        const { data: article } = await db
          .from("articles")
          .select("source_id, category")
          .eq("id", id)
          .maybeSingle();

        if (!article) {
          return Response.json({ error: "not found" }, { status: 404 });
        }

        let query = db
          .from("articles")
          .select("*, source:source_id(name)")
          .neq("id", id)
          .limit(6);

        query = article.category
          ? query.eq("category", article.category)
          : query.eq("source_id", article.source_id);

        const { data: related } = await query;
        return Response.json({
          articles: (related ?? []).filter((a: Article) => a.body).map(serializeRelated),
        });
      }

      // Articles: single
      const articleMatch = path.match(/^\/articles\/(\d+)$/);
      if (articleMatch) {
        const id = parseInt(articleMatch[1]);
        const { data: article } = await db
          .from("articles")
          .select("*, source:source_id(name)")
          .eq("id", id)
          .maybeSingle();

        if (!article) {
          return Response.json({ error: "not found" }, { status: 404 });
        }

        const words = ((article.body as string) ?? "").split(/\s+/).length;
        const readingTime = Math.max(1, Math.round(words / 200));

        // Increment view count via admin client (bypasses RLS)
        await admin
          .from("articles")
          .update({ view_count: ((article.view_count as number) ?? 0) + 1 })
          .eq("id", id);

        const result = serializeArticle(article as Article);
        result.reading_time = readingTime;
        return Response.json(result);
      }

      // Articles: search
      if (path === "/articles/search") {
        const q = params.get("q")?.trim() ?? "";
        const page = parseInt(params.get("page") || "1");
        const perPage = Math.min(parseInt(params.get("per_page") || "30"), 100);

        if (!q) {
          return Response.json({ articles: [], total: 0, page: 1, pages: 0 });
        }

        const from = (page - 1) * perPage;
        const to = from + perPage - 1;

        const { data, error, count } = await db
          .from("articles")
          .select("*, source:source_id(name)", { count: "exact" })
          .or(`title.ilike.%${q}%,summary.ilike.%${q}%,author.ilike.%${q}%`)
          .order("published_at", { ascending: false, nullsFirst: false })
          .range(from, to);

        if (error) throw error;

        return Response.json({
          articles: (data ?? []).map((a: Article) => ({
            id: a.id,
            title: a.title,
            url: a.url,
            summary: a.summary ?? null,
            image_url: a.image_url ?? null,
            source: a.source?.name ?? "",
            source_id: a.source_id ?? null,
            author: a.author ?? null,
            category: a.category ?? null,
            language: a.language ?? null,
            published_at: a.published_at ?? null,
          })),
          page,
          pages: Math.ceil((count ?? 0) / perPage) || 1,
          total: count ?? 0,
        });
      }

      // Articles: trending
      if (path === "/articles/trending") {
        const { data, error } = await db
          .from("articles")
          .select("*, source:source_id(name)")
          .gt("view_count", 0)
          .order("view_count", { ascending: false })
          .limit(10);

        if (error) throw error;

        return Response.json({
          articles: (data ?? []).map((a: Article) => ({
            id: a.id,
            title: a.title,
            url: a.url,
            summary: a.summary ?? null,
            image_url: a.image_url ?? null,
            source: a.source?.name ?? "",
            view_count: a.view_count ?? 0,
            published_at: a.published_at ?? null,
          })),
        });
      }

      // Articles: list
      if (path === "/articles") {
        const page = parseInt(params.get("page") || "1");
        let perPage = parseInt(params.get("per_page") || "20");
        perPage = Math.min(perPage, 100);
        const sourceId = params.has("source") ? parseInt(params.get("source")!) : null;

        let query = db
          .from("articles")
          .select("*, source:source_id(name)", { count: "exact" })
          .order("published_at", { ascending: false, nullsFirst: false });

        if (sourceId) query = query.eq("source_id", sourceId);

        const from = (page - 1) * perPage;
        const to = from + perPage - 1;

        const { data, error, count } = await query.range(from, to);

        if (error) throw error;

        return Response.json({
          articles: (data ?? []).map(serializeArticle),
          page,
          pages: Math.ceil((count ?? 0) / perPage) || 1,
          total: count ?? 0,
        });
      }

      // Sources
      if (path === "/sources") {
        const { data: sources } = await db.from("sources").select("*").order("name");

        const enResult = await db
          .from("articles")
          .select("*", { count: "exact", head: true })
          .eq("language", "en");

        const amResult = await db
          .from("articles")
          .select("*", { count: "exact", head: true })
          .eq("language", "am");

        return Response.json({
          sources: sources ?? [],
          lang_en: enResult.count ?? 0,
          lang_am: amResult.count ?? 0,
        });
      }

      // Categories
      if (path === "/categories") {
        const { data, error } = await db.from("articles").select("category");
        if (error) throw error;

        const counts = new Map<string, number>();
        for (const row of data ?? []) {
          const cat = (row.category as string)?.trim();
          if (cat) counts.set(cat, (counts.get(cat) ?? 0) + 1);
        }

        return Response.json({
          categories: Array.from(counts.entries())
            .sort((a, b) => b[1] - a[1])
            .map(([name, count]) => ({ name, count })),
        });
      }

      // Dashboard
      if (path === "/dashboard") {
        const { data: sources } = await db.from("sources").select("*").order("name");

        const totalResult = await db
          .from("articles")
          .select("*", { count: "exact", head: true });

        const enResult = await db
          .from("articles")
          .select("*", { count: "exact", head: true })
          .eq("language", "en");

        const amResult = await db
          .from("articles")
          .select("*", { count: "exact", head: true })
          .eq("language", "am");

        return Response.json({
          total_articles: totalResult.count ?? 0,
          total_sources: (sources ?? []).length,
          lang_en: enResult.count ?? 0,
          lang_am: amResult.count ?? 0,
          sources: sources ?? [],
        });
      }

      // Digest
      if (path === "/digest") {
        const totalResult = await db
          .from("articles")
          .select("*", { count: "exact", head: true });

        const enResult = await db
          .from("articles")
          .select("*", { count: "exact", head: true })
          .eq("language", "en");

        const amResult = await db
          .from("articles")
          .select("*", { count: "exact", head: true })
          .eq("language", "am");

        const sourceCountResult = await db
          .from("sources")
          .select("*", { count: "exact", head: true });

        const { data: newest } = await db
          .from("articles")
          .select("*, source:source_id(name)")
          .order("published_at", { ascending: false, nullsFirst: false })
          .limit(1)
          .maybeSingle();

        return Response.json({
          name: "The Ethiopia Digest",
          description:
            "Curated news from across Ethiopia's media landscape. English and Amharic articles from independent sources.",
          total_articles: totalResult.count ?? 0,
          total_sources: sourceCountResult.count ?? 0,
          lang_en: enResult.count ?? 0,
          lang_am: amResult.count ?? 0,
          newest_article: newest ? serializeArticle(newest as Article) : null,
        });
      }

      // Health / index
      if (path === "/") {
        return Response.json({
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

      return Response.json({ error: "Not found" }, { status: 404 });
    } catch (err) {
      console.error(err);
      const message = err instanceof Error ? err.message : "Internal error";
      return Response.json({ error: message }, { status: 500 });
    }
  }),
};
