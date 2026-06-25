import { proxyUpload } from '../_proxyUpload';

export const runtime = 'nodejs';

export async function POST(request: Request) {
  return proxyUpload(request, '/pgx');
}
