"use client";

import { useState } from "react";

interface Subscriber {
  id: number;
  email: string;
  name?: string;
}

type Status = "idle" | "loading" | "success" | "error" | "not_found";

export default function UnsubscribePage() {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [errorMsg, setErrorMsg] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setStatus("loading");
    setErrorMsg("");

    try {
      const res = await fetch("/api/subscribers");
      if (!res.ok) throw new Error("구독자 정보를 불러오지 못했습니다.");

      const subscribers: Subscriber[] = await res.json();
      const match = subscribers.find(
        (s) => s.email.toLowerCase() === email.toLowerCase()
      );

      if (!match) {
        setStatus("not_found");
        return;
      }

      const delRes = await fetch(`/api/subscribers/${match.id}`, {
        method: "DELETE",
      });

      if (!delRes.ok) throw new Error(`삭제 중 오류가 발생했습니다 (${delRes.status})`);

      setStatus("success");
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "알 수 없는 오류");
      setStatus("error");
    }
  }

  if (status === "success") {
    return (
      <div className="text-center py-16">
        <div className="text-5xl mb-4">👋</div>
        <h2 className="text-2xl font-bold mb-2">구독이 해지되었습니다</h2>
        <p className="text-gray-600">
          <span className="font-medium">{email}</span>의 구독을 해지했습니다.
        </p>
      </div>
    );
  }

  return (
    <div>
      <h2 className="text-2xl font-bold mb-2">구독 해지</h2>
      <p className="text-gray-600 mb-8">
        이메일 주소를 입력하면 구독을 해지합니다.
      </p>

      <form
        onSubmit={handleSubmit}
        className="bg-white rounded-xl border border-gray-200 p-6 space-y-4"
      >
        <div>
          <label className="block text-sm font-medium mb-1" htmlFor="email">
            이메일
          </label>
          <input
            id="email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="your@email.com"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {status === "not_found" && (
          <p className="text-sm text-yellow-700 bg-yellow-50 rounded-lg px-3 py-2">
            해당 이메일로 등록된 구독자를 찾을 수 없습니다.
          </p>
        )}

        {status === "error" && (
          <p className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">{errorMsg}</p>
        )}

        <button
          type="submit"
          disabled={status === "loading"}
          className="w-full bg-gray-800 text-white rounded-lg py-2 text-sm font-medium hover:bg-gray-900 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
        >
          {status === "loading" ? "처리 중..." : "구독 해지하기"}
        </button>
      </form>
    </div>
  );
}
