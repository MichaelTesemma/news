import { useEffect, useRef } from "react";

export function useInfiniteScroll(hasMore, loading, onLoadMore, options = {}) {
  const sentinelRef = useRef(null);
  const loadingRef = useRef(loading);

  useEffect(() => {
    loadingRef.current = loading;
  }, [loading]);

  useEffect(() => {
    if (!hasMore) return;
    const el = sentinelRef.current;
    if (!el) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !loadingRef.current) {
          onLoadMore();
        }
      },
      { rootMargin: options.rootMargin || "200px" }
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, [hasMore, onLoadMore, options.rootMargin]);

  return sentinelRef;
}
