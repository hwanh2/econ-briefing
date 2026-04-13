"use client";

import { useState } from "react";

const SECTORS: Record<string, string> = {
  macro: "매크로",
  finance: "금융",
  tech: "테크",
  ai: "AI",
  energy: "에너지",
  realestate: "부동산",
  politics: "정치",
  startup: "스타트업",
};

export default function Home() {
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [sectors, setSectors] = useState<string[]>([]);
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [errorMsg, setErrorMsg] = useState("");

  function toggleSector(key: string) {
    setSectors((prev) =>
      prev.includes(key) ? prev.filter((s) => s !== key) : [...prev, key]
    );
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setStatus("loading");
    setErrorMsg("");

    try {
      const res = await fetch("/api/subscribers", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, name, sectors }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data?.detail || `오류가 발생했습니다 (${res.status})`);
      }

      setStatus("success");
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "알 수 없는 오류");
      setStatus("error");
    }
  }

  if (status === "success") {
    return (
      <div className="text-center py-16">
        <div className="text-5xl mb-4">✅</div>
        <h2 className="text-2xl font-bold mb-2">구독 완료!</h2>
        <p className="text-gray-600">
          <span className="font-medium">{email}</span>으로 경제 브리핑을 보내드립니다.
        </p>
      </div>
    );
  }

  return (
    <div>
      <h2 className="text-2xl font-bold mb-2">경제 브리핑 구독</h2>
      <p className="text-gray-600 mb-8">
        매일 아침 경제 뉴스를 큐레이션해서 이메일로 보내드립니다.
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

        <div>
          <label className="block text-sm font-medium mb-1" htmlFor="name">
            이름
          </label>
          <input
            id="name"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="홍길동"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div>
          <p className="block text-sm font-medium mb-2">관심 섹터</p>
          <div className="flex flex-wrap gap-2">
            {Object.entries(SECTORS).map(([key, label]) => (
              <label
                key={key}
                className={`flex items-center gap-1.5 cursor-pointer px-3 py-1.5 rounded-full border text-sm transition-colors ${
                  sectors.includes(key)
                    ? "bg-blue-600 border-blue-600 text-white"
                    : "border-gray-300 text-gray-700 hover:border-gray-400"
                }`}
              >
                <input
                  type="checkbox"
                  className="sr-only"
                  checked={sectors.includes(key)}
                  onChange={() => toggleSector(key)}
                />
                {label}
              </label>
            ))}
          </div>
        </div>

        {status === "error" && (
          <p className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">{errorMsg}</p>
        )}

        <button
          type="submit"
          disabled={status === "loading"}
          className="w-full bg-blue-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-blue-700 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
        >
          {status === "loading" ? "처리 중..." : "구독하기"}
        </button>
      </form>
    </div>
  );
}
