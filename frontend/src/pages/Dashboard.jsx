import React from "react";

// 설정한 함수는 나중에 꼭 수정 필요!!
const sidebarTabs = ["대시보드", "관심종목", "내 자산", "거래 내역", "설정"];

const assetTrend = [68, 72, 70, 78, 76, 84, 88, 91, 86, 94, 101, 108];

const dashboardData = {
  user: {
    accountLabel: "내 계좌",
    investmentProfile: "균형 성장형",
    investmentProfileDescription: "국내 대형주 중심에 해외 성장주를 일부 섞는 패턴입니다.",
  },
  summaryCards: [
    { id: "total", label: "총 자산", value: "5,109,700원", rate: "+4.82%" },
    { id: "domestic", label: "국내 주식", value: "2,569,000원", rate: "+5.01%" },
    { id: "overseas", label: "해외 주식", value: "1,353,800원", rate: "+2.57%" },
  ],
  totalAsset: {
    value: "5,109,700원",
    periodLabel: "지난 30일 기준",
    change: "+235,400원",
  },
};

const watchlist = [
  { id: "005930", name: "삼성전자", market: "국내 주식", account: "KIS 모의", quantity: "18주", average: "72,400원", change: "+2.14%" },
  { id: "000660", name: "SK하이닉스", market: "국내 주식", account: "KIS 모의", quantity: "6주", average: "182,000원", change: "+7.82%" },
  { id: "NVDA", name: "NVIDIA", market: "해외 주식", account: "해외 위탁", quantity: "4주", average: "$126.40", change: "+4.31%" },
  { id: "TSLA", name: "Tesla", market: "해외 주식", account: "해외 위탁", quantity: "3주", average: "$188.20", change: "-1.26%" },
];

const holdings = [
  { id: "holding-005930", name: "삼성전자", account: "국내 주식", quantity: "18주", average: "72,400원", value: "1,341,000원", returnRate: "+2.14%", weight: 26 },
  { id: "holding-000660", name: "SK하이닉스", account: "국내 주식", quantity: "6주", average: "182,000원", value: "1,228,000원", returnRate: "+7.82%", weight: 24 },
  { id: "holding-NVDA", name: "NVIDIA", account: "해외 주식", quantity: "4주", average: "$126.40", value: "732,500원", returnRate: "+4.31%", weight: 14 },
  { id: "holding-TSLA", name: "Tesla", account: "해외 주식", quantity: "3주", average: "$188.20", value: "621,300원", returnRate: "-1.26%", weight: 12 },
  { id: "cash", name: "예수금", account: "현금", quantity: "-", average: "-", value: "1,186,900원", returnRate: "0.00%", weight: 24 },
];

const allocation = [
  { id: "domestic", label: "국내 주식", value: 50, color: "bg-primary" },
  { id: "overseas", label: "해외 주식", value: 26, color: "bg-cyan" },
  { id: "cash", label: "현금", value: 24, color: "bg-slate-500" },
];

function Rate({ value }) {
  const isPositive = value.startsWith("+");
  const isFlat = value.startsWith("0");

  return (
    <span className={`number font-semibold ${isFlat ? "text-slate-400" : isPositive ? "text-gain" : "text-loss"}`}>
      {value}
    </span>
  );
}

