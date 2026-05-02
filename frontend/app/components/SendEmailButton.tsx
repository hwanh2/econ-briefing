"use client";

import { useState } from "react";
import Link from "next/link";

interface PipelineResult {
  date?: string;
  raw_count?: number;
  curated_count?: number;
  translated_count?: number;
  report_id?: number;
  publish?: {
    sent?: number;
    failed?: number;
    skipped?: number;
    reason?: string;
  };
  error?: string;
  timings?: Record<string, number>;
}

export default function SendEmailButton() {
  const [status, setStatus] = useState<
    "idle" | "loading" | "success" | "error"
  >("idle");
  const [result, setResult] = useState<PipelineResult | null>(null);

  async function handleRun() {
    setStatus("loading");
    setResult(null);

    try {
      const res = await fetch("/api/pipeline/run-sync", {
        method: "POST",
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "파이프라인 실행 실패");
      }
      const data: PipelineResult = await res.json();
      setResult(data);
      setStatus("success");
    } catch (err) {
      setStatus("error");
      setResult({
        error: err instanceof Error ? err.message : "알 수 없는 오류",
      });
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <button
        onClick={handleRun}
        disabled={status === "loading"}
        className="inline-flex items-center gap-2 bg-green-600 text-white rounded-lg px-4 py-2 text-sm font-medium hover:bg-green-700 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
      >
        {status === "loading" ? (
          <>
            <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            파이프라인 실행 중...
          </>
        ) : (
          <>
            🚀 파이프라인 실행 + 이메일 발송
          </>
        )}
      </button>

      {status === "success" && result && (
        <div className="text-sm text-green-700 bg-green-50 rounded-lg px-3 py-2 space-y-1">
          <p className="font-medium">
            ✓ 파이프라인 완료 ({result.date})
          </p>
          {result.raw_count !== undefined && (
            <p className="text-xs text-green-600">
              수집 {result.raw_count}건 → 선별 {result.curated_count}건 → 번역 {result.translated_count}건
            </p>
          )}
          {result.report_id && (
            <p className="text-xs">
              <Link
                href={`/reports/${result.report_id}`}
                className="underline hover:text-green-800"
              >
                리포트 #{result.report_id} 보기
              </Link>
            </p>
          )}
          {result.publish && (
            <p className="text-xs text-green-600">
              이메일: 성공 {result.publish.sent ?? 0}건 / 실패 {result.publish.failed ?? 0}건 / 스킵 {result.publish.skipped ?? 0}건
              {result.publish.reason && result.publish.reason !== "no_api_key" && (
                <span className="block">사유: {result.publish.reason}</span>
              )}
            </p>
          )}
          {result.error && (
            <p className="text-xs text-red-600">오류: {result.error}</p>
          )}
        </div>
      )}

      {status === "error" && result?.error && (
        <p className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">
          {result.error}
        </p>
      )}
    </div>
  );
}
