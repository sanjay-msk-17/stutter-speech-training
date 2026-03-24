import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { Toaster } from 'react-hot-toast';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'StutterAI — Speech Detection & Training',
  description: 'AI-powered stutter detection, analysis, and speech therapy training platform',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.className} bg-gray-950 text-white min-h-screen`}>
        <Toaster
          position="top-right"
          toastOptions={{
            style: { background: '#1e1b4b', color: '#fff', border: '1px solid #4f46e5' },
          }}
        />
        {children}
      </body>
    </html>
  );
}
