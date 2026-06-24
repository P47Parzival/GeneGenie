import { NextResponse } from 'next/server';

// Server-side proxy for gene knowledge-graph lookups -> annotation backend.
const API_BASE = process.env.ANNOTATION_API_BASE ?? 'http://3.6.214.176:8000';

export async function GET(_request: Request, { params }: { params: Promise<{ symbol: string }> }) {
  const { symbol } = await params;
  try {
    const upstream = await fetch(`${API_BASE}/gene/${encodeURIComponent(symbol)}`, { cache: 'no-store' });
    const data = await upstream.json();
    return NextResponse.json(data, { status: upstream.status });
  } catch {
    return NextResponse.json(
      { detail: 'Annotation service unreachable. Is the API up and port 8000 open?' },
      { status: 502 },
    );
  }
}
