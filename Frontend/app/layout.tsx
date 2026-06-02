import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import Navbar from './components/Navbar';

const inter = Inter({
  subsets: ['latin'],
  display: 'swap',
});

export const metadata: Metadata = {
  title: {
    default: 'GeneGenie | AI Gene Editing Platform',
    template: '%s | GeneGenie',
  },
  description:
    'GeneGenie is an enterprise AI platform for gene editor design, sequence intelligence, and biological workflow orchestration.',
  metadataBase: new URL('https://genegenie.ai'),
  openGraph: {
    title: 'GeneGenie',
    description: 'AI-native gene editing infrastructure for research and translational teams.',
    type: 'website',
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={inter.className}>
      <body>
        <div className="pointer-events-none fixed inset-0 bg-data-grid bg-[length:44px_44px] opacity-35" />
        <div className="relative mx-auto flex min-h-screen w-full max-w-7xl flex-col px-4 py-4 sm:px-6 lg:px-8">
          <Navbar />
          {children}
        </div>
      </body>
    </html>
  );
}
