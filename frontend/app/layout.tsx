import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "경제 브리핑",
  description: "경제 뉴스 자동 큐레이션 서비스",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <body className="bg-gray-50 text-gray-900 min-h-screen">
        <header className="bg-white border-b border-gray-200">
          <div className="max-w-3xl mx-auto px-4 py-4 flex items-center justify-between">
            <Link href="/" className="text-xl font-bold hover:text-blue-600 transition-colors">
              경제 브리핑
            </Link>
            <nav className="flex items-center gap-6 text-sm font-medium text-gray-600">
              <Link href="/" className="hover:text-gray-900 transition-colors">
                홈
              </Link>
              <Link href="/reports" className="hover:text-gray-900 transition-colors">
                리포트
              </Link>
              <Link href="/unsubscribe" className="hover:text-gray-900 transition-colors">
                구독 해지
              </Link>
            </nav>
          </div>
        </header>
        <main className="max-w-3xl mx-auto px-4 py-8">{children}</main>
      </body>
    </html>
  );
}
