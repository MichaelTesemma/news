import { useEffect, useState, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import { fetchArticle, fetchRelated } from "../api";
import { formatDate } from "../utils/date-utils";
import { setPageMeta, injectJsonLd } from "../utils/meta-utils";
import BodyRenderer from "../components/BodyRenderer";
import ImagePlaceholder from "../components/ImagePlaceholder";
import BookmarkButton from "../components/BookmarkButton";

export default function Article() {
  const { id } = useParams();
  const [article, setArticle] = useState(null);
  const [related, setRelated] = useState([]);
  const [error, setError] = useState(false);
  const [progress, setProgress] = useState(0);
  const [fontSize, setFontSize] = useState(() => {
    return parseFloat(localStorage.getItem("article-font-size") || "16");
  });

  useEffect(() => {
    localStorage.setItem("article-font-size", fontSize.toString());
  }, [fontSize]);

  useEffect(() => {
    fetchArticle(id)
      .then((a) => {
        setArticle(a);
        const url = window.location.href;
        setPageMeta({
          title: a.title,
          description: a.summary || a.body?.slice(0, 200),
          image: a.image_url || undefined,
          url,
          type: "article",
        });
        injectJsonLd({
          "@context": "https://schema.org",
          "@type": "NewsArticle",
          headline: a.title,
          description: a.summary || a.body?.slice(0, 300),
          url,
          image: a.image_url,
          author: a.author ? { "@type": "Person", name: a.author } : undefined,
          publisher: {
            "@type": "Organization",
            name: a.source,
          },
          datePublished: a.published_at,
          dateModified: a.updated_at || a.published_at,
          mainEntityOfPage: { "@type": "WebPage", "@id": url },
        });
        fetchRelated(id).then((r) => setRelated(r.articles || [])).catch(() => {});
      })
      .catch(() => setError(true));
  }, [id]);

  useEffect(() => {
    const handleScroll = () => {
      const scrollTop = window.scrollY;
      const docHeight = document.documentElement.scrollHeight - window.innerHeight;
      setProgress(docHeight > 0 ? Math.min((scrollTop / docHeight) * 100, 100) : 0);
    };
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const adjustFont = useCallback((delta) => {
    setFontSize((prev) => Math.min(Math.max(prev + delta, 12), 24));
  }, []);

  if (error) {
    return <div className="empty">Article not found.</div>;
  }

  if (!article) {
    return <div className="empty">Loading...</div>;
  }

  const hasUpdate = article.updated_at && article.published_at && article.updated_at !== article.published_at;
  const pubDate = article.published_at ? new Date(article.published_at) : null;

  return (
    <div className="article-page">
      <div className="progress-bar">
        <div className="progress-bar-fill" style={{ width: `${progress}%` }} />
      </div>

      <div className="back-bar">
        <Link to="/">&larr; Back to feed</Link>
        <span className="site-name">The Ethiopia Digest</span>
      </div>

      <div className="article-layout">
        <aside className="share-sidebar">
          <div className="share-sidebar-inner">
            <span className="share-label">Share</span>
            <button
              className="share-icon-btn"
              onClick={() => {
                const url = window.location.href;
                window.open(`https://twitter.com/intent/tweet?url=${encodeURIComponent(url)}&text=${encodeURIComponent(article.title)}`, "_blank", "noopener");
              }}
              aria-label="Share on X"
            >
              <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
            </button>
            <button
              className="share-icon-btn"
              onClick={() => {
                const url = window.location.href;
                window.open(`https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}`, "_blank", "noopener");
              }}
              aria-label="Share on Facebook"
            >
              <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/></svg>
            </button>
            <button
              className="share-icon-btn"
              onClick={() => navigator.clipboard?.writeText(window.location.href)}
              aria-label="Copy link"
            >
              <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M7.24 2h4.52c2.12 0 2.84.22 3.6.63.76.42 1.36 1.01 1.77 1.77.42.76.63 1.48.63 3.6v1.45c0 2.12-.21 2.84-.63 3.6-.41.76-1.01 1.36-1.77 1.77-.76.42-1.48.63-3.6.63H7.24c-2.12 0-2.84-.21-3.6-.63-.76-.41-1.36-1.01-1.77-1.77C1.45 13.51 1.24 12.79 1.24 10.67V9.22c0-2.12.21-2.84.63-3.6.41-.76 1.01-1.36 1.77-1.77.76-.42 1.48-.63 3.6-.63Zm0 1.5c-1.8 0-2.36.17-2.95.5-.55.3-.99.74-1.29 1.29-.33.59-.5 1.15-.5 2.95v1.45c0 1.8.17 2.36.5 2.95.3.55.74.99 1.29 1.29.59.33 1.15.5 2.95.5h4.52c1.8 0 2.36-.17 2.95-.5.55-.3.99-.74 1.29-1.29.33-.59.5-1.15.5-2.95V9.22c0-1.8-.17-2.36-.5-2.95-.3-.55-.74-.99-1.29-1.29-.59-.33-1.15-.5-2.95-.5H7.24Z"/><path d="M6.76 9.22c0-2.12.21-2.84.63-3.6.41-.76 1.01-1.36 1.77-1.77.76-.42 1.48-.63 3.6-.63h1.45c.34 0 .66.03.95.09a4.76 4.76 0 0 0-.95-.09h-1.45c-2.12 0-2.84.21-3.6.63-.76.41-1.36 1.01-1.77 1.77-.42.76-.63 1.48-.63 3.6v2.53c0 .46.05.87.15 1.24-.1-.37-.15-.78-.15-1.24V9.22Z"/></svg>
            </button>
          </div>
        </aside>

        <div className="article-main">
          <div className={`article-hero${article.image_url ? "" : " placeholder"}`}>
            {article.image_url ? (
              <img src={article.image_url} alt="" />
            ) : (
              <ImagePlaceholder size={48} />
            )}
          </div>

          <article className="article-body-container" style={{ "--body-font-size": `${fontSize}px` }}>
            {article.category && <div className="kicker">{article.category}</div>}
            <h1>{article.title}</h1>

            <div className="byline">
              <div className="byline-main">
                {article.author && <span>By <strong>{article.author}</strong></span>}
                {article.author && article.source && <span className="dot">&middot;</span>}
                {article.source && <span>{article.source}</span>}
              </div>
              <div className="byline-meta">
                {article.reading_time && (
                  <span className="reading-time">{article.reading_time} min read</span>
                )}
                {pubDate && (
                  <time dateTime={article.published_at}>
                    {formatDate(article.published_at)}
                  </time>
                )}
                {hasUpdate && (
                  <span className="updated-badge">Updated {formatDate(article.updated_at)}</span>
                )}
              </div>
              <div className="byline-actions">
                <BookmarkButton article={article} />
                <div className="font-controls">
                  <button onClick={() => adjustFont(-1)} className="font-btn" aria-label="Decrease font size">A&minus;</button>
                  <button onClick={() => adjustFont(1)} className="font-btn" aria-label="Increase font size">A+</button>
                </div>
              </div>
            </div>

            <div className="body-text">
              <BodyRenderer body={article.body || article.summary} />
            </div>
          </article>

          <footer className="article-footer">
            <div className="full-bleed-divider" />
            {article.source_description && (
              <p className="source-description">{article.source_description}</p>
            )}
            <div className="footer-actions">
              <a href={article.url} target="_blank" rel="noopener noreferrer" className="footer-btn">
                Read original article &rarr;
              </a>
            </div>

            {related.length > 0 && (
              <>
                <div className="full-bleed-divider" />
                <section className="related-section">
                  <h3 className="related-heading">More from {article.source}</h3>
                  <div className="related-grid">
                    {related.map((r) => (
                      <Link key={r.id} to={`/article/${r.id}`} className="related-card">
                        {r.image_url && (
                          <div className="related-card-img">
                            <img src={r.image_url} alt="" />
                          </div>
                        )}
                        <h4>{r.title}</h4>
                        <span className="related-date">{formatDate(r.published_at)}</span>
                      </Link>
                    ))}
                  </div>
                </section>
              </>
            )}
          </footer>
        </div>
      </div>

      <div className="share-sheet">
        <button onClick={() => { if (navigator.share) navigator.share({ title: article.title, url: window.location.href }); }}>
          Share
        </button>
        <button onClick={() => { navigator.clipboard?.writeText(window.location.href); }}>
          Copy Link
        </button>
        <a href={`https://twitter.com/intent/tweet?url=${encodeURIComponent(window.location.href)}&text=${encodeURIComponent(article.title)}`} target="_blank" rel="noopener noreferrer">
          Post on X
        </a>
        <a href={article.url} target="_blank" rel="noopener noreferrer">
          Original &nearr;
        </a>
      </div>
    </div>
  );
}
