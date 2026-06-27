const SITE_NAME = "The Ethiopia Digest";
const SITE_DESC = "Curated news from across Ethiopia's media landscape. English and Amharic articles from independent sources.";
const SITE_URL = typeof window !== "undefined" ? window.location.origin : "https://ethiopiadigest.com";

function getMeta(name) {
  let el = document.querySelector(`meta[name="${name}"], meta[property="${name}"]`);
  return el;
}

function setOrUpdate(selector, attrs) {
  let el = document.querySelector(selector);
  if (!el) {
    el = document.createElement("meta");
    document.head.appendChild(el);
  }
  for (const [k, v] of Object.entries(attrs)) {
    el.setAttribute(k, v);
  }
}

export function setPageMeta({ title, description, image, url, type = "website" }) {
  document.title = title ? `${title} — ${SITE_NAME}` : SITE_NAME;

  const desc = description || SITE_DESC;

  setOrUpdate('meta[name="description"]', { name: "description", content: desc });
  setOrUpdate('meta[property="og:title"]', { property: "og:title", content: title || SITE_NAME });
  setOrUpdate('meta[property="og:description"]', { property: "og:description", content: desc });
  setOrUpdate('meta[property="og:type"]', { property: "og:type", content: type });
  setOrUpdate('meta[property="og:url"]', { property: "og:url", content: url || SITE_URL });
  setOrUpdate('meta[property="og:site_name"]', { property: "og:site_name", content: SITE_NAME });
  setOrUpdate('meta[property="og:image"]', { property: "og:image", content: image || "/favicon.svg" });
  setOrUpdate('meta[name="twitter:card"]', { name: "twitter:card", content: "summary_large_image" });
  setOrUpdate('meta[name="twitter:title"]', { name: "twitter:title", content: title || SITE_NAME });
  setOrUpdate('meta[name="twitter:description"]', { name: "twitter:description", content: desc });
  setOrUpdate('meta[name="twitter:image"]', { name: "twitter:image", content: image || "/favicon.svg" });
}

export function injectJsonLd(data) {
  let el = document.getElementById("json-ld");
  if (!el) {
    el = document.createElement("script");
    el.id = "json-ld";
    el.type = "application/ld+json";
    document.head.appendChild(el);
  }
  el.textContent = JSON.stringify(data, null, 2);
}

export function clearPageMeta() {
  document.title = SITE_NAME;
}

export { SITE_NAME, SITE_DESC };
