import { Link } from "react-router-dom";

const TOPICS = [
  { name: "Politics", count: 48 },
  { name: "Economy", count: 32 },
  { name: "Culture", count: 27 },
  { name: "Technology", count: 21 },
  { name: "Sports", count: 18 },
  { name: "Diplomacy", count: 15 },
  { name: "Agriculture", count: 12 },
  { name: "Health", count: 11 },
  { name: "Education", count: 9 },
  { name: "Environment", count: 8 },
];

export default function TrendingTopics({ onSelect }) {
  const max = Math.max(...TOPICS.map((t) => t.count));

  return (
    <section className="trending-section">
      <h2 className="trending-heading">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/>
          <polyline points="17 6 23 6 23 12"/>
        </svg>
        Trending Topics
      </h2>
      <div className="trending-cloud">
        {TOPICS.map((topic) => {
          const size = 0.7 + (topic.count / max) * 0.6;
          return (
            <Link
              key={topic.name}
              to={`/search?q=${encodeURIComponent(topic.name)}`}
              className="trending-tag"
              style={{ fontSize: `${size}rem` }}
              onClick={(e) => {
                if (onSelect) {
                  e.preventDefault();
                  onSelect(topic.name);
                }
              }}
            >
              {topic.name}
            </Link>
          );
        })}
      </div>
    </section>
  );
}
