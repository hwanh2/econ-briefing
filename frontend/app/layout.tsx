import type { Metadata } from "next";
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
          <div className="max-w-3xl mx-auto px-4 py-4">
            <h1 className="text-xl font-bold">경제 브리핑</h1>
          </div>
        </header>
        <main className="max-w-3xl mx-auto px-4 py-8">{children}</main>
      </body>
    </html>
  );
}
