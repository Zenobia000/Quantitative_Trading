/*
 * 三區 IA sidebar 導覽配置（真相源 dev_docs/web_design/03 §4.7 / §5.2）。
 * 順序：Research（主軸）→ Monitor（live 子視圖）→ System。首頁為 root。
 * label 已 i18n 化：item 存 `nav` namespace 的 key（見 i18n/resources 各語言 nav.json），
 * 由 AppShell / CommandPalette 以 t() 渲染；zone 顯示由 zone id 推導（t nav:zone.id）。
 */
export interface NavItem {
  /** i18n key，對應 nav namespace（如 'item.strategies' 或 HOME 的 'home'） */
  key: string
  to: string
  /** 對應 page 規格檔（dev_docs/web_design/pages/）供建頁參照 */
  spec: string
}
export interface NavZone {
  zone: 'research' | 'monitor' | 'system'
  items: NavItem[]
}

export const HOME: NavItem = { key: 'home', to: '/', spec: 'home_overview' }

export const NAV: NavZone[] = [
  {
    zone: 'research',
    items: [
      { key: 'item.strategies', to: '/research/strategies', spec: 'research_01_strategy_library' },
      { key: 'item.runsNew', to: '/research/runs/new', spec: 'research_02_run_new' },
      { key: 'item.runs', to: '/research/runs', spec: 'research_03_runs_table' },
      { key: 'item.compare', to: '/research/compare', spec: 'research_05_compare' },
      { key: 'item.sweep', to: '/research/sweep', spec: 'research_06_sweep' },
      { key: 'item.validate', to: '/research/validate', spec: 'research_07_validate_gate' },
    ],
  },
  {
    zone: 'monitor',
    items: [
      { key: 'item.fleet', to: '/monitor', spec: 'monitor_fleet' },
      { key: 'item.board', to: '/monitor/board', spec: 'monitor_board' },
      { key: 'item.watch', to: '/monitor/watch', spec: 'monitor_watch' },
      { key: 'item.performance', to: '/monitor/performance', spec: 'monitor_a_performance' },
      { key: 'item.positions', to: '/monitor/positions', spec: 'monitor_b_positions' },
      { key: 'item.signals', to: '/monitor/signals', spec: 'monitor_c_signals' },
      { key: 'item.risk', to: '/monitor/risk', spec: 'monitor_d_risk' },
    ],
  },
  {
    zone: 'system',
    items: [
      { key: 'item.data', to: '/system/data', spec: 'system_data' },
      { key: 'item.alerts', to: '/system/alerts', spec: 'system_alerts' },
    ],
  },
]
