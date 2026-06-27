/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useState, useEffect, useCallback } from "react";

const BookmarkContext = createContext();

function loadBookmarks() {
  try {
    const raw = localStorage.getItem("bookmarks");
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function BookmarkProvider({ children }) {
  const [bookmarks, setBookmarks] = useState(loadBookmarks);

  useEffect(() => {
    localStorage.setItem("bookmarks", JSON.stringify(bookmarks));
  }, [bookmarks]);

  const toggleBookmark = useCallback((article) => {
    setBookmarks((prev) => {
      const exists = prev.find((b) => b.id === article.id);
      if (exists) return prev.filter((b) => b.id !== article.id);
      return [{ id: article.id, title: article.title, source: article.source, published_at: article.published_at, image_url: article.image_url, savedAt: Date.now() }, ...prev];
    });
  }, []);

  const isBookmarked = useCallback((id) => {
    return bookmarks.some((b) => b.id === id);
  }, [bookmarks]);

  const removeBookmark = useCallback((id) => {
    setBookmarks((prev) => prev.filter((b) => b.id !== id));
  }, []);

  return (
    <BookmarkContext.Provider value={{ bookmarks, toggleBookmark, isBookmarked, removeBookmark }}>
      {children}
    </BookmarkContext.Provider>
  );
}

export function useBookmarks() {
  return useContext(BookmarkContext);
}
