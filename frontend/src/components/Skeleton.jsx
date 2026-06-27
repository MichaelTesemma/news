export function CardSkeleton() {
  return (
    <div className="skeleton-card" aria-hidden="true">
      <div className="skeleton-img skeleton-pulse" />
      <div className="skeleton-line skeleton-pulse" style={{ width: "85%" }} />
      <div className="skeleton-line skeleton-pulse" style={{ width: "60%" }} />
      <div className="skeleton-line skeleton-pulse" style={{ width: "40%", height: 10 }} />
    </div>
  );
}

export function HeroSkeleton() {
  return (
    <div className="skeleton-hero" aria-hidden="true">
      <div className="skeleton-hero-img skeleton-pulse" />
      <div className="skeleton-hero-content">
        <div className="skeleton-line skeleton-pulse" style={{ width: "20%", height: 12 }} />
        <div className="skeleton-line skeleton-pulse" style={{ width: "90%", height: 24 }} />
        <div className="skeleton-line skeleton-pulse" style={{ width: "75%", height: 16 }} />
        <div className="skeleton-line skeleton-pulse" style={{ width: "30%", height: 12 }} />
      </div>
    </div>
  );
}

export function ArticleSkeleton() {
  return (
    <div className="skeleton-article" aria-hidden="true">
      <div className="skeleton-full skeleton-pulse" style={{ height: 300 }} />
      <div style={{ padding: "32px 24px", maxWidth: 620, margin: "0 auto" }}>
        <div className="skeleton-line skeleton-pulse" style={{ width: "20%", height: 12, marginBottom: 16 }} />
        <div className="skeleton-line skeleton-pulse" style={{ width: "95%", height: 32, marginBottom: 8 }} />
        <div className="skeleton-line skeleton-pulse" style={{ width: "70%", height: 32, marginBottom: 24 }} />
        <div className="skeleton-line skeleton-pulse" style={{ width: "40%", height: 14, marginBottom: 32 }} />
        {[95, 88, 75, 92, 65, 80, 70, 55].map((w, i) => (
          <div key={i} className="skeleton-line skeleton-pulse" style={{ width: `${w}%`, height: 14, marginBottom: 12 }} />
        ))}
      </div>
    </div>
  );
}
