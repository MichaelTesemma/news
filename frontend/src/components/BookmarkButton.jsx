import { useBookmarks } from "../context/BookmarkContext";

export default function BookmarkButton({ article, className = "", compact = false }) {
  const { isBookmarked, toggleBookmark } = useBookmarks();
  const active = isBookmarked(article?.id);

  return (
    <button
      className={`bookmark-btn ${active ? "bookmarked" : ""} ${className}`}
      onClick={(e) => {
        e.preventDefault();
        e.stopPropagation();
        toggleBookmark(article);
      }}
      aria-label={active ? "Remove bookmark" : "Save article"}
    >
      <svg viewBox="0 0 24 24" width={compact ? 14 : 16} height={compact ? 14 : 16} fill={active ? "currentColor" : "none"} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/>
      </svg>
      {!compact && (active ? "Saved" : "Save")}
    </button>
  );
}
