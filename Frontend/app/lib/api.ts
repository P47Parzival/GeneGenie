// Resolves the base for browser → API calls.
//
// - In production (Vercel), set NEXT_PUBLIC_ANNOTATION_API_BASE to the HTTPS API
//   domain (e.g. https://api.genegenie.tech). The browser then calls the API
//   DIRECTLY, which avoids Vercel serverless limits (the ~4.5 MB request-body cap
//   and function timeouts) on VCF uploads, and keeps traffic encrypted.
// - Locally (unset), calls fall through to the same-origin Next.js /api proxy
//   routes, so `npm run dev` keeps working without any extra config.
const BASE = process.env.NEXT_PUBLIC_ANNOTATION_API_BASE;

export function apiUrl(path: string): string {
  return BASE ? `${BASE}${path}` : `/api${path}`;
}
