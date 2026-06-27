import { Link } from "react-router-dom";

export default function Footer() {
  return (
    <footer className="site-footer">
      <div className="footer-inner">
        <div className="footer-brand">
          <strong>The Ethiopia Digest</strong>
          <span>Curated news from across Ethiopia</span>
        </div>
        <nav className="footer-links">
          <Link to="/about">About</Link>
          <Link to="/search">Search</Link>
          <Link to="/bookmarks">Bookmarks</Link>
          <Link to="/dashboard">Dashboard</Link>
          <a href="/rss.xml" target="_blank" rel="noopener noreferrer">RSS Feed</a>
        </nav>
      </div>
      <div className="footer-bottom">
        <span>Data sourced from publicly available RSS feeds.</span>
      </div>
    </footer>
  );
}
