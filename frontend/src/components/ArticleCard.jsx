import { Link } from "react-router-dom";
import { timeAgo } from "../utils/date-utils";
import ImagePlaceholder from "./ImagePlaceholder";
import BookmarkButton from "./BookmarkButton";

export function HeroCard({ article }) {
  return (
    <Link to={`/article/${article.id}`} className="hero-article">
      <div className={`hero-image-wrap${article.image_url ? "" : " placeholder"}`}>
        {article.image_url ? (
          <img src={article.image_url} alt="" loading="lazy" />
        ) : (
          <ImagePlaceholder size={48} />
        )}
      </div>
      <div className="hero-content">
        {article.category && <div className="kicker">{article.category}</div>}
        <h2>{article.title}</h2>
        {article.summary && <p className="summary">{article.summary}</p>}
        <div className="meta">
          {article.source}
          {article.author && <span> &middot; By {article.author}</span>}
          {article.published_at && <span> &middot; {timeAgo(article.published_at)}</span>}
        </div>
      </div>
    </Link>
  );
}

export function GridCard({ article }) {
  return (
    <div className="article-card-wrap">
      <Link to={`/article/${article.id}`} className="article-card">
        <div className={`card-img${article.image_url ? "" : " placeholder"}`}>
          {article.image_url ? (
            <img src={article.image_url} alt="" loading="lazy" />
          ) : (
            <ImagePlaceholder />
          )}
        </div>
        <h3>{article.title}</h3>
        <div className="meta">
          {article.source}
          {article.published_at && <span> &middot; {timeAgo(article.published_at)}</span>}
        </div>
      </Link>
      <BookmarkButton article={article} compact className="card-bookmark" />
    </div>
  );
}

export function MobileCard({ article }) {
  return (
    <Link to={`/article/${article.id}`} className="mobile-card">
      <h3>{article.title}</h3>
      <div className="meta">
        {article.source}
        {article.published_at && <span> &middot; {timeAgo(article.published_at)}</span>}
      </div>
    </Link>
  );
}

export default GridCard;
