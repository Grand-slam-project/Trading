import { useEffect, useState } from 'react'
import { fetchNewsArticles } from '../lib/supabaseClient.js'
import { WATCHLIST_MOCK, WATCH_CHARTS_MOCK } from '../dashboardConstants.js'
import { MiniSparkline, Rate, SectionHeader } from '../components/DashboardComponents.jsx'
import { formatNewsDate, getWatchlistNewsMarket, mergeLatestNews } from '../dashboardUtils.js'

export default function WatchlistTab() {
  const [selectedId, setSelectedId] = useState(WATCHLIST_MOCK[0]?.id || '')
  const [newsItems, setNewsItems] = useState([])
  const [newsLoading, setNewsLoading] = useState(false)
  const [newsError, setNewsError] = useState('')
  const selectedItem = WATCHLIST_MOCK.find((item) => item.id === selectedId) || WATCHLIST_MOCK[0]
  const useSlider = WATCHLIST_MOCK.length >= 5

  useEffect(() => {
    if (!selectedItem) return

    let isMounted = true
    const queries = [selectedItem.id, selectedItem.name].filter(Boolean)
    const uniqueQueries = [...new Set(queries)]

    async function loadWatchlistNews() {
      setNewsLoading(true)
      setNewsError('')

      try {
        const results = await Promise.all(
          uniqueQueries.map((query) =>
            fetchNewsArticles({
              market: getWatchlistNewsMarket(selectedItem),
              query,
              limit: 4,
              offset: 0,
            }),
          ),
        )

        if (!isMounted) return
        setNewsItems(mergeLatestNews(results.flatMap((result) => result.items || [])))
      } catch (error) {
        if (!isMounted) return
        setNewsItems([])
        setNewsError(error.message || '뉴스를 불러오지 못했습니다.')
      } finally {
        if (isMounted) setNewsLoading(false)
      }
    }

    loadWatchlistNews()

    return () => {
      isMounted = false
    }
  }, [selectedItem])

  return (
    <main className="max-w-7xl mx-auto flex flex-col gap-6">
      <section className="bg-slate-surface border border-slate-700/80 rounded-lg p-5">
        <SectionHeader title="관심종목 명단" />
        <div className={useSlider ? 'flex snap-x gap-2 overflow-x-auto pb-2' : 'grid gap-2 md:grid-cols-2 xl:grid-cols-4'}>
          {WATCHLIST_MOCK.map((item) => (
            <button
              key={item.id}
              className={`${useSlider ? 'min-w-60 snap-start' : 'w-full'} rounded-lg px-4 py-3 text-left transition ${selectedItem?.id === item.id ? 'bg-institutional-blue text-white' : 'bg-[#0f172a] text-slate-300 hover:bg-white/5'
                }`}
              type="button"
              onClick={() => setSelectedId(item.id)}
            >
              <span className="block font-bold">{item.name}</span>
              <span className="mt-1 block text-xs opacity-70 font-mono">{item.market} · {item.account}</span>
            </button>
          ))}
        </div>
      </section>

      <section className="bg-slate-surface border border-slate-700/80 rounded-lg p-5">
        <SectionHeader title="관심 종목의 차트" action={selectedItem?.id} />
        <div className="rounded-lg border border-slate-800 bg-[#0f172a]/70 p-4">
          <MiniSparkline values={WATCH_CHARTS_MOCK[selectedItem?.id]} />
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-5">
          {[
            ['종목명', selectedItem?.name],
            ['계좌종류', selectedItem?.account],
            ['수량', selectedItem?.quantity],
            ['평균 단가', selectedItem?.average],
            ['등락율', selectedItem?.change],
          ].map(([label, value]) => (
            <div key={label} className="rounded-lg bg-[#0f172a] p-4">
              <p className="text-xs font-bold text-slate-500">{label}</p>
              <p className="mt-2 font-bold text-white font-mono">{label === '등락율' ? <Rate value={value} /> : value}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="bg-slate-surface border border-slate-700/80 rounded-lg p-5">
        <SectionHeader title="관심종목 관련 최근 뉴스피드" />
        <div className="grid gap-3 lg:grid-cols-2">
          {newsLoading && newsItems.length === 0 ? (
            <div className="rounded-lg border border-slate-800 bg-[#0f172a] p-4 text-sm text-slate-400 lg:col-span-2">
              최신 뉴스피드를 불러오는 중입니다...
            </div>
          ) : null}

          {newsError ? (
            <div className="rounded-lg border border-red-800 bg-red-950/30 p-4 text-sm text-red-300 lg:col-span-2">
              {newsError}
            </div>
          ) : null}

          {!newsLoading && newsItems.length === 0 && !newsError ? (
            <div className="rounded-lg border border-slate-800 bg-[#0f172a] p-4 text-sm text-slate-400 lg:col-span-2">
              선택한 관심종목과 연결된 최신 뉴스가 없습니다.
            </div>
          ) : null}

          {newsItems.map((news, index) => (
            <article key={news.id || news.url || `${news.title}-${index}`} className="rounded-lg border border-slate-800 bg-[#0f172a] p-4">
              <div className="flex items-center justify-between gap-3 text-xs text-slate-500">
                <span className="font-bold text-ai-cyan">{news.source}</span>
                <span className="font-mono">{formatNewsDate(news.published_at)}</span>
              </div>
              <h3 className="mt-3 text-sm font-bold leading-6 text-white">{news.title}</h3>
              <p className="mt-2 text-sm leading-6 text-slate-400">{news.summary}</p>
              <a className="mt-4 inline-flex rounded-lg bg-ai-cyan px-4 py-2 text-sm font-bold text-[#07111f] transition hover:bg-ai-cyan/80" href={news.url || '#'} rel="noreferrer" target="_blank">
                원문 열기
              </a>
            </article>
          ))}
        </div>
      </section>
    </main>
  )
}
