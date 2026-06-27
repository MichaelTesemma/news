import { Link } from "react-router-dom";
import { useTheme } from "../context/ThemeContext";

export default function Masthead({ sources, activeSource, onChange, totalArticles, scraping, onScrape }) {
  const { dark, toggle } = useTheme();
  const srcCount = sources.length;
  const today = new Date().toLocaleDateString("en-US", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  return (
    <header className="masthead">
      <h1 className="nameplate">
        <Link to="/">The Ethiopia Digest</Link>
      </h1>
      <div className="dateline">
        <span>{today}</span>
        <span>{srcCount} Sources &middot; {totalArticles} Articles</span>
        <div className="dateline-actions">
          <Link to="/search" className="nav-icon-link" title="Search">
            <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="8"/>
              <path d="m21 21-4.35-4.35"/>
            </svg>
          </Link>
          <Link to="/bookmarks" className="nav-icon-link" title="Saved articles">
            <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/>
            </svg>
          </Link>
          <Link to="/dashboard" className="nav-icon-link" title="Dashboard">
            <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="3" width="7" height="7"/>
              <rect x="14" y="3" width="7" height="7"/>
              <rect x="14" y="14" width="7" height="7"/>
              <rect x="3" y="14" width="7" height="7"/>
            </svg>
          </Link>
          <button className="theme-toggle" onClick={toggle} title="Toggle dark mode">
            {dark ? "\u2600" : "\u263E"}
          </button>
          <button className="scrape-link" onClick={onScrape} disabled={scraping}>
            {scraping ? "Scraping..." : "Scrape"}
          </button>
        </div>
      </div>
      <nav className="source-nav">
        <button
          className={!activeSource ? "active" : ""}
          onClick={() => onChange(null)}
        >
          All
        </button>
        {sources.map((s) => (
          <button
            key={s.id}
            className={activeSource === s.id ? "active" : ""}
            onClick={() => onChange(s.id)}
          >
            {s.name}
          </button>
        ))}
      </nav>
    </header>
  );
}
