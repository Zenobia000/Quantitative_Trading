/*
 * Wall Street operations console IA.
 * 真相源：dev_docs/product_repositioning/17_frontend_information_architecture.md
 * + 18_refactor_wbs.md §7。七層產品子系統是一等導航；舊 Live OOS/Deployment
 * 併入 Governance，不再保護舊研究後台 IA。
 */
export interface NavItem {
  /** i18n key，對應 nav namespace（如 'item.strategies' 或 HOME 的 'home'） */
  key: string
  to: string
  /** 對應 page 規格檔（dev_docs/web_design/pages/）供建頁參照 */
  spec: string
}
export interface NavZone {
  zone: 'data' | 'research' | 'governance' | 'trading' | 'risk' | 'operations' | 'system'
  items: NavItem[]
}

export const HOME: NavItem = { key: 'home', to: '/', spec: 'command_center' }

export const NAV: NavZone[] = [
  {
    zone: 'data',
    items: [{ key: 'item.data', to: '/system/data', spec: 'system_data' }],
  },
  {
    zone: 'research',
    items: [
      { key: 'item.strategies', to: '/research/strategies', spec: 'research_01_strategy_library' },
      { key: 'item.runsNew', to: '/research/runs/new', spec: 'research_02_run_new' },
      { key: 'item.runs', to: '/research/runs', spec: 'research_03_runs_table' },
      { key: 'item.compare', to: '/research/compare', spec: 'research_05_compare' },
      { key: 'item.sweep', to: '/research/sweep', spec: 'research_06_sweep' },
    ],
  },
  {
    zone: 'governance',
    items: [
      { key: 'item.candidates', to: '/research/candidates', spec: 'research_candidate_pool' },
      { key: 'item.liveOosQueue', to: '/live-oos/queue', spec: 'live_oos_queue' },
      { key: 'item.watch', to: '/live-oos/watch', spec: 'monitor_watch' },
      { key: 'item.strictGate', to: '/deploy/gate', spec: 'research_07_validate_gate' },
    ],
  },
  {
    zone: 'trading',
    items: [
      { key: 'item.positions', to: '/monitor/positions', spec: 'monitor_b_positions' },
      { key: 'item.signals', to: '/monitor/signals', spec: 'monitor_c_signals' },
    ],
  },
  {
    zone: 'risk',
    items: [
      { key: 'item.risk', to: '/monitor/risk', spec: 'monitor_d_risk' },
    ],
  },
  {
    zone: 'operations',
    items: [
      { key: 'item.fleet', to: '/monitor', spec: 'monitor_fleet' },
      { key: 'item.board', to: '/monitor/board', spec: 'monitor_board' },
      { key: 'item.performance', to: '/monitor/performance', spec: 'monitor_a_performance' },
    ],
  },
  {
    zone: 'system',
    items: [{ key: 'item.alerts', to: '/system/alerts', spec: 'system_alerts' }],
  },
]
