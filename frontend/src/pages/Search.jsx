/* eslint-disable react-hooks/set-state-in-effect */
import { useState, useEffect, useCallback } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { fetchSearch } from "../api";
import SearchBar from "../components/SearchBar";
import TrendingTopics from "../components/TrendingTopics";
import { CardSkeleton } from "../components/Skeleton";
import { GridCard } from "../components/ArticleCard";

export default function Search() {
  const [searchParams, setSearchParams] = useSearchParams();
  const q = searchParams.get("q") || "";

  const [results, setResults] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);

  const doSearch = useCallback(async (query, pageNum = 1) => {
    if (!query.trim()) {
      setResults([]);
      setTotal(0);
      setSearched(false);
      return;
    }
    setLoading(true);
    setSearched(true);
    try {
      const data = await fetchSearch({ q: query, page: pageNum });
      const articles = data.articles || [];
      setResults((prev) => (pageNum === 1 ? articles : [...prev, ...articles]));
      setTotal(data.total || articles.length);
      setHasMore(articles.length >= 30);
    } catch {
      if (pageNum === 1) setResults([]);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    if (q) {
      setPage(1);
      doSearch(q, 1);
    } else {
      setResults([]);
      setTotal(0);
      setSearched(false);
    }
  }, [q, doSearch]);

  const handleSearch = (query) => {
    setSearchParams(query ? { q: query } : {});
  };

  const handleLoadMore = () => {
    const next = page + 1;
    setPage(next);
    doSearch(q, next);
  };

  return (
    <div className="search-page">
      <div className="search-header">
        <Link to="/" className="search-back">&larr; Feed</Link>
        <h1 className="search-title">Discover</h1>
      </div>

      <div className="search-hero">
        <SearchBar onSearch={handleSearch} initialQuery={q} autoFocus={!q} />
        {!searched && !loading && (
          <p className="search-hint">Search across all articles from Ethiopian news sources</p>
        )}
        {searched && !loading && (
          <p className="search-results-count">{total} article{total !== 1 ? "s" : ""} found{q ? ` for "${q}"` : ""}</p>
        )}
        {loading && <p className="search-results-count loading">Searching...</p>}
      </div>

      {!searched && !loading && (
        <div className="search-landing">
          <TrendingTopics onSelect={handleSearch} />
        </div>
      )}

      {loading && results.length === 0 && (
        <div className="search-grid">
          {[...Array(6)].map((_, i) => <CardSkeleton key={i} />)}
        </div>
      )}

      {results.length > 0 && (
        <>
          <div className="search-grid">
            {results.map((a) => (
              <GridCard key={a.id} article={a} />
            ))}
          </div>
          {hasMore && (
            <div className="search-more">
              <button className="load-more-btn" onClick={handleLoadMore} disabled={loading}>
                {loading ? "Loading..." : "Load more"}
              </button>
            </div>
          )}
        </>
      )}

      {searched && !loading && results.length === 0 && (
        <div className="search-empty">
          <svg viewBox="0 0 24 24" width="40" height="40" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="8"/>
            <path d="m21 21-4.35-4.35"/>
            <path d="M8 11h6"/>
          </svg>
          <p>No articles found. Try a different search term.</p>
          <TrendingTopics onSelect={handleSearch} />
        </div>
      )}
    </div>
  );
}
