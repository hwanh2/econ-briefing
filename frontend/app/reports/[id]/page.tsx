import Link from "next/link";
import { notFound } from "next/navigation";
import SendEmailButton from "../../components/SendEmailButton";

interface Article {
  title: string;
  url: string;
  source: string;
  published?: string;
  title_ko?: string;
}

interface ReportDetail {
  id: number;
  date: string;
  title: string;
  content_md: string;
  content_html: string;
  articles: Article[];
}

async function getReport(id: string): Promise<ReportDetail | null> {
  try {
    const res = await fetch(`http://backend:8000/api/reports/${id}`, {
      cache: "no-store",
    });
    if (res.status === 404) return null;
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export default async function ReportDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const report = await getReport(id);

  if (!report) notFound();

  return (
    <div>
      <Link
        href="/reports"
        className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-6 transition-colors"
      >
        ← 리포트 목록
      </Link>

      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <h2 className="text-2xl font-bold mb-1">{report.title}</h2>
          <p className="text-sm text-gray-500">{report.date}</p>
        </div>
        <SendEmailButton reportId={report.id} />
      </div>

      {report.content_html ? (
        <div
          className="prose prose-gray max-w-none bg-white rounded-xl border border-gray-200 p-6 mb-8"
          dangerouslySetInnerHTML={{ __html: report.content_html }}
        />
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-8 whitespace-pre-wrap text-sm text-gray-800">
          {report.content_md}
        </div>
      )}

      {report.articles && report.articles.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold mb-3">참고 기사</h3>
          <ul className="space-y-2">
            {report.articles.map((article, i) => (
              <li
                key={i}
                className="bg-white rounded-lg border border-gray-200 px-4 py-3 flex items-start justify-between gap-4"
              >
                <div>
                  <a
                    href={article.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm font-medium text-blue-600 hover:underline"
                  >
                    {article.title_ko || article.title}
                  </a>
                  {article.title_ko && (
                    <p className="text-xs text-gray-500 mt-0.5">{article.title}</p>
                  )}
                </div>
                <span className="text-xs text-gray-400 shrink-0 mt-0.5">{article.source}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
