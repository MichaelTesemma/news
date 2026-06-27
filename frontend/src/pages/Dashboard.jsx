import { useEffect, useState, useRef } from "react";
import { Link } from "react-router-dom";
import { fetchDashboard, startScrape, cancelScrape, scrapeProgressStream } from "../api";
import { useQuery } from "../hooks/useQuery";

export default function Dashboard() {
  const { data: dashboard, setData: setDashboard } = useQuery(fetchDashboard, []);
  const [progress, setProgress] = useState(null);
  const [scraping, setScraping] = useState(false);
  const [lastResults, setLastResults] = useState(null);
  const evtSource = useRef(null);

  useEffect(() => {
    return () => {
      if (evtSource.current) {
        evtSource.current.close();
        evtSource.current = null;
      }
    };
  }, []);

  const startScrapeHandler = () => {
    if (scraping) return;
    setScraping(true);
    setLastResults(null);
    setProgress({ running: true, total: 0, current: 0, source_name: "Starting...", sources: [] });

    startScrape()
      .then(() => {
        evtSource.current = scrapeProgressStream();
        evtSource.current.onmessage = (e) => {
          const data = JSON.parse(e.data);
          setProgress(data);
          if (data.done || (!data.running && data.current >= data.total && data.total > 0)) {
            cleanupScrape(data);
          }
        };
        evtSource.current.onerror = () => {
          cleanupScrape(null);
        };
      })
      .catch(() => {
        setScraping(false);
      });
  };

  const cleanupScrape = (data) => {
    if (evtSource.current) {
      evtSource.current.close();
      evtSource.current = null;
    }
    setScraping(false);
    if (data) setLastResults(data);
    fetchDashboard().then(setDashboard).catch(() => {});
  };

  const cancelScrapeHandler = () => {
    cancelScrape().catch(() => {});
  };

  const pct = progress && progress.total > 0
    ? Math.round((progress.current / progress.total) * 100)
    : 0;

  return (
    <div className="dashboard-page">
      <header className="dashboard-header">
        <Link to="/" className="dashboard-back">&larr; Feed</Link>
        <h1>Dashboard</h1>
      </header>

      {dashboard && (
        <div className="dashboard-stats">
          <div className="stat-card">
            <span className="stat-value">{dashboard.total_articles}</span>
            <span className="stat-label">Total Articles</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">{dashboard.total_sources}</span>
            <span className="stat-label">Sources</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">{dashboard.lang_en}</span>
            <span className="stat-label">English</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">{dashboard.lang_am}</span>
            <span className="stat-label">Amharic</span>
          </div>
        </div>
      )}

      <div className="dashboard-scrape">
        <div className="scrape-actions">
          <button className="scrape-btn" onClick={startScrapeHandler} disabled={scraping}>
            {scraping ? "Scraping..." : "Run Scrape"}
          </button>
          {scraping && (
            <button className="cancel-btn" onClick={cancelScrapeHandler}>
              Cancel
            </button>
          )}
        </div>

        {scraping && progress && (
          <div className="scrape-progress">
            <div className="progress-track">
              <div className="progress-fill" style={{ width: `${pct}%` }} />
            </div>
            <div className="progress-info">
              <span className="progress-source">{progress.source_name}</span>
              <span className="progress-count">
                {progress.current} / {progress.total}
              </span>
            </div>
            {progress.sources?.map((s, i) => (
              <div key={i} className={`progress-item ${s.error ? "error" : "done"}`}>
                <span className="item-name">{s.name}</span>
                {s.error ? (
                  <span className="item-error">{s.error}</span>
                ) : (
                  <span className="item-count">+{s.new}</span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {lastResults && (
        <div className="dashboard-results">
          <h2>
            Last Scrape
            {lastResults.source_name === "Cancelled" && (
              <span className="results-cancelled"> Cancelled</span>
            )}
          </h2>
          <table className="source-table">
            <thead>
              <tr>
                <th>Source</th>
                <th>Result</th>
              </tr>
            </thead>
            <tbody>
              {lastResults.sources?.map((s, i) => (
                <tr key={i} className={s.error ? "row-error" : s.name === "Cancelled" ? "row-cancelled" : ""}>
                  <td className="source-name">{s.name}</td>
                  <td>
                    {s.name === "Cancelled" ? (
                      <span className="badge badge-cancelled">Cancelled</span>
                    ) : s.error ? (
                      <span className="badge badge-error" title={s.error}>Failed</span>
                    ) : (
                      <span className="badge badge-ok">+{s.new} new</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="results-summary">
            {lastResults.sources?.filter((s) => !s.error && s.name !== "Cancelled").reduce((sum, s) => sum + (s.new || 0), 0)} new articles
          </p>
        </div>
      )}

      {dashboard && (
        <div className="dashboard-sources">
          <h2>All Sources</h2>
          <table className="source-table">
            <thead>
              <tr>
                <th>Source</th>
                <th>Articles</th>
                <th>Last Scraped</th>
              </tr>
            </thead>
            <tbody>
              {dashboard.sources.map((s) => (
                <tr key={s.id}>
                  <td className="source-name">{s.name}</td>
                  <td>{s.article_count}</td>
                  <td className="source-last">
                    {s.last_scraped
                      ? new Date(s.last_scraped).toLocaleString()
                      : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
