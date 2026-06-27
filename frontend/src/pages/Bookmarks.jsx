import { Link } from "react-router-dom";
import { useBookmarks } from "../context/BookmarkContext";

function timeAgo(dateStr) {
  if (!dateStr) return "";
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diff = now - then;
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(dateStr).toLocaleDateString();
}

export default function Bookmarks() {
  const { bookmarks, removeBookmark } = useBookmarks();

  return (
    <div className="bookmarks-page">
      <div className="bookmarks-header">
        <Link to="/" className="search-back">&larr; Feed</Link>
        <h1 className="bookmarks-title">
          <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor" stroke="none">
            <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/>
          </svg>
          Saved Articles
        </h1>
        <span className="bookmarks-count">{bookmarks.length} saved</span>
      </div>

      {bookmarks.length === 0 ? (
        <div className="bookmarks-empty">
          <svg viewBox="0 0 24 24" width="48" height="48" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/>
          </svg>
          <h2>No saved articles yet</h2>
          <p>Bookmark articles to read them later.</p>
          <Link to="/" className="bookmarks-browse-btn">Browse articles</Link>
        </div>
      ) : (
        <div className="bookmarks-list">
          {bookmarks.map((b) => (
            <div key={b.id} className="bookmark-item">
              <Link to={`/article/${b.id}`} className="bookmark-item-link">
                {b.image_url && (
                  <div className="bookmark-item-img">
                    <img src={b.image_url} alt="" />
                  </div>
                )}
                <div className="bookmark-item-content">
                  <h3>{b.title}</h3>
                  <div className="bookmark-item-meta">
                    <span>{b.source}</span>
                    {b.published_at && <span> &middot; {timeAgo(b.published_at)}</span>}
                  </div>
                </div>
              </Link>
              <button
                className="bookmark-remove"
                onClick={() => removeBookmark(b.id)}
                aria-label="Remove bookmark"
              >
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                  <path d="M18 6 6 18M6 6l12 12"/>
                </svg>
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
