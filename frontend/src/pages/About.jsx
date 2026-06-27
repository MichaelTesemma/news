import { useEffect } from "react";
import { Link } from "react-router-dom";
import { setPageMeta } from "../utils/meta-utils";

export default function About() {
  useEffect(() => {
    setPageMeta({
      title: "About",
      description: "The Ethiopia Digest curates news from across Ethiopia's media landscape, aggregating English and Amharic articles from independent sources.",
    });
  }, []);

  return (
    <div className="about-page">
      <div className="about-header">
        <Link to="/" className="search-back">&larr; Feed</Link>
      </div>

      <div className="about-content">
        <h1>About The Ethiopia Digest</h1>

        <section>
          <h2>What is this?</h2>
          <p>
            The Ethiopia Digest is a news aggregator that collects articles from
            across Ethiopia's media landscape. It brings together English and
            Amharic reporting from independent sources, making it easy to browse,
            search, and discover coverage in one place.
          </p>
        </section>

        <section>
          <h2>Sources</h2>
          <p>
            Articles are aggregated from publicly available RSS feeds of Ethiopian
            and Ethiopia-focused news outlets. Each article links back to the
            original source. We do not modify or editorialize the content.
          </p>
        </section>

        <section>
          <h2>Features</h2>
          <ul>
            <li>Browse articles from 14+ Ethiopian news sources</li>
            <li>Full-text search across all articles</li>
            <li>English and Amharic language articles</li>
            <li>Bookmark articles for later reading</li>
            <li>Adjustable reading font size</li>
            <li>Dark mode support</li>
            <li>RSS feed for external readers</li>
            <li>Mobile-friendly progressive web app</li>
          </ul>
        </section>

        <section>
          <h2>Privacy</h2>
          <p>
            This site does not use trackers, cookies, or analytics services.
            Bookmark data is stored locally in your browser and never sent to
            any server.
          </p>
        </section>
      </div>
    </div>
  );
}