function Sparkline() {
  const points = assetTrend
    .map((value, index) => `${(index / (assetTrend.length - 1)) * 100},${110 - value}`)
    .join(" ");

  return (
    <svg className="h-48 w-full" viewBox="0 0 100 56" preserveAspectRatio="none" role="img" aria-label="총 자산 가치 그래프">
      <defs>
        <linearGradient id="assetFill2" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor="#00e0ff" stopOpacity="0.28" />
          <stop offset="100%" stopColor="#00e0ff" stopOpacity="0" />
        </linearGradient>
      </defs>
      <polyline points={`0,56 ${points} 100,56`} fill="url(#assetFill2)" stroke="none" />
      <polyline points={points} fill="none" stroke="#00e0ff" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function SectionHeader({ eyebrow, title, action }) {
  return (
    <div className="mb-4 flex items-start justify-between gap-3">
      <div>
        {eyebrow ? <p className="text-xs font-bold uppercase tracking-[0.16em] text-cyan">{eyebrow}</p> : null}
        <h2 className="mt-1 text-lg font-bold text-white">{title}</h2>
      </div>
      {action ? (
        <button className="rounded-lg border border-line px-3 py-2 text-xs font-bold text-slate-300 transition hover:border-primary hover:text-white" type="button">
          {action}
        </button>
      ) : null}
    </div>
  );
}

function DashBoard() {
  const { summaryCards, totalAsset, user } = dashboardData;

  return (
    <main className="min-h-screen bg-obsidian text-slate-200">
      <div className="grid min-h-screen grid-cols-1 lg:grid-cols-[248px_minmax(0,1fr)]">
        <aside className="border-b border-line bg-[#0f172a] lg:border-b-0 lg:border-r">
          <div className="sticky top-0 flex gap-3 overflow-x-auto p-4 lg:h-screen lg:flex-col lg:overflow-visible lg:p-5">
            <div className="hidden pb-5 lg:block">
              <div className="flex items-center gap-3">
                <span className="grid size-10 place-items-center rounded-lg bg-primary text-lg font-extrabold text-white">T</span>
                <div>
                  <p className="text-sm font-extrabold text-white">Trading AI</p>
                  <p className="text-xs text-slate-500">My Page 2</p>
                </div>
              </div>
            </div>

            {sidebarTabs.map((tab, index) => (
              <button
                key={tab}
                className={`shrink-0 rounded-lg px-4 py-3 text-left text-sm font-bold transition ${
                  index === 0
                    ? "bg-primary text-white shadow-[0_10px_24px_rgba(0,71,187,0.25)]"
                    : "text-slate-400 hover:bg-white/5 hover:text-white"
                }`}
                type="button"
              >
                {tab}
              </button>
            ))}

            <div className="mt-auto hidden rounded-lg border border-cyan/20 bg-white/[0.04] p-4 lg:block">
              <p className="text-xs font-bold text-cyan">AI Layer</p>
              <p className="mt-2 text-sm leading-6 text-slate-300">매매 제안은 사용자 승인 전까지 실행되지 않습니다.</p>
            </div>
          </div>
        </aside>

        <section className="min-w-0 p-4 md:p-6 xl:p-8">
          <header className="mb-5 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="text-sm font-semibold text-slate-400">{user.accountLabel}</p>
              <h1 className="mt-1 text-2xl font-extrabold text-white md:text-3xl">마이페이지 대시보드</h1>
            </div>
            <div className="flex flex-wrap gap-2">
              {["전체", "국내 주식", "해외 주식"].map((item, index) => (
                <button
                  key={item}
                  className={`rounded-lg px-4 py-2 text-sm font-bold ${
                    index === 0 ? "bg-white text-[#0f172a]" : "border border-line text-slate-300"
                  }`}
                  type="button"
                >
                  {item}
                </button>
              ))}
            </div>
          </header>

          <section className="grid gap-3 md:grid-cols-3">
            {summaryCards.map((card) => (
              <article key={card.id} className="panel rounded-lg p-4">
                <p className="text-sm font-bold text-slate-400">{card.label}</p>
                <p className="number mt-3 text-2xl font-extrabold text-white">{card.value}</p>
                <p className="mt-2 text-sm"><Rate value={card.rate} /></p>
              </article>
            ))}
          </section>

          <section className="mt-3 grid gap-3 xl:grid-cols-[minmax(0,1.45fr)_minmax(340px,0.55fr)]">
            <article className="panel rounded-lg p-5">
              <SectionHeader eyebrow="Portfolio" title="총 자산 가치 그래프" action="기간 변경" />
              <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
                <div>
                  <p className="number text-4xl font-extrabold text-white">{totalAsset.value}</p>
                  <p className="mt-2 text-sm text-slate-400">{totalAsset.periodLabel} <Rate value={totalAsset.change} /></p>
                </div>
                <div className="flex gap-2 text-xs font-bold text-slate-400">
                  {["1주", "1개월", "3개월", "1년"].map((item, index) => (
                    <button key={item} className={`rounded-md px-3 py-2 ${index === 1 ? "bg-cyan/10 text-cyan" : "bg-[#0f172a]"}`} type="button">
                      {item}
                    </button>
                  ))}
                </div>
              </div>
              <div className="mt-4 rounded-lg border border-line bg-[#0f172a] p-4">
                <Sparkline />
              </div>
            </article>

            <article className="glass rounded-lg p-5">
              <SectionHeader eyebrow="AI Profile" title="유저의 투자 성향" />
              <div className="rounded-lg border border-cyan/20 bg-[#0f172a]/70 p-4">
                <p className="text-xl font-extrabold text-white">
                  당신은 <span className="text-cyan">{user.investmentProfile}</span> 성향입니다.
                </p>
                <p className="mt-2 text-sm leading-6 text-slate-300">{user.investmentProfileDescription}</p>
              </div>
            </article>
          </section>

          <section className="mt-3 grid gap-3 xl:grid-cols-[minmax(0,1fr)_420px]">
            <article className="panel overflow-hidden rounded-lg">
              <div className="p-5 pb-2">
                <SectionHeader title="관심 종목 명단" action="관심종목 관리" />
              </div>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[760px] border-collapse text-sm">
                  <thead className="border-y border-line bg-[#0f172a] text-xs text-slate-400">
                    <tr>
                      {["종목명", "시장", "계좌 종류", "수량", "평균 단가", "등락율"].map((head) => (
                        <th key={head} className="px-5 py-3 text-left font-bold">{head}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {watchlist.map((item) => (
                      <tr key={item.id} className="border-b border-line/80 last:border-b-0">
                        <td className="px-5 py-4 font-bold text-white">{item.name}</td>
                        <td className="px-5 py-4 text-slate-300">{item.market}</td>
                        <td className="px-5 py-4 text-slate-300">{item.account}</td>
                        <td className="number px-5 py-4">{item.quantity}</td>
                        <td className="number px-5 py-4">{item.average}</td>
                        <td className="px-5 py-4"><Rate value={item.change} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </article>

            <article className="panel rounded-lg p-5">
              <SectionHeader title="자산 배분 상태" />
              <div className="flex h-4 overflow-hidden rounded-full bg-[#0f172a]">
                {allocation.map((item) => (
                  <span key={item.id} className={item.color} style={{ width: `${item.value}%` }} />
                ))}
              </div>
              <div className="mt-5 space-y-3">
                {allocation.map((item) => (
                  <div key={item.id} className="flex items-center justify-between rounded-lg bg-[#0f172a] px-3 py-3">
                    <span className="flex items-center gap-2 text-sm font-bold">
                      <span className={`size-2 rounded-full ${item.color}`} />
                      {item.label}
                    </span>
                    <span className="number text-slate-300">{item.value}%</span>
                  </div>
                ))}
              </div>
            </article>
          </section>

          <section className="mt-3">
            <article className="panel overflow-hidden rounded-lg">
              <div className="p-5 pb-2">
                <SectionHeader title="보유 재산 현황" action="내 자산 보기" />
              </div>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[920px] border-collapse text-sm">
                  <thead className="border-y border-line bg-[#0f172a] text-xs text-slate-400">
                    <tr>
                      {["종목명", "계좌종류", "수량", "평균단가", "평가금액", "수익률", "비중"].map((head) => (
                        <th key={head} className="px-5 py-3 text-left font-bold">{head}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {holdings.map((item) => (
                      <tr key={item.id} className="border-b border-line/80 last:border-b-0">
                        <td className="px-5 py-4 font-bold text-white">{item.name}</td>
                        <td className="px-5 py-4 text-slate-300">{item.account}</td>
                        <td className="number px-5 py-4">{item.quantity}</td>
                        <td className="number px-5 py-4">{item.average}</td>
                        <td className="number px-5 py-4 font-bold text-white">{item.value}</td>
                        <td className="px-5 py-4"><Rate value={item.returnRate} /></td>
                        <td className="px-5 py-4">
                          <div className="flex items-center gap-3">
                            <div className="h-2 w-24 rounded-full bg-[#0f172a]">
                              <div className="h-2 rounded-full bg-primary" style={{ width: `${item.weight}%` }} />
                            </div>
                            <span className="number text-xs text-slate-400">{item.weight}%</span>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </article>
          </section>
        </section>
      </div>
    </main>
  );
}

export default DashBoard;
