# GeneGenie Frontend Context

## Project

GeneGenie is a Next.js App Router application for an AI-powered gene-editing platform. The site is structured as a corporate marketing surface plus a backend-ready authenticated portal skeleton.

## Stack

- Next.js 16 App Router
- React 19
- TypeScript strict mode
- Tailwind CSS
- Lucide React icons

## Routes

- `/` - Enterprise landing page with protein hero image from `public/frontpage_logo.jpg`
- `/platform` - Platform explanation page with three pipeline cards connected by neon SVG flow traces
- `/applications` - Use-case page using image assets from `public/antibodies.jpg`, `public/agriculture.png`, and `public/research.png`
- `/portal` - Dashboard skeleton with typed data contracts, loading states, and empty states ready for real API integration

## Design Direction

- Deep zinc/slate dark background
- Glassmorphism panels with `border-zinc-800`
- Cyan, emerald, and occasional purple biological-tech accents
- Clean corporate structure inspired by biotech platform sites
- Avoid fake metrics; portal should show skeleton or empty states until backend data is connected

## Key Files

- `app/layout.tsx` - Global metadata, font, background, and shared navbar
- `app/components/Navbar.tsx` - Site navigation and Access Portal CTA
- `app/components/SectionHeader.tsx` - Shared section header component
- `app/page.tsx` - Landing page
- `app/platform/page.tsx` - Platform page and pipeline flow SVG
- `app/applications/page.tsx` - Applications page image cards
- `app/portal/page.tsx` - Backend-ready portal skeleton
- `app/globals.css` - Tailwind imports plus custom protein and pipeline animations

## Verification

Latest validation command:

```bash
npm run build
```

Build passed after the most recent UI changes.
