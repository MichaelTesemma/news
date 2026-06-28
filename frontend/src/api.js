const BASE = import.meta.env.VITE_API_URL ||
  "https://ofzuqyqvhxibbaqxlmyn.functions.supabase.co/api";
const API_KEY = import.meta.env.VITE_PUBLISHABLE_KEY ||
  "sb_publishable_I8UCMJCKaq7FtC-Ojah-Fw_G39FeuFY";

const headers = { apikey: API_KEY };

async function apiFetch(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, { ...options, headers: { ...headers, ...options.headers } });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(body || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function fetchArticles({ page = 1, source } = {}) {
  const params = new URLSearchParams({ page, per_page: 20 });
  if (source) params.set("source", source);
  return apiFetch(`/articles?${params}`);
}

export async function fetchArticle(id) {
  return apiFetch(`/articles/${id}`);
}

export async function fetchSources() {
  return apiFetch("/sources");
}

export async function fetchDashboard() {
  return apiFetch("/dashboard");
}

export async function fetchRelated(id) {
  return apiFetch(`/articles/${id}/related`);
}

export async function triggerScrape(sourceId) {
  return apiFetch("/scrape", {
    method: "POST",
    body: JSON.stringify({ source_id: sourceId }),
  });
}

export async function fetchSearch({ q, page = 1 } = {}) {
  const params = new URLSearchParams({ q, page, per_page: 30 });
  try {
    return await apiFetch(`/articles/search?${params}`);
  } catch {
    return { articles: [], total: 0 };
  }
}

export async function fetchCategories() {
  try {
    return await apiFetch("/categories");
  } catch {
    return { categories: [] };
  }
}

export async function startScrape(sourceId) {
  return apiFetch("/scrape/start", {
    method: "POST",
    body: JSON.stringify({ source_id: sourceId }),
  });
}

export async function cancelScrape() {
  return apiFetch("/scrape/cancel", { method: "POST" });
}

export function scrapeProgressStream() {
  return new EventSource(`${BASE}/scrape/progress`);
}

export async function fetchTrending() {
  try {
    return await apiFetch("/articles/trending");
  } catch {
    return { articles: [] };
  }
}

export async function fetchDigest() {
  try {
    return await apiFetch("/digest");
  } catch {
    return {};
  }
}
