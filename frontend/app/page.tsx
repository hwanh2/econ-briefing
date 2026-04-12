export default function Home() {
  return (
    <div>
      <h2 className="text-2xl font-bold mb-2">경제 브리핑 구독</h2>
      <p className="text-gray-600 mb-8">
        매일 아침 경제 뉴스를 큐레이션해서 이메일로 보내드립니다.
      </p>

      {/* Subscribe form placeholder */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1" htmlFor="email">
            이메일
          </label>
          <input
            id="email"
            type="email"
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
            placeholder="홍길동"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <p className="block text-sm font-medium mb-2">관심 섹터</p>
          <div className="flex flex-wrap gap-2">
            {["거시경제", "기술", "에너지", "금융", "부동산"].map((sector) => (
              <label key={sector} className="flex items-center gap-1 cursor-pointer">
                <input type="checkbox" className="rounded" />
                <span className="text-sm">{sector}</span>
              </label>
            ))}
          </div>
        </div>
        <button className="w-full bg-blue-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-blue-700 transition-colors">
          구독하기
        </button>
      </div>
    </div>
  );
}
