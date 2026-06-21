import { NextResponse } from 'next/server';

// Server-side proxy for VCF file uploads -> annotation backend.
const API_BASE = process.env.ANNOTATION_API_BASE ?? 'http://43.204.32.86:8000';

export async function POST(request: Request) {
  let form: FormData;
  try {
    form = await request.formData();
  } catch {
    return NextResponse.json({ detail: 'Expected multipart form upload' }, { status: 400 });
  }

  const file = form.get('file');
  if (!file) {
    return NextResponse.json({ detail: 'No file provided' }, { status: 400 });
  }

  try {
    const upstream = await fetch(`${API_BASE}/annotate`, {
      method: 'POST',
      body: form,
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
