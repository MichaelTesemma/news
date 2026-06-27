import { useEffect, useState, useCallback } from "react";
import { fetchArticles, fetchSources, triggerScrape } from "../api";
import Masthead from "../components/Masthead";
import { HeroCard, GridCard, MobileCard } from "../components/ArticleCard";
import { groupByDate } from "../utils/date-utils";
import { useInfiniteScroll } from "../hooks/useInfiniteScroll";

function DateSection({ label, articles, collapsed, onToggle }) {
  if (articles.length === 0) return null;
  return (
    <div className="mobile-date-group">
      <div className="date-divider" onClick={onToggle}>
        <span>{label} ({articles.length})</span>
        <span className="toggle-icon">{collapsed ? "+" : "-"}</span>
      </div>
      {!collapsed && articles.map((a) => (
        <MobileCard key={a.id} article={a} />
      ))}
    </div>
  );
}

export default function Feed() {
  const [articles, setArticles] = useState([]);
  const [sources, setSources] = useState([]);
  const [activeSource, setActiveSource] = useState(null);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [loading, setLoading] = useState(true);
  const [scraping, setScraping] = useState(false);
  const [collapsed, setCollapsed] = useState({});

  const load = useCallback(async (pageNum, source) => {
    setLoading(true);
    try {
      const data = await fetchArticles({ page: pageNum, source });
      setArticles((prev) =>
        pageNum === 1 ? data.articles : [...prev, ...data.articles]
      );
      setHasMore(data.page < data.pages);
    } catch {
      setArticles([]);
      setHasMore(false);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchSources()
      .then((data) => setSources(data.sources || []))
      .catch(() => {});
  }, []);

  useEffect(() => {
    setPage(1);
    load(1, activeSource);
  }, [activeSource, load]);

  const handleLoadMore = useCallback(() => {
    const next = page + 1;
    setPage(next);
    load(next, activeSource);
  }, [page, activeSource, load]);

  const sentinelRef = useInfiniteScroll(hasMore, loading, handleLoadMore);

  const handleScrape = async () => {
    setScraping(true);
    try {
      await triggerScrape();
    } catch {
      // scrape failed silently
    }
    setScraping(false);
    setPage(1);
    await load(1, activeSource);
    await fetchSources().then((data) => setSources(data.sources || []));
  };

  const totalInDb = sources.reduce((sum, s) => sum + (s.article_count || 0), 0);

  const toggleGroup = (key) => {
    setCollapsed((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const groups = groupByDate(articles);

  return (
    <>
      <Masthead
        sources={sources}
        activeSource={activeSource}
        onChange={setActiveSource}
        totalArticles={totalInDb}
        scraping={scraping}
        onScrape={handleScrape}
      />
      <main className="feed-page">
        {loading && articles.length === 0 && (
          <div className="empty">Loading articles...</div>
        )}

        {!loading && articles.length === 0 && (
          <div className="empty">No articles match this filter.</div>
        )}

        <div className="desktop-layout">
          {articles.length > 0 && <HeroCard article={articles[0]} />}
          {articles.length > 1 && (
            <div className="article-grid">
              {articles.slice(1).map((a) => (
                <GridCard key={a.id} article={a} />
              ))}
            </div>
          )}
        </div>

        <div className="mobile-layout">
          <DateSection
            label="Today"
            articles={groups.today}
            collapsed={!!collapsed.today}
            onToggle={() => toggleGroup("today")}
          />
          <DateSection
            label="Yesterday"
            articles={groups.yesterday}
            collapsed={!!collapsed.yesterday}
            onToggle={() => toggleGroup("yesterday")}
          />
          <DateSection
            label="Older"
            articles={groups.older}
            collapsed={!!collapsed.older}
            onToggle={() => toggleGroup("older")}
          />
        </div>

        {hasMore && (
          <div ref={sentinelRef} className="infinite-scroll-sentinel">
            {loading && <span className="infinite-scroll-loader">Loading...</span>}
          </div>
        )}
      </main>
    </>
  );
}
