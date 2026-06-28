const BASE = import.meta.env.VITE_API_URL ||
  "https://ofzuqyqvhxibbaqxlmyn.functions.supabase.co/api";

export async function fetchArticles({ page = 1, source } = {}) {
  const params = new URLSearchParams({ page, per_page: 20 });
  if (source) params.set("source", source);
  const res = await fetch(`${BASE}/articles?${params}`);
  return res.json();
}

export async function fetchArticle(id) {
  const res = await fetch(`${BASE}/articles/${id}`);
  if (!res.ok) throw new Error("Not found");
  return res.json();
}

export async function fetchSources() {
  const res = await fetch(`${BASE}/sources`);
  return res.json();
}

export async function fetchDashboard() {
  const res = await fetch(`${BASE}/dashboard`);
  return res.json();
}

export async function fetchRelated(id) {
  const res = await fetch(`${BASE}/articles/${id}/related`);
  return res.json();
}

export async function triggerScrape(sourceId) {
  const res = await fetch(`${BASE}/scrape`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ source_id: sourceId }),
  });
  return res.json();
}

export async function fetchSearch({ q, page = 1 } = {}) {
  const params = new URLSearchParams({ q, page, per_page: 30 });
  const res = await fetch(`${BASE}/articles/search?${params}`);
  if (!res.ok) return { articles: [], total: 0 };
  return res.json();
}

export async function fetchCategories() {
  const res = await fetch(`${BASE}/categories`);
  if (!res.ok) return { categories: [] };
  return res.json();
}

export async function startScrape(sourceId) {
  const res = await fetch(`${BASE}/scrape/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ source_id: sourceId }),
  });
  return res.json();
}

export async function cancelScrape() {
  const res = await fetch(`${BASE}/scrape/cancel`, { method: "POST" });
  return res.json();
}

export function scrapeProgressStream() {
  return new EventSource(`${BASE}/scrape/progress`);
}

export async function fetchTrending() {
  const res = await fetch(`${BASE}/articles/trending`);
  if (!res.ok) return { articles: [] };
  return res.json();
}

export async function fetchDigest() {
  const res = await fetch(`${BASE}/digest`);
  if (!res.ok) return {};
  return res.json();
}
