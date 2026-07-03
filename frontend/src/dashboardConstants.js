export const DASHBOARD_TABS = [
  { key: 'dashboard', label: '대시보드', enabled: true },
  { key: 'inquiry', label: '문의하기', enabled: true, route: '/inquiry', authOnly: true },
  { key: 'watchlist', label: '관심종목', enabled: true },
  { key: 'assets', label: '내 자산', enabled: true },
  { key: 'history', label: '거래 내역', enabled: true },
  { key: 'settings', label: '설정', enabled: true },
  { key: 'admin', label: '관리자', enabled: true },
]
