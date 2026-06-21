import { NextResponse } from 'next/server';

// Server-side proxy to the annotation backend. Keeps the API base URL off the
// client and sidesteps CORS — the browser only ever talks to this Next route.
const API_BASE = process.env.ANNOTATION_API_BASE ?? 'http://3.6.214.176:8000';

export async function POST(request: Request) {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ detail: 'Invalid JSON body' }, { status: 400 });
  }

  try {
    const upstream = await fetch(`${API_BASE}/annotate/variant`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      cache: 'no-store',
    });
    const data = await upstream.json();
    return NextResponse.json(data, { status: upstream.status });
  } catch {
    return NextResponse.json(
      { detail: 'Annotation service unreachable. Is the API up and port 8000 open?' },
      { status: 502 },
    );
  }
}
