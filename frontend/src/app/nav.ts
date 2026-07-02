/*
 * 三區 IA sidebar 導覽配置（真相源 dev_docs/web_design/03 §4.7 / §5.2）。
 * 順序：Research（主軸）→ Monitor（live 子視圖）→ System。首頁為 root。
 */
export interface NavItem {
  label: string
  to: string
  /** 對應 page 規格檔（dev_docs/web_design/pages/）供建頁參照 */
  spec: string
}
export interface NavZone {
  zone: 'research' | 'monitor' | 'system'
  label: string
  items: NavItem[]
}

export const HOME: NavItem = { label: '首頁', to: '/', spec: 'home_overview' }

export const NAV: NavZone[] = [
  {
    zone: 'research',
    label: 'RESEARCH',
    items: [
      { label: '策略庫', to: '/research/strategies', spec: 'research_01_strategy_library' },
      { label: 'New Run', to: '/research/runs/new', spec: 'research_02_run_new' },
      { label: 'Runs', to: '/research/runs', spec: 'research_03_runs_table' },
      { label: 'Compare', to: '/research/compare', spec: 'research_05_compare' },
      { label: 'Sweep', to: '/research/sweep', spec: 'research_06_sweep' },
      { label: 'Validate', to: '/research/validate', spec: 'research_07_validate_gate' },
    ],
  },
  {
    zone: 'monitor',
    label: 'MONITOR',
    items: [
      { label: '艦隊總控', to: '/monitor', spec: 'monitor_fleet' },
      { label: '觀察艙', to: '/monitor/watch', spec: 'monitor_watch' },
      { label: '績效總覽', to: '/monitor/performance', spec: 'monitor_a_performance' },
      { label: '部位狀態', to: '/monitor/positions', spec: 'monitor_b_positions' },
      { label: '訊號日誌', to: '/monitor/signals', spec: 'monitor_c_signals' },
      { label: '風控指標', to: '/monitor/risk', spec: 'monitor_d_risk' },
    ],
  },
  {
    zone: 'system',
    label: 'SYSTEM',
    items: [
      { label: '資料管理', to: '/system/data', spec: 'system_data' },
      { label: '告警設定', to: '/system/alerts', spec: 'system_alerts' },
    ],
  },
]
