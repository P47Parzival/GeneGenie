import { NextResponse } from 'next/server';

const API_BASE = process.env.ANNOTATION_API_BASE ?? 'http://3.6.214.176:8000';

// Stream a multipart upload straight through to the backend without buffering the
// whole file in the Next server (critical for large VCFs). `duplex: 'half'` is
// required by Node's fetch when sending a streaming request body.
export async function proxyUpload(request: Request, path: string): Promise<Response> {
  const contentType = request.headers.get('content-type') ?? '';
  if (!contentType.includes('multipart/form-data')) {
    return NextResponse.json({ detail: 'Expected multipart form upload' }, { status: 400 });
  }
  try {
    const upstream = await fetch(`${API_BASE}${path}`, {
      method: 'POST',
      body: request.body,
      headers: { 'content-type': contentType },
      cache: 'no-store',
      // @ts-expect-error duplex is required for streaming bodies but missing from lib types
      duplex: 'half',
    });
    const data = await upstream.json();
    return NextResponse.json(data, { status: upstream.status });
  } catch {
    return NextResponse.json(
      {
        detail:
          'Upload failed before completing — for large genomes upload a bgzipped .vcf.gz, ' +
          'or confirm the API is up and port 8000 is open.',
      },
      { status: 502 },
    );
  }
}
