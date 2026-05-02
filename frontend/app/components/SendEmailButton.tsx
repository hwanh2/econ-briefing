"use client";

import { useState } from "react";

interface SendResult {
  sent?: number;
  failed?: number;
  skipped?: number;
  reason?: string;
}

export default function SendEmailButton({ reportId }: { reportId: number }) {
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">(
    "idle"
  );
  const [result, setResult] = useState<SendResult | null>(null);

  async function handleSend() {
    setStatus("loading");
    setResult(null);

    try {
      const res = await fetch(`/api/reports/${reportId}/send`, {
        method: "POST",
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "발송 요청 실패");
      }
      const data: SendResult = await res.json();
      setResult(data);
      setStatus("success");
    } catch (err) {
      setStatus("error");
      setResult({ reason: err instanceof Error ? err.message : "알 수 없는 오류" });
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <button
        onClick={handleSend}
        disabled={status === "loading"}
        className="inline-flex items-center gap-2 bg-green-600 text-white rounded-lg px-4 py-2 text-sm font-medium hover:bg-green-700 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
      >
        {status === "loading" ? (
          <>
            <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            발송 중...
          </>
        ) : (
          <>📧 이메일 발송</>
        )}
      </button>

      {status === "success" && result && (
        <p className="text-sm text-green-700 bg-green-50 rounded-lg px-3 py-2">
          성공 {result.sent}건 / 실패 {result.failed}건 / 스킵 {result.skipped ?? 0}건
          {result.reason && result.reason !== "no_api_key" && (
            <span className="block text-xs text-green-600 mt-0.5">{result.reason}</span>
          )}
        </p>
      )}

      {status === "error" && result?.reason && (
        <p className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">
          {result.reason}
        </p>
      )}
    </div>
  );
}
