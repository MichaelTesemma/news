# NYT-Style Redesign for Ethiopia News Digest

## Overview

Redesign the frontend to mimic The New York Times landing page aesthetic: strict black-and-white serif typography, multi-column newspaper grid with visual hierarchy, and a centered reading experience for article pages.

## Design Decisions

| Aspect | Choice |
|---|---|
| Layout | Hero + Grid — dominant lead story, then multi-column grid below |
| Color | Classic B&W — pure grayscale palette (#000, #333, #666, #ccc, #f5f5f5) |
| Typography | Georgia serif for headlines, system sans-serif for metadata |
| Header | Classic newspaper masthead with date line + source navigation |
| Cards | Headline + thumbnail (hero card for lead story slot) |
| Mobile feed | Chronological stream grouped by date with collapsible dividers |
| Article page | Centered column (desktop), edge-to-edge with progress bar + sticky bottom sheet (mobile) |

## Component Architecture

### App Structure
```
App
├── Masthead (sticky top)
│   ├── Newspaper Nameplate (Georgia, 38px, double border)
│   ├── Date Line (date, source count, article count, Scrape link)
│   └── Source Nav (horizontal list, "All" + each source, underline active)
├── Feed
│   ├── HeroArticle (full-width, image + large headline + summary)
│   └── ArticleGrid (responsive multi-column)
│       └── ArticleCard (thumbnail + headline + source + timestamp)
└── ArticlePage
    ├── BackBar (thin bar with ← Back link)
    ├── HeroImage (full-bleed)
    ├── ArticleBody (centered 600px column)
    │   ├── Category label
    │   ├── Headline (32px Georgia bold)
    │   ├── Byline (author + source + date)
    │   └── Body text (16px/1.7 leading)
    ├── ReadOriginal link
    └── Mobile: ProgressBar + StickyShareSheet
```

### Mobile Variants
- **Feed**: Single-column chronological stream with date dividers (Today, Yesterday, Older). Tap divider to collapse/expand.
- **Article**: Edge-to-edge padding. Sticky top progress bar (3px black on gray). Sticky bottom share sheet (Share, Copy Link, Original).

## Files to Create/Modify

### Modified files
- `src/index.css` — global typography (Georgia serif base), B&W color system
- `src/App.css` — replace entirely with new NYT-style styles
- `src/App.jsx` — rename "News2" to "The Ethiopia Digest", restructure layout
- `src/components/NavBar.jsx` — rewrite as Masthead with nameplate, date line, source nav
- `src/components/ArticleCard.jsx` — rewrite as thumbnail + headline card (hero variant for index 0)
- `src/pages/Feed.jsx` — restructure with hero slot + grid; remove stats cards
- `src/pages/Article.jsx` — rewrite for centered column layout, progress bar, share sheet
- `src/components/SourceFilter.jsx` — merge into Masthead nav (inline pill-style links)

### Deleted files
- `src/components/SourceFilter.jsx` (logic merged into Masthead)

## Responsive Breakpoints

| Breakpoint | Columns | Layout |
|---|---|---|
| < 640px | 1 | Single-column stream, date dividers, edge-to-edge |
| 640-1024px | 2 | Two-column grid, compact masthead |
| > 1024px | 3 (hero span 3) | Three-column grid, full masthead |

### Hero Article Behavior
- Desktop (>1024px): Hero spans all 3 columns, image + headline side-by-side
- Tablet (640-1024px): Hero spans 2 columns, stacked layout
- Mobile (<640px): Hero becomes first card in stream with larger image

## Notes
- "Scrape Now" appears as a subtle text link in the date line, not a button
- Stats cards are removed entirely — count shown in date line ("13 Sources · 760 Articles")
- Source filter is a horizontal nav bar below the masthead, not pill buttons
- Article images use object-fit: cover with a light gray placeholder background
- Active source is underlined or bolded in the source nav
