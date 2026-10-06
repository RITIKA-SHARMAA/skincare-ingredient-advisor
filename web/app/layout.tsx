import type { Metadata } from 'next';
import Link from 'next/link';

import './globals.css';

export const metadata: Metadata = {
  title: 'Skincare Ingredient Advisor',
  description:
    'Paste a skincare ingredient list for plain-language explanations, irritant flags and routine conflict checks.',
};

const NAV = [
  { href: '/analyse', label: 'Analyse' },
  { href: '/products', label: 'Catalogue' },
  { href: '/routine', label: 'My routine' },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <a href="#main" className="skip-link">
          Skip to content
        </a>
        <header className="border-b bg-white">
          <nav
            className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-3 p-4"
            aria-label="Primary"
          >
            <Link className="focus-ring font-bold text-teal-800" href="/">
              Skincare Ingredient Advisor
            </Link>
            <ul className="flex gap-4 text-sm">
              {NAV.map((item) => (
                <li key={item.href}>
                  <Link className="focus-ring" href={item.href}>
                    {item.label}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
        </header>
        <main id="main" className="mx-auto max-w-5xl p-4 sm:p-8">
          {children}
        </main>
        <footer className="border-t bg-white p-5 text-center text-xs text-stone-600">
          Illustrative ingredient data and conflict rules. Not medical or dermatological advice.
        </footer>
      </body>
    </html>
  );
}
