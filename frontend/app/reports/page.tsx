import Link from "next/link";

interface ReportSummary {
  id: number;
  date: string;
  title: string;
  created_at: string;
}

async function getReports(): Promise<ReportSummary[]> {
  try {
    const res = await fetch("http://backend:8000/api/reports", {
      cache: "no-store",
    });
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

export default async function ReportsPage() {
  const reports = await getReports();

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">리포트</h2>

      {reports.length === 0 ? (
        <div className="text-center py-16 text-gray-500">
          <p className="text-lg">아직 리포트가 없습니다</p>
          <p className="text-sm mt-2">파이프라인을 실행하면 리포트가 생성됩니다.</p>
        </div>
      ) : (
        <ul className="space-y-3">
          {reports.map((report) => (
            <li key={report.id}>
              <Link
                href={`/reports/${report.id}`}
                className="block bg-white rounded-xl border border-gray-200 p-5 hover:border-blue-300 hover:shadow-sm transition-all"
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="font-semibold text-gray-900">{report.title}</p>
                    <p className="text-sm text-gray-500 mt-1">{report.date}</p>
                  </div>
                  <span className="text-gray-400 text-sm shrink-0 mt-0.5">→</span>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
