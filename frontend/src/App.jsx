import { BrowserRouter, Routes, Route } from "react-router-dom";
import { BookmarkProvider } from "./context/BookmarkContext";
import { ThemeProvider } from "./context/ThemeContext";
import ErrorBoundary from "./components/ErrorBoundary";
import ScrollToTop from "./components/ScrollToTop";
import Footer from "./components/Footer";
import Feed from "./pages/Feed";
import Article from "./pages/Article";
import Dashboard from "./pages/Dashboard";
import Search from "./pages/Search";
import Bookmarks from "./pages/Bookmarks";
import About from "./pages/About";
import "./App.css";

export default function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
        <BookmarkProvider>
          <ErrorBoundary>
            <ScrollToTop />
            <div id="main-content">
              <Routes>
                <Route path="/" element={<Feed />} />
                <Route path="/article/:id" element={<Article />} />
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/search" element={<Search />} />
                <Route path="/bookmarks" element={<Bookmarks />} />
                <Route path="/about" element={<About />} />
                <Route path="*" element={<NotFound />} />
              </Routes>
              <Footer />
            </div>
          </ErrorBoundary>
        </BookmarkProvider>
      </ThemeProvider>
    </BrowserRouter>
  );
}

function NotFound() {
  return (
    <div className="not-found-page">
      <h1>404</h1>
      <p>Page not found.</p>
      <a href="/" className="btn-primary">Go to feed</a>
    </div>
  );
}
